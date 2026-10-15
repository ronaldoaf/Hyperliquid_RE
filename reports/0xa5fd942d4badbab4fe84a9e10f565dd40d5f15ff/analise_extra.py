"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff/analise_extra.py

Lê só os arquivos em data/. A API só entrega os fills de 29/mai/2026 em diante
(mais fatias antigas de TWAP), mas a conta opera desde dez/2024. Por isso:

1. capital e curva vêm do `portfolio` e do ledger;
2. antes dos fills, a posição diária por moeda vem do histórico de funding;
3. no período com fills, o PnL é exato e é comparado com a aproximação diária
   (posição média × movimento do dia) para medir o quanto vem de dentro do dia;
4. lotes FIFO dão o PnL por tempo de carregamento, classe, lado e tipo de
   execução (maker/taker na entrada e na saída);
5. contexto das entradas em alts e as escadas de ordens abertas hoje;
6. teste mecânico no universo inteiro: escada de compra X% abaixo do
   fechamento com alvo X% acima, contra comprar em qualquer dia.
"""
from __future__ import annotations

import json
import os
import sys
from collections import deque

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import (Wallet, approx_price_pnl, daily_exposure, exact_mtm,  # noqa: E402
                          executions)
from hlre.market import candles_df  # noqa: E402
from hlre.universe import week_bootstrap_diff  # noqa: E402

USER = "0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff"
DATA = os.path.join(ROOT, "data")
FILLS_FROM = pd.Timestamp("2026-05-29")
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def cat(coin: str) -> str:
    if ":" in coin:
        return "hip3"
    return "BTC/ETH" if coin in ("BTC", "ETH") else "alts"


def capital(w: Wallet):
    print("======== 1. Capital e curva")
    L = w.ledger
    print(L.loc[L["usd"] != 0, ["t", "type", "usd", "counterparty"]].round(0).to_string())
    print(f"entradas: {L.loc[L['usd'] > 0, 'usd'].sum():,.0f}  saídas: {L.loc[L['usd'] < 0, 'usd'].sum():,.0f}")
    a, p = w.portfolio("allTime"), w.portfolio("perpAllTime")
    m = pd.DataFrame({"equity": a["account_value"].resample("ME").last(), "pnl": a["pnl"].resample("ME").last(),
                      "pnl_perp": p["pnl"].resample("ME").last()})
    m["d_pnl"], m["d_perp"] = m["pnl"].diff(), m["pnl_perp"].diff()
    print(m.round(0).to_string())
    x = a[a.index >= "2024-12-01"]
    dd = x["pnl"] - x["pnl"].cummax()
    t1 = dd.idxmin()
    t0 = x["pnl"][:t1].idxmax()
    print(f"maior recuo: {dd.min():,.0f} de {t0:%Y-%m-%d} (equity {x.loc[t0, 'account_value']:,.0f}) "
          f"a {t1:%Y-%m-%d} (equity {x.loc[t1, 'account_value']:,.0f})")


def funding_book(w: Wallet):
    print("\n======== 2. Livro pela posição do funding (todo o histórico)")
    expo = daily_exposure(w.funding)
    cl = w.closes(expo.columns)
    usd = (expo * cl.reindex(expo.index)[expo.columns]).fillna(0.0)
    ap = approx_price_pnl(expo, w.opens(expo.columns), cl)
    n = (usd.abs() > 1000).sum(axis=1)
    book = pd.DataFrame({"moedas (mediana)": n, "long": usd.clip(lower=0).sum(axis=1),
                         "short": usd.clip(upper=0).sum(axis=1)})
    print(book[book.index >= "2024-12-01"].resample("QE").agg(
        {"moedas (mediana)": "median", "long": "mean", "short": "mean"}).round(0).to_string())
    by_cat = usd.T.groupby(usd.columns.map(cat)).sum().T
    print("correlação diária da posição líquida (US$) entre classes:")
    print(by_cat[by_cat.index >= "2025-01-01"].corr().round(2).to_string())
    fd = w.funding.groupby(["day", "coin"])["usdc"].sum().unstack().reindex(expo.index).fillna(0.0)
    pre = ap.index < FILLS_FROM
    tot = ap[pre].sum().add(fd[pre].sum(), fill_value=0.0).sort_values()
    print(f"antes dos fills, preço aprox. + funding por moeda ({(ap[pre].abs().sum() > 0).sum()} moedas):")
    print(pd.concat([tot.head(8), tot.tail(10)]).round(0).to_string())
    print("por classe (antes dos fills):", tot.groupby(tot.index.map(cat)).sum().round(0).to_dict())
    port = w.portfolio("perpAllTime")["pnl"]
    p0 = port[port.index <= "2024-12-01"].iloc[-1]
    p1 = port[port.index <= FILLS_FROM].iloc[-1]
    print(f"dez/2024 → 29/mai/2026: portfolio perp {p1 - p0:+,.0f} vs aproximação diária {tot.sum():+,.0f}")
    # o short de IP de fev/2025
    ip = w.funding[(w.funding["coin"] == "IP") & (w.funding["t"].between("2025-02-12", "2025-02-28"))]
    print(ip[["t", "szi", "fundingRate", "usdc"]].round(5).to_string())
    print(w.closes(["IP"]).loc["2025-02-14":"2025-02-27"].T.round(2).to_string())
    return ap


def fills_window(w: Wallet, ap: pd.DataFrame):
    print("\n======== 3. Período com fills (29/mai/2026 →): PnL exato")
    F = w.fills[(w.fills["t"] >= FILLS_FROM - pd.Timedelta(days=1)) & w.fills["kind"].isin(("perp", "hip3"))]
    cl = w.closes(sorted(F["coin"].unique()))
    m = exact_mtm(F, cl, end=cl.index.max())
    m = m[m.index >= FILLS_FROM]
    fund = w.funding[w.funding["t"] >= FILLS_FROM].groupby("coin")["usdc"].sum()
    tot = pd.DataFrame({"preço": m.sum(), "funding": fund, "taxas": -F.groupby("coin")["fee"].sum()}).fillna(0.0)
    tot["pnl"] = tot.sum(axis=1)
    port = w.portfolio("perpAllTime")["pnl"]
    print(f"portfolio perp no período: {port.iloc[-1] - port[port.index <= FILLS_FROM].iloc[-1]:+,.0f}; "
          f"soma por moeda: {tot['pnl'].sum():+,.0f}")
    print(tot.groupby(tot.index.map(cat)).sum().round(0).to_string())
    t = tot.sort_values("pnl")
    print(pd.concat([t.head(8), t.tail(10)]).round(0).to_string())
    a = ap[ap.index >= FILLS_FROM][m.columns]
    print(f"preço exato {m.values.sum():+,.0f} vs aproximação diária {a.values.sum():+,.0f} "
          f"→ dentro do dia {m.values.sum() - a.values.sum():+,.0f}")
    mm = pd.DataFrame({"aprox": a.sum(axis=1), "exato": m.sum(axis=1)}).resample("ME").sum()
    print(mm.round(0).to_string())
    return F


def fifo_lots(F: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for coin, g in F.sort_values("time", kind="mergesort").groupby("coin"):
        q = deque()
        p0 = g["startPosition"].iloc[0]
        if abs(p0) > 1e-12:
            q.append([p0, np.nan, pd.NaT, None])  # posição herdada: custo desconhecido
        for r in g.itertuples():
            x = r.q
            while abs(x) > 1e-12 and q and np.sign(q[0][0]) != np.sign(x):
                lot = q[0]
                k = min(abs(x), abs(lot[0]))
                s = np.sign(lot[0])
                rows.append({"coin": coin, "lado": "long" if s > 0 else "short", "t0": lot[2], "t1": r.t,
                             "ntl": k * r.px, "pnl": s * k * (r.px - lot[1]),
                             "entrada_taker": lot[3], "saida_taker": bool(r.crossed)})
                lot[0] -= s * k
                x += s * k
                if abs(lot[0]) < 1e-12:
                    q.popleft()
            if abs(x) > 1e-12:
                q.append([x, r.px, r.t, bool(r.crossed)])
    L = pd.DataFrame(rows).dropna(subset=["pnl"])
    L["horas"] = (L["t1"] - L["t0"]).dt.total_seconds() / 3600
    L["prazo"] = pd.cut(L["horas"], [-1, 1, 24, 24 * 7, 24 * 30, 1e9], labels=["<1h", "1h–1d", "1–7d", "7–30d", ">30d"])
    L["classe"] = L["coin"].map(cat)
    return L


def lots_and_execution(F: pd.DataFrame):
    print("\n======== 4. Lotes FIFO e execução")
    ex = executions(F)
    ex["taker"] = ex["taker"].astype(float) > 0.5
    op, cl = ex["dir"].str.startswith("Open"), ex["dir"].str.startswith("Close")
    mk = ex["ntl"] * ~ex["taker"]
    print(f"maker (nocional): total {mk.sum() / ex['ntl'].sum():.0%}, aberturas {mk[op].sum() / ex['ntl'][op].sum():.0%}, "
          f"fechamentos {mk[cl].sum() / ex['ntl'][cl].sum():.0%}")
    print(ex[cl].groupby("taker").agg(ordens=("oid", "size"), realizado=("closed_pnl", "sum"),
                                      com_lucro=("closed_pnl", lambda s: (s > 0).mean())).round(2).to_string())
    o = ex[op].copy()
    same = o.groupby(["coin", "side", o["sz"].round(6)])["oid"].transform("size")
    print(f"aberturas em degraus de tamanho igual (≥3 com o mesmo tamanho): {(same >= 3).mean():.0%} das ordens")
    print(ex.groupby(ex["coin"].map(cat)).apply(
        lambda d: pd.Series({"volume": d["ntl"].sum(), "maker": (d["ntl"] * ~d["taker"]).sum() / d["ntl"].sum()}),
        include_groups=False).round(2).to_string())
    L = fifo_lots(F)
    print(f"lotes fechados: PnL {L['pnl'].sum():+,.0f}; prazo mediano ponderado por nocional "
          f"{np.average(L['horas'], weights=L['ntl']) / 24:.1f} dias")
    print(L.pivot_table(index="classe", columns="prazo", values="pnl", aggfunc="sum", observed=False).round(0).to_string())
    print(L.pivot_table(index="classe", columns="lado", values="pnl", aggfunc="sum").round(0).to_string())
    print(L.groupby(["entrada_taker", "saida_taker"]).agg(nocional=("ntl", "sum"), pnl=("pnl", "sum")).round(0).to_string())
    print("UTC, execuções por hora:", ex.groupby(ex["t"].dt.hour).size().to_dict())


def entry_context(F: pd.DataFrame):
    print("\n======== 5. Contexto das aberturas em alts (candles de 4h)")
    A = F[F["dir"].str.startswith("Open") & (F["kind"] == "perp") & ~F["coin"].isin(["BTC", "ETH"])]
    rows, base = [], []
    for coin, g in A.groupby("coin"):
        c = candles_df(coin, "4h", DATA)
        hi7, cl = c["high"].rolling(42).max(), c["close"]
        w30 = c[c.index >= FILLS_FROM]["close"]
        base.append(pd.DataFrame({"1d": w30.shift(-6) / w30 - 1, "7d": w30.shift(-42) / w30 - 1}))
        for r in g.itertuples():
            i = c.index.searchsorted(r.t, side="right") - 1
            if i < 43:
                continue
            fwd = {h: (cl.iloc[i + n] / r.px - 1 if i + n < len(c) else np.nan) for h, n in (("1d", 6), ("7d", 42))}
            rows.append({"lado": "compra" if r.side == "B" else "venda", "taker": bool(r.crossed), "ntl": r.ntl,
                         "vs máx. 7d": r.px / hi7.iloc[i] - 1, "ret. 7d antes": cl.iloc[i - 1] / cl.iloc[i - 43] - 1,
                         "posição na vela 4h": (r.px - c["low"].iloc[i]) / (c["high"].iloc[i] - c["low"].iloc[i] + 1e-12),
                         **fwd})
    D = pd.DataFrame(rows)

    def agg(d):
        wavg = lambda col: np.average(d[col].dropna(), weights=d.loc[d[col].notna(), "ntl"])  # noqa: E731
        return pd.Series({"fills": len(d), "nocional": d["ntl"].sum(), "vs máx. 7d": wavg("vs máx. 7d"),
                          "ret. 7d antes (mediana)": d["ret. 7d antes"].median(),
                          "posição na vela 4h": wavg("posição na vela 4h"), "1d depois": wavg("1d"),
                          "7d depois": wavg("7d")})
    print(D.groupby(["lado", "taker"]).apply(agg, include_groups=False).round(3).to_string())
    print("base (qualquer vela de 4h das mesmas moedas):", pd.concat(base).mean().round(3).to_dict())


def open_orders(w: Wallet):
    print("\n======== 6. Ordens abertas agora (escadas)")
    s = w.snapshot
    o = pd.DataFrame(s["frontendOpenOrders"])
    for c in ("limitPx", "sz"):
        o[c] = o[c].astype(float)
    mark = {p["position"]["coin"]: float(p["position"]["positionValue"]) / abs(float(p["position"]["szi"]))
            for p in s["clearinghouseState"]["assetPositions"]}
    o["dist"] = o["limitPx"] / o["coin"].map(mark) - 1
    o["ntl"] = o["limitPx"] * o["sz"]
    o["criada"] = pd.to_datetime(o["timestamp"], unit="ms")
    print(f"{len(o)} ordens, compra US$ {o.loc[o['side'] == 'B', 'ntl'].sum():,.0f}, "
          f"venda US$ {o.loc[o['side'] == 'A', 'ntl'].sum():,.0f}; tipos {o['orderType'].value_counts().to_dict()}")
    lad = o[~o["reduceOnly"]].groupby(["coin", "side"]).agg(
        ordens=("oid", "size"), nocional=("ntl", "sum"), dist_min=("dist", "min"), dist_max=("dist", "max"),
        criada=("criada", "min"), lotes=("timestamp", "nunique"))
    print(lad[lad["ordens"] >= 5].round(3).to_string())
    P = pd.DataFrame([{"coin": p["position"]["coin"], "szi": float(p["position"]["szi"]),
                       "ntl": float(p["position"]["positionValue"]), "upnl": float(p["position"]["unrealizedPnl"])}
                      for p in s["clearinghouseState"]["assetPositions"]])
    P["lado"] = np.where(P["szi"] > 0, "long", "short")
    print(P.groupby("lado").agg(n=("coin", "size"), nocional=("ntl", "sum"), nao_realizado=("upnl", "sum")).round(0).to_string())


def funding_cost(w: Wallet):
    print("\n======== 7. Funding")
    fu = w.funding.assign(lado=np.where(w.funding["szi"] > 0, "long", "short"))
    print(fu.groupby("lado")["usdc"].sum().round(0).to_dict())
    print(fu.groupby(["coin", "lado"])["usdc"].sum().sort_values().head(10).round(0).to_string())


def universe_ladder():
    print("\n======== 8. Universo: escada de compra com alvo, contra comprar em qualquer dia")
    with open(os.path.join(DATA, "market", "universe.json")) as f:
        uni = json.load(f)
    P = {n: candles_df(n, "1d", DATA) for n, _ in uni if n not in ("BTC", "ETH")}
    P = {k: v for k, v in P.items() if len(v) >= 31}
    O, H, Lo, C = (pd.DataFrame({k: v[c] for k, v in P.items()}).sort_index() for c in ("open", "high", "low", "close"))
    o, h, lo, c = O.values, H.values, Lo.values, C.values
    age = np.cumsum(~np.isnan(c), axis=0)
    r30 = (C / C.shift(30) - 1).values
    idx = C.index

    def run(d, hold, start, end, ladder=True):
        rows = []
        s, e = idx.searchsorted(pd.Timestamp(start)), idx.searchsorted(pd.Timestamp(end))
        for t in range(s, min(e, len(idx) - hold - 2)):
            for j in range(c.shape[1]):
                if age[t, j] < 31 or np.isnan(c[t, j]) or np.isnan(o[t + 1, j]):
                    continue
                if ladder:  # limite d abaixo do fechamento, válido no dia seguinte
                    lim = c[t, j] * (1 - d)
                    if not lo[t + 1, j] <= lim:
                        continue
                    ent = min(o[t + 1, j], lim)
                else:
                    ent = o[t + 1, j]
                tgt, ex = ent * (1 + d), np.nan
                for k in range(t + 2, t + 2 + hold):  # alvo a partir do dia seguinte ao fill
                    if np.isnan(h[k, j]):
                        break
                    if h[k, j] >= tgt:
                        ex = max(tgt, o[k, j])
                        break
                else:
                    ex = c[t + 1 + hold, j]
                if np.isfinite(ex):
                    rows.append((idx[t], ex / ent - 1 - 0.0003, r30[t, j]))
        return pd.DataFrame(rows, columns=["t", "ret", "r30"])

    out = []
    for a, b in (("2024-12-01", "2025-10-31"), ("2025-11-01", "2026-09-10")):
        base = run(0.10, 30, a, b, ladder=False)
        for d in (0.05, 0.10, 0.20):
            ev = run(d, 30, a, b)
            for lab, me, mb in (("todas", ev["r30"] == ev["r30"], base["r30"] == base["r30"]),
                                ("30d > 0", ev["r30"] > 0, base["r30"] > 0)):
                e2, b2 = ev[me], base[mb]
                lo_, hi_ = week_bootstrap_diff(e2, b2)
                out.append({"período": f"{a} → {b}", "queda/alvo": f"{d:.0%}", "filtro": lab, "trades": len(e2),
                            "média": e2["ret"].mean() * 100, "% com lucro": (e2["ret"] > 0).mean() * 100,
                            "pior 10%": e2["ret"].quantile(0.1) * 100, "base": b2["ret"].mean() * 100,
                            "diferença": (e2["ret"].mean() - b2["ret"].mean()) * 100,
                            "IC95": f"[{lo_ * 100:+.1f}, {hi_ * 100:+.1f}]"})
    print(pd.DataFrame(out).round(2).to_string())


def copy_delay(w: Wallet, F: pd.DataFrame):
    print("\n======== 9. Copiar cada execução com ~30 min de atraso (mercado, taxa taker)")
    # O preço "depois" é a abertura do próximo candle, nunca o candle do próprio fill
    # (que costuma ser o pavio): 1h → atraso de 0–60 min (média 30); 15m a partir de
    # t + 22,5 min → 22,5–37,5 min. Candles de 1h e 15m: python -m hlre.market <moedas> --intervals 1h 15m
    ex = executions(F[F["t"] >= FILLS_FROM])
    ex["taker"] = ex["taker"].astype(float) > 0.5
    C = {iv: {c: candles_df(c, iv, DATA) for c in ex["coin"].unique()} for iv in ("1h", "15m")}

    def next_open(coin, ts, iv):
        d = C[iv][coin]
        i = d.index.searchsorted(ts, side="left")
        return d["open"].iloc[i] if i < len(d) and d.index[i] - ts < pd.Timedelta("2h") else np.nan

    ex["pend"] = ex["coin"].map({c: C["1h"][c]["close"].iloc[-1] for c in ex["coin"].unique()})

    def sim(s, p):
        ok = ~np.isnan(p)
        s, p = s[ok], p[ok]
        wal = (s["q"] * (s["pend"] - s["vwap"])).sum() - s["fee"].sum()
        cop = (s["q"] * (s["pend"] - p)).sum() - (0.00045 * s["q"].abs() * p).sum()
        return pd.Series({"execuções": len(s), "carteira": wal, "cópia": cop,
                          "preço pior": (s["q"] * (s["vwap"] - p)).sum(),
                          "taxa extra": s["fee"].sum() - (0.00045 * s["q"].abs() * p).sum(), "fica com": cop / wal})

    for lab, sh in (("~30 min", "0h"), ("4h", "3.5h"), ("24h", "23.5h")):
        p = np.array([next_open(c, t + pd.Timedelta(sh), "1h") for c, t in zip(ex["coin"], ex["t"])])
        if lab == "~30 min":
            ex["p30"] = p
        print(lab, sim(ex, p).round(2).to_dict())
    start15 = max(d.index[0] for d in C["15m"].values()) + pd.Timedelta("1h")
    s = ex[ex["t"] >= start15]
    p15 = np.array([next_open(c, t + pd.Timedelta("22.5min"), "15m") for c, t in zip(s["coin"], s["t"])])
    print(f"desde {start15:%Y-%m-%d}:", pd.DataFrame({"15m": sim(s, p15), "1h": sim(s, s["p30"].values)}).round(2).to_string())
    g = {k: sim(d, d["p30"].values) for k, d in ex.groupby(ex["coin"].map(cat))}
    g["entrada maker"] = sim(ex[~ex["taker"]], ex.loc[~ex["taker"], "p30"].values)
    g["entrada taker"] = sim(ex[ex["taker"]], ex.loc[ex["taker"], "p30"].values)
    print(pd.DataFrame(g).round(2).to_string())
    print(pd.DataFrame({k: sim(d, d["p30"].values) for k, d in ex.groupby("coin")
                        if k in ("LIT", "MET", "HYPE", "VIRTUAL", "CASHCAT", "ENA", "XMR", "REZ", "BTC", "ETH")}
                       ).T[["carteira", "cópia", "fica com"]].round(2).to_string())
    # espelhar as escadas: quantas execuções maker vieram de ordens com mais de 30 min no livro
    first = w.orders.groupby("oid")["timestamp"].min()
    m = ex[~ex["taker"]].join(first, on="oid").dropna(subset=["timestamp"])
    age = (m["t"] - pd.to_datetime(m["timestamp"], unit="ms")).dt.total_seconds() / 60
    print(f"execuções maker com hora de criação conhecida: {len(m)} de {(~ex['taker']).sum()}; ordem com ≥30 min no livro: "
          f"{(age >= 30).mean():.0%} das execuções, {m.loc[age >= 30, 'ntl'].sum() / m['ntl'].sum():.0%} do nocional")


def main():
    w = Wallet(USER, DATA)
    capital(w)
    ap = funding_book(w)
    F = fills_window(w, ap)
    lots_and_execution(F)
    entry_context(F)
    open_orders(w)
    funding_cost(w)
    copy_delay(w, F)
    universe_ladder()


if __name__ == "__main__":
    main()
