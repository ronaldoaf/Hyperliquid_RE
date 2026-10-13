"""One-shot pipeline: download wallet + market data, then build the report.

Usage:
    python -m hlre.run 0xWALLET [0xWALLET ...] [--top 3] [--no-binance]
"""
from __future__ import annotations

import argparse

from .analyze import Wallet, episodes, executions, rank_coins
from .api import InfoClient
from .binance import fetch_klines
from .collect import collect
from .market import binance_symbol, fetch_candles, fetch_funding_history
from .report import build


def run(user: str, data_dir: str = "data", out: str = "reports", top: int = 3, binance: bool = True):
    collect(user, data_dir)
    w = Wallet(user, data_dir)
    c = InfoClient()
    coins = set(w.funding["coin"].unique()) if len(w.funding) else set()
    if len(w.fills):
        coins |= set(w.fills.loc[w.fills["kind"] != "spot", "coin"].unique())
    print(f"daily candles for {len(coins)} coins", flush=True)
    for coin in sorted(coins):
        try:
            fetch_candles(c, coin, "1d", data_dir)
        except Exception as e:  # delisted/unknown names should not stop the run
            print(f"  skip {coin}: {e}")
    mains = rank_coins(w, top)
    print("main coins:", mains, flush=True)
    # 4h candles (one request covers ~800 days) give hourly-ish entry context for every traded coin;
    # the funding-rate history is fetched for coins that carried sizeable positions
    traded = sorted(set(w.fills.loc[w.fills["kind"] != "spot", "coin"])) if len(w.fills) else []
    for coin in traded:
        try:
            fetch_candles(c, coin, "4h", data_dir)
        except Exception as e:
            print(f"  skip 4h {coin}: {e}")
    big = set()
    if len(w.fills):
        ex = executions(w.fills)
        for coin in traded:
            ep = episodes(ex, coin)
            if len(ep) and ep["max_ntl"].max() >= 100_000:
                big.add(coin)
    for coin in sorted(big - set(mains)):
        try:
            fetch_funding_history(c, coin, data_dir)
        except Exception as e:
            print(f"  skip funding {coin}: {e}")
    for coin in mains:
        for iv in ("1h", "4h"):
            fetch_candles(c, coin, iv, data_dir)
        fetch_funding_history(c, coin, data_dir)
        sym = binance_symbol(coin)
        if binance and sym:
            try:
                fetch_klines(sym, "1h", start=str(w.fills["t"].min().to_period("M")) if len(w.fills) else "2024-01",
                             data_dir=data_dir)
            except Exception as e:
                print(f"  binance {sym}: {e}")
    print(build(user, data_dir, out, mains))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("users", nargs="+")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--no-binance", action="store_true")
    a = ap.parse_args()
    for u in a.users:
        run(u, a.data_dir, a.out, a.top, not a.no_binance)


if __name__ == "__main__":
    main()
