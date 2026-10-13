"""Test whether simple, explicit rules reproduce a wallet's book.

The idea: if a mechanical rule built from observable market features tracks
the wallet's position path (high correlation) and earns a similar PnL, the
wallet is effectively systematic and the rule is a usable replica. If not,
the edge lives in discretionary calls that the rule does not capture.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def daily_backtest(target: pd.Series, close: pd.Series, open_: pd.Series,
                   funding_daily: pd.Series | None = None, fee_bps: float = 3.5) -> pd.DataFrame:
    """Hold `target` (coin units, decided with information up to the previous
    close) through each UTC day. Price PnL uses that day's open->close move;
    rebalances pay `fee_bps` on traded notional; funding is paid by longs
    (`funding_daily` = sum of hourly rates for the day)."""
    idx = target.index
    pos = target.astype(float)
    move = (close - open_).reindex(idx).fillna(0.0)
    px = open_.reindex(idx).ffill()
    trade = pos.diff().abs().fillna(pos.abs())
    out = pd.DataFrame(index=idx)
    out["pos"] = pos
    out["price_pnl"] = pos * move
    out["fees"] = -trade * px * fee_bps / 1e4
    fr = (funding_daily.reindex(idx).fillna(0.0) if funding_daily is not None else 0.0)
    out["funding"] = -pos * px * fr
    out["pnl"] = out[["price_pnl", "fees", "funding"]].sum(axis=1)
    return out


def features(close: pd.Series) -> pd.DataFrame:
    """Daily features known at the close (shift by one day before using them
    to decide the next day's position)."""
    lc = np.log(close)
    X = pd.DataFrame(index=close.index)
    for n in (20, 50, 100, 200):
        X[f"dma{n}"] = lc - np.log(close.rolling(n).mean())
    for n in (7, 30, 90):
        hi, lo = close.rolling(n).max(), close.rolling(n).min()
        X[f"rng{n}"] = (close - lo) / (hi - lo)
    for n in (7, 30, 90):
        X[f"r{n}"] = lc.diff(n)
    return X


def rule_trend_fade(close: pd.Series, size: float, ma: int = 100, rng: int = 30,
                    bull_frac: float = 0.3, fade: float = 0.6) -> pd.Series:
    """Short-biased book: full size below the moving average (bear regime),
    `bull_frac` of it above; within the regime the short is scaled up near the
    top of the `rng`-day range and down near the bottom (sell rips / cover dips)."""
    m = close.rolling(ma).mean()
    hi, lo = close.rolling(rng).max(), close.rolling(rng).min()
    r = ((close - lo) / (hi - lo)).clip(0, 1)
    regime = np.where(close < m, 1.0, bull_frac)
    tgt = -size * regime * ((1 - fade) + fade * r)
    return pd.Series(tgt, index=close.index).shift(1)


def grid_search(close, open_, funding_daily, actual, train, test, size, grid=None, fee_bps=3.5):
    """Fit rule_trend_fade on `train` (max PnL) and report train/test stats,
    including correlation of the rule's position with the actual position."""
    grid = grid or {
        "ma": [50, 100, 200], "rng": [7, 30, 90],
        "bull_frac": [0.0, 0.3, 0.6, 1.0], "fade": [0.0, 0.3, 0.6, 0.9],
    }
    rows = []
    for vals in itertools.product(*grid.values()):
        p = dict(zip(grid.keys(), vals))
        tgt = rule_trend_fade(close, size, **p).reindex(actual.index).fillna(0.0)
        bt = daily_backtest(tgt, close, open_, funding_daily, fee_bps)
        row = dict(p)
        for name, (a, b) in {"train": train, "test": test}.items():
            sl = bt.loc[a:b]
            row[f"{name}_pnl"] = sl["pnl"].sum()
            sd = sl["pnl"].std()
            row[f"{name}_sharpe"] = sl["pnl"].mean() / sd * np.sqrt(365) if sd > 0 else np.nan
            act = actual.loc[a:b]
            row[f"{name}_corr"] = np.corrcoef(sl["pos"], act)[0, 1] if act.std() > 0 and sl["pos"].std() > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("train_pnl", ascending=False).reset_index(drop=True)


def linear_clone(X: pd.DataFrame, actual: pd.Series, train, test):
    """Behavioural cloning: least-squares fit of the actual position on the
    previous day's features; returns in-sample and out-of-sample predictions."""
    d = X.shift(1).reindex(actual.index).assign(pos=actual).dropna()
    tr, te = d.loc[train[0]:train[1]], d.loc[test[0]:test[1]]
    A = lambda df: np.column_stack([np.ones(len(df)), df.drop(columns="pos").values])
    beta, *_ = np.linalg.lstsq(A(tr), tr["pos"].values, rcond=None)
    pred_tr = pd.Series(A(tr) @ beta, index=tr.index)
    pred_te = pd.Series(A(te) @ beta, index=te.index)
    r2 = lambda y, yh: 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return {
        "beta": pd.Series(beta, index=["const"] + list(X.columns)),
        "pred": pd.concat([pred_tr, pred_te]),
        "r2_train": r2(tr["pos"], pred_tr), "r2_test": r2(te["pos"], pred_te),
        "corr_test": np.corrcoef(te["pos"], pred_te)[0, 1],
    }
