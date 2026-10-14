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
    if coin.startswith("#"):
        return "outcome"  # HIP-4 outcome market: shares settle at 0 or 1, no candles or funding
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


def load_twap_fills(path: str) -> list:
    """TWAP slice fills come from a separate endpoint and are *not* in
    userFills (they carry a zero hash); tag them with their twapId."""
    return [{**r["fill"], "twapId": r.get("twapId")} for r in _gz(path)]


def merge_twap(fills: pd.DataFrame, twap: list) -> pd.DataFrame:
    if not twap:
        return fills
    tw = pd.DataFrame(twap)
    if len(fills):
        tw = tw[~tw["tid"].isin(fills["tid"])]
    if tw.empty:
        return fills
    for c in ["px", "sz", "startPosition", "closedPnl", "fee"]:
        tw[c] = tw[c].astype(float)
    tw["t"] = pd.to_datetime(tw["time"], unit="ms")
    tw["q"] = np.where(tw["side"] == "B", 1.0, -1.0) * tw["sz"]
    tw["endPosition"] = tw["startPosition"] + tw["q"]
    tw["ntl"] = tw["px"] * tw["sz"]
    tw["kind"] = tw["coin"].map(market_kind)
    out = pd.concat([fills, tw], ignore_index=True)
    # stable sort keeps the API order of fills that share a timestamp
    return out.sort_values("time", kind="mergesort").reset_index(drop=True)


def position_gaps(fills: pd.DataFrame, min_gap_s: float = 1.0) -> pd.DataFrame:
    """Jumps in the startPosition chain between fills more than `min_gap_s`
    apart: size that changed without a fill we can see (TWAP slices older than
    the endpoint keeps, or other missing executions). When this is non-empty
    the exact PnL from fills is not exact."""
    rows = []
    for coin, g in fills[fills["kind"].isin(("perp", "hip3"))].groupby("coin"):
        g = g.sort_values("time", kind="mergesort")
        t = g["time"].values
        cut = np.r_[np.where(np.diff(t) > min_gap_s * 1000)[0], len(g) - 1]
        # position at the end of each burst of fills / at the start of the next
        start = g["startPosition"].values
        q = g["q"].values
        b0 = 0
        ends, starts, times = [], [], []
        for b1 in cut:
            seg_s = start[b0:b1 + 1]
            seg_e = seg_s + q[b0:b1 + 1]
            first = [x for x in np.round(seg_s, 8) if x not in set(np.round(seg_e, 8))]
            last = [x for x in np.round(seg_e, 8) if x not in set(np.round(seg_s, 8))]
            starts.append(first[0] if first else seg_s[0])
            ends.append(last[0] if last else seg_e[-1])
            times.append((t[b0], t[b1]))
            b0 = b1 + 1
        for i in range(1, len(starts)):
            jump = starts[i] - ends[i - 1]
            if abs(jump) > 1e-6 * max(1.0, abs(ends[i - 1])):
                rows.append({"coin": coin, "after": pd.to_datetime(times[i - 1][1], unit="ms"),
                             "before": pd.to_datetime(times[i][0], unit="ms"), "jump": jump,
                             "jump_ntl": abs(jump) * float(g["px"].iloc[0])})
    return pd.DataFrame(rows, columns=["coin", "after", "before", "jump", "jump_ntl"])


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
            if d.get("user", "").lower() == user and d.get("destination", "").lower() == user:
                usd = 0.0  # move between the wallet's own perp/spot/HIP-3 balances, not an inflow
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
        self.fills = merge_twap(load_fills(os.path.join(self.dir, "fills.json.gz")),
                                load_twap_fills(os.path.join(self.dir, "twap_fills.json.gz")))
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
    e = funding.groupby(["day", "coin"])["expo"].sum().unstack().fillna(0.0)
    if len(e):  # days with no funding row were flat: keep them as zeros, not gaps
        e = e.reindex(pd.date_range(e.index.min(), e.index.max(), freq="D", name="day"), fill_value=0.0)
    return e


def approx_price_pnl(expo: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame) -> pd.DataFrame:
    """Daily price PnL ~= average exposure x (close - open). Ignores intraday
    timing, so it under-states active day trading but is close for swing books."""
    move = (closes - opens).reindex(expo.index)
    return (expo * move.reindex(columns=expo.columns)).fillna(0.0)


