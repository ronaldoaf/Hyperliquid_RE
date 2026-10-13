"""Turn raw Info API dumps into analysable tables.

Everything here is pure pandas on top of the files written by
`hlre.collect` and `hlre.market`; nothing hits the network.
"""
from __future__ import annotations

import gzip
import json
import os

import numpy as np
import pandas as pd

from .market import candles_df

EPS = 1e-9


def _gz(path: str) -> list:
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt") as f:
        return json.load(f)


def market_kind(coin: str) -> str:
    if coin.startswith("@") or "/" in coin:
        return "spot"
    if ":" in coin:
        return "hip3"  # builder-deployed perp dex (e.g. xyz:CL)
    return "perp"


# --------------------------------------------------------------------- loaders
def load_fills(path: str) -> pd.DataFrame:
    df = pd.DataFrame(_gz(path))
    if df.empty:
        return df
    for c in ["px", "sz", "startPosition", "closedPnl", "fee"]:
        df[c] = df[c].astype(float)
    df["t"] = pd.to_datetime(df["time"], unit="ms")
    df["q"] = np.where(df["side"] == "B", 1.0, -1.0) * df["sz"]
    df["endPosition"] = df["startPosition"] + df["q"]
    df["ntl"] = df["px"] * df["sz"]
    df["kind"] = df["coin"].map(market_kind)
    # stored order (API order, stable on time) keeps startPosition chains intact
    return df.reset_index(drop=True)


def load_funding(path: str) -> pd.DataFrame:
    rows = [{"time": r["time"], **r["delta"]} for r in _gz(path)]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ["usdc", "szi", "fundingRate"]:
        df[c] = df[c].astype(float)
    # Older history is pre-aggregated per UTC day: szi/fundingRate are averages
    # over `nSamples` hourly payments. Recent rows are hourly (no nSamples).
    df["nSamples"] = pd.to_numeric(df.get("nSamples"), errors="coerce").fillna(1.0)
    df["t"] = pd.to_datetime(df["time"], unit="ms")
    df["day"] = df["t"].dt.floor("D")
    df["expo"] = df["szi"] * df["nSamples"] / 24.0  # coin-days of exposure
    return df


def load_ledger(path: str, user: str) -> pd.DataFrame:
    user = user.lower()
    rows = []
    for r in _gz(path):
        d = r["delta"]
        t = d["type"]
        usd = 0.0
        if t == "deposit":
            usd = float(d["usdc"])
        elif t == "withdraw":
            usd = -float(d["usdc"])
        elif t in ("send", "spotTransfer", "internalTransfer"):
            v = float(d.get("usdcValue") or d.get("usdc") or 0.0)
            usd = v if d.get("destination", "").lower() == user else -v
        elif t == "vaultDeposit":
            usd = -float(d["usdc"])
        elif t == "vaultWithdraw":
            usd = float(d.get("netWithdrawnUsd") or 0.0)
        rows.append({
            "time": r["time"], "t": pd.to_datetime(r["time"], unit="ms"), "type": t,
            "token": d.get("token", "USDC" if "usdc" in d else None),
            "amount": float(d.get("amount") or d.get("usdc") or 0.0),
            "usd": usd,
            "counterparty": (d.get("destination") if d.get("user", "").lower() == user else d.get("user")) if "destination" in d else d.get("vault"),
            "raw": d,
        })
    return pd.DataFrame(rows)


