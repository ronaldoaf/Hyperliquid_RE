"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0xfce053a5e461683454bf37ad66d20344c0e3f4c0/analise_extra.py [--online]

Lê só os arquivos em data/ (os mesmos do relatório). `--online` acrescenta o
perfil da carteira de serviço 0x6b9e…, que precisa de uma chamada à API.
Cada bloco indica a seção do ANALISE.md que ele sustenta. Se os dados forem
atualizados (novo `hlre.run`), os números que dependem de preço atual e de
posições abertas mudam.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import (  # noqa: E402
    Wallet, averaging_stats, copy_lag_pnl, daily_exposure, episode_metrics, exact_mtm, executions, sessions,
)
from hlre.binance import klines_df  # noqa: E402
from hlre.market import candles_df, hourly_close  # noqa: E402

USER = "0xfce053a5e461683454bf37ad66d20344c0e3f4c0"
SERVICE = "0x6b9e773128f453f5c2c60935ee2de2cbc5390a24"
DATA = os.path.join(ROOT, "data")
PHASES = {
    "1: dez/24–fev/25": ("2024-12-01", "2025-02-28"),
    "pausa: mar–abr/25": ("2025-03-01", "2025-04-28"),
    "2: 29/abr/25–10/out/25": ("2025-04-29", "2025-10-10"),
    "3: 11/out/25–11/jun/26": ("2025-10-11", "2026-06-11"),
    "4: 12/jun/26–hoje": ("2026-06-12", "2026-12-31"),
}
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def title(s: str):
    print(f"\n{'=' * 8} {s}")


def group_of(coin: str) -> str:
    if coin in ("BTC", "ETH"):
        return "BTC/ETH"
    if coin.startswith("xyz:"):
        return "HIP-3"
    return "HYPE perp" if coin == "HYPE" else "alts e memecoins"


def pnl_by_coin_day(w: Wallet, pf: pd.DataFrame) -> dict:
    cl = w.closes(sorted(pf["coin"].unique()), "1d")
    price = exact_mtm(pf, cl, end=cl.index.max())
    fund = w.funding.pivot_table(index="day", columns="coin", values="usdc", aggfunc="sum").fillna(0.0)
    fees = pf.assign(day=pf["t"].dt.floor("D")).pivot_table(index="day", columns="coin", values="fee", aggfunc="sum").fillna(0.0)
    return {"price": price, "funding": fund, "fees": fees}


