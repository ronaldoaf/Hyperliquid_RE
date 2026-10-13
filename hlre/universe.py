"""Universe-wide tests: does a wallet's entry pattern carry an edge across
every Hyperliquid perp, or only in the coins the wallet happened to pick?

Usage:
    python -m hlre.universe fetch                       # daily candles for every perp (listed + delisted)
    python -m hlre.universe study --start 2024-12-16 --end 2026-10-12 \
        --funding-a POPCAT TRUMP ... --funding-b APT WIF ...

`study` writes reports/estudos/regras_short.md with three tests, all for a
*short* opened at the next daily open after the signal day:

A. event study over all alts: short after a pump, after a dump, or on a
   bounce inside a downtrend, against the baseline of shorting any alt on any
   day (the period may simply have been bad for alts);
B. funding buckets: forward returns by the level of the funding rate (longs
   paying shorts a lot = crowded longs), for two coin groups;
C. BTC/ETH "short below the moving average" rules over several years, to
   see whether a macro short is a rule or a discretionary regime call.

The rules are fixed (no parameter search) and every mean comes
with a 95% interval from a bootstrap that resamples whole calendar weeks,
since signals on the same days are not independent.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from .api import InfoClient
from .market import candles_df, fetch_candles, funding_df

MAJORS = ("BTC", "ETH")


def fetch_universe(c: InfoClient, data_dir: str = "data") -> list:
    meta = c.post({"type": "meta"})
    uni = [(u["name"], bool(u.get("isDelisted"))) for u in meta["universe"]]
    path = os.path.join(data_dir, "market", "universe.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(uni, f)
    for name, _ in uni:
        try:
            fetch_candles(c, name, "1d", data_dir)
        except Exception as e:  # keep going: a delisted name may have no candles
            print(f"  skip {name}: {e}", flush=True)
    return uni


def load_panel(data_dir: str = "data", exclude=MAJORS, min_days: int = 30):
    """Daily open/high/close panels (days x coins) for the saved universe."""
    with open(os.path.join(data_dir, "market", "universe.json")) as f:
        uni = json.load(f)
    O, H, C = {}, {}, {}
    for name, _ in uni:
        if name in exclude:
            continue
        d = candles_df(name, "1d", data_dir)
        if len(d) < min_days:
            continue
        O[name], H[name], C[name] = d["open"], d["high"], d["close"]
    return tuple(pd.DataFrame(x).sort_index() for x in (O, H, C))


def short_returns(O: pd.DataFrame, hold: int) -> pd.DataFrame:
    """Return of a short opened at the next day's open and closed `hold` days later."""
    return 1 - O.shift(-(1 + hold)) / O.shift(-1)


def events(O, H, C, mask: pd.DataFrame, hold: int, start, end, min_age: int = 31, cooldown: int | None = None):
    """One row per signal (coin, day), skipping repeats within `cooldown` days."""
    cooldown = cooldown or hold
    fwd = short_returns(O, hold)
    age = C.notna().cumsum()
    rows = []
    for coin in C.columns:
        sig = (mask[coin].fillna(False) & (age[coin] >= min_age)).loc[start:end]
        last = None
        for t in sig.index[sig.values.astype(bool)]:
            if last is not None and (t - last).days < cooldown:
                continue
            v = fwd.at[t, coin]
            if not np.isfinite(v):
                continue
            last = t
            i = C.index.get_loc(t)
            p0 = O[coin].iloc[i + 1]
            mae = H[coin].iloc[i + 1: i + 1 + hold].max() / p0 - 1
            rows.append({"coin": coin, "t": t, "ret": v, "adverse": mae})
    return pd.DataFrame(rows, columns=["coin", "t", "ret", "adverse"])


def week_bootstrap(df: pd.DataFrame, col: str = "ret", n: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval for the mean, resampling calendar weeks (clustered signals)."""
    if df.empty:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    groups = [g[col].values for _, g in df.groupby(df["t"].dt.to_period("W"))]
    sums = np.array([g.sum() for g in groups])
    cnts = np.array([len(g) for g in groups])
    means = []
    for _ in range(n):
        pick = rng.integers(0, len(groups), len(groups))
        means.append(sums[pick].sum() / cnts[pick].sum())
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def week_bootstrap_diff(ev: pd.DataFrame, base: pd.DataFrame, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval for mean(rule) - mean(base), resampling the same calendar
    weeks for both, so a week that was bad for every alt counts against both."""
    if ev.empty:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    bw = base.groupby(base["t"].dt.to_period("W"))["ret"].agg(["sum", "count"])
    ew = ev.groupby(ev["t"].dt.to_period("W"))["ret"].agg(["sum", "count"]).reindex(bw.index).fillna(0.0)
    es, ec, bs, bc = ew["sum"].values, ew["count"].values, bw["sum"].values, bw["count"].values
    diffs = []
    for _ in range(n):
        pick = rng.integers(0, len(bw), len(bw))
        if ec[pick].sum() == 0:
            continue
        diffs.append(es[pick].sum() / ec[pick].sum() - bs[pick].sum() / bc[pick].sum())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi)


