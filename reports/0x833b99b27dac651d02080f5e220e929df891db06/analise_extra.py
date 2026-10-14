"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x833b99b27dac651d02080f5e220e929df891db06/analise_extra.py

Lê só os arquivos em data/ (os mesmos do relatório) e grava img/btc_funding.png.
Cada bloco indica a seção do ANALISE.md que ele sustenta.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, approx_price_pnl, daily_exposure  # noqa: E402
from hlre.market import candles_df, funding_df  # noqa: E402

USER = "0x833b99b27dac651d02080f5e220e929df891db06"
DATA = os.path.join(ROOT, "data")
OUT = os.path.dirname(os.path.abspath(__file__))
START, END = "2025-05-23", "2026-10-13"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def title(s: str):
    print(f"\n{'=' * 8} {s}")


def boot_ci(x, n=4000, seed=0):
    r = np.random.default_rng(seed)
    x = np.asarray(x)
    m = [r.choice(x, len(x)).mean() for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])


def ann_funding(coin: str) -> pd.Series:
    """Funding diário médio, anualizado (positivo = longs pagam shorts)."""
    return funding_df(coin, DATA)["fundingRate"].astype(float).resample("D").mean() * 24 * 365


w = Wallet(USER, DATA)
fu = w.funding
expo = daily_exposure(fu)
coins = list(expo.columns)
idx = pd.date_range(START, END)

# --- Seção 3: PnL aproximado por mês e por moeda (preço + funding) contra o portfolio
title("PnL por mês (US$ mil): aproximado por moeda vs portfolio")
ap = approx_price_pnl(expo, w.opens(coins), w.closes(coins)).select_dtypes("number")
pm = ap.groupby(ap.index.to_period("M")).sum()
fm = fu.groupby([fu["t"].dt.to_period("M"), "coin"])["usdc"].sum().unstack().fillna(0)
tot = pm.add(fm, fill_value=0)
keep = tot.abs().sum() > 60_000
tab = tot.loc[:, keep].copy()
tab["outros"] = tot.loc[:, ~keep].sum(axis=1)
tab["soma"] = tot.sum(axis=1)
port = w.portfolio()["pnl"].resample("ME").last().diff()
port.index = port.index.to_period("M")
tab["portfolio"] = port
print((tab / 1e3).round(0))
print("total por moeda (US$ mil):", (tot.sum() / 1e3).round(0).sort_values().to_dict())
btc_px = ap["BTC"]
print(f"BTC preço quando short: {btc_px[expo['BTC'] < 0].sum() / 1e6:+.2f}M; quando long: "
      f"{btc_px[expo['BTC'] > 0].sum() / 1e6:+.2f}M; funding BTC: {fu.loc[fu.coin == 'BTC', 'usdc'].sum() / 1e6:+.2f}M")

# --- Seção 2: exposição média mensal por moeda em US$
title("Exposição média mensal (US$ mil)")
usd = expo * w.closes(coins).reindex(expo.index).ffill()
mu = usd.groupby(usd.index.to_period("M")).mean() / 1e3
print(mu.loc[:, mu.abs().max() > 100].round(0))
pos = expo["BTC"].reindex(idx).fillna(0)
print(f"BTC: posição média {pos.mean():.1f}, mediana {pos.median():.1f}; dias short (< -1 BTC) "
      f"{(pos < -1).mean():.0%}, long (> 1) {(pos > 1).mean():.0%}, ~zerado {(pos.abs() <= 1).mean():.0%}")

# --- Seção 2: o tamanho não reage ao preço
title("Posição diária de BTC x retornos anteriores")
kc = candles_df("BTC", "1d", DATA)
c = kc["close"]
ctx = pd.DataFrame({"r1": c.pct_change(), "r7": c.pct_change(7), "r30": c.pct_change(30),
                    "rng7": (c - kc["low"].rolling(7).min()) / (kc["high"].rolling(7).max() - kc["low"].rolling(7).min())
                    }).reindex(idx)
ctx["pos"] = expo["BTC"].reindex(idx).fillna(0)
ctx["dpos"] = ctx["pos"].diff()
print(ctx.corr().loc[["pos", "dpos"], ["r1", "r7", "r30", "rng7"]].round(2))

