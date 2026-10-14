"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0xc7c37b0c7af5af560bf31b0bcbfec04b97361275/analise_extra.py

Lê só os arquivos em data/. A carteira opera em "pacotes": ordens disparadas
juntas (muitas vezes duas TWAPs simultâneas, uma por perna). O relatório
automático olha ativo por ativo; aqui os fills são agrupados em pacotes
(atividade separada por mais de 2 horas) e cada par long/short vira uma linha,
com o contexto da razão entre as duas pernas antes da entrada.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet  # noqa: E402
from hlre.market import hourly_close  # noqa: E402

USER = "0xc7c37b0c7af5af560bf31b0bcbfec04b97361275"
DATA = os.path.join(ROOT, "data")
# pares identificados nos pacotes: (nome, perna comprada, perna vendida, entrada, saída ou None se aberto)
PAIRS = [
    ("P1", "ETH", "BTC", "2026-08-24 10:28", "2026-08-26 10:15"),
    ("P2", "BTC", "xyz:GOLD", "2026-08-26 10:20", "2026-09-02 10:13"),
    ("P3", "BTC", "xyz:GOLD", "2026-09-03 07:35", "2026-09-04 06:59"),
    ("P4", "BTC", "xyz:GOLD", "2026-09-16 09:18", "2026-09-21 12:29"),
    ("P5", "xyz:GOLD", "BTC", "2026-10-06 10:10", "2026-10-08 14:49"),
    ("P6", "ETH", "BTC", "2026-10-14 07:20", None),
]
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)


def main():
    w = Wallet(USER, DATA)
    f = w.fills.sort_values("time").copy()

    print("======== Pacotes de ordens (atividade separada por > 2h)")
    f["pkg"] = (f["t"].diff().dt.total_seconds().fillna(1e9) > 7200).cumsum()
    g = f.groupby(["pkg", "coin"]).agg(início=("t", "min"), fim=("t", "max"), qtd=("q", "sum"), nocional=("ntl", "sum"),
                                       realizado=("closedPnl", "sum"), taxas=("fee", "sum"), fills=("sz", "size"),
                                       twap=("twapId", lambda s: s.notna().mean()))
    g["preço médio"] = g["nocional"] / f.groupby(["pkg", "coin"])["sz"].sum()
    g["início"] = g["início"].dt.strftime("%Y-%m-%d %H:%M")
    g["fim"] = g["fim"].dt.strftime("%Y-%m-%d %H:%M")
    print(g.round(2).to_string())

    print("\n======== Ordens TWAP (fatias de 30 s)")
    tw = f[f["twapId"].notna()]
    t = tw.groupby("twapId").agg(ativo=("coin", "first"), lado=("side", "first"), início=("t", "min"), fim=("t", "max"),
                                 fatias=("sz", "size"), nocional=("ntl", "sum"))
    t["minutos"] = (t["fim"] - t["início"]).dt.total_seconds() / 60
    t = t.sort_values("início")
    t["início"], t["fim"] = t["início"].dt.strftime("%Y-%m-%d %H:%M"), t["fim"].dt.strftime("%H:%M")
    print(t.round(1).to_string())

    print("\n======== Pares: PnL realizado por perna e contexto da razão (perna comprada / perna vendida)")
    h = {c: hourly_close(c, DATA) for c in ["BTC", "ETH", "xyz:GOLD"]}
    rows = []
    for name, lg, sh, a, b in PAIRS:
        t0 = pd.Timestamp(a)
        t1 = pd.Timestamp(b) if b else f["t"].max()
        legs = f[f["coin"].isin([lg, sh]) & (f["t"] >= t0 - pd.Timedelta(minutes=2)) & (f["t"] <= t1 + pd.Timedelta(minutes=2))]
        r = (h[lg] / h[sh]).dropna()
        pre = r.loc[: t0.floor("h") - pd.Timedelta(hours=1)]
        win = pre.iloc[-720:]
        after = r.loc[: (t1 if b else r.index.max()).floor("h")]
        rows.append({
            "par": name, "comprado": lg, "vendido": sh, "entrada": a, "saída": b or "aberto",
            "razão 7d antes %": round((pre.iloc[-1] / pre.iloc[-169] - 1) * 100, 1),
            "razão 30d antes %": round((pre.iloc[-1] / pre.iloc[-721] - 1) * 100, 1),
            "posição no range 30d": round((pre.iloc[-1] - win.min()) / (win.max() - win.min()), 2),
            "razão durante %": round((after.iloc[-1] / pre.iloc[-1] - 1) * 100, 1),
            "realizado": round(legs["closedPnl"].sum()), "taxas": round(legs["fee"].sum()),
        })
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n======== Dinheiro")
    print(w.ledger[["t", "type", "usd", "counterparty"]].to_string(index=False))
    pa = w.portfolio("allTime")
    print(f"valor da conta hoje US$ {pa['account_value'].iloc[-1]:,.0f}; PnL all-time US$ {pa['pnl'].iloc[-1]:,.0f}; "
          f"maior valor US$ {pa['account_value'].max():,.0f}")
    pos = w.snapshot["clearinghouseState"]
    gross = sum(abs(float(p["position"]["positionValue"])) for p in pos["assetPositions"])
    print(f"exposição bruta agora US$ {gross:,.0f} sobre equity de US$ {float(pos['marginSummary']['accountValue']):,.0f} "
          f"= {gross / float(pos['marginSummary']['accountValue']):.1f}x")


if __name__ == "__main__":
    main()
