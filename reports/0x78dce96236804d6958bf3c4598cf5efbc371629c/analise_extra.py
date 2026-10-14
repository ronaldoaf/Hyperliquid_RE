"""Números do ANALISE.md da 0x78dc que não estão no relatório automático.

Uso: python reports/0x78dce96236804d6958bf3c4598cf5efbc371629c/analise_extra.py [--refresh]

--refresh baixa de novo as subcontas da conta mestre (data/<carteira>/master_subaccounts.json)
e os candles de 1 min de BTC usados no markout (data/<carteira>/btc_1m.json).
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ADDR = "0x78dce96236804d6958bf3c4598cf5efbc371629c"
MASTER = "0x7839e2f2c375dd2935193f2736167514efff9916"
URL = "https://api.hyperliquid.xyz/info"
D = Path(__file__).resolve().parents[2] / "data" / ADDR
REFRESH = "--refresh" in sys.argv


def post(body):
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def cached(name, fetch):
    p = D / name
    if REFRESH or not p.exists():
        p.write_text(json.dumps(fetch()))
    return json.loads(p.read_text())


snap = json.loads((D / "snapshot.json").read_text())
fills = pd.DataFrame(json.load(gzip.open(D / "fills.json.gz")))
for c in ["px", "sz", "fee", "closedPnl", "startPosition"]:
    fills[c] = fills[c].astype(float)
fills["t"] = pd.to_datetime(fills.time, unit="ms")
fills["sgn"] = np.where(fills.side == "B", 1, -1)
fills["ntl"] = fills.px * fills.sz

print("== PnL mensal (portfolio all-time) ==")
pf = dict(snap["portfolio"])
pnl = pd.Series({pd.to_datetime(t, unit="ms"): float(v) for t, v in pf["allTime"]["pnlHistory"]})
av = pd.Series({pd.to_datetime(t, unit="ms"): float(v) for t, v in pf["allTime"]["accountValueHistory"]})
m = pd.DataFrame({"pnl": pnl, "equity": av}).resample("ME").last()
m["pnl_mes"] = m.pnl.diff().fillna(m.pnl)
print(m.round(0).to_string())

vol_all = float(pf["allTime"]["vlm"])
vol_month = float(pf["month"]["vlm"])
pnl_all = float(pf["allTime"]["pnlHistory"][-1][1])
pnl_month = float(pf["month"]["pnlHistory"][-1][1])
print(f"\nvolume all-time ${vol_all/1e9:.2f}B, PnL ${pnl_all/1e3:.0f}K = {pnl_all/vol_all*1e4:.2f} bp do volume")
print(f"últimos 30 dias: volume ${vol_month/1e6:.0f}M, PnL ${pnl_month/1e3:.0f}K = {pnl_month/vol_month*1e4:.2f} bp")
print(f"antes disso: {(pnl_all-pnl_month)/(vol_all-vol_month)*1e4:.2f} bp")

print("\n== posição diária de BTC (funding) por mês ==")
fu = json.load(gzip.open(D / "funding.json.gz"))
f = pd.DataFrame([{"t": pd.to_datetime(x["time"], unit="ms"), "szi": float(x["delta"]["szi"]),
                   "usdc": float(x["delta"]["usdc"])} for x in fu]).set_index("t")
print(f.resample("ME").agg({"szi": ["min", "max", "mean"], "usdc": "sum"}).round(2).to_string())

print("\n== fills (período disponível) ==")
print(f"{fills.t.min()} → {fills.t.max()}, {len(fills)} fills, taker {fills.crossed.mean():.0%}")
print(f"volume ${fills.ntl.sum()/1e6:.1f}M (compra {fills[fills.side=='B'].ntl.sum()/1e6:.1f}M, "
      f"venda {fills[fills.side=='A'].ntl.sum()/1e6:.1f}M); taxa {fills.fee.sum()/fills.ntl.sum()*1e4:.2f} bp "
      f"(US$ {fills.fee.sum():,.0f}); closedPnl US$ {fills.closedPnl.sum():,.0f}")
pos = fills.startPosition + fills.sgn * fills.sz
print("posição BTC (quantis 0/5/50/95/100%):", pos.quantile([0, .05, .5, .95, 1]).round(2).tolist())
print("fills por hora (mediana):", fills.set_index("t").resample("h").size().median())


def fetch_candles():
    st, en, out = int(fills.time.min()) - 60_000, int(fills.time.max()) + 4 * 3_600_000, []
    while st < en:
        r = post({"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "1m", "startTime": st, "endTime": en}})
        if not r:
            break
        out += r
        st = r[-1]["t"] + 60_000
        if len(r) < 10:
            break
    return out


c = pd.DataFrame(cached("btc_1m.json", fetch_candles)).drop_duplicates("t")
close = pd.Series(c.c.astype(float).values, index=pd.to_datetime(c.t, unit="ms"))
print(f"\n== markout (candles 1m de {close.index.min()} em diante; + = a favor do maker) ==")
for h in [1, 5, 15, 60, 240]:
    ref = close.reindex((fills.t + pd.Timedelta(minutes=h)).dt.floor("min")).values
    mo = fills.sgn * (ref - fills.px) / fills.px * 1e4
    ok = ~np.isnan(mo)
    print(f"{h:>4} min: {np.sum(mo[ok] * fills.ntl[ok]) / fills.ntl[ok].sum():+.2f} bp ({ok.sum()} fills)")

print("\n== ordens (últimas 2.000 da API) ==")
o = pd.DataFrame([{"st": x["status"], "t": x["order"]["timestamp"], "cloid": x["order"].get("cloid"),
                   "tif": x["order"]["tif"]} for x in json.load(gzip.open(D / "orders.json.gz"))])
span = (o.t.max() - o.t.min()) / 1000
print(o.st.value_counts().to_string())
print(f"janela {span:.0f} s → {len(o)/span:.0f} ordens/s; com cloid {o.cloid.notna().mean():.0%}; tif {o.tif.unique()}")
rl = snap["userRateLimit"]
print(f"requisições acumuladas (userRateLimit): {rl['nRequestsUsed']:,}")

print("\n== transferências com a conta mestre ==")
rows = []
for x in json.load(gzip.open(D / "ledger.json.gz")):
    dl = x["delta"]
    if dl["type"] == "subAccountTransfer":
        s = 1 if dl["destination"].lower() == ADDR else -1
        rows.append({"t": pd.to_datetime(x["time"], unit="ms"), "v": s * float(dl["usdc"])})
tr = pd.DataFrame(rows).set_index("t")
print(tr.resample("ME").v.agg(["count", "sum"]).round(0).to_string())
print(f"total: {len(tr)} transferências, líquido US$ {tr.v.sum():,.0f} (− = mandado para a mestre)")
gaps = tr.index.to_series().diff().dt.total_seconds().div(60)
print("intervalo entre transferências seguidas (min, mediana desde ago/2026):",
      round(gaps[tr.index >= "2026-08-01"].median(), 1))

print("\n== subcontas da mestre 0x7839…9916 ==")
subs = cached("master_subaccounts.json", lambda: post({"type": "subAccounts", "user": MASTER}))
rows = []
for a in subs:
    cs = a["clearinghouseState"]
    btc = sum(float(p["position"]["szi"]) for p in cs["assetPositions"] if p["position"]["coin"] == "BTC")
    gross = sum(float(p["position"]["positionValue"]) for p in cs["assetPositions"])
    rows.append({"nome": a["name"], "end": a["subAccountUser"][:6], "equity": float(cs["marginSummary"]["accountValue"]),
                 "ativos": len(cs["assetPositions"]), "bruto": gross, "btc": btc})
g = pd.DataFrame(rows).sort_values("bruto", ascending=False)
print(f"{len(g)} subcontas, equity somada US$ {g.equity.sum()/1e6:.2f}M, exposição bruta US$ {g.bruto.sum()/1e6:.2f}M, "
      f"com posição: {(g.ativos > 0).sum()}")
print(g[g.btc.abs() > 0.1].round(2).to_string(index=False))
print(f"BTC líquido do grupo: {g.btc.sum():.2f} (esta conta: {g[g.end == ADDR[:6]].btc.sum():.2f})")
fees = post({"type": "userFees", "user": MASTER})
v = pd.DataFrame(fees["dailyUserVlm"]).astype({"userAdd": float, "userCross": float, "exchange": float})
print(f"grupo, últimos {len(v)} dias: maker US$ {v.userAdd.mean()/1e6:.0f}M/dia, taker US$ {v.userCross.mean()/1e6:.0f}M/dia, "
      f"{(v.userAdd + v.userCross).sum() / v.exchange.sum():.1%} do volume da bolsa; taxa maker {fees['userAddRate']}")