def load_orders(path: str) -> pd.DataFrame:
    rows = [{**r["order"], "status": r["status"], "statusTimestamp": r["statusTimestamp"]} for r in _gz(path)]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ["limitPx", "sz", "origSz", "triggerPx"]:
        df[c] = df[c].astype(float)
    df["t"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def portfolio_frame(snapshot: dict, key: str = "allTime") -> pd.DataFrame:
    P = dict(snapshot["portfolio"])
    av = pd.DataFrame(P[key]["accountValueHistory"], columns=["time", "account_value"])
    pn = pd.DataFrame(P[key]["pnlHistory"], columns=["time", "pnl"])
    df = av.merge(pn, on="time", how="outer").sort_values("time")
    df[["account_value", "pnl"]] = df[["account_value", "pnl"]].astype(float)
    df["t"] = pd.to_datetime(df["time"], unit="ms")
    return df.set_index("t")[["account_value", "pnl"]]


class Wallet:
    def __init__(self, user: str, data_dir: str = "data"):
        self.user = user.lower()
        self.data_dir = data_dir
        self.dir = os.path.join(data_dir, self.user)
        with open(os.path.join(self.dir, "snapshot.json")) as f:
            self.snapshot = json.load(f)
        self.fills = load_fills(os.path.join(self.dir, "fills.json.gz"))
        self.funding = load_funding(os.path.join(self.dir, "funding.json.gz"))
        self.ledger = load_ledger(os.path.join(self.dir, "ledger.json.gz"), self.user)
        self.orders = load_orders(os.path.join(self.dir, "orders.json.gz"))

    def portfolio(self, key: str = "allTime") -> pd.DataFrame:
        return portfolio_frame(self.snapshot, key)

    def closes(self, coins, interval: str = "1d") -> pd.DataFrame:
        return pd.DataFrame({c: candles_df(c, interval, self.data_dir)["close"] for c in coins})

    def opens(self, coins, interval: str = "1d") -> pd.DataFrame:
        return pd.DataFrame({c: candles_df(c, interval, self.data_dir)["open"] for c in coins})


# ------------------------------------------------------------------ executions
def executions(fills: pd.DataFrame) -> pd.DataFrame:
    """One row per order (fills grouped by coin+oid), with the position effect.

    action: open (from flat), add, reduce, close (to flat), flip (crosses 0).
    """
    g = fills.groupby(["coin", "oid"], sort=False)
    ex = g.agg(
        t=("t", "first"), t_last=("t", "last"), time=("time", "first"), side=("side", "first"),
        sz=("sz", "sum"), q=("q", "sum"), ntl=("ntl", "sum"), n_fills=("sz", "size"),
        start_pos=("startPosition", "first"), end_pos=("endPosition", "last"),
        closed_pnl=("closedPnl", "sum"), fee=("fee", "sum"), taker=("crossed", "mean"),
        kind=("kind", "first"), dir=("dir", "first"), px_first=("px", "first"), px_last=("px", "last"),
    ).reset_index()
    ex["vwap"] = ex["ntl"] / ex["sz"]
    s0, s1 = ex["start_pos"], ex["end_pos"]
    flat0, flat1 = s0.abs() < EPS, s1.abs() < EPS
    flip = (np.sign(s0) * np.sign(s1) < 0)
    grow = s1.abs() > s0.abs() + EPS
    ex["action"] = np.select(
        [flat0, flat1, flip, grow],
        ["open", "close", "flip", "add"],
        default="reduce",
    )
    # direction of the exposure the order works on (+1 long / -1 short)
    ex["book"] = np.where(flat0 | grow | flip, np.sign(s1), np.sign(s0))
    ex["slippage_bps"] = np.where(ex["side"] == "B", 1, -1) * (ex["px_last"] / ex["px_first"] - 1) * 1e4
    return ex.sort_values("time").reset_index(drop=True)


def position_path(fills: pd.DataFrame, coin: str) -> pd.Series:
    f = fills[fills["coin"] == coin]
    return pd.Series(f["endPosition"].values, index=f["t"]).groupby(level=0).last()


def avg_entry_path(fills: pd.DataFrame, coin: str) -> pd.DataFrame:
    """Walk the fills of one coin tracking the average entry price of the open
    position; `avg_before` is the average entry just before each fill."""
    f = fills[fills["coin"] == coin]
    pos, avg = (float(f["startPosition"].iloc[0]) if len(f) else 0.0), np.nan
    out = []
    for t, q, px, oid in zip(f["t"], f["q"], f["px"], f["oid"]):
        before = avg if abs(pos) > EPS else np.nan
        if abs(pos) < EPS or np.isnan(avg):
            avg = px
        new = pos + q
        if abs(pos) > EPS and abs(new) > EPS and np.sign(new) != np.sign(pos):
            avg = px  # flipped: the remainder opened at this price
        elif abs(new) > abs(pos):
            avg = (avg * abs(pos) + px * abs(q)) / abs(new)
        pos = new
        out.append((t, oid, pos, before, avg if abs(pos) > EPS else np.nan))
    return pd.DataFrame(out, columns=["t", "oid", "pos", "avg_before", "avg_entry"])


def episodes(ex: pd.DataFrame, coin: str, min_abs: float = EPS) -> pd.DataFrame:
    """Split a coin's executions into flat-to-flat episodes (a flip ends one
    episode and starts the next)."""
    e = ex[ex["coin"] == coin].reset_index(drop=True)
    eps_rows, cur = [], None
    for _, r in e.iterrows():
        if cur is None:
            cur = {"coin": coin, "start": r["t"], "side": np.sign(r["end_pos"]) or np.sign(r["q"]),
                   "rows": []}
        cur["rows"].append(r)
        ended = abs(r["end_pos"]) < min_abs or r["action"] == "flip"
        if ended:
            eps_rows.append(cur)
            cur = None
            if r["action"] == "flip":
                cur = {"coin": coin, "start": r["t"], "side": np.sign(r["end_pos"]), "rows": [r]}
    if cur is not None:
        eps_rows.append(cur)
    out = []
    for k, c in enumerate(eps_rows):
        rows = pd.DataFrame(c["rows"])
        side = c["side"]
        inc = rows[(rows["action"].isin(["open", "add"])) | ((rows["action"] == "flip") & (np.sign(rows["end_pos"]) == side))]
        dec = rows[rows["action"].isin(["reduce", "close"]) | ((rows["action"] == "flip") & (np.sign(rows["start_pos"]) == side))]
        max_abs = max(rows["start_pos"].abs().max(), rows["end_pos"].abs().max())
        open_at_end = abs(rows["end_pos"].iloc[-1]) > min_abs and rows["action"].iloc[-1] != "flip"
        out.append({
            "coin": coin, "episode": k, "side": "long" if side > 0 else "short",
            "start": c["start"], "end": rows["t"].iloc[-1], "open": open_at_end,
            "n_orders": len(rows), "n_increase": len(inc), "n_decrease": len(dec),
            "max_size": max_abs, "max_ntl": float((rows[["start_pos", "end_pos"]].abs().max(axis=1) * rows["vwap"]).max()),
            "entry_vwap": float((inc["vwap"] * inc["sz"]).sum() / inc["sz"].sum()) if len(inc) else np.nan,
            "exit_vwap": float((dec["vwap"] * dec["sz"]).sum() / dec["sz"].sum()) if len(dec) else np.nan,
            "realized": float(rows["closed_pnl"].sum()), "fees": float(rows["fee"].sum()),
        })
    df = pd.DataFrame(out)
    if len(df):
        df["days"] = (df["end"] - df["start"]).dt.total_seconds() / 86400
    return df


# ------------------------------------------------------------------- PnL views
def daily_exposure(funding: pd.DataFrame) -> pd.DataFrame:
    """Average daily position (coin units) per coin, from the funding ledger.

    Funding is paid hourly on every open perp position, so its `szi` field is
    an hourly position snapshot covering the whole account history, even the
    periods where fills are no longer served by the API.
    """
    return funding.groupby(["day", "coin"])["expo"].sum().unstack().fillna(0.0)


def approx_price_pnl(expo: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame) -> pd.DataFrame:
    """Daily price PnL ~= average exposure x (close - open). Ignores intraday
    timing, so it under-states active day trading but is close for swing books."""
    move = (closes - opens).reindex(expo.index)
    return (expo * move.reindex(columns=expo.columns)).fillna(0.0)


def exact_mtm(fills: pd.DataFrame, closes: pd.DataFrame, end=None) -> pd.DataFrame:
    """Exact daily mark-to-market price PnL per coin from fills (UTC closes):
    carry of the start-of-day position plus each fill marked to the close."""
    f = fills[fills["kind"] != "spot"].copy()
    f["day"] = f["t"].dt.floor("D")
    end = pd.Timestamp(end) if end is not None else f["day"].max()
    out = {}
    for coin, g in f.groupby("coin"):
        if coin not in closes:
            continue
        days = pd.date_range(g["day"].min(), end, freq="D")
        close = closes[coin].reindex(days).ffill()
        pos0 = g["startPosition"].iloc[0]
        eod = g.groupby("day")["q"].sum().reindex(days).fillna(0.0).cumsum() + pos0
        sod = eod.shift(1).fillna(pos0)
        trade = (g["q"] * (close.reindex(g["day"]).values - g["px"])).groupby(g["day"]).sum()
        carry = (sod * close.diff()).fillna(0.0)
        out[coin] = carry + trade.reindex(days).fillna(0.0)
    return pd.DataFrame(out).fillna(0.0)


def funding_by_coin(funding: pd.DataFrame) -> pd.Series:
    return funding.groupby("coin")["usdc"].sum().sort_values()


# --------------------------------------------------------- behaviour analytics
LOOKBACKS = {"r1h": 1, "r4h": 4, "r24h": 24, "r72h": 72, "r7d": 168}
FORWARD = {"f24h": 24, "f72h": 72, "f7d": 168}


def classify(ex: pd.DataFrame) -> pd.Series:
    """short+ / short- / long+ / long- / flip, from the order's position effect."""
    inc = ex["action"].isin(["open", "add"])
    dec = ex["action"].isin(["reduce", "close"])
    return pd.Series(np.select(
        [inc & (ex["book"] < 0), dec & (ex["book"] < 0), inc & (ex["book"] > 0), dec & (ex["book"] > 0)],
        ["short+", "short-", "long+", "long-"], default="flip"), index=ex.index)


def market_context(ex: pd.DataFrame, hourly: pd.Series) -> pd.DataFrame:
    """Attach the market state each order saw: % returns over the lookbacks
    ending at the last completed hour, position inside the 7-day range
    (0 = at the low, 1 = at the high) and forward returns afterwards."""
    e = ex.copy()
    h = e["t"].dt.floor("h")
    last = hourly.shift(1)  # close of the previous (completed) hour, indexed by hour start
    p0 = last.reindex(h).values
    for k, n in LOOKBACKS.items():
        e[k] = (p0 / hourly.shift(1 + n).reindex(h).values - 1) * 100
    for k, n in FORWARD.items():
        e[k] = (hourly.shift(1 - n).reindex(h).values / p0 - 1) * 100
    hi, lo = hourly.rolling(168).max().shift(1), hourly.rolling(168).min().shift(1)
    e["rng7d"] = ((last - lo) / (hi - lo)).reindex(h).values
    e["cls"] = classify(e)
    return e


def baseline_context(hourly: pd.Series, start, end) -> pd.DataFrame:
    b = pd.DataFrame(index=hourly.index)
    last = hourly.shift(1)
    for k, n in LOOKBACKS.items():
        b[k] = (last / hourly.shift(1 + n) - 1) * 100
    for k, n in FORWARD.items():
        b[k] = (hourly.shift(1 - n) / last - 1) * 100
    hi, lo = hourly.rolling(168).max().shift(1), hourly.rolling(168).min().shift(1)
    b["rng7d"] = (last - lo) / (hi - lo)
    return b.loc[start:end]


def averaging_stats(fills: pd.DataFrame, ex: pd.DataFrame, coin: str) -> dict:
    """How often the trader adds to a position that is underwater (short add
    above the average entry, long add below it) and how reductions pay off."""
    ae = avg_entry_path(fills, coin)
    first = ae.groupby("oid")["avg_before"].first()
    e = ex[ex["coin"] == coin].copy()
    e["avg_before"] = e["oid"].map(first)
    adds = e[e["action"] == "add"].copy()
    under = np.where(adds["book"] < 0, adds["vwap"] > adds["avg_before"], adds["vwap"] < adds["avg_before"])
    dist = (adds["vwap"] / adds["avg_before"] - 1) * 100 * np.where(adds["book"] < 0, 1, -1)
    red = e[e["action"].isin(["reduce", "close"])]
    win = red["closed_pnl"] > 0
    return {
        "adds": int(len(adds)),
        "adds_underwater_share": float(np.mean(under)) if len(adds) else np.nan,
        "adds_underwater_share_by_size": float((adds["sz"] * under).sum() / adds["sz"].sum()) if len(adds) else np.nan,
        "adds_median_dist_from_avg_pct": float(np.nanmedian(dist)) if len(adds) else np.nan,
        "reductions": int(len(red)),
        "reduction_win_rate": float(win.mean()) if len(red) else np.nan,
        "avg_win": float(red.loc[win, "closed_pnl"].mean()) if win.any() else np.nan,
        "avg_loss": float(red.loc[~win, "closed_pnl"].mean()) if (~win).any() else np.nan,
        "realized": float(red["closed_pnl"].sum()),
    }


def hold_decomposition(fills: pd.DataFrame, coin: str, closes: pd.Series, end=None) -> dict:
    """Split a coin's price PnL (exact, daily marks) into
    - carry: start-of-day position x daily move ("holding" PnL)
    - intraday: fills marked to that day's close ("trading" PnL)
    and the carry part into bias (average position x total move) and timing
    (deviation from the average position x move)."""
    f = fills[fills["coin"] == coin].copy()
    if f.empty:
        return {}
    f["day"] = f["t"].dt.floor("D")
    end = pd.Timestamp(end) if end is not None else closes.index.max()
    days = pd.date_range(f["day"].min(), end, freq="D")
    c = closes.reindex(days).ffill()
    pos0 = f["startPosition"].iloc[0]
    eod = f.groupby("day")["q"].sum().reindex(days).fillna(0.0).cumsum() + pos0
    sod = eod.shift(1).fillna(pos0)
    dp = c.diff().fillna(0.0)
    carry = sod * dp
    intraday = (f["q"] * (c.reindex(f["day"]).values - f["px"])).groupby(f["day"]).sum().reindex(days).fillna(0.0)
    m = sod.mean()
    return {
        "carry": float(carry.sum()), "intraday": float(intraday.sum()),
        "total": float(carry.sum() + intraday.sum()),
        "mean_pos": float(m), "total_move": float(dp.sum()),
        "bias": float(m * dp.sum()), "timing": float(((sod - m) * dp).sum()),
        "daily": pd.DataFrame({"carry": carry, "intraday": intraday, "sod": sod}),
    }


def copy_lag_pnl(fills: pd.DataFrame, coin: str, hourly: pd.Series, lags=(0, 1, 4, 12, 24, 72, 168)) -> pd.Series:
    """PnL of mirroring the wallet's position in `coin` with a delay of `lag`
    hours (hourly marks, no costs). Shows whether the edge survives the delay
    a follower inevitably has."""
    pp = position_path(fills, coin)
    if pp.empty:
        return pd.Series(dtype=float)
    pos_end_of_hour = pp.resample("h").last().ffill()
    idx = hourly.loc[pos_end_of_hour.index.min():].index
    pos = pos_end_of_hour.reindex(idx).ffill().fillna(0.0)
    nxt = hourly.reindex(idx).shift(-1) - hourly.reindex(idx)  # close(h+1) - close(h)
    return pd.Series({lag: float((pos.shift(lag).fillna(0.0) * nxt).sum()) for lag in lags})


def sessions(ex: pd.DataFrame, gap_minutes: float = 30) -> pd.DataFrame:
    e = ex.sort_values("t")
    new = e["t"].diff().dt.total_seconds().fillna(np.inf) > gap_minutes * 60
    sid = new.cumsum()
    return e.groupby(sid).agg(start=("t", "first"), end=("t", "last"), orders=("sz", "size"),
                              coins=("coin", "nunique"), ntl=("ntl", "sum"))


def leverage_frame(funding: pd.DataFrame, closes: pd.DataFrame, perp_equity: pd.Series) -> pd.DataFrame:
    expo = daily_exposure(funding)
    c = closes.reindex(expo.index.union(closes.index)).ffill().reindex(expo.index)
    ntl = (expo * c.reindex(columns=expo.columns)).fillna(0.0)
    eq = perp_equity.copy()
    eq.index = eq.index.floor("D")
    eq = eq[~eq.index.duplicated(keep="last")].reindex(ntl.index.union(eq.index)).ffill().reindex(ntl.index)
    out = pd.DataFrame({"gross": ntl.abs().sum(axis=1), "net": ntl.sum(axis=1), "perp_equity": eq})
    out["leverage"] = out["gross"] / out["perp_equity"].where(out["perp_equity"] > 0)
    return out, ntl


def flows(ledger: pd.DataFrame) -> pd.DataFrame:
    keep = ["deposit", "withdraw", "send", "spotTransfer", "internalTransfer", "vaultDeposit", "vaultWithdraw"]
    L = ledger[ledger["type"].isin(keep)]
    return L.groupby("type")["usd"].agg(["count", "sum"]).sort_values("sum")


def liquidation_events(fills: pd.DataFrame) -> pd.DataFrame:
    m = fills["dir"].str.contains("Liquidat|Deleverag", regex=True, na=False)
    return fills.loc[m, ["t", "coin", "dir", "side", "px", "sz", "startPosition", "closedPnl"]]


def session_context(ctx: pd.DataFrame, base: pd.DataFrame, gap_minutes: float = 30) -> pd.DataFrame:
    """Session-level version of `market_context` (orders < `gap_minutes` apart
    form one decision), with Mann-Whitney p-values against the baseline hours.
    Sessions are classified by their net effect on the short/long book."""
    from scipy.stats import mannwhitneyu

    e = ctx.sort_values("t").copy()
    e["sid"] = (e["t"].diff().dt.total_seconds().fillna(np.inf) > gap_minutes * 60).cumsum()
    e["dshort"] = np.where(e["book"] < 0, -e["q"], 0.0)
    e["dlong"] = np.where(e["book"] > 0, e["q"], 0.0)
    s = e.groupby("sid").agg(t=("t", "first"), dshort=("dshort", "sum"), dlong=("dlong", "sum"),
                             r24h=("r24h", "first"), r72h=("r72h", "first"), r7d=("r7d", "first"),
                             rng7d=("rng7d", "first"))
    unit = e["sz"].median() * 0.5
    s["kind"] = np.select([s["dshort"] > unit, s["dshort"] < -unit, s["dlong"] > unit, s["dlong"] < -unit],
                          ["short+", "short-", "long+", "long-"], default="other")
    rows = {}
    b = base.dropna(subset=["r72h", "rng7d"])
    for k in ["short+", "short-", "long+", "long-"]:
        g = s[s["kind"] == k]
        if len(g) < 3:
            continue
        row = {"sessões": len(g)}
        for col in ["r24h", "r72h", "r7d", "rng7d"]:
            x = g[col].dropna()
            p = mannwhitneyu(x, b[col].dropna(), alternative="two-sided").pvalue if len(x) >= 3 else np.nan
            row[col] = float(x.median())
            row[f"p_{col}"] = float(p)
        row["top30"] = float((g["rng7d"] > 0.7).mean())
        row["bottom30"] = float((g["rng7d"] < 0.3).mean())
        rows[k] = row
    out = pd.DataFrame(rows).T
    out.attrs["base_top30"] = float((b["rng7d"] > 0.7).mean())
    out.attrs["base_bottom30"] = float((b["rng7d"] < 0.3).mean())
    return out


def rank_coins(w: "Wallet", top: int = 3) -> list[str]:
    """Perp coins that matter most for the wallet's PnL: |approximate price PnL
    + funding| over the full history (needs daily candles on disk)."""
    expo = daily_exposure(w.funding) if len(w.funding) else pd.DataFrame()
    score = pd.Series(dtype=float)
    if len(expo):
        approx = approx_price_pnl(expo, w.opens(expo.columns), w.closes(expo.columns)).sum()
        fund = w.funding.groupby("coin")["usdc"].sum()
        score = approx.add(fund, fill_value=0.0).abs()
    if len(w.fills):
        pf = w.fills[w.fills["kind"] != "spot"]
        if len(pf):
            cl = w.closes(sorted(pf["coin"].unique()))
            mtm = exact_mtm(pf, cl).sum().abs()
            score = pd.concat([score, mtm], axis=1).max(axis=1)
    return list(score.sort_values(ascending=False).index[:top])