def summarize(df: pd.DataFrame, col: str = "ret") -> dict:
    s = df[col]
    lo, hi = week_bootstrap(df, col)
    return {"sinais": int(len(s)), "média": s.mean() * 100, "IC95 da média": f"[{lo * 100:+.1f}%, {hi * 100:+.1f}%]",
            "mediana": s.median() * 100, "% com lucro": (s > 0).mean() * 100, "pior 10%": s.quantile(0.1) * 100,
            "contra mediano": df["adverse"].median() * 100 if "adverse" in df else np.nan}


RULES = {
    "subiu ≥30% em 7d": lambda r3, r7, r30: r7 >= 0.30,
    "subiu ≥100% em 7d": lambda r3, r7, r30: r7 >= 1.00,
    "caiu ≥20% em 7d": lambda r3, r7, r30: r7 <= -0.20,
    "repique em queda (30d ≤ −30% e 3d ≥ +15%)": lambda r3, r7, r30: (r30 <= -0.30) & (r3 >= 0.15),
}


def event_study(O, H, C, start, end, holds=(7, 14)) -> pd.DataFrame:
    r3, r7, r30 = C / C.shift(3) - 1, C / C.shift(7) - 1, C / C.shift(30) - 1
    age = C.notna().cumsum()
    rows = []
    for hold in holds:
        base = short_returns(O, hold).where(age >= 31).loc[start:end].stack().rename("ret").reset_index()
        base.columns = ["t", "coin", "ret"]
        base = base.dropna(subset=["ret"])
        rows.append({"regra": "qualquer alt, qualquer dia (base)", "dias": hold, **summarize(base), "vs. base (IC95)": "—"})
        for name, f in RULES.items():
            ev = events(O, H, C, f(r3, r7, r30), hold, start, end)
            lo, hi = week_bootstrap_diff(ev, base)
            rows.append({"regra": name, "dias": hold, **summarize(ev),
                         "vs. base (IC95)": f"[{lo * 100:+.1f}, {hi * 100:+.1f}] p.p."})
    return pd.DataFrame(rows)


def funding_buckets(coins, data_dir: str, start, end, hold: int = 7,
                    edges=(-np.inf, 0.0, 0.11, 0.30, 0.60, np.inf),
                    labels=("< 0", "0–11%", "11–30%", "30–60%", "> 60%")) -> pd.DataFrame:
    """Forward short returns grouped by the day's average funding rate
    (annualised; Hyperliquid's resting rate is ~11%/yr)."""
    frames = []
    for coin in coins:
        d, fr = candles_df(coin, "1d", data_dir), funding_df(coin, data_dir)
        if d.empty or fr.empty:
            continue
        fd = fr["fundingRate"].resample("D").mean() * 24 * 365
        fwd = 1 - d["open"].shift(-(1 + hold)) / d["open"].shift(-1)
        x = pd.DataFrame({"f": fd.reindex(d.index), "ret": fwd}).dropna().loc[start:end]
        x["coin"] = coin
        frames.append(x.rename_axis("t").reset_index())
    if not frames:
        return pd.DataFrame()
    X = pd.concat(frames, ignore_index=True)
    X["faixa"] = pd.cut(X["f"], list(edges), labels=list(labels))
    rows = []
    for lab, g in X.groupby("faixa", observed=True):
        lo, hi = week_bootstrap(g)
        rows.append({"funding anualizado": lab, "dias-moeda": len(g), "média": g["ret"].mean() * 100,
                     "IC95 da média": f"[{lo * 100:+.1f}%, {hi * 100:+.1f}%]", "mediana": g["ret"].median() * 100,
                     "% com lucro": (g["ret"] > 0).mean() * 100})
    return pd.DataFrame(rows)


