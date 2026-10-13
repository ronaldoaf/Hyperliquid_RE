"""Market context: candles and funding-rate history, cached under data/market/.

Usage:
    python -m hlre.market BTC HYPE ETH --intervals 1h 4h 1d
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import time

import pandas as pd

from .api import InfoClient

INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
    "4h": 14_400_000, "1d": 86_400_000,
}


def _path(data_dir: str, name: str) -> str:
    d = os.path.join(data_dir, "market")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def _load(path: str) -> list:
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt") as f:
        return json.load(f)


def _save(path: str, rows: list) -> None:
    with gzip.open(path + ".tmp", "wt") as f:
        json.dump(rows, f, separators=(",", ":"))
    os.replace(path + ".tmp", path)


def fetch_candles(c: InfoClient, coin: str, interval: str, data_dir: str = "data",
                  start_ms: int = 0) -> list:
    """The API serves only the latest 5000 candles per interval, so the cache is
    merged with every new download to keep older history."""
    p = _path(data_dir, f"candles_{coin.replace(':', '_')}_{interval}.json.gz")
    old = {r["t"]: r for r in _load(p)}
    step = INTERVAL_MS[interval]
    end = int(time.time() * 1000)
    cur = max(start_ms, (max(old) if old else 0))
    while cur < end:
        page = c.post({"type": "candleSnapshot",
                       "req": {"coin": coin, "interval": interval, "startTime": cur, "endTime": end}})
        if not page:
            break
        for r in page:
            old[r["t"]] = r
        last = max(r["t"] for r in page)
        if last + step >= end or len(page) < 2:
            break
        cur = last + step
    rows = [old[k] for k in sorted(old)]
    _save(p, rows)
    return rows


def fetch_funding_history(c: InfoClient, coin: str, data_dir: str = "data", start_ms: int = 0) -> list:
    p = _path(data_dir, f"funding_{coin.replace(':', '_')}.json.gz")
    old = _load(p)
    start = old[-1]["time"] + 1 if old else start_ms
    new = c.paginate_time({"type": "fundingHistory", "coin": coin}, start,
                          key=lambda x: x["time"], page_limit=500)
    rows = {r["time"]: r for r in old + new}
    rows = [rows[k] for k in sorted(rows)]
    _save(p, rows)
    return rows


def candles_df(coin: str, interval: str, data_dir: str = "data") -> pd.DataFrame:
    rows = _load(_path(data_dir, f"candles_{coin.replace(':', '_')}_{interval}.json.gz"))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.rename(columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "n": "trades"})
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = df[k].astype(float)
    df["t"] = pd.to_datetime(df["time"], unit="ms")
    return df.set_index("t")[["open", "high", "low", "close", "volume", "trades"]]


def funding_df(coin: str, data_dir: str = "data") -> pd.DataFrame:
    rows = _load(_path(data_dir, f"funding_{coin.replace(':', '_')}.json.gz"))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["fundingRate"] = df["fundingRate"].astype(float)
    df["premium"] = df["premium"].astype(float)
    df["t"] = pd.to_datetime(df["time"], unit="ms")
    return df.set_index("t")[["fundingRate", "premium"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("coins", nargs="+")
    ap.add_argument("--intervals", nargs="+", default=["1h", "4h", "1d"])
    ap.add_argument("--no-funding", action="store_true")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    c = InfoClient()
    for coin in a.coins:
        for iv in a.intervals:
            rows = fetch_candles(c, coin, iv, a.data_dir)
            print(f"{coin} {iv}: {len(rows)} candles", flush=True)
        if not a.no_funding:
            rows = fetch_funding_history(c, coin, a.data_dir)
            print(f"{coin} funding: {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()


def binance_symbol(coin: str) -> str | None:
    """Best-effort map of a Hyperliquid perp name to a Binance USDT-M symbol."""
    if ":" in coin or coin.startswith("@") or "/" in coin:
        return None
    if coin.startswith("k") and coin[1:].isupper():
        return f"1000{coin[1:]}USDT"  # kPEPE -> 1000PEPEUSDT
    return f"{coin}USDT"


def hourly_close(coin: str, data_dir: str = "data") -> pd.Series:
    """Hourly close series stitched from (in priority order) Hyperliquid 1h
    candles, cached Binance 1h klines, and Hyperliquid 4h candles forward-filled.
    Index = candle open time (UTC); the close is the price at index + 1h."""
    from .binance import klines_df

    parts = []
    hl1 = candles_df(coin, "1h", data_dir)
    if len(hl1):
        parts.append(hl1["close"])
    sym = binance_symbol(coin)
    if sym:
        bn = klines_df(sym, "1h", data_dir)
        if len(bn):
            parts.append(bn["close"])
    hl4 = candles_df(coin, "4h", data_dir)
    if len(hl4):
        # a 4h candle's close is the price at its end: place it on the last hour
        s = hl4["close"].copy()
        s.index = s.index + pd.Timedelta(hours=3)
        parts.append(s.resample("1h").ffill())
    if not parts:
        return pd.Series(dtype=float)
    out = parts[0]
    for p in parts[1:]:
        out = out.combine_first(p)
    return out.sort_index()
