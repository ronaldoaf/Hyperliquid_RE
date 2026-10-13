"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2/analise_extra.py

Lê os arquivos em data/ (os mesmos do relatório) e grava img/livros.png. A única
chamada de rede é a dos fills da subconta "Liminal 1" (seção 1).
Cada bloco indica a seção do ANALISE.md que ele sustenta.

Posições diárias: vêm do histórico de funding (tamanho médio do dia, desde jun/2024),
porque os fills só cobrem jun/2026 em diante e as fatias de TWAP antigas não existem
mais na API. "Carry" = posição média do dia anterior × retorno close→close do dia, ou seja,
o que ganharia quem copiasse a posição com ~1 dia de atraso.
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, daily_exposure, position_gaps  # noqa: E402
from hlre.api import InfoClient  # noqa: E402

USER = "0x0748e296e5a350ec36c8487a1cea406e1b57d4b2"
SUB = "0xfa2dbdbee70ff0b29171670573a1fff1a02d1ca2"  # subconta "Liminal 1"
DATA = os.path.join(ROOT, "data")
OUT = os.path.dirname(os.path.abspath(__file__))
SPOT = {"@188": "UPUMP", "@107": "HYPE", "@156": "USOL", "@142": "UBTC"}
# cestas da tese (seção 3.3): nomes que a carteira mais carregou de cada lado
LONG = ["AAVE", "UNI", "LDO", "PENDLE", "MKR", "ENA", "JUP", "AERO", "JTO", "RUNE", "HYPE", "PUMP", "ZEC"]
SHORT = ["ADA", "XLM", "XRP", "SUI", "AVAX", "APT", "HBAR", "TON", "INJ", "IP", "WLD", "WLFI", "TRUMP", "BERA",
         "MON", "XPL", "LAYER"]
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def title(s: str):
    print(f"\n{'=' * 8} {s}")


