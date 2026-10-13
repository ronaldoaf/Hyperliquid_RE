"""Supplementary hourly/minute klines from Binance's public archive.

Hyperliquid's candleSnapshot serves only the latest 5000 candles per
interval (about 7 months of 1h bars), so older intraday context comes from
data.binance.vision (USDT-margined futures, monthly zip files).

Usage:
    python -m hlre.binance BTCUSDT ETHUSDT --interval 1h --start 2025-01
"""
from __future__ import annotations

import argparse
import io
import os
import zipfile

import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _read_zip(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        name = z.namelist()[0]
        raw = z.read(name).decode()
    first = raw.split("\n", 1)[0]
    header = 0 if first.startswith("open_time") else None
    df = pd.read_csv(io.StringIO(raw), header=header, names=None if header == 0 else COLS)
    return df


def fetch_klines(symbol: str, interval: str = "1h", start: str = "2025-01",
                 data_dir: str = "data") -> pd.DataFrame:
    """Download monthly archives (falling back to daily files for the current
    month) and cache them as one CSV per symbol/interval."""
    out_dir = os.path.join(data_dir, "market")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"binance_{symbol}_{interval}.csv.gz")
    have = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=COLS)
    have_months = set(pd.to_datetime(have["open_time"], unit="ms").dt.strftime("%Y-%m")) if len(have) else set()
    now = pd.Timestamp.now("UTC").tz_localize(None)
    months = pd.period_range(start, now.to_period("M"), freq="M")
    frames = [have]
    s = requests.Session()
    recent = {str(m) for m in months[-2:]}  # re-fetch: may have been partial
    for m in months:
        ms = str(m)
        if ms in have_months and ms not in recent:
            continue
        r = s.get(f"{BASE}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{ms}.zip", timeout=60)
        if r.status_code == 200:
            frames.append(_read_zip(r.content))
            continue
        # current (or not-yet-published) month: use the daily files
        for d in pd.date_range(m.start_time, min(m.end_time, now - pd.Timedelta(days=1)), freq="D"):
            r = s.get(f"{BASE}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{d:%Y-%m-%d}.zip", timeout=60)
            if r.status_code == 200:
                frames.append(_read_zip(r.content))
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    df = df[COLS].drop_duplicates("open_time").sort_values("open_time")
    df.to_csv(path, index=False)
    return df


def klines_df(symbol: str, interval: str = "1h", data_dir: str = "data") -> pd.DataFrame:
    path = os.path.join(data_dir, "market", f"binance_{symbol}_{interval}.csv.gz")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["t"] = pd.to_datetime(df["open_time"], unit="ms")
    return df.set_index("t")[["open", "high", "low", "close", "volume"]].astype(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--start", default="2025-01")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    for sym in a.symbols:
        df = fetch_klines(sym, a.interval, a.start, a.data_dir)
        print(sym, a.interval, len(df), "rows", flush=True)


if __name__ == "__main__":
    main()