def ma_short_table(data_dir: str = "data", periods: dict | None = None) -> pd.DataFrame:
    """'Short when the daily close is below its n-day average' on Binance
    daily closes (long history), by period."""
    from .binance import klines_df

    periods = periods or {}
    rows = []
    for sym, coin in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")]:
        c = klines_df(sym, "1d", data_dir)["close"]
        if c.empty:
            continue
        ret = c.pct_change()
        for n in (50, 100, 200):
            pos = -(c < c.rolling(n).mean()).astype(float)
            r = pos.shift(1) * ret
            row = {"ativo": coin, "regra": f"short abaixo da MA{n}"}
            for name, (a, b) in periods.items():
                x = r.loc[a:b].dropna()
                row[name] = (np.prod(1 + x) - 1) * 100 if len(x) else np.nan
            rows.append(row)
        row = {"ativo": coin, "regra": "sempre short"}
        for name, (a, b) in periods.items():
            x = -ret.loc[a:b].dropna()
            row[name] = (np.prod(1 + x) - 1) * 100 if len(x) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _md(df: pd.DataFrame, pct_cols=(), share_cols=("% com lucro",)) -> str:
    d = df.copy()
    for col in d.columns:
        if col in share_cols:
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}%")
        elif col in pct_cols:
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else f"{v:+.1f}%")
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(lines)


def study(data_dir: str, start: str, end: str, funding_a: list, funding_b: list,
          out: str = "reports/estudos/regras_short.md") -> str:
    O, H, C = load_panel(data_dir)
    es = event_study(O, H, C, start, end)
    md = ["# Regras de short testadas no universo da Hyperliquid", "",
          f"Gerado por `python -m hlre.universe study` em {pd.Timestamp.now('UTC'):%Y-%m-%d}. Período dos sinais: "
          f"{start} → {end}. Universo: {C.shape[1]} perps (inclui deslistados; BTC e ETH ficam de fora em A). "
          "Retorno = short aberto na abertura do dia seguinte ao sinal e fechado N dias depois, sem taxas e sem "
          "funding. IC95 = intervalo de 95% da média por bootstrap de semanas inteiras.", "",
          "## A. Short depois de alta, de queda ou de repique em tendência de queda", "",
          _md(es, pct_cols=["média", "mediana", "% com lucro", "pior 10%", "contra mediano"]), "",
          "*contra mediano*: quanto o preço subiu (máxima) acima da entrada durante o período, na mediana. "
          "*vs. base*: intervalo de 95% da diferença entre a média da regra e a da base, sorteando as mesmas semanas "
          "para as duas (semanas ruins para todas as alts pesam igual nos dois lados); se não inclui zero, a regra "
          "fez diferença além de simplesmente estar vendido em alts.", ""]
    for name, coins in [("moedas operadas pela carteira", funding_a), ("amostra aleatória de moedas que a carteira não operou", funding_b)]:
        fb = funding_buckets(coins, data_dir, start, end)
        if len(fb):
            md += [f"## B. Funding alto como sinal: {name}", "",
                   f"{len(coins)} moedas: {', '.join(coins)}. Retorno de um short de 7 dias por faixa do funding "
                   "médio do dia do sinal. Janelas sobrepostas (dias seguidos compartilham o futuro); o IC por semanas "
                   "leva isso em conta só em parte.", "",
                   _md(fb, pct_cols=["média", "mediana", "% com lucro"]), ""]
    periods = {"2020–2024": ("2020-08-01", "2024-12-15"), "2022 (baixa)": ("2022-01-01", "2022-12-31"),
               "2023–24 (alta)": ("2023-01-01", "2024-12-15"), "período da carteira": (start, end)}
    ma = ma_short_table(data_dir, periods)
    if len(ma):
        md += ["## C. BTC e ETH: short abaixo da média móvel em vários anos", "",
               "Retorno acumulado de ficar vendido quando o fechamento diário está abaixo da média de N dias "
               "(fechamentos diários da Binance; sem alavancagem, taxas ou funding).", "",
               _md(ma, pct_cols=list(periods)), ""]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(md))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["fetch", "study"])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--start", default="2024-12-16")
    ap.add_argument("--end", default=str(pd.Timestamp.now("UTC").date()))
    ap.add_argument("--funding-a", nargs="*", default=[])
    ap.add_argument("--funding-b", nargs="*", default=[])
    ap.add_argument("--out", default="reports/estudos/regras_short.md")
    a = ap.parse_args()
    if a.cmd == "fetch":
        uni = fetch_universe(InfoClient(), a.data_dir)
        print(f"{len(uni)} perps")
    else:
        print(study(a.data_dir, a.start, a.end, a.funding_a, a.funding_b, a.out))


if __name__ == "__main__":
    main()
