"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x0812f31ccf62c48e6da3da3fbf98663779e1f45d/analise_extra.py

Lê só os arquivos em data/. A carteira tem duas fases: de 20 a 23/ago/2026 um
bot de teste (agente "hermes-rail-live") abre e fecha ordens de ~US$ 11 em
rodízio BTC → ETH → SOL; a partir de 27/ago o operador negocia à mão
(interface e app). O relatório automático mistura as duas; aqui a fase de teste
é isolada e a fase manual é medida sozinha: PnL por mês, lado e ativo,
episódios com o contexto antes da entrada, alavancagem diária e ordens de stop.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, episode_metrics, executions, episodes  # noqa: E402

USER = "0x0812f31ccf62c48e6da3da3fbf98663779e1f45d"
DATA = os.path.join(ROOT, "data")
MANUAL_FROM = pd.Timestamp("2026-08-24")
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def main():
    w = Wallet(USER, DATA)
    f = w.fills.sort_values("time").copy()
    test, man = f[f["t"] < MANUAL_FROM], f[f["t"] >= MANUAL_FROM]

    print("======== Fase 1: bot de teste (20–23/ago)")
    ex = executions(test)
    print(f"fills {len(test)}, ordens {ex['oid'].nunique()}, de {test['t'].min()} a {test['t'].max()}")
    print(test.groupby("coin").agg(fills=("sz", "size"), nocional=("ntl", "sum"), ntl_mediano=("ntl", "median"),
                                   realizado=("closedPnl", "sum"), taxas=("fee", "sum")).round(2).to_string())
    opens = ex[ex["dir"].str.startswith("Open")].sort_values("t")
    gap = opens["t"].diff().dt.total_seconds() / 60
    print(f"intervalo entre aberturas (min): mediana {gap.median():.1f}, p10 {gap.quantile(.1):.1f}, p90 {gap.quantile(.9):.1f}")
    seq = "".join(opens["coin"].str[0].tolist()[:30])
    print(f"sequência das 30 primeiras aberturas: {seq}")
    closes = ex[ex["dir"].str.startswith("Close")]
    hold = (closes["t"].values - opens["t"].values[: len(closes)]).astype("timedelta64[s]").astype(float)
    print(f"tempo aberto (s): mediana {np.median(hold):.0f}; abertura taker {opens['taker'].mean():.0%}, "
          f"fechamento taker {closes['taker'].mean():.0%}")
    print(f"lado das aberturas alterna: {(opens['dir'] != opens['dir'].shift()).mean():.0%}")

    print("\n======== Fase 2: manual (desde 24/ago) — PnL realizado, taxas, volume")
    m = man.copy()
    m["mes"] = m["t"].dt.to_period("M")
    print(m.groupby("mes").agg(realizado=("closedPnl", "sum"), taxas=("fee", "sum"), volume=("ntl", "sum"),
                               ordens=("oid", "nunique")).round(0).to_string())
    print(f"taker (nocional): {(m['ntl'] * m['crossed']).sum() / m['ntl'].sum():.0%}")

    exm = executions(m)
    eps = []
    for coin in exm["coin"].unique():
        e = episodes(exm, coin)
        e["coin"] = coin
        eps.append(e)
    E = pd.concat(eps).sort_values("start").reset_index(drop=True)
    E["classe"] = np.where(E["coin"].isin(["BTC", "ETH"]), "BTC/ETH", "alts")
    E["quinzena"] = E["start"].dt.to_period("W").dt.start_time.dt.strftime("%m-%d")

    print("\n======== PnL realizado por classe × lado")
    print(E.pivot_table(index="classe", columns="side", values="realized", aggfunc="sum").round(0).to_string())
    print(E.pivot_table(index="classe", columns="side", values="realized", aggfunc="count").to_string())

    big = E[E["max_ntl"] >= 10_000]
    print("\n======== Episódios com nocional máx. ≥ US$ 10 mil")
    print(f"n={len(big)}, com lucro {(big['realized'] > 0).mean():.0%}, ganho médio "
          f"{big.loc[big['realized'] > 0, 'realized'].mean():,.0f} vs perda média "
          f"{big.loc[big['realized'] <= 0, 'realized'].mean():,.0f}; soma {big['realized'].sum():,.0f}")
    print(big.groupby("side").agg(n=("realized", "size"), lucro=("realized", lambda s: (s > 0).mean()),
                                  soma=("realized", "sum"), dias_med=("days", "median")).round(2).to_string())
    print("\nTamanho por semana (nocional máximo mediano e máximo dos episódios ≥ US$ 10 mil):")
    print(big.groupby("quinzena").agg(n=("realized", "size"), ntl_mediano=("max_ntl", "median"),
                                      ntl_max=("max_ntl", "max"), realizado=("realized", "sum")).round(0).to_string())

    print("\n======== Contexto antes da entrada: shorts de alts com nocional ≥ US$ 10 mil")
    em = episode_metrics(w, exm, min_ntl=10_000)
    alt_s = em[(em["side"] == "short") & ~em["coin"].isin(["BTC", "ETH"])]
    cols = ["coin", "start", "days", "max_ntl", "r7d", "r30d", "vs_30d_high", "funding_ann_pre", "adverse_pct",
            "realized"]
    print(alt_s[cols].round(1).to_string())
    print("medianas:", alt_s[["r7d", "r30d", "vs_30d_high", "funding_ann_pre"]].median().round(1).to_dict())
    print(f"com lucro {(alt_s['realized'] > 0).mean():.0%}; soma {alt_s['realized'].sum():,.0f}")
    print("por retorno de 30d antes:")
    alt_s = alt_s.assign(pump=np.where(alt_s["r30d"] >= 30, "30d ≥ +30%", "30d < +30%"))
    print(alt_s.groupby("pump")["realized"].agg(["size", "sum", lambda s: (s > 0).mean()]).round(2).to_string())

    print("\n======== Alavancagem: maior nocional bruto do dia / patrimônio total (perp + spot)")
    pos = {}
    for coin, g in m.groupby("coin"):
        pos[coin] = g.set_index("t")["endPosition"].groupby(level=0).last()
    P = pd.DataFrame(pos).sort_index().ffill().fillna(0.0)
    # preço: o do próprio fill (bom o bastante para o pico do dia)
    px = m.pivot_table(index="t", columns="coin", values="px", aggfunc="last").reindex(P.index).ffill()
    gross = (P.abs() * px).sum(axis=1).resample("D").max()
    eq = w.portfolio("allTime")["account_value"].resample("D").last()
    lev = pd.DataFrame({"bruto_max": gross, "patrimonio": eq}).dropna()
    lev = lev[lev["patrimonio"] > 1000]
    lev["alav"] = lev["bruto_max"] / lev["patrimonio"]
    print(lev.resample("W").agg({"bruto_max": "max", "patrimonio": "last", "alav": "max"}).round(1).to_string())
    print(f"alavancagem máx. {lev['alav'].max():.1f}x em {lev['alav'].idxmax().date()}; "
          f"mediana dos dias com posição {lev.loc[lev['bruto_max'] > 0, 'alav'].median():.1f}x")

    print("\n======== Patrimônio, aportes e drawdown")
    pf = w.portfolio("allTime")
    led = w.ledger
    print(led[["t", "type", "usd", "counterparty"]].to_string())
    av = pf["account_value"]
    pn = pf["pnl"]
    dd = pn - pn.cummax()
    eq_peak = av.loc[: dd.idxmin()].max()
    print(f"PnL all-time {pn.iloc[-1]:,.0f}; pior drawdown do PnL {dd.min():,.0f} em {dd.idxmin()} "
          f"({dd.min() / eq_peak:.0%} do pico de patrimônio até ali, {eq_peak:,.0f}); "
          f"pico do patrimônio {av.max():,.0f} em {av.idxmax()}")
    d = pn.resample("D").last().diff().dropna()
    d = d[d.index >= "2026-08-27"]
    print(f"dias: {len(d)}, positivos {(d > 0).mean():.0%}, melhor {d.max():,.0f}, pior {d.min():,.0f}")

    print("\n======== Ordens de gatilho (stop / take profit) da fase manual")
    o = w.orders.sort_values("statusTimestamp").drop_duplicates("oid", keep="last")
    trig = o[o["orderType"].str.contains("Stop|Take", na=False)]
    print(f"ordens de gatilho: {len(trig)} em {trig['t'].dt.date.nunique()} dias, de {trig['t'].min().date()} "
          f"a {trig['t'].max().date()}")
    print(trig.groupby(["orderType", "status"]).size().to_string())
    trig = trig.assign(dia=trig["t"].dt.date)
    print("stops por (dia, ativo) — quantas vezes o stop é recolocado:")
    print(trig.groupby(["dia", "coin"]).size().describe().round(1).to_string())
    hit = trig[trig["status"] == "triggered"]
    print(hit[["t", "coin", "side", "orderType", "triggerPx", "origSz"]].to_string())
    lim = o[(o["orderType"] == "Limit") & o["reduceOnly"].astype(bool)]
    print(f"limites reduceOnly (alvos no livro): {len(lim)}; preenchidos {(lim['status'] == 'filled').sum()}")

    print("\n======== Horário das decisões (UTC, sessões de ordens a < 30 min)")
    s = exm.sort_values("t")
    sess = s[(s["t"].diff().dt.total_seconds().fillna(1e9) > 1800)]
    print(sess["t"].dt.hour.value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
