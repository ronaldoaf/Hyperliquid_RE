"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x63d417a577b50c96f4f09148d4e4d70950db0522/analise_extra.py

Lê só os arquivos em data/. Dois blocos:
- liquidações próprias: fills em que a própria carteira foi liquidada, agrupados
  por evento (mesmo minuto e moeda) e somados pelo PnL realizado nos fills;
- livro atual: posições do snapshot (clearinghouseState), com exposição bruta,
  líquida e margem da conta cross.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, liquidation_events  # noqa: E402

USER = "0x63d417a577b50c96f4f09148d4e4d70950db0522"
DATA = os.path.join(ROOT, "data")


def liquidations() -> None:
    w = Wallet(USER, DATA)
    liq = liquidation_events(w.fills, USER).copy()
    liq["evento"] = liq["t"].dt.floor("min")
    ev = (liq.groupby(["evento", "coin"])
             .agg(fills=("t", "size"), pnl=("closedPnl", "sum"))
             .reset_index())
    print(f"liquidações próprias: {len(ev)} eventos (minuto + moeda), {len(liq)} fills")
    print(ev.to_string(index=False, float_format=lambda x: f"{x:,.0f}"))
    print(f"PnL realizado nos fills de liquidação: {liq['closedPnl'].astype(float).sum():,.0f}")
    print("\npor moeda:")
    print(liq.groupby("coin")["closedPnl"].sum().sort_values().round(0).to_string())


def book() -> None:
    with open(os.path.join(DATA, USER, "snapshot.json")) as fh:
        snap = json.load(fh)
    ch = snap.get("clearinghouseState", snap)
    rows = []
    for a in ch["assetPositions"]:
        p = a["position"]
        rows.append((p["coin"], float(p["szi"]), float(p["positionValue"]),
                     float(p["unrealizedPnl"]), p["leverage"]["type"], float(p["leverage"]["value"])))
    df = pd.DataFrame(rows, columns=["coin", "szi", "ntl", "upnl", "tipo", "alav"])
    longs = df.loc[df.szi > 0, "ntl"].sum()
    shorts = df.loc[df.szi < 0, "ntl"].sum()
    cross = ch["crossMarginSummary"]
    print(f"\nlivro atual: {len(df)} posições")
    print(f"  long  ${longs:,.0f}")
    print(f"  short ${shorts:,.0f}")
    print(f"  bruto ${longs + shorts:,.0f} | líquido ${longs - shorts:,.0f}")
    print(f"  uPnL total ${df['upnl'].sum():,.0f}")
    print(f"  conta cross: valor ${float(cross['accountValue']):,.0f} | "
          f"margem usada ${float(cross['totalMarginUsed']):,.0f} | "
          f"manutenção ${float(ch['crossMaintenanceMarginUsed']):,.0f}")
    print(f"  bruto / valor da conta cross: {(longs + shorts) / float(cross['accountValue']):.2f}x")


if __name__ == "__main__":
    liquidations()
    book()