# --- Seção 2: o tamanho segue o funding da semana anterior
title("Posição média diária x funding médio dos 7 dias anteriores (a.a.)")
bins = [-9, 0, 0.05, 0.10, 0.15, 9]
for coin in ("BTC", "XMR", "xyz:SP500", "xyz:CL"):
    fr = ann_funding(coin)
    d = pd.DataFrame({"pos": expo[coin].reindex(idx).fillna(0),
                      "f7": fr.rolling(7).mean().shift(1).reindex(idx)}).dropna()
    if coin != "BTC":  # só os dias em que havia mercado e alguma posição no mês
        d = d[d["pos"].groupby(d.index.to_period("M")).transform(lambda s: s.abs().sum()) > 0]
    d["faixa"] = pd.cut(d["f7"], bins)
    print(f"\n{coin}: correlação posição x funding 7d anterior = {d['pos'].corr(d['f7']):+.2f}")
    print(d.groupby("faixa", observed=True)["pos"].agg(["mean", "median", "count"]).round(1))

# --- Seção 4: regra mecânica "short de BTC proporcional ao funding" (sem hedge e só o funding)
title("Regra: short BTC = 100 x clip((f7 - 0%) / 15%, 0, 1)")
k = candles_df("BTC", "1d", DATA)
fd = ann_funding("BTC")
f7 = fd.rolling(7).mean().shift(1)
first = fd.index.min() + pd.Timedelta(days=8)
ridx = k.index[(k.index >= first) & (k.index <= END)]
rpos = -(f7 / 0.15).clip(0, 1).reindex(ridx) * 100
px = rpos * (k["close"] - k["open"]).reindex(ridx)
fund = -rpos * k["close"].reindex(ridx) * fd.reindex(ridx) / 365
real = expo["BTC"].reindex(ridx).fillna(0)
for a, b in ((first.strftime("%Y-%m-%d"), "2025-05-22"), (START, END)):
    s = slice(a, b)
    c = rpos.loc[s].corr(real.loc[s]) if real.loc[s].abs().sum() else np.nan
    print(f"{a} → {b}: preço {px.loc[s].sum() / 1e6:+.2f}M, funding {fund.loc[s].sum() / 1e6:+.2f}M, "
          f"total {(px + fund).loc[s].sum() / 1e6:+.2f}M, correlação com a posição real {c:+.2f}")

title("O funding prevê o retorno de 7 dias do BTC? (por semana, IC 95% bootstrap)")
d = pd.DataFrame({"f7": f7, "fwd7": k["close"].shift(-7) / k["close"] - 1}).reindex(ridx).dropna()
d = d[d.index.dayofweek == 0]  # uma observação por semana: sem sobreposição
d["faixa"] = pd.cut(d["f7"], [-9, 0.05, 0.15, 9])
for fx, g in d.groupby("faixa", observed=True):
    lo, hi = boot_ci(g["fwd7"])
    print(f"funding {fx}: {len(g)} semanas, retorno 7d médio {g['fwd7'].mean():+.2%} (IC {lo:+.2%} a {hi:+.2%})")
print(f"correlação funding 7d x retorno 7d seguinte: {d['f7'].corr(d['fwd7']):+.2f}")

# --- Seção 5: fluxos de caixa contra o PnL
title("Fluxos externos x PnL diário aproximado")
L = w.ledger
ext = L[L["type"].isin(("deposit", "withdraw", "send")) & (L["counterparty"] != USER)]
flow = ext.groupby(ext["t"].dt.floor("D"))["usd"].sum().reindex(idx).fillna(0)
pnl = (ap.sum(axis=1).add(fu.groupby("day")["usdc"].sum(), fill_value=0)).reindex(idx).fillna(0)
for n in (1, 3, 7, 30):
    print(f"janela de {n:>2} dias: correlação fluxo x PnL = {flow.rolling(n).sum().corr(pnl.rolling(n).sum()):+.2f}")
print(f"dias com fluxo: {(flow != 0).mean():.0%}")
dep, wd = L[L["type"] == "deposit"], L[L["type"] == "withdraw"]
rnd = lambda s: (s.abs() % 5_000 < 1.5).mean()  # noqa: E731 (múltiplos de US$ 5k, com a taxa de US$ 1)
print(f"depósitos: {len(dep)}, US$ {dep['usd'].sum() / 1e6:.2f}M, mediana {dep['usd'].median():,.0f}, "
      f"redondos {rnd(dep['usd'] + 0):.0%}")