def main(online: bool):
    w = Wallet(USER, DATA)
    pf = w.fills[w.fills["kind"] != "spot"]
    ex = executions(w.fills)
    pe = ex[ex["kind"] != "spot"].copy()
    parts = pnl_by_coin_day(w, pf)
    total = parts["price"].add(parts["funding"], fill_value=0).sub(parts["fees"], fill_value=0).fillna(0.0)

    title("Seção 2: PnL de perps por fase (preço + funding − taxas)")
    rows = {}
    for name, (a, b) in PHASES.items():
        s = total.loc[a:b].sum()
        rows[name] = {**s.groupby(group_of).sum().round(0).to_dict(), "total": round(s.sum())}
    print(pd.DataFrame(rows).T.fillna(0).astype(int))
    print("soma:", round(total.values.sum()), "| portfolio perp:", round(w.portfolio("perpAllTime")["pnl"].iloc[-1]))

    title("Seção 4: PnL de perps por categoria")
    cat = pd.DataFrame({k: v.sum() for k, v in parts.items()}).fillna(0.0)
    cat["fees"] = -cat["fees"]
    cat["total"] = cat.sum(axis=1)
    print(cat.groupby(group_of).sum().round(0))
    memes = ["POPCAT", "FARTCOIN", "TRUMP", "LAUNCHCOIN", "AI16Z", "MOODENG", "PUMP"]
    print("7 memecoins:", round(cat.loc[cat.index.isin(memes), "total"].sum()))
    q = total.sum(axis=1)
    print("por trimestre:", (q.groupby(q.index.to_period("Q")).sum() / 1e6).round(2).to_dict())
    print("melhores dias:", (q.nlargest(3) / 1e6).round(2).to_dict())
    print("dia 10/out/2025 por ativo:", total.loc["2025-10-10"][total.loc["2025-10-10"].abs() > 1000].round(0).to_dict())

    title("Seção 1: execução")
    o = w.orders.sort_values("statusTimestamp")
    first, last = o.groupby("oid").first(), o.groupby("oid").last()
    print(f"ordens guardadas pela API: {len(last)} ({o['t'].min():%Y-%m-%d} → {o['t'].max():%Y-%m-%d})")
    print(last.groupby(["orderType", "tif", "isTrigger"]).size().to_string())
    life = (pd.to_datetime(last["statusTimestamp"], unit="ms") - pd.to_datetime(first["timestamp"], unit="ms")).dt.total_seconds() / 60
    print("vida das ordens limite (min, mediana):",
          life[last["orderType"] == "Limit"].groupby(last["status"]).median().round(2).to_dict())
    for coin in ("BTC", "ETH"):
        h = hourly_close(coin, DATA)
        lim = last[(last["orderType"] == "Limit") & (last["coin"] == coin)]
        ref = h.shift(1).reindex(pd.to_datetime(lim["timestamp"], unit="ms").dt.floor("h")).values
        dist = (lim["limitPx"].values / ref - 1) * 100
        print(f"{coin}: distância do limite ao último fechamento horário, mediana {np.nanmedian(dist):+.2f}%, "
              f"p25–p75 {np.nanpercentile(dist, 25):+.2f}% a {np.nanpercentile(dist, 75):+.2f}%")
    pe["grp"] = pe["coin"].map(lambda c: "BTC/ETH" if c in ("BTC", "ETH") else ("HIP-3" if c.startswith("xyz:") else "alts"))
    pe["inc"] = np.where(pe["action"].isin(["open", "add"]), "aumenta", "reduz")
    mk = pe.groupby(["grp", "inc"]).apply(
        lambda g: pd.Series({"ordens": len(g), "maker % (nocional)": 100 * (1 - (g["ntl"] * g["taker"]).sum() / g["ntl"].sum()),
                             "nocional mediano": g["ntl"].median()}), include_groups=False)
    print(mk.round(1))
    for coin in ("BTC", "ETH", "TRUMP", "POPCAT", "FARTCOIN"):
        vc = pe[pe["coin"] == coin]["sz"].round(6).value_counts()
        print(f"lotes {coin}: {vc.head(5).to_dict()} | top-5 = {100 * vc.head(5).sum() / vc.sum():.0f}% de {vc.sum()} ordens")
    for day, coin in [("2025-04-29", "TRUMP"), ("2025-01-09", "POPCAT")]:
        d = w.fills[(w.fills["coin"] == coin) & (w.fills["t"].dt.strftime("%Y-%m-%d") == day)]
        print(f"{coin} em {day}: {d['oid'].nunique()} ordens, {len(d)} fills, {d['q'].sum():+,.0f} unidades")
    print("ordens por hora UTC:", pe["t"].dt.hour.value_counts().sort_index().to_dict())
    se = sessions(pe)
    wk = se["start"].dt.dayofweek
    print(f"sessões: {len(se)}, mediana de {se['orders'].median():.0f} ordens; fim de semana: {100 * (wk >= 5).mean():.0f}%; "
          f"dias ativos: {pe['t'].dt.floor('D').nunique()} de {(pe['t'].max() - pe['t'].min()).days}")
    f = w.fills
    fg = f.assign(g=f["coin"].map(lambda c: "spot" if c.startswith("@") else group_of(c)))
    print("taxa (bps):", (1e4 * fg.groupby("g")["fee"].sum() / fg.groupby("g")["ntl"].sum()).round(2).to_dict(),
          f"| geral {1e4 * f['fee'].sum() / f['ntl'].sum():.2f}")
    print("taxa por trimestre (bps):", (1e4 * f.groupby(f["t"].dt.to_period("Q"))["fee"].sum()
                                         / f.groupby(f["t"].dt.to_period("Q"))["ntl"].sum()).round(2).to_dict())
    S = w.snapshot
    print("userRateLimit:", S["userRateLimit"], "| agentes:", S["extraAgents"])

    title("Seções 1 e 3.4: dinheiro entrando e saindo")
    L = w.ledger
    for t in ("deposit", "withdraw"):
        x = L[L["type"] == t]
        rnd = ((x["amount"] - x["amount"].round(-3)).abs() < 2).mean()
        print(f"{t}: {len(x)}, US$ {x['usd'].sum():,.0f}, valores redondos (múltiplo de US$ 1k, ±2): {100 * rnd:.0f}%")
    sends = L[L["type"] == "send"]
    print("sends por contraparte:", sends.groupby(["counterparty", sends["usd"] > 0])["usd"].agg(["size", "sum"]).round(0).to_string())
    pp = w.portfolio("perpAllTime")
    print(f"maior equity de perps: US$ {pp['account_value'].max():,.0f} em {pp['account_value'].idxmax():%Y-%m-%d}")
    fl = L[L["type"].isin(["deposit", "withdraw", "send"])]
    mon = fl.groupby([fl["t"].dt.to_period("M"), fl["usd"] > 0])["usd"].sum().unstack(fill_value=0)
    print("fluxos mensais (saques, depósitos):\n", (mon / 1e6).round(2).loc["2025-11":"2026-02"])
    expo = daily_exposure(w.funding)
    gross = (expo * w.closes(expo.columns).reindex(expo.index).ffill()).abs().sum(axis=1)
    dep = fl[(fl["t"] >= "2025-11-24") & (fl["t"] < "2025-11-28") & (fl["usd"] > 0)]["usd"].sum()
    print(f"24–27/nov/2025: depósitos US$ {dep:,.0f}; exposição bruta {gross.loc['2025-11-24']:,.0f} → {gross.loc['2025-11-27']:,.0f}")

    title("Seção 3.2: episódios de alts (nocional máximo ≥ US$ 50k)")
    em = episode_metrics(w, ex)
    print(f"episódios ≥ US$ 50k: {len(em)} ({em['side'].value_counts().to_dict()})")
    alts = em[(em["side"] == "short") & ~em["coin"].isin(["BTC", "ETH"]) & ~em["coin"].str.startswith("xyz:")]
    done = alts[~alts["open"]]
    win = done["realized"] > 0
    print(f"shorts de alts fechados: {len(done)}, com lucro: {win.sum()}, realizado US$ {done['realized'].sum():,.0f}, "
          f"funding US$ {done['funding'].sum():,.0f}")
    print("medianas: dias {:.1f} | vs. máx. 30d {:+.1f}% | funding a.a. na entrada {:.1f}% (vencedores {:.1f}%) | "
          "capturado {:.1f}% | contra (máx.) {:.1f}%".format(
              done["days"].median(), done["vs_30d_high"].median(), done["funding_ann_pre"].median(),
              done.loc[win, "funding_ann_pre"].median(), done["captured_pct"].median(), done["adverse_pct"].median()))
    hi = done[done["funding_ann_pre"] > 30]
    print(f"funding > 30% a.a. na entrada: {len(hi)} episódios, {int((hi['realized'] > 0).sum())} com lucro")
    lose = done.loc[~win, ["coin", "start", "funding_ann_pre", "vs_30d_high", "r30d", "adverse_pct", "realized"]]
    print("perdedores:\n", lose.assign(start=lose["start"].dt.date).round(1).to_string())
    longs = em[em["coin"].isin(["DOT", "FARTCOIN", "LAUNCHCOIN"]) & (em["days"] > 100)]
    print(f"funding nos shorts de 3–4 meses (DOT, FARTCOIN, LAUNCHCOIN): US$ {longs['funding'].sum():,.0f}")
    after = em[em["coin"].isin(["POPCAT", "TRUMP"])][["coin", "start", "next30d_more_pct"]]
    print("queda adicional nos 30 dias após a saída (%):\n", after.assign(start=after["start"].dt.date).round(1).to_string())

    title("Seção 3.3: livro macro de BTC e ETH")
    for coin, a, b in [("BTC", "2025-11-24", "2025-11-26"), ("ETH", "2025-11-25", "2025-11-28")]:
        x = pe[(pe["coin"] == coin) & (pe["t"] >= a) & (pe["t"] < pd.Timestamp(b) + pd.Timedelta(days=1)) & (pe["q"] < 0)]
        print(f"{coin} {a}→{b}: vendeu {-x['q'].sum():,.0f} a US$ {x['ntl'].sum() / x['sz'].sum():,.0f} (US$ {x['ntl'].sum() / 1e6:.1f}M)")
    btc = candles_df("BTC", "1d", DATA)
    ma200 = btc["close"].rolling(200).mean()
    print(f"BTC 24/nov/2025: fechamento {btc['close'].loc['2025-11-24']:,.0f}, MA200 {ma200.loc['2025-11-24']:,.0f}, "
          f"máxima até ali {btc['high'].loc[:'2025-11-24'].max():,.0f}")
    for coin, a, b in [("BTC", "2026-01-21", "2026-01-30"), ("BTC", "2026-06-02", "2026-06-11"), ("BTC", "2026-01-14", "2026-01-17")]:
        x = pe[(pe["coin"] == coin) & (pe["t"] >= a) & (pe["t"] < pd.Timestamp(b) + pd.Timedelta(days=1))]
        print(f"{coin} {a}→{b}: líquido {x['q'].sum():+.0f}, realizado US$ {x['closed_pnl'].sum():,.0f}")
    for coin in ("BTC", "ETH"):
        av = averaging_stats(w.fills, ex, coin)
        print(f"{coin}: aumentos com a posição no lucro {100 * (1 - av['adds_underwater_share']):.0f}%, "
              f"distância mediana do preço médio {av['adds_median_dist_from_avg_pct']:+.1f}%")
    eth = pe[pe["coin"] == "ETH"].set_index("t")["end_pos"]
    print("ETH, posição em 1/dez/2025 e 1/mai/2026:", eth.loc[:"2025-12-01"].iloc[-1], eth.loc[:"2026-05-01"].iloc[-1])
    for coin in ("BTC", "ETH"):
        d = pe[pe["coin"] == coin].assign(day=lambda x: x["t"].dt.floor("D"))
        g = d.groupby("day").agg(ordens=("q", "size"), q=("q", "sum"), pos=("end_pos", "last"), realizado=("closed_pnl", "sum"))
        g["vwap"] = d.groupby("day").apply(lambda x: (x["vwap"] * x["sz"]).sum() / x["sz"].sum(), include_groups=False)
        print(f"{coin}, fluxo diário de ordens:\n", g.round(1).to_string())

    title("Seção 3.6: spot")
    s = w.fills[w.fills["kind"] == "spot"]
    h107 = s[s["coin"] == "@107"].assign(m=lambda x: x["t"].dt.to_period("M"))
    hm = h107.groupby(["m", "side"]).agg(qtd=("sz", "sum"), usd=("ntl", "sum"), realizado=("closedPnl", "sum"))
    hm["preço médio"] = hm["usd"] / hm["qtd"]
    print("HYPE spot (@107):\n", hm.round(2).to_string())
    print("UFART (@162):", s[s["coin"] == "@162"].groupby("side").agg(qtd=("sz", "sum"), usd=("ntl", "sum"), realizado=("closedPnl", "sum")).round(2).to_dict())
    print("HYPE perp em dez/2024:", round(pf[(pf["coin"] == "HYPE") & (pf["t"] < "2025-01-01")]["closedPnl"].sum()),
          "| funding HYPE dez/2024:", round(w.funding[(w.funding["coin"] == "HYPE") & (w.funding["t"] < "2025-01-01")]["usdc"].sum()))
    print("staking:", S["delegatorSummary"])

    title("Seção 6, teste D: cópia com atraso (marcação horária, sem custos)")
    lag = {c: copy_lag_pnl(pf, c, hourly_close(c, DATA)) for c in ["BTC", "ETH", "POPCAT", "FARTCOIN", "TRUMP", "LAUNCHCOIN"]}
    print((pd.DataFrame(lag) / 1e6).round(2))

    title("Seção 6, teste C: short abaixo da média móvel vs. carteira")
    for sym, coin in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")]:
        c = klines_df(sym, "1d", DATA)["close"]
        r = c.pct_change()
        win_ret = np.prod(1 - r.loc["2025-09-24":"2026-06-11"].dropna()) - 1
        pos = -(c < c.rolling(200).mean()).astype(float)
        a, b = "2024-12-16", "2026-10-12"
        act = expo[coin].reindex(pos.loc[a:b].index).fillna(0.0)
        corr = np.corrcoef(pos.loc[a:b].shift(1).fillna(0.0), act)[0, 1]
        print(f"{coin}: sempre vendido 24/set/2025→11/jun/2026 {100 * win_ret:+.0f}% | correlação 'short abaixo da MA200' "
              f"com a posição da carteira {corr:.2f}")

    if online:
        from hlre.api import InfoClient

        title("Seção 1: perfil da carteira de serviço 0x6b9e… (API)")
        rows = InfoClient(min_interval=1.5).post({"type": "userNonFundingLedgerUpdates", "user": SERVICE, "startTime": 0})
        d = pd.DataFrame([{"t": pd.to_datetime(r["time"], unit="ms"), **r["delta"]} for r in rows])
        out = d[d["user"].str.lower() == SERVICE] if "user" in d else d.iloc[0:0]
        inc = d[d.get("destination", pd.Series(dtype=str)).str.lower() == SERVICE] if "destination" in d else d.iloc[0:0]
        print(f"{len(d)} lançamentos de {d['t'].min():%Y-%m-%d} a {d['t'].max():%Y-%m-%d}; tipos {d['type'].value_counts().to_dict()}")
        print(f"envia para {out['destination'].str.lower().nunique()} carteiras diferentes; recebe de "
              f"{inc['user'].str.lower().value_counts().head(3).to_dict()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="inclui o perfil da carteira de serviço (chamada à API)")
    main(ap.parse_args().online)