def alpha(r: pd.Series, rb: pd.Series, n=2000, seed=0) -> str:
    x = pd.concat([r, rb], axis=1, join="inner").dropna()
    b = np.polyfit(x.iloc[:, 1], x.iloc[:, 0], 1)[0]
    res = (x.iloc[:, 0] - b * x.iloc[:, 1]).values
    rng = np.random.default_rng(seed)
    boot = [rng.choice(res, len(res)).mean() * 365 for _ in range(n)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    t = res.mean() / res.std() * np.sqrt(len(res))
    return (f"n={len(x):4d} retorno/ano {365 * x.iloc[:, 0].mean():+.0%} beta {b:+.2f} "
            f"alfa/ano {365 * res.mean():+.0%} (IC95 {lo:+.0%} a {hi:+.0%}) t={t:.2f}")


def main():
    w = Wallet(USER, DATA)
    f, L = w.fills, w.ledger

    # posição diária em US$ por moeda (funding) e retornos diários
    E = daily_exposure(w.funding)
    C = w.closes(list(E.columns)).reindex(E.index).ffill()
    N = E * C
    R = w.closes(list(N.columns)).reindex(N.index).pct_change(fill_method=None)
    W = N.shift(1)

    title("1. Quem é: execução, subconta, referral")
    o = w.orders
    print(o["tif"].value_counts().to_string())
    print("ordens com cloid (todas ALO):", int(o["cloid"].notna().sum()),
          "| moedas:", o.loc[o["cloid"].notna(), "coin"].unique().tolist())
    rl = w.snapshot["userRateLimit"]
    print(f"requisições {rl['nRequestsUsed']:,} para volume acumulado US$ {float(rl['cumVlm']):,.0f}")
    print("referral:", w.snapshot["referral"]["referredBy"], "| extraAgents:", w.snapshot["extraAgents"])
    tw = f[f["twapId"].notna()]
    print(f"fatias de TWAP guardadas: {len(tw)} ({tw['t'].min():%Y-%m-%d} → {tw['t'].max():%Y-%m-%d}), "
          f"US$ {tw['ntl'].sum():,.0f}")
    print(tw.groupby(["coin", "twapId"]).agg(n=("q", "size"), q=("q", "sum"), ntl=("ntl", "sum"),
                                              t0=("t", "min"), t1=("t", "max")).to_string())
    g = position_gaps(f)
    print(f"saltos de posição sem fill visível: {len(g)}, ~US$ {g['jump_ntl'].sum():,.0f}")
    print(g.groupby("coin")["jump_ntl"].sum().sort_values(ascending=False).round(0).to_string())
    lq = f[f["liquidation"].notna()]
    own = lq[lq["liquidation"].map(lambda d: d["liquidatedUser"].lower() == USER)]
    print(f"liquidações da própria carteira: {own['coin'].unique().tolist()} "
          f"{own['t'].min():%Y-%m-%d}, US$ {own['ntl'].sum():,.0f}, PnL {own['closedPnl'].sum():,.0f}")
    try:
        sub = pd.DataFrame(InfoClient().post({"type": "userFills", "user": SUB}))
        sub["ntl"] = sub["px"].astype(float) * sub["sz"].astype(float)
        sub["t"] = pd.to_datetime(sub["time"], unit="ms")
        print("subconta Liminal 1:")
        print(sub.groupby(["coin", "dir"]).agg(n=("ntl", "size"), ntl=("ntl", "sum"), t0=("t", "min"),
                                                pnl=("closedPnl", lambda x: x.astype(float).sum())).round(0).to_string())
    except Exception as e:  # sem rede: o resto do script não depende disso
        print("subconta: sem acesso à API:", e)

    title("2. Dinheiro: entradas e saídas externas")
    x = L[L["type"].isin(["deposit", "withdraw", "send", "spotTransfer"])].copy()
    x = x[x["counterparty"].fillna("").str.lower() != USER]
    x["grupo"] = x["type"] + ":" + x["token"].astype(str)
    print(x.groupby("grupo")["usd"].agg(["sum", "count"]).round(0).sort_values("sum").to_string())
    print(f"entrou US$ {x.loc[x['usd'] > 0, 'usd'].sum():,.0f} | saiu US$ {-x.loc[x['usd'] < 0, 'usd'].sum():,.0f} | "
          f"líquido US$ {x['usd'].sum():,.0f}")
    print(x.set_index("t")["usd"].resample("QS").sum().round(0).to_string())
    for tok in ["HYPE", "USOL", "UBTC", "UPUMP"]:
        y = x[x["token"] == tok]
        print(f"{tok}: entrou US$ {y.loc[y['usd'] > 0, 'usd'].sum():,.0f} ({y.loc[y['usd'] > 0, 'amount'].sum():,.0f}) | "
              f"saiu US$ {-y.loc[y['usd'] < 0, 'usd'].sum():,.0f} ({y.loc[y['usd'] < 0, 'amount'].sum():,.0f}) desde "
              f"{y['t'].min():%Y-%m}")
    pa = w.portfolio("allTime")
    print(f"patrimônio desde jul/2025: US$ {pa.loc['2025-07-01':, 'account_value'].min():,.0f} a "
          f"US$ {pa.loc['2025-07-01':, 'account_value'].max():,.0f}; PnL no período "
          f"US$ {pa['pnl'].iloc[-1] - pa['pnl'].asof(pd.Timestamp('2025-07-01')):,.0f}")
    gen = L[L["type"] == "spotGenesis"][["t", "token", "amount"]]
    print("airdrops (spotGenesis):"); print(gen.to_string())
    stk = L[L["type"] == "cStakingTransfer"]
    print("staking de HYPE:", stk[["t", "amount"]].to_string(), "| delegado agora:",
          w.snapshot["delegatorSummary"]["delegated"])

    title("3.1 O livro por trimestre (média diária em US$)")
    q = N.resample("QS").mean()
    for d, row in q.iterrows():
        r = row[row.abs() > 5e4]
        lo = ", ".join(f"{c} {v / 1e3:.0f}k" for c, v in r[r > 0].sort_values(ascending=False).head(7).items())
        sh = ", ".join(f"{c} {v / 1e3:.0f}k" for c, v in r[r < 0].sort_values().head(7).items())
        print(f"{d:%Y-%m} LONG: {lo} | SHORT: {sh}")
    av = w.portfolio("allTime")["account_value"].resample("D").last().ffill().reindex(N.index).ffill()
    lng = N.clip(lower=0).sum(axis=1)
    sht = -N.clip(upper=0).sum(axis=1)
    lev = pd.DataFrame({"bruta_x": (lng + sht) / av, "liquida_x": (lng - sht) / av,
                        "short/long": sht / lng.replace(0, np.nan), "posições": (N.abs() > 2e4).sum(axis=1),
                        "patrimônio": av})
    print(lev.resample("QS").median().round(2).to_string())
    runs = []
    for c in N.columns:
        s = (N[c].abs() > 2e4).astype(int)
        grp = (s.diff() != 0).cumsum()
        rr = s.groupby(grp).agg(["first", "size"])
        runs += list(rr[rr["first"] == 1]["size"])
    runs = pd.Series(runs)
    print(f"duração das posições (dias): n={len(runs)} mediana {runs.median():.0f} p75 {runs.quantile(.75):.0f} "
          f"p90 {runs.quantile(.9):.0f}")

    title("3.2 PnL de carry por livro e por moeda")
    D = W * R
    dl, ds = D.where(W > 0).sum(axis=1), D.where(W < 0).sum(axis=1)
    print(pd.DataFrame({"long": dl, "short": ds, "total": dl + ds}).resample("QS").sum().round(0).to_string())
    print(f"total carry: long {dl.sum():,.0f} short {ds.sum():,.0f}; correlação diária long×short "
          f"{np.corrcoef(dl[(W > 0).any(axis=1) & (W < 0).any(axis=1)], ds[(W > 0).any(axis=1) & (W < 0).any(axis=1)])[0, 1]:.2f}")
    print("short, por moeda:"); print(D.where(W < 0).sum().sort_values().round(0)[lambda s: s.abs() > 5e4].to_string())
    print("long, por moeda:"); print(D.where(W > 0).sum().sort_values().round(0)[lambda s: s.abs() > 5e4].to_string())
    print("melhores dias do short:")
    for d in ds.nlargest(4).index:
        print(f"  {d:%Y-%m-%d} {ds[d]:,.0f}", D.loc[d].where(W.loc[d] < 0).dropna().nlargest(3).round(0).to_dict())
    fund = w.funding.groupby("coin")["usdc"].sum()
    print(f"funding total {fund.sum():,.0f} (longs {fund[fund.index.isin(N.columns[(N > 0).sum() > (N < 0).sum()])].sum():,.0f})")

    title("3.3 Alfa: beta ao BTC e comparação com cestas estáticas")
    rb = R["BTC"]
    Lw, Sw = W.clip(lower=0), -W.clip(upper=0)
    rlb = (Lw * R).sum(axis=1, min_count=1) / Lw.sum(axis=1)
    rsb = -(Sw * R).sum(axis=1, min_count=1) / Sw.sum(axis=1)  # ganho do short
    okl, oks = Lw.sum(axis=1) > 2e5, Sw.sum(axis=1) > 2e5
    alts = R[[c for c in N.columns if ":" not in c]].mean(axis=1)
    print("livro long          ", alpha(rlb[okl], rb))
    print("livro short (ganho) ", alpha(rsb[oks], rb))
    print("long − média das alts", alpha((rlb - alts)[okl], rb))
    print("média das alts − short", alpha((alts + rsb)[oks], rb))
    print("livro inteiro/US$ bruto", alpha(((W * R).sum(axis=1) / W.abs().sum(axis=1))[W.abs().sum(axis=1) > 5e5], rb))
    no_om = D.drop(columns=["OM"]).where(W.drop(columns=["OM"]) < 0).sum(axis=1)
    print(f"carry do short sem OM: {no_om.sum():,.0f}")
    CB = w.closes(LONG + SHORT + ["BTC"]).loc[N.index.min():N.index.max()].pct_change(fill_method=None)
    bl, bs = CB[LONG].mean(axis=1), CB[SHORT].mean(axis=1)
    for name, r in [("cesta long", bl), ("cesta short", bs), ("BTC", CB["BTC"]), ("long − short", bl - bs)]:
        r = r.dropna()
        print(f"{name:14s} retorno/ano {365 * r.mean():+.0%} vol {np.sqrt(365) * r.std():.0%} "
              f"sharpe {np.sqrt(365) * r.mean() / r.std():.2f}")
    for y in ["2024", "2025", "2026"]:
        r = (bl - bs).loc[y].dropna()
        print(f"  {y} long−short {365 * r.mean():+.0%} sharpe {np.sqrt(365) * r.mean() / r.std():.2f}")
    # fora da amostra: cestas com o que carregou no 1º ano (média > US$ 20k), testadas depois
    m = N.loc[:"2025-06-30"].mean()
    L1 = [c for c in m.index if m[c] > 2e4 and ":" not in c]
    S1 = [c for c in m.index if m[c] < -2e4 and ":" not in c]
    RT = w.closes(L1 + S1 + ["BTC"]).pct_change(fill_method=None).loc["2025-07-01":N.index.max()]
    ls = (RT[L1].mean(axis=1) - RT[S1].mean(axis=1)).dropna()
    rng = np.random.default_rng(0)
    wk = ls.groupby(ls.index.to_period("W")).sum().values  # bootstrap por semanas
    lo, hi = np.percentile([rng.choice(wk, len(wk)).mean() * 52 for _ in range(4000)], [2.5, 97.5])
    print(f"fora da amostra: long {L1} | short {S1}")
    print(f"  jul/2025 → fim: long {365 * RT[L1].mean(axis=1).mean():+.0%}/ano, short {365 * RT[S1].mean(axis=1).mean():+.0%}/ano, "
          f"BTC {365 * RT['BTC'].mean():+.0%}/ano; long−short {365 * ls.mean():+.0%}/ano (IC95 {lo:+.0%} a {hi:+.0%}), "
          f"sharpe {np.sqrt(365) * ls.mean() / ls.std():.2f}")
    static = lng.shift(1) * bl.reindex(N.index).fillna(0) - sht.shift(1) * bs.reindex(N.index).fillna(0)
    real = D.sum(axis=1)
    print(f"carry real {real.sum():,.0f} | mesmo US$ long/short nas cestas fixas {static.sum():,.0f}")
    print(pd.DataFrame({"real": real, "cestas fixas": static}).resample("QS").sum().round(0).to_string())

    title("3.4 Contexto das mudanças de posição (dias com variação > US$ 100k)")
    cols = [c for c in E.columns if ":" not in c]
    r7, r30 = C[cols].pct_change(7, fill_method=None), C[cols].pct_change(30, fill_method=None)
    hi30 = C[cols] / C[cols].rolling(30).max() - 1
    f7 = C[cols].shift(-7) / C[cols] - 1
    dE = E[cols].diff()
    rows = []
    for c in cols:
        for d in dE.index[dE[c].abs() * C[c] > 1e5]:
            pos, new, ch = E[c].shift(1).loc[d], E[c].loc[d], dE[c].loc[d]
            kind = ("aumenta long" if ch > 0 and new > 0 and pos >= 0 else
                    "reduz long" if ch < 0 and pos > 0 and new >= 0 else
                    "aumenta short" if ch < 0 and new < 0 and pos <= 0 else
                    "reduz short" if ch > 0 and pos < 0 and new <= 0 else "inverte")
            rows.append({"tipo": kind, "r7": r7[c].shift(1).loc[d], "r30": r30[c].shift(1).loc[d],
                         "hi30": hi30[c].shift(1).loc[d], "f7": f7[c].loc[d]})
    X = pd.DataFrame(rows)
    base = pd.DataFrame({"r7": r7.stack(), "r30": r30.stack(), "hi30": hi30.stack(), "f7": f7.stack()})
    print(X.groupby("tipo").agg(n=("r7", "size"), r7=("r7", "median"), r30=("r30", "median"),
                                hi30=("hi30", "median"), f7=("f7", "median")).round(3).to_string())
    print("base (todas as moedas-dia):", base.median().round(3).to_dict())
    for k in ["aumenta long", "aumenta short", "reduz long"]:
        s = X[X["tipo"] == k]
        print(k, {v: round(mannwhitneyu(s[v].dropna(), base[v].dropna()).pvalue, 4) for v in ["r7", "r30", "hi30", "f7"]})

    title("4. Spot")
    for coin, name in SPOT.items():
        s = f[f["coin"] == coin]
        if not len(s):
            continue
        g = s.groupby([s["t"].dt.date, "side"]).apply(
            lambda x: pd.Series({"qtd": x["sz"].sum(), "vwap": (x["ntl"]).sum() / x["sz"].sum(), "usd": x["ntl"].sum(),
                                 "pnl": x["closedPnl"].sum()}), include_groups=False)
        print(name); print(g.round(5).to_string())
    print("saldos spot agora:", [(b["coin"], round(float(b["total"]))) for b in
                                 w.snapshot["spotClearinghouseState"]["balances"] if float(b["total"]) > 1])

    title("5. Copiar com atraso (carry, sem custos)")
    for lag in [1, 2, 3, 7, 14]:
        Wl = N.shift(lag)
        print(f"{lag:2d} dia(s): total {(Wl * R).sum().sum():>12,.0f} | long {(Wl.clip(lower=0) * R).sum().sum():>12,.0f}"
              f" | short {(Wl.clip(upper=0) * R).sum().sum():>12,.0f}")

    title("5b. PnL real de preço (portfolio − funding) vs carry, por trimestre")
    pp = w.portfolio("perpAllTime")["pnl"].resample("D").last().ffill()
    rec = pd.DataFrame({"perp (portfolio)": pp.diff(), "funding": w.funding.groupby("day")["usdc"].sum(),
                        "carry": D.sum(axis=1)}).resample("QS").sum()
    rec["preço real"] = rec["perp (portfolio)"] - rec["funding"]
    rec["dentro do dia"] = rec["preço real"] - rec["carry"]
    print(rec.round(0).to_string()); print(rec.sum().round(0).to_string())
    x10 = N.loc["2025-10-07":"2025-10-14"]
    print("crash de 10/out/2025, livro (média diária):")
    print(pd.DataFrame({"long": x10.clip(lower=0).sum(axis=1), "short": x10.clip(upper=0).sum(axis=1)}).round(0).to_string())
    print("OM:", N["OM"][N["OM"].abs() > 1].round(0).to_dict())
    tp = pd.DataFrame(w.snapshot["frontendOpenOrders"])
    ent = {p["position"]["coin"]: float(p["position"]["entryPx"]) for p in w.snapshot["clearinghouseState"]["assetPositions"]}
    tp["vs entrada"] = tp.apply(lambda r: float(r["triggerPx"]) / ent[r["coin"]] - 1 if r["coin"] in ent else np.nan, axis=1)
    print("TP/SL abertos:"); print(tp[["coin", "orderType", "triggerPx", "vs entrada"]].round(3).to_string())

    title("6. Drawdown (portfolio all-time)")
    pnl = w.portfolio("allTime")["pnl"]
    dd = pnl - pnl.cummax()
    print(f"maior drawdown {dd.min():,.0f}: pico {pnl.loc[:dd.idxmin()].idxmax():%Y-%m-%d} → fundo {dd.idxmin():%Y-%m-%d}")
    print(pnl.resample("QS").last().diff().round(0).to_string())

    # gráfico: carry acumulado de cada livro + exposição bruta e líquida
    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    ax[0].plot(dl.cumsum() / 1e6, color="#2f6fb0", label="livro long")
    ax[0].plot(ds.cumsum() / 1e6, color="#c0392b", label="livro short")
    ax[0].plot((dl + ds).cumsum() / 1e6, color="#333", lw=1.6, label="total")
    ax[0].axhline(0, color="#999", lw=0.6)
    ax[0].set_ylabel("US$ milhões")
    ax[0].set_title("PnL de carregar a posição (média do dia anterior × retorno do dia), por livro")
    ax[0].legend(frameon=False, loc="upper left")
    ax[1].fill_between(N.index, lng / 1e6, color="#2f6fb0", alpha=0.35, lw=0, label="long")
    ax[1].fill_between(N.index, -sht / 1e6, color="#c0392b", alpha=0.35, lw=0, label="short")
    ax[1].plot(N.index, (lng - sht) / 1e6, color="#333", lw=1, label="líquido")
    ax[1].set_ylabel("US$ milhões")
    ax[1].set_title("Exposição em perps")
    ax[1].legend(frameon=False, loc="upper left", ncol=3)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
    fig.savefig(os.path.join(OUT, "img", "livros.png"), dpi=130)
    print("\ngrava img/livros.png")


if __name__ == "__main__":
    main()