print(f"saques: {len(wd)}, US$ {wd['usd'].sum() / 1e6:.2f}M, mediana {wd['usd'].median():,.0f}, redondos {rnd(wd['usd'] - 1):.0%}")
s = L[L["type"] == "send"]
print(s.groupby("counterparty")["usd"].agg(["count", "sum"]))
print("send por mês:", (s.groupby(s["t"].dt.to_period("M"))["usd"].sum() / 1e3).round(0).to_dict())
eq = w.portfolio()["account_value"]
print(f"valor da conta: mediana {eq.median() / 1e3:.0f}k, máx {eq.max() / 1e3:.0f}k")

# --- Seção 6: execução
title("Execução (período das ordens)")
o = w.orders.drop_duplicates("oid", keep="last")
print(o["tif"].value_counts().to_dict(), "cloid:", int(o["cloid"].notna().sum()))
print("status final:", w.orders.loc[w.orders["status"] != "open"].drop_duplicates("oid")["status"].value_counts().to_dict())
oa = w.orders.sort_values("timestamp")
fin = oa[oa["status"] != "open"].drop_duplicates("oid")
life = (fin["statusTimestamp"] - fin["timestamp"]) / 1e3
print(f"tempo até executar (ordens executadas): mediana {life[fin['status'] == 'filled'].median():.0f} s")
rej = fin[fin["status"] == "badAloPxRejected"]
nxt = []
for _, r in rej.iterrows():  # próxima ordem da mesma moeda e lado depois da rejeição
    n = fin[(fin["coin"] == r["coin"]) & (fin["side"] == r["side"]) & (fin["timestamp"] > r["timestamp"])].head(1)
    if len(n):
        dt = (n["timestamp"].iloc[0] - r["timestamp"]) / 1e3
        dp = (float(n["limitPx"].iloc[0]) - float(r["limitPx"])) * (1 if r["side"] == "A" else -1)
        nxt.append((r["coin"], dt, dp / float(r["limitPx"]) * 1e4, float(n["origSz"].iloc[0]) == float(r["origSz"])))
nx = pd.DataFrame(nxt, columns=["coin", "s", "bp_mais_longe", "mesmo_tam"])
print(f"rejeições post-only: {len(rej)}; reenviadas em até 10 s: {(nx['s'] <= 10).mean():.0%}; "
      f"mediana {nx['s'].median():.1f} s; mais longe {(nx['bp_mais_longe'] > 0).mean():.0%} "
      f"(mediana {nx['bp_mais_longe'].median():.2f} bp); mesmo tamanho {nx['mesmo_tam'].mean():.0%}")
print(nx.groupby("coin")["s"].agg(["count", "median"]))
fl = w.fills
mk = (fl["ntl"] * ~fl["crossed"]).groupby(fl["coin"]).sum() / fl.groupby("coin")["ntl"].sum()
print("% maker (nocional):", mk.round(3).sort_values().to_dict())
print(f"taxas: US$ {fl['fee'].astype(float).sum():,.0f} sobre US$ {fl['ntl'].sum() / 1e6:.1f}M "
      f"({fl['fee'].astype(float).sum() / fl['ntl'].sum() * 1e4:.2f} bp)")
snap = json.load(open(os.path.join(DATA, USER, "snapshot.json")))
f = snap["userFees"]
print("taxa maker/taker:", f["userAddRate"], f["userCrossRate"], "desconto de staking:", f["activeStakingDiscount"])
print("staking:", snap["delegatorSummary"])
oo = pd.DataFrame(snap["frontendOpenOrders"])
print("ordens abertas:", oo[["coin", "side", "limitPx", "sz", "tif"]].to_dict("records"),
      pd.to_datetime(oo["timestamp"], unit="ms").min())

# --- Gráfico: posição de BTC x funding
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
p = expo["BTC"].reindex(idx).fillna(0)
a1.fill_between(p.index, p, 0, where=p < 0, color="#d62728", alpha=0.5, lw=0, label="short")
a1.fill_between(p.index, p, 0, where=p > 0, color="#1f77b4", alpha=0.5, lw=0, label="long")
a1.set_ylabel("posição média diária (BTC)")
a1.legend(loc="lower left")
a1.set_title("BTC: posição da carteira e funding da semana anterior")
f7d = f7.reindex(idx) * 100
a2.plot(f7d.index, f7d, color="#555")
a2.axhline(0, color="k", lw=0.6)
a2.axhline(15, color="#d62728", lw=0.6, ls="--")
a2.set_ylabel("funding 7d (% a.a.)")
fig.tight_layout()
os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
fig.savefig(os.path.join(OUT, "img", "btc_funding.png"), dpi=110)
print("\nimg/btc_funding.png gravado")
