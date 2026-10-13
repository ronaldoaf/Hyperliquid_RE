"""Build the automatic (quantitative) report for one wallet.

Usage:
    python -m hlre.report 0xWALLET [--data-dir data] [--out reports] [--coins BTC HYPE]

Reads only local files (run `python -m hlre.run` to download first) and
writes reports/<wallet>/relatorio_auto.md, img/*.png and metrics.json.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from . import charts
from .analyze import (
    Wallet, approx_price_pnl, averaging_stats, baseline_context, copy_lag_pnl, daily_exposure,
    daily_perp_pnl, episode_metrics, episodes, exact_mtm, executions, flow_behaviour, hold_decomposition,
    leverage_frame, liquidation_events, market_context, position_gaps, rank_coins, session_context, sessions,
)
from .market import funding_df, hourly_close
from .replicate import features, grid_search, linear_clone

KNOWN = {
    "0x8dafbe89302656a7df43c470e9ebcb4c540835c0": "Unit: emissor/ponte do UETH (depósitos de ETH nativo)",
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303": "HLP (vault do protocolo)",
    "0x2222222222222222222222222222222222222222": "sistema: ponte de HYPE HyperCore↔HyperEVM",
    "0x6b9e773128f453f5c2c60935ee2de2cbc5390a24": "hot wallet de serviço (recebe USDC da HyperEVM e repassa a centenas de usuários: exchange/ponte)",
}

CLASS_LABEL = {"short+": "aumenta short", "short-": "reduz short", "long+": "aumenta long",
               "long-": "reduz long", "flip": "inverte lado", "base": "todas as horas (base)"}


def usd(x, signed=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = "+" if signed and x > 0 else ""
    a = abs(x)
    sign = "-" if x < 0 else s
    if a >= 1e6:
        return f"{sign}${a / 1e6:,.2f}M"
    if a >= 1e3:
        return f"{sign}${a / 1e3:,.1f}K"
    return f"{sign}${a:,.0f}"


def pct(x, d=1):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%"


def num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 1:
        return f"{v:,.2f}"
    return f"{v:.4g}"


def md_table(df: pd.DataFrame, index=True) -> str:
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


def build(user: str, data_dir: str = "data", out_dir: str = "reports", coins: list[str] | None = None) -> str:
    w = Wallet(user, data_dir)
    out = os.path.join(out_dir, w.user)
    img = os.path.join(out, "img")
    os.makedirs(img, exist_ok=True)
    for old in os.listdir(img):  # generated content only: drop charts of coins no longer selected
        if old.endswith(".png"):
            os.remove(os.path.join(img, old))
    S = w.snapshot
    M: dict = {"user": w.user, "generated_at": pd.Timestamp.now("UTC").isoformat()}
    md: list[str] = []
    rel = lambda p: os.path.relpath(p, out)

    fills, fund = w.fills, w.funding
    perp_fills = fills[fills["kind"] != "spot"] if len(fills) else fills
    ex = executions(fills) if len(fills) else pd.DataFrame()
    pa, pp = w.portfolio("allTime"), w.portfolio("perpAllTime")
    ch = S["clearinghouseState"]

    # ------------------------------------------------------------ attribution
    expo = daily_exposure(fund) if len(fund) else pd.DataFrame()
    allcoins = sorted(set(expo.columns) | set(perp_fills["coin"].unique() if len(perp_fills) else []))
    closes, opens = w.closes(allcoins), w.opens(allcoins)
    approx = approx_price_pnl(expo, opens, closes) if len(expo) else pd.DataFrame()
    fund_by = fund.groupby("coin")["usdc"].sum() if len(fund) else pd.Series(dtype=float)
    attrib = pd.DataFrame({"preço (aprox.)": approx.sum() if len(approx) else pd.Series(dtype=float),
                           "funding": fund_by}).fillna(0.0)
    attrib["total"] = attrib.sum(axis=1)
    if len(perp_fills):
        mtm = exact_mtm(perp_fills, closes, end=closes.index.max())
        attrib["preço exato (período dos fills)"] = mtm.sum()
        attrib["taxas (período dos fills)"] = -perp_fills.groupby("coin")["fee"].sum()
    attrib = attrib.sort_values("total")
    main = coins or rank_coins(w, 3)
    M["main_coins"] = main

    # ------------------------------------------------------------- overview
    port = dict(S["portfolio"])
    M.update({
        "account_value": float(pa["account_value"].iloc[-1]),
        "pnl_all_time": float(pa["pnl"].iloc[-1]), "pnl_perp_all_time": float(pp["pnl"].iloc[-1]),
        "volume_all_time": float(port["allTime"]["vlm"]), "first_activity": str(pa.index.min().date()),
        "n_fills": int(len(fills)), "fills_from": str(fills["t"].min()) if len(fills) else None,
        "n_orders": int(len(ex)), "funding_net": float(fund["usdc"].sum()) if len(fund) else 0.0,
        "fees_fills_period": float(fills["fee"].sum()) if len(fills) else 0.0,
    })
    agents = S.get("extraAgents") or []
    pos_rows = []
    for ap in ch.get("assetPositions", []):
        p = ap["position"]
        pos_rows.append({"ativo": p["coin"], "tamanho": float(p["szi"]), "nocional": usd(float(p["positionValue"])),
                         "entrada": p["entryPx"], "alav.": f'{p["leverage"]["value"]}x {p["leverage"]["type"]}',
                         "PnL não realizado": usd(float(p["unrealizedPnl"]), True),
                         "liq.": p.get("liquidationPx") or "—"})
    liq_led = w.ledger[w.ledger["type"] == "liquidation"]
    liq_f = liquidation_events(fills, w.user) if len(fills) else pd.DataFrame()

    md += [f"# Relatório automático — `{w.user}`", "",
           f"Gerado em {pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M} UTC a partir da API pública da Hyperliquid "
           "(`POST /info`). Valores em USD. Este arquivo é regenerado por `python -m hlre.report`; "
           "a interpretação da estratégia fica em `ANALISE.md`.", "",
           "## 1. Visão geral", "",
           md_table(pd.DataFrame({"métrica": [
               "Valor da conta (perp + spot)", "PnL all-time (portfolio, inclui spot/airdrops)",
               "PnL all-time só de perps", "Volume all-time", "Primeira atividade",
               "Fills disponíveis na API", "Ordens (fills agrupados por oid)", "Funding líquido (recebido > 0)",
               "Taxas pagas (período dos fills)", "Liquidações (ledger)", "Fills de liquidação/ADL",
               "Papel da conta", "API wallets (agentes)"],
               "valor": [usd(M["account_value"]), usd(M["pnl_all_time"], True), usd(M["pnl_perp_all_time"], True),
                         usd(M["volume_all_time"]), M["first_activity"],
                         f'{M["n_fills"]:,} (desde {fills["t"].min():%Y-%m-%d})' if len(fills) else "0",
                         f'{M["n_orders"]:,}', usd(M["funding_net"], True), usd(-M["fees_fills_period"], True),
                         str(len(liq_led)), str(len(liq_f)), S["userRole"].get("role", "?"),
                         str(len(agents))]}), index=False), ""]
    if pos_rows:
        md += ["**Posições abertas agora:**", "", md_table(pd.DataFrame(pos_rows), index=False), ""]

    # -------------------------------------------------------------- PnL curve
    events = []
    if len(liq_led):
        liq_day = liq_led.assign(ntl=liq_led["raw"].map(lambda d: float(d["liquidatedNtlPos"])),
                                 day=liq_led["t"].dt.floor("D")).groupby("day")["ntl"].sum()
        events += [(d, f"liquidação {usd(v)}") for d, v in liq_day.items()]
    gen = w.ledger[(w.ledger["type"] == "spotGenesis") & (w.ledger["token"] == "HYPE")]
    for _, r in gen.iterrows():
        events.append((r["t"], f'airdrop HYPE {r["amount"]:,.0f}'))
    p1 = charts.pnl_curve({"PnL all-time (perp + spot)": pa["pnl"], "PnL só perps": pp["pnl"]}, events,
                          os.path.join(img, "pnl_curve.png"), "PnL acumulado segundo o portfolio da Hyperliquid")
    md += ["## 2. Curva de PnL", "", f"![PnL]({rel(p1)})", ""]

    # exact daily perp PnL: only when the fills reach back to the first trade
    dpnl = daily_perp_pnl(w) if len(perp_fills) else pd.DataFrame()
    starts = [x for x in [fund["t"].min() if len(fund) else None, w.ledger["t"].min() if len(w.ledger) else None] if x is not None]
    from_start = bool(len(perp_fills)) and bool(starts) and perp_fills["t"].min() <= min(starts) + pd.Timedelta(days=2)
    full_history = from_start and bool(len(dpnl)) and \
        abs(dpnl["pnl"].sum() - M["pnl_perp_all_time"]) <= max(0.02 * abs(M["pnl_perp_all_time"]), 5_000)
    M["fills_cover_full_history"] = full_history
    gaps = position_gaps(w.fills) if len(perp_fills) else pd.DataFrame()
    M["position_gaps"] = int(len(gaps))
    if len(gaps):
        g = gaps.groupby("coin")["jump_ntl"].sum().sort_values(ascending=False)
        md += [f"**Atenção: execuções que não aparecem nos fills.** A posição muda sem fill visível em {len(gaps)} "
               f"pontos (~{usd(gaps['jump_ntl'].sum())} de nocional; maiores: "
               + ", ".join(f"{c} {usd(v)}" for c, v in g.head(5).items())
               + "). O mais comum são fatias de TWAP: ficam fora de `userFills` e o endpoint de TWAP só guarda as "
               "2.000 mais recentes. O *preço exato* e as tabelas por episódio dessas moedas não são exatos.", ""]
    if full_history:
        cum = dpnl["pnl"].cumsum()
        dd = cum - cum.cummax()
        trough = dd.idxmin()
        peak = cum.loc[:trough].idxmax()
        qtr = dpnl.groupby(dpnl.index.to_period("Q")).sum()
        qtr.index = pd.Index([str(q) for q in qtr.index], name="trimestre")
        qtr.columns = ["preço", "funding", "taxas", "total"]
        M["max_drawdown_perp"] = float(dd.min())
        md += [f"Os fills cobrem todo o histórico: o PnL diário exato de perps (preço + funding − taxas) soma "
               f"{usd(dpnl['pnl'].sum(), True)}, contra {usd(M['pnl_perp_all_time'], True)} do portfolio. "
               f"Maior drawdown: **{usd(dd.min())}** (pico em {peak:%Y-%m-%d}, fundo em {trough:%Y-%m-%d}); "
               f"dias positivos: {pct((dpnl['pnl'][dpnl['pnl'] != 0] > 0).mean(), 0)}.", "",
               "<details><summary>PnL de perps por trimestre</summary>", "",
               md_table(qtr.map(lambda v: usd(v, True))), "", "</details>", ""]

    # ------------------------------------------------------------ attribution
    top = attrib.reindex(attrib["total"].abs().sort_values(ascending=False).index[:12])
    p2 = charts.attribution_bars(top[["preço (aprox.)", "funding"]], os.path.join(img, "attribution.png"),
                                 "PnL por ativo em perps: preço (aprox.) e funding, histórico completo")
    show = attrib.reindex(attrib["total"].abs().sort_values(ascending=False).index[:15]).copy()
    rest = attrib.drop(show.index).sum()
    show.loc[f"outros ({len(attrib) - len(show)})"] = rest
    md += ["## 3. De onde veio o PnL", "",
           "*Preço (aprox.)* usa a posição média diária de cada ativo, reconstruída a partir do histórico de "
           "funding (que traz o tamanho da posição a cada hora/dia desde o início da conta), vezes o movimento "
           "open→close do dia. Subestima o PnL de day trade, mas cobre o período sem fills. *Preço exato* "
           "marca cada fill no fechamento diário e só existe para o período coberto pelos fills.", "",
           f"![Atribuição]({rel(p2)})", "",
           md_table(show.map(lambda v: usd(v, True)).rename_axis("ativo")), ""]

    # decomposition for main coins
    dec_rows = {}
    for coin in main:
        if coin not in closes or not len(perp_fills[perp_fills["coin"] == coin]):
            continue
        d = hold_decomposition(perp_fills, coin, closes[coin])
        fz = fund[(fund["coin"] == coin) & (fund["t"] >= perp_fills["t"].min())]["usdc"].sum()
        fe = perp_fills[perp_fills["coin"] == coin]["fee"].sum()
        dec_rows[coin] = {"carregar posição (carry)": usd(d["carry"], True), "  ↳ viés (posição média × movimento)": usd(d["bias"], True),
                          "  ↳ timing (variação do tamanho)": usd(d["timing"], True),
                          "trades intradiários": usd(d["intraday"], True), "funding": usd(fz, True),
                          "taxas": usd(-fe, True), "posição média": f'{d["mean_pos"]:,.2f}',
                          "movimento do preço no período": f'{d["total_move"]:,.2f}'}
        M[f"decomp_{coin}"] = {k: v for k, v in d.items() if k != "daily"}
    if dec_rows:
        md += ["**Decomposição no período dos fills** (preço exato): quanto veio de *carregar* a posição "
               "(e, dentro disso, do viés médio vs. do *timing* de aumentar/reduzir), quanto de trades "
               "intradiários, funding e taxas.", "", md_table(pd.DataFrame(dec_rows).rename_axis("componente")), ""]

    # ------------------------------------------------------------- positions
    md += ["## 4. Posições ao longo do tempo", "",
           "Área clara: posição média diária (funding). Linha: posição exata (fills). Azul = long, vermelho = short.", ""]
    for coin in main:
        if coin not in closes:
            continue
        price = closes[coin].dropna()
        pdaily = expo[coin] if coin in expo else None
        if pdaily is not None:
            nz = pdaily[pdaily.abs() > 0]
            pdaily = pdaily.loc[nz.index.min() - pd.Timedelta(days=10):] if len(nz) else None
        start = min([x.index.min() for x in [pdaily] if x is not None and len(x)] +
                    ([perp_fills[perp_fills["coin"] == coin]["t"].min()] if len(perp_fills[perp_fills["coin"] == coin]) else []))
        price = price.loc[start - pd.Timedelta(days=15):]
        pf = None
        if len(perp_fills[perp_fills["coin"] == coin]):
            from .analyze import position_path
            pf = position_path(perp_fills, coin)
            pf = pd.concat([pf, pd.Series([pf.iloc[-1]], index=[closes.index.max()])])
        pth = charts.price_and_position(price, pdaily, pf, os.path.join(img, f"pos_{coin.replace(':', '_')}.png"), coin)
        md += [f"![{coin}]({rel(pth)})", ""]

    lev, ntl = leverage_frame(fund, closes, pp["account_value"])
    lev_m = lev.resample("MS").agg({"gross": "mean", "net": "mean", "perp_equity": "mean", "leverage": "median"})
    p4 = charts.exposure_leverage(lev["net"].rolling(7, min_periods=1).mean(), lev["gross"].rolling(7, min_periods=1).mean(),
                                  lev["leverage"].clip(upper=40).rolling(7, min_periods=1).median(), os.path.join(img, "exposure.png"))
    tbl = lev_m.copy()
    for c in ["gross", "net", "perp_equity"]:
        tbl[c] = tbl[c].map(usd)
    tbl["leverage"] = tbl["leverage"].map(lambda v: "—" if np.isnan(v) else f"{v:.1f}x")
    tbl.index = pd.Index(tbl.index.strftime("%Y-%m"), name="mês")
    tbl.columns = ["exposição bruta", "exposição líquida", "equity perp", "alavancagem (mediana)"]
    md += [f"![Exposição]({rel(p4)})", "", "<details><summary>Tabela mensal de exposição e alavancagem</summary>", "",
           md_table(tbl), "", "</details>", ""]
    M["leverage_median"] = float(lev["leverage"].median())

    # -------------------------------------------------------------- execution
    md += ["## 5. Execução", ""]
    o = w.orders
    if len(o):
        uo = o.sort_values("statusTimestamp").groupby("oid").agg(orderType=("orderType", "first"), tif=("tif", "first"),
                                                                    reduceOnly=("reduceOnly", "first"), isTrigger=("isTrigger", "first"),
                                                                    tpsl=("isPositionTpsl", "first"), status=("status", "last"))
        ot = uo.groupby(["orderType", "tif", "reduceOnly", "isTrigger"]).size().rename("ordens").reset_index()
        md += [f"**Tipos de ordem** (últimas {len(uo):,} ordens que a API guarda, {o['t'].min():%Y-%m-%d} → {o['t'].max():%Y-%m-%d}):", "",
               md_table(ot, index=False), "",
               "`FrontendMarket` = ordem a mercado enviada pela interface web; `Gtc` = limite que fica no livro; "
               "gatilhos (`isTrigger`) seriam stop/take-profit.", ""]
        M["order_types"] = {f"{r.orderType}/{r.tif}": int(r.ordens) for r in ot.itertuples()}
    if len(ex):
        pe = ex[ex["kind"] != "spot"]
        tk = pe.groupby("coin").apply(lambda g: (g["ntl"] * g["taker"]).sum() / g["ntl"].sum(), include_groups=False)
        vol = pe.groupby("coin")["ntl"].sum()
        exr = pd.DataFrame({"volume": vol.map(usd), "ordens": pe.groupby("coin").size(),
                            "% taker (nocional)": tk.map(lambda v: pct(v, 0)),
                            "tamanho mediano": pe.groupby("coin")["sz"].median().map(lambda v: f"{v:,.4g}")})
        exr = exr.reindex(vol.sort_values(ascending=False).index[:10]).rename_axis("ativo")
        md += ["**Perfil por ativo (top 10 por volume):**", "", md_table(exr), ""]
        M["taker_share_ntl"] = float((pe["ntl"] * pe["taker"]).sum() / pe["ntl"].sum())
        c0 = main[0]
        sz = pe[pe["coin"] == c0]["sz"].round(4).value_counts()
        share_top = sz.head(5).sum() / sz.sum()
        p5 = charts.histogram_bars(sz.head(12).rename(lambda v: f"{v:g}"), os.path.join(img, "clip_sizes.png"),
                                   f"{c0}: tamanhos de ordem mais usados (nº de ordens)", f"tamanho da ordem ({c0})")
        md += [f"![Lotes]({rel(p5)})", "",
               f"Os 5 tamanhos mais comuns respondem por {pct(share_top, 0)} das ordens de {c0} — lotes redondos e repetidos "
               "são assinatura de execução manual.", ""]
        se = sessions(pe)
        hrs = se["start"].dt.hour.value_counts().sort_index().reindex(range(24), fill_value=0)
        p6 = charts.histogram_bars(hrs.rename(lambda h: f"{h:02d}"), os.path.join(img, "sessions_hour.png"),
                                   "Início das sessões de trading por hora (UTC)", "hora UTC")
        wd = se["start"].dt.dayofweek.value_counts().sort_index()
        days = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
        md += [f"Sessões (ordens separadas por < 30 min): {len(se):,}; mediana de {se['orders'].median():.0f} ordens e "
               f"{((se['end'] - se['start']).dt.total_seconds() / 60).median():.1f} min por sessão; dias com atividade: "
               f"{pe['t'].dt.floor('D').nunique()} de {(pe['t'].max() - pe['t'].min()).days}.", "",
               f"![Sessões]({rel(p6)})", "",
               "Por dia da semana: " + ", ".join(f"{days[i]} {pct(wd.get(i, 0) / wd.sum(), 0)}" for i in range(7)), ""]

    # --------------------------------------------------- entries and exits
    md += ["## 6. Comportamento de entrada e saída", ""]
    for coin in main:
        if not len(ex) or not len(ex[ex["coin"] == coin]):
            continue
        hourly = hourly_close(coin, data_dir)
        if hourly.empty:
            continue
        e = market_context(ex[ex["coin"] == coin], hourly)
        base = baseline_context(hourly, e["t"].min(), e["t"].max())
        cols = ["r24h", "r72h", "r7d", "rng7d", "f24h", "f7d"]
        med = e.groupby("cls")[cols].median()
        med.loc["base"] = base[cols].median()
        cnt = e.groupby("cls").size()
        order = [c for c in ["short+", "short-", "long+", "long-", "base"] if c in med.index]
        med = med.reindex(order)
        tbl = med.copy()
        for c in cols:
            tbl[c] = tbl[c].map(lambda v: "—" if np.isnan(v) else (f"{v:.2f}" if c == "rng7d" else f"{v:+.2f}%"))
        tbl.insert(0, "ordens", [str(cnt.get(i, "")) if i != "base" else "" for i in med.index])
        tbl.index = pd.Index([CLASS_LABEL[i] for i in med.index], name="ação")
        tbl.columns = ["ordens", "retorno 24h antes", "72h antes", "7d antes", "posição no range 7d", "24h depois", "7d depois"]
        sc = session_context(e, base)
        if len(sc):
            fmtp = lambda v: "<1e-4" if v < 1e-4 else f"{v:.3f}"
            st = pd.DataFrame({
                "sessões": sc["sessões"].astype(int).values,
                "retorno 24h antes": [f"{a:+.2f}% (p={fmtp(b)})" for a, b in zip(sc["r24h"], sc["p_r24h"])],
                "72h antes": [f"{a:+.2f}% (p={fmtp(b)})" for a, b in zip(sc["r72h"], sc["p_r72h"])],
                "7d antes": [f"{a:+.2f}% (p={fmtp(b)})" for a, b in zip(sc["r7d"], sc["p_r7d"])],
                "range 7d": [f"{a:.2f} (p={fmtp(b)})" for a, b in zip(sc["rng7d"], sc["p_rng7d"])],
                "no topo (>0,7)": sc["top30"].map(lambda v: pct(v, 0)).values,
                "no fundo (<0,3)": sc["bottom30"].map(lambda v: pct(v, 0)).values,
            }, index=pd.Index([CLASS_LABEL[i] for i in sc.index], name="sessão"))
            st.loc["todas as horas (base)"] = ["", "", "", "", "", pct(sc.attrs["base_top30"], 0), pct(sc.attrs["base_bottom30"], 0)]
            M[f"sessions_{coin}"] = sc.round(6).to_dict()
        src = sc if len(sc) else med.drop(index="base", errors="ignore")
        bmed = base[["r72h", "r24h", "rng7d"]].median()
        panels = {}
        for col, name in [("r72h", "retorno 72h antes (%)"), ("r24h", "retorno 24h antes (%)"),
                          ("rng7d", "posição no range de 7d (0=fundo, 1=topo)")]:
            ser = src[col].astype(float).copy()
            ser.loc["base"] = bmed[col]
            panels[name] = ser.rename(CLASS_LABEL)
        p7 = charts.hbar_panels(panels, os.path.join(img, f"context_{coin.replace(':', '_')}.png"),
                                f"{coin}: contexto de mercado no início das sessões (medianas)",
                                fmt=lambda v, _=None: f"{v:.2f}", baseline_label=CLASS_LABEL["base"])
        av = averaging_stats(fills, ex, coin)
        ep = episodes(ex, coin)
        M[f"context_{coin}"] = med.round(3).to_dict()
        M[f"averaging_{coin}"] = av
        md += [f"### {coin}", "", f"![Contexto {coin}]({rel(p7)})", "", "Por ordem (medianas):", "", md_table(tbl), ""]
        if len(sc):
            md += ["Por sessão (ordens a menos de 30 min uma da outra contam como uma decisão; p = teste de "
                   "Mann-Whitney contra todas as horas do período):", "", md_table(st), ""]
        md += [
               f"- Aumentos de posição feitos com a posição no prejuízo (preço pior que o preço médio): "
               f"**{pct(av['adds_underwater_share'], 0)}** das ordens ({pct(av['adds_underwater_share_by_size'], 0)} do tamanho); "
               f"distância mediana do preço médio: {av['adds_median_dist_from_avg_pct']:+.2f}%.",
               f"- Reduções/fechamentos com lucro: **{pct(av['reduction_win_rate'], 0)}** de {av['reductions']}; "
               f"ganho médio {usd(av['avg_win'])} vs. perda média {usd(av['avg_loss'])}; realizado {usd(av['realized'], True)}.", ""]
        if len(ep):
            closed = ep[~ep["open"]]
            wins = closed["realized"] > 0
            best = closed["realized"].max() if len(closed) else np.nan
            conc = best / closed.loc[wins, "realized"].sum() if wins.any() else np.nan
            md += [f"- Episódios (de zerado a zerado, ou até inverter): {len(ep)}; fechados com lucro: "
                   f"{pct(wins.mean() if len(closed) else np.nan, 0)}; duração mediana {closed['days'].median():.1f} dias; "
                   f"o melhor episódio sozinho = {pct(conc, 0)} da soma dos episódios lucrativos.", ""]
            tope = ep.reindex(ep["realized"].abs().sort_values(ascending=False).index[:10]).copy()
            tope = tope.assign(início=tope["start"].dt.strftime("%Y-%m-%d"), fim=tope["end"].dt.strftime("%Y-%m-%d"),
                               dias=tope["days"].map(lambda v: f"{v:.1f}"), lado=tope["side"],
                               tam_max=tope["max_size"].map(num), nocional_max=tope["max_ntl"].map(usd),
                               ordens=tope["n_orders"], entrada=tope["entry_vwap"].map(num),
                               saída=tope["exit_vwap"].map(num), realizado=tope["realized"].map(lambda v: usd(v, True)))
            md += ["<details><summary>Maiores episódios por PnL realizado</summary>", "",
                   md_table(tope[["início", "fim", "dias", "lado", "tam_max", "nocional_max", "ordens", "entrada", "saída", "realizado"]], index=False),
                   "", "</details>", ""]

    # cross-coin episode table: what every sizeable trade looked like at entry
    em = episode_metrics(w, ex) if len(ex) else pd.DataFrame()
    if len(em):
        closed = em[~em["open"]]
        M["episodes_all"] = {"n": int(len(em)), "win_rate": float((closed["realized"] > 0).mean()) if len(closed) else None,
                             "realized": float(em["realized"].sum()), "funding": float(em["funding"].sum()),
                             "median_adverse_pct": float(em["adverse_pct"].median()) if "adverse_pct" in em else None}
        f1 = lambda v: "—" if pd.isna(v) else f"{v:+.0f}%"
        tb = em.reindex(em["realized"].abs().sort_values(ascending=False).index[:25]).sort_values("start")
        tb = pd.DataFrame({
            "ativo": tb["coin"], "lado": tb["side"], "início": tb["start"].dt.strftime("%Y-%m-%d"),
            "dias": tb["days"].map(lambda v: f"{v:.0f}"), "nocional máx.": tb["max_ntl"].map(usd),
            "7d antes": tb.get("r7d", pd.Series(np.nan, index=tb.index)).map(f1),
            "30d antes": tb.get("r30d", pd.Series(np.nan, index=tb.index)).map(f1),
            "vs. máx. 30d": tb.get("vs_30d_high", pd.Series(np.nan, index=tb.index)).map(f1),
            "funding a.a. na entrada": tb.get("funding_ann_pre", pd.Series(np.nan, index=tb.index)).map(f1),
            "entrada média vs. 1ª ordem": tb["scale_in_pct"].map(f1),
            "contra (máx.)": tb.get("adverse_pct", pd.Series(np.nan, index=tb.index)).map(f1),
            "pior PnL aberto": tb.get("worst_upnl", pd.Series(np.nan, index=tb.index)).map(lambda v: usd(v, True)),
            "capturado": tb["captured_pct"].map(f1),
            "realizado": tb["realized"].map(lambda v: usd(v, True)), "funding": tb["funding"].map(lambda v: usd(v, True)),
        })
        p_tl = charts.episode_timeline(em, os.path.join(img, "episodes_timeline.png"),
                                       "Episódios de posição por ativo (nocional máximo ≥ $50K)".replace("$", r"\$"))
        md += ["### Todos os episódios relevantes (todas as moedas)", "", f"![Episódios]({rel(p_tl)})", "",
               f"Episódios com nocional máximo ≥ $50K: {len(em)}; fechados com lucro: "
               f"{pct((closed['realized'] > 0).mean() if len(closed) else np.nan, 0)}. Abaixo, os 25 maiores por PnL "
               "realizado, em ordem de data. *7d/30d antes* e *vs. máx. 30d*: o que o preço tinha feito até a "
               "primeira ordem; *funding a.a.*: taxa anualizada nas 24h anteriores (positiva = longs pagam shorts); "
               "*entrada média vs. 1ª ordem*: positivo = foi aumentando a posição com o preço indo contra; "
               "*contra (máx.)*: quanto o preço andou contra a primeira ordem durante o episódio; *capturado*: "
               "movimento entre o preço médio de entrada e o de saída.", "",
               md_table(tb, index=False), ""]

    # ----------------------------------------------------------------- funding
    if len(fund):
        fd = fund.copy()
        c = closes.reindex(fd["day"].unique()).ffill()
        md += ["## 7. Funding", "",
               f"Funding líquido total: **{usd(fund['usdc'].sum(), True)}** "
               f"(recebido {usd(fund.loc[fund['usdc'] > 0, 'usdc'].sum())}, pago {usd(fund.loc[fund['usdc'] < 0, 'usdc'].sum())}). "
               "Na Hyperliquid o funding é pago de hora em hora; quando positivo, longs pagam shorts.", ""]
        rows = {}
        for coin in main + ["(outros)"]:
            sel = fd[fd["coin"] == coin] if coin != "(outros)" else fd[~fd["coin"].isin(main)]
            if not len(sel):
                continue
            px = np.array([closes[co].reindex([d]).ffill().iloc[0] if co in closes else np.nan for co, d in zip(sel["coin"], sel["day"])])
            ntl_days = np.abs(sel["szi"].values) * px * sel["nSamples"].values / 24
            for side, m in [("short", sel["szi"].values < 0), ("long", sel["szi"].values > 0)]:
                if m.sum() == 0:
                    continue
                y = sel["usdc"].values[m].sum() / np.nansum(ntl_days[m]) * 365
                rows[(coin, side)] = {"funding": usd(sel["usdc"].values[m].sum(), True), "rendimento anualizado s/ nocional": pct(y)}
        if rows:
            md += [md_table(pd.DataFrame(rows).T.rename_axis(["ativo", "lado"])), ""]

    # ----------------------------------------------------------- flows/events
    md += ["## 8. Fluxos, eventos e carteiras relacionadas", ""]
    L = w.ledger
    fl = L.groupby("type").agg(eventos=("usd", "size"), usd=("usd", "sum")).sort_values("usd")
    fl["usd"] = fl["usd"].map(lambda v: usd(v, True) if v else "— (sem valor em USD)")
    fl = fl.rename_axis("tipo").rename(columns={"usd": "USD (+ entra / − sai)"})
    md += [md_table(fl), ""]
    # margin management: are deposits a response to losses / new positions, withdrawals to gains?
    if full_history:
        pnl_d = dpnl["pnl"]
    else:
        pnl_d = (approx.sum(axis=1) if len(approx) else pd.Series(dtype=float)).add(
            fund.groupby("day")["usdc"].sum() if len(fund) else pd.Series(dtype=float), fill_value=0.0)
    fb = flow_behaviour(L, pnl_d, lev["gross"]) if len(pnl_d) else {}
    if fb:
        M["flow_behaviour"] = fb
        md += [f"**Gestão de margem.** Dias com depósito: {fb['deposit_days']}; em {pct(fb['deposit_after_loss_share'], 0)} "
               f"deles o PnL dos 3 dias anteriores era negativo (mediana {usd(fb['median_prev_pnl_deposit'], True)}). "
               f"Dias com saque: {fb['withdraw_days']}; em {pct(fb['withdraw_after_gain_share'], 0)} deles o PnL dos 3 dias "
               f"anteriores era positivo (mediana {usd(fb['median_prev_pnl_withdraw'], True)}). Base: "
               f"{pct(fb['all_days_after_loss_share'], 0)} de todos os dias vêm depois de 3 dias negativos. Correlação "
               f"entre o fluxo do dia e a variação da exposição bruta: {fb.get('corr_flow_exposure_change', float('nan')):.2f} "
               "(positiva = deposita para abrir posição e saca ao reduzir).", ""]
        fl_d = L[L["type"].isin(["deposit", "withdraw", "send"])].assign(day=lambda x: x["t"].dt.floor("D")).groupby("day")["usd"].sum()
        p_fl = charts.flows_and_exposure(lev["gross"].rolling(7, min_periods=1).mean(), fl_d,
                                         os.path.join(img, "flows_exposure.png"),
                                         "Exposição bruta (média de 7 dias) e depósitos/saques diários")
        md += [f"![Fluxos]({rel(p_fl)})", ""]
    sysm = L["counterparty"].fillna("").str.lower().str.startswith(("0x2000000000000000000000000000000000000",
                                                                     "0x2222222222222222222222222222222222222222"))
    if sysm.any():
        sl = L[sysm]
        md += [f"Ponte HyperCore↔HyperEVM (endereços de sistema `0x2000…`/`0x2222…`): {len(sl)} transferências, "
               f"entrada {usd(sl.loc[sl['usd'] > 0, 'usd'].sum())}, saída {usd(-sl.loc[sl['usd'] < 0, 'usd'].sum())} — "
               "uso de DeFi na HyperEVM.", ""]
    rel_rows = []
    for r in S.get("related", []):
        label = KNOWN.get(r["address"], r.get("relation", ""))
        rel_rows.append({"carteira": f'`{r["address"]}`', "relação": label, "transferências": r.get("n_transfers", 0),
                         "volume transferido": usd(r.get("transfer_usd")), "valor da conta hoje": usd(r.get("account_value")),
                         "PnL all-time": usd(r.get("all_time_pnl"), True), "HYPE em staking": f'{r.get("hype_staked") or 0:,.0f}',
                         "maiores saldos spot": ", ".join(f"{c} {v:,.0f}" for c, v in (r.get("top_spot") or [])) or "—"})
    if rel_rows:
        md += ["**Carteiras relacionadas** (conta vinculada de staking para desconto de taxa + maiores contrapartes de "
               "transferências; o saldo de staking e o PnL ajudam a ver se posições aqui são hedge de algo mantido lá):", "",
               md_table(pd.DataFrame(rel_rows), index=False), ""]
    if len(liq_f):
        lf = liq_f.copy()
        lf["t"] = lf["t"].dt.strftime("%Y-%m-%d %H:%M:%S")
        lf["closedPnl"] = lf["closedPnl"].map(lambda v: usd(v, True))
        lf = lf.rename(columns={"t": "quando (UTC)", "coin": "ativo", "dir": "tipo", "side": "lado", "px": "preço",
                                "sz": "tamanho", "startPosition": "posição antes", "closedPnl": "PnL realizado"})
        md += ["**Liquidações e ADL (auto-deleveraging) nos fills:**", "", md_table(lf, index=False), ""]

    # ------------------------------------------------------------ copy test
    md += ["## 9. Dá para copiar? (espelhar a posição com atraso)", "",
           "PnL de quem replicasse exatamente a posição da carteira, mas com N horas de atraso (marcação horária, "
           "sem custos). Se o PnL se mantém com atraso, a vantagem está em horizontes longos e é copiável; se "
           "desaba, depende de timing fino.", ""]
    lagrows = {}
    for coin in main:
        if not len(perp_fills[perp_fills["coin"] == coin]):
            continue
        hourly = hourly_close(coin, data_dir)
        if hourly.empty:
            continue
        s = copy_lag_pnl(perp_fills, coin, hourly)
        lagrows[coin] = s
    if lagrows:
        lg = pd.DataFrame(lagrows)
        M["copy_lag"] = {c: {int(k): float(v) for k, v in lg[c].items()} for c in lg}
        tbl = lg.map(lambda v: usd(v, True))
        tbl.index = [f"{h}h" for h in lg.index]
        tbl.index.name = "atraso"
        md += [md_table(tbl), ""]

    # ------------------------------------------------------------ replication
    c0 = main[0]
    if c0 in expo and c0 in closes:
        idx = pd.date_range(expo.index.min(), closes.index.max() - pd.Timedelta(days=1), freq="D")
        actual = expo[c0].reindex(idx).fillna(0.0)
        fr = funding_df(c0, data_dir)
        frd = fr["fundingRate"].resample("D").sum() if len(fr) else None
        cut = idx[0] + (idx[-1] - idx[0]) / 2
        train, test = (idx[0], cut), (cut + pd.Timedelta(days=1), idx[-1])
        size = float(actual.abs().quantile(0.9)) or 1.0
        g = grid_search(closes[c0], opens[c0], frd, actual, train, test, size)
        lc = linear_clone(features(closes[c0]), actual, train, test)
        from .replicate import daily_backtest
        act_bt = daily_backtest(actual, closes[c0], opens[c0], frd, fee_bps=0)
        best = g.iloc[0]
        M["replication"] = {"train": [str(train[0].date()), str(train[1].date())], "test": [str(test[0].date()), str(test[1].date())],
                            "best_params": {k: best[k] for k in ["ma", "rng", "bull_frac", "fade"]},
                            "rule_test_pnl": float(best["test_pnl"]), "rule_test_corr": float(best["test_corr"]),
                            "actual_test_pnl": float(act_bt.loc[test[0]:test[1], "pnl"].sum()),
                            "clone_r2_train": float(lc["r2_train"]), "clone_r2_test": float(lc["r2_test"])}
        md += [f"## 10. Teste de replicação por regras ({c0})", "",
               f"Regra testada: *short-bias com filtro de tendência e fade* — short de até {size:,.4g} {c0} "
               "(o percentil 90 do tamanho real), cheio abaixo da média móvel e reduzido acima; dentro do regime, "
               "mais short perto do topo do range e menos perto do fundo. Parâmetros escolhidos no treino "
               f"({train[0]:%Y-%m-%d} → {train[1]:%Y-%m-%d}) e avaliados no teste ({test[0]:%Y-%m-%d} → {test[1]:%Y-%m-%d}).", "",
               md_table(pd.DataFrame({
                   "": ["melhor regra no treino", "carteira real (aprox.)"],
                   "parâmetros": [f"MA{int(best['ma'])}, range {int(best['rng'])}d, fração em alta {best['bull_frac']}, fade {best['fade']}", "—"],
                   "PnL treino": [usd(best["train_pnl"], True), usd(act_bt.loc[train[0]:train[1], "pnl"].sum(), True)],
                   "PnL teste": [usd(best["test_pnl"], True), usd(act_bt.loc[test[0]:test[1], "pnl"].sum(), True)],
                   "correlação c/ posição real (teste)": [f"{best['test_corr']:.2f}", "1.00"]}), index=False), "",
               f"Clone comportamental (regressão linear da posição real em médias móveis, ranges e retornos): "
               f"R² treino {lc['r2_train']:.2f}, R² teste {lc['r2_test']:.2f}, correlação no teste {lc['corr_test']:.2f}.", ""]
        rule_pos = None
        from .replicate import rule_trend_fade
        rule_pos = rule_trend_fade(closes[c0], size, int(best["ma"]), int(best["rng"]), best["bull_frac"], best["fade"]).reindex(idx).fillna(0)
        rule_bt = daily_backtest(rule_pos, closes[c0], opens[c0], frd)
        p8 = charts.lines_panels({"posição real (média diária)": actual, "regra replicante": rule_pos},
                                 {"real (preço + funding, aprox.)": act_bt["pnl"].cumsum(), "regra replicante": rule_bt["pnl"].cumsum()},
                                 os.path.join(img, f"replica_{c0}.png"), f"{c0}: posição real vs. regra replicante",
                                 "PnL acumulado", unit_top=c0)
        md += [f"![Replicação]({rel(p8)})", ""]

    md += ["---", "", "Metodologia e código: ver `README.md` na raiz do repositório.", ""]
    path = os.path.join(out, "relatorio_auto.md")
    with open(path, "w") as f:
        f.write("\n".join(md))
    with open(os.path.join(out, "metrics.json"), "w") as f:
        json.dump(M, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--coins", nargs="*")
    a = ap.parse_args()
    print(build(a.user, a.data_dir, a.out, a.coins))


if __name__ == "__main__":
    main()