def exact_mtm(fills: pd.DataFrame, closes: pd.DataFrame, end=None) -> pd.DataFrame:
    """Exact daily mark-to-market price PnL per coin from fills (UTC closes):
    carry of the start-of-day position plus each fill marked to the close."""
    f = fills[fills["kind"].isin(("perp", "hip3"))].copy()
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
    eq = eq[~eq.index.duplicated(keep="last")]
    eq = eq.reindex(ntl.index.union(eq.index)).ffill().reindex(ntl.index)
    out = pd.DataFrame({"gross": ntl.abs().sum(axis=1), "net": ntl.sum(axis=1), "perp_equity": eq})
    out["leverage"] = out["gross"] / out["perp_equity"].where(out["perp_equity"] > 0)
    return out, ntl


def flows(ledger: pd.DataFrame) -> pd.DataFrame:
    keep = ["deposit", "withdraw", "send", "spotTransfer", "internalTransfer", "vaultDeposit", "vaultWithdraw"]
    L = ledger[ledger["type"].isin(keep)]
    return L.groupby("type")["usd"].agg(["count", "sum"]).sort_values("sum")


def liquidation_events(fills: pd.DataFrame, user: str | None = None) -> pd.DataFrame:
    """Fills where the wallet itself was liquidated or auto-deleveraged. Newer
    fills carry a `liquidation` dict instead of a special `dir`; when it names
    another liquidatedUser the wallet was only the counterparty."""
    m = fills["dir"].str.contains("Liquidat|Deleverag", regex=True, na=False)
    if user is not None and "liquidation" in fills:
        own = fills["liquidation"].map(
            lambda d: isinstance(d, dict) and str(d.get("liquidatedUser", "")).lower() == user.lower())
        m = m | own
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
        pf = w.fills[w.fills["kind"].isin(("perp", "hip3"))]
        if len(pf):
            cl = w.closes(sorted(pf["coin"].unique()))
            mtm = exact_mtm(pf, cl).sum().abs()
            score = pd.concat([score, mtm], axis=1).max(axis=1)
    return list(score.sort_values(ascending=False).index[:top])


# ------------------------------------------------ cross-coin episode metrics
def daily_perp_pnl(w: "Wallet") -> pd.DataFrame:
    """Exact daily perp PnL from fills: price (marked to UTC closes) + funding
    - fees. Only meaningful when the fills cover the whole history (check
    against the portfolio's perp PnL)."""
    pf = w.fills[w.fills["kind"].isin(("perp", "hip3"))]
    if pf.empty:
        return pd.DataFrame(columns=["price", "funding", "fees", "pnl"])
    cl = w.closes(sorted(pf["coin"].unique()))
    price = exact_mtm(pf, cl, end=cl.index.max()).sum(axis=1)
    fund = w.funding.groupby("day")["usdc"].sum() if len(w.funding) else pd.Series(dtype=float)
    fees = pf.groupby(pf["t"].dt.floor("D"))["fee"].sum()
    idx = price.index.union(fund.index).union(fees.index)
    out = pd.DataFrame({"price": price.reindex(idx).fillna(0.0), "funding": fund.reindex(idx).fillna(0.0),
                        "fees": -fees.reindex(idx).fillna(0.0)})
    out["pnl"] = out.sum(axis=1)
    return out


