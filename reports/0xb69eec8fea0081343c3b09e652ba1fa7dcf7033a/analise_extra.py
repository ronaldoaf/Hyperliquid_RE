"""Liquidações desta carteira nos fills (o ledger não registra nenhuma) agrupadas por hora e ativo."""
import collections, datetime, gzip, json, sys

ADDR = "0xb69eec8fea0081343c3b09e652ba1fa7dcf7033a"
fills = json.load(gzip.open(f"data/{ADDR}/fills.json.gz"))
g = collections.defaultdict(lambda: [0.0, 0.0])
for x in fills:
    liq = x.get("liquidation")
    if liq and liq.get("liquidatedUser") == ADDR:
        t = datetime.datetime.fromtimestamp(x["time"] / 1000, datetime.UTC).strftime("%Y-%m-%d %H")
        g[(t, x["coin"])][0] += float(x["closedPnl"])
        g[(t, x["coin"])][1] += float(x["sz"]) * float(x["px"])
for k in sorted(g):
    print(*k, f"realizado {g[k][0]:+,.0f}", f"nocional {g[k][1]:,.0f}")
print("total realizado", round(sum(v[0] for v in g.values())))