def episode_metrics(w: "Wallet", ex: pd.DataFrame, min_ntl: float = 50_000, coins=None) -> pd.DataFrame:
    """One row per position episode (flat to flat) with at least `min_ntl` of
    peak notional, across every perp coin: what the market looked like before
    the first order (returns, distance from the 30-day high/low, funding rate),
    how the position was built (average entry vs. first fill), how far the
    price went against it (adverse excursion, worst unrealised PnL on hourly
    marks), how much of the move was captured and what came after the exit."""
    from .market import funding_df, hourly_close

    pe = ex[ex["kind"].isin(("perp", "hip3"))]
    coins = coins or list(pe["coin"].unique())
    rows = []
    for coin in coins:
        ep = episodes(ex, coin)
        if ep.empty:
            continue
        ep = ep[ep["max_ntl"] >= min_ntl]
        if ep.empty:
            continue
        h = hourly_close(coin, w.data_dir)
        fr = funding_df(coin, w.data_dir)
        fc = w.fills[w.fills["coin"] == coin]
        for _, e in ep.iterrows():
            sel = pe[(pe["coin"] == coin) & (pe["t"] >= e["start"]) & (pe["t"] <= e["end"])]
            p0, t0 = float(sel["vwap"].iloc[0]), sel["t"].iloc[0]
            sgn = -1.0 if e["side"] == "short" else 1.0
            r = {"coin": coin, "side": e["side"], "start": t0, "end": e["end"], "days": e["days"], "open": e["open"],
                 "orders": e["n_orders"], "max_ntl": e["max_ntl"], "first_px": p0, "entry_vwap": e["entry_vwap"],
                 "exit_vwap": e["exit_vwap"], "realized": e["realized"]}
            if len(h):
                hh = h.loc[: t0.floor("h") - pd.Timedelta(hours=1)].dropna()
                for k, n in {"r24h": 24, "r7d": 168, "r30d": 720}.items():
                    r[k] = (hh.iloc[-1] / hh.iloc[-1 - n] - 1) * 100 if len(hh) > n else np.nan
                win = hh.iloc[-720:]
                r["vs_30d_high"] = (hh.iloc[-1] / win.max() - 1) * 100 if len(win) else np.nan
                r["vs_30d_low"] = (hh.iloc[-1] / win.min() - 1) * 100 if len(win) else np.nan
                during = h.loc[t0.floor("h"): e["end"].ceil("h")].dropna()
                if len(during):
                    worst = during.max() if sgn < 0 else during.min()
                    r["adverse_pct"] = (worst / p0 - 1) * 100 * -sgn
                    # worst unrealised PnL: hourly position x (price - average entry)
                    fe = fc[(fc["t"] >= e["start"]) & (fc["t"] <= e["end"])]
                    ae = avg_entry_path(fe, coin).set_index("t")
                    pos_h = ae["pos"].groupby(level=0).last().resample("h").last().reindex(during.index).ffill()
                    avg_h = ae["avg_entry"].groupby(level=0).last().resample("h").last().reindex(during.index).ffill()
                    upnl = (pos_h * (during - avg_h)).dropna()
                    if len(upnl):
                        r["worst_upnl"], r["worst_upnl_t"] = float(upnl.min()), upnl.idxmin()
                after = h.loc[e["end"].ceil("h"): e["end"] + pd.Timedelta(days=30)].dropna()
                if len(after) and not e["open"]:
                    best = after.min() if sgn < 0 else after.max()
                    r["next30d_more_pct"] = (best / e["exit_vwap"] - 1) * 100 * sgn
            if len(fr):
                pre = fr.loc[t0 - pd.Timedelta(hours=24): t0, "fundingRate"]
                r["funding_ann_pre"] = pre.mean() * 24 * 365 * 100 if len(pre) else np.nan
            fz = w.funding[(w.funding["coin"] == coin) & (w.funding["t"] >= e["start"].floor("D")) &
                           (w.funding["t"] <= e["end"] + pd.Timedelta(days=1))]["usdc"].sum() if len(w.funding) else 0.0
            r["funding"] = float(fz)
            rows.append(r)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values("start").reset_index(drop=True)
        side = np.where(out["side"] == "short", 1.0, -1.0)
        out["scale_in_pct"] = (out["entry_vwap"] / out["first_px"] - 1) * 100 * side
        out["captured_pct"] = (1 - out["exit_vwap"] / out["entry_vwap"]) * 100 * side
    return out


def flow_behaviour(ledger: pd.DataFrame, daily_pnl: pd.Series, gross: pd.Series | None = None,
                   lookback: int = 3) -> dict:
    """How deposits and withdrawals relate to recent PnL (topping up margin
    after losses / sweeping profits after gains) and to changes in exposure
    (funding new positions)."""
    fl = ledger[ledger["type"].isin(["deposit", "withdraw", "send"])].copy()
    if fl.empty or daily_pnl.empty:
        return {}
    fl["day"] = fl["t"].dt.floor("D")
    flow = fl.groupby("day")["usd"].sum()
    idx = daily_pnl.index.union(flow.index)
    pnl = daily_pnl.reindex(idx).fillna(0.0)
    flow = flow.reindex(idx).fillna(0.0)
    prev = pnl.rolling(lookback, min_periods=1).sum().shift(1)  # PnL of the days *before* the flow
    dep, wd = flow > 0, flow < 0
    out = {
        "deposits_usd": float(fl.loc[fl["usd"] > 0, "usd"].sum()), "withdrawals_usd": float(fl.loc[fl["usd"] < 0, "usd"].sum()),
        "deposit_days": int(dep.sum()), "withdraw_days": int(wd.sum()),
        "deposit_after_loss_share": float((prev[dep] < 0).mean()) if dep.any() else np.nan,
        "withdraw_after_gain_share": float((prev[wd] > 0).mean()) if wd.any() else np.nan,
        "all_days_after_loss_share": float((prev < 0).mean()),
        "median_prev_pnl_deposit": float(prev[dep].median()) if dep.any() else np.nan,
        "median_prev_pnl_withdraw": float(prev[wd].median()) if wd.any() else np.nan,
        "corr_flow_prev_pnl": float(flow.corr(prev)),
    }
    if gross is not None and len(gross):
        g = gross.reindex(idx).ffill().fillna(0.0)
        out["corr_flow_exposure_change"] = float(flow.corr(g.diff()))
    return out
