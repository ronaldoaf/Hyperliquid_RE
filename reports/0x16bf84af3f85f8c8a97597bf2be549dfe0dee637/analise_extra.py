"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x16bf84af3f85f8c8a97597bf2be549dfe0dee637/analise_extra.py

Lê só os arquivos em data/ (os mesmos do relatório) e grava img/btc_perp_spot.png.
Cada bloco indica a seção do ANALISE.md que ele sustenta.
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, episode_metrics, executions, sessions  # noqa: E402
from hlre.binance import klines_df  # noqa: E402
from hlre.market import candles_df, hourly_close  # noqa: E402

USER = "0x16bf84af3f85f8c8a97597bf2be549dfe0dee637"
DATA = os.path.join(ROOT, "data")
OUT = os.path.dirname(os.path.abspath(__file__))
SPOT_BTC = "@142"  # UBTC/USDC
DEPOSIT_UBTC = 27.1669316267  # chegou por spotTransfer da ponte Unit e foi vendido em seguida
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)


def title(s: str):
    print(f"\n{'=' * 8} {s}")


def btc_book(f: pd.DataFrame) -> pd.DataFrame:
    """Posição de BTC no perp e no spot após cada fill (o spot começa no depósito de UBTC)."""
    b = f[f["coin"].isin(["BTC", SPOT_BTC])].sort_values("time").copy()
    dq = np.where(b["side"] == "B", b["sz"], -b["sz"])
    b["perp"] = np.where(b["coin"] == "BTC", dq, 0.0).cumsum()
    b["spot"] = DEPOSIT_UBTC + np.where(b["coin"] == SPOT_BTC, dq, 0.0).cumsum()
    return b.set_index("t")[["perp", "spot"]]


def boot_ci(x, n=4000, seed=0):
    r = np.random.default_rng(seed)
    x = np.asarray(x)
    m = [r.choice(x, len(x)).mean() for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])


def main():
    w = Wallet(USER, DATA)
    f = w.fills
    ex = executions(f)
    pe = ex[ex["kind"] != "spot"].copy()

    title("Seção 1: origem do dinheiro e fluxos")
    L = w.ledger
    print(L[["t", "type", "token", "amount", "counterparty"]].to_string(index=False))
    pa, pp = w.portfolio("allTime"), w.portfolio("perpAllTime")
    print(f"valor da conta hoje: US$ {pa['account_value'].iloc[-1]:,.0f} | PnL total US$ {pa['pnl'].iloc[-1]:,.0f} "
          f"| PnL perps US$ {pp['pnl'].iloc[-1]:,.0f} | spot (diferença) US$ {pa['pnl'].iloc[-1] - pp['pnl'].iloc[-1]:,.0f}")
    print("equity no fim de cada mês (US$ M):", (pa["account_value"].resample("1ME").last() / 1e6).round(2).to_dict())
    print("saldos spot hoje:", [(b["coin"], b["total"]) for b in w.snapshot["spotClearinghouseState"]["balances"]
                                if float(b["total"])])
    m = pa["pnl"].resample("1ME").last().diff()
    mp = pp["pnl"].resample("1ME").last().diff()
    print("PnL mensal (US$ mil):\n", (pd.DataFrame({"total": m, "perps": mp, "spot": m - mp}) / 1e3).round(0))

    title("Seção 2: execução")
    o = w.orders.sort_values("statusTimestamp")
    first, last = o.groupby("oid").first(), o.groupby("oid").last()
    last["placed"] = first["timestamp"]
    print(f"ordens guardadas pela API: {len(last)} ({o['t'].min():%Y-%m-%d} → {o['t'].max():%Y-%m-%d})")
    batch = last.groupby(["placed", "coin", "side"]).agg(
        n=("limitPx", "size"), sz=("origSz", "first"), pxmin=("limitPx", "min"), pxmax=("limitPx", "max"),
        reduceOnly=("reduceOnly", "first"), filled=("status", lambda s: int((s == "filled").sum())))
    ladders = batch[batch["n"] >= 3].reset_index()
    ladders["placed"] = pd.to_datetime(ladders["placed"], unit="ms").dt.strftime("%Y-%m-%d %H:%M")
    print(f"escadas (≥3 limites iguais no mesmo milissegundo): {len(ladders)}, com {ladders['n'].sum()} de "
          f"{len(last)} ordens")
    print(ladders.to_string(index=False))
    trig = last[last["isTrigger"] == True]  # noqa: E712
    print("ordens de gatilho:\n", trig[["coin", "orderType", "triggerCondition", "status", "t"]].to_string())
    pe["estilo"] = np.where(pe["taker"] > 0.5, "agressiva", "passiva")
    pe["efeito"] = np.where(pe["action"].isin(["open", "add"]), "aumenta", "reduz")
    st = pe.groupby(["estilo", "efeito"])["ntl"].agg(["size", "sum", "median"])
    st["% nocional"] = 100 * st["sum"] / st["sum"].sum()
    print(st.round(0))
    big = pe[pe["ntl"] >= 5e6]
    print(f"ordens ≥ US$ 5M: {len(big)}, taker médio {big['taker'].mean():.0%}, "
          f"slippage mediano {big['slippage_bps'].median():.1f} bps, fills medianos {big['n_fills'].median():.0f}")
    fee = f.groupby("kind").agg(fee=("fee", "sum"), ntl=("ntl", "sum"))
    fee["bps"] = 1e4 * fee["fee"] / fee["ntl"]
    print(fee.round(2))
    print("userRateLimit:", w.snapshot["userRateLimit"], "| agentes:", w.snapshot["extraAgents"])
    se = sessions(ex)
    print(f"sessões: {len(se)}; início por hora UTC:", se["start"].dt.hour.value_counts().sort_index().to_dict())
    print("por dia da semana (0 = seg):", se["start"].dt.dayofweek.value_counts().sort_index().to_dict())

    title("Seção 3: livro de BTC = perp + spot")
    book = btc_book(f)
    h = hourly_close("BTC", DATA)
    pos = book.resample("1h").last().ffill().reindex(h.index).ffill().loc["2025-10-24 03:00":].fillna(0.0)
    move = h.reindex(pos.index).diff().shift(-1)
    pnl = pos.mul(move, axis=0)
    print(f"PnL marcado hora a hora (sem taxas/funding): perp US$ {pnl['perp'].sum():,.0f} | "
          f"spot US$ {pnl['spot'].sum():,.0f}")
    d = pos.resample("1D").last()
    d["px"] = h.resample("1D").last()
    chg = d[["perp", "spot"]].diff().abs().sum(axis=1) > 0.5
    print(d[chg].round(1).to_string())
    for a, b in [("2025-12-01", "2026-01-21"), ("2026-02-03", "2026-02-13"), ("2026-04-29", "2026-06-24"),
                 ("2026-07-23", "2026-09-22")]:
        print(f"spot {a} → {b}: US$ {pnl['spot'].loc[a:b].sum():,.0f}")
    sp = ex[ex["kind"] == "spot"]
    for day in ("2026-02-12", "2026-06-23", "2026-07-23"):
        x = pd.concat([sp[sp["t"].dt.strftime("%Y-%m-%d") == day], pe[(pe["coin"] == "BTC") &
                                                                         (pe["t"].dt.strftime("%Y-%m-%d") == day)]])
        print(f"{day}: " + "; ".join(f"{r.t:%H:%M} {'spot' if r.kind == 'spot' else 'perp'} {r.side} {r.sz:.1f} @ {r.vwap:,.0f}"
                                    for r in x.sort_values("t").itertuples() if r.sz > 1))
    fb = w.funding[w.funding["coin"] == "BTC"]
    print(f"funding BTC: longs pagaram US$ {fb.loc[fb['szi'] > 0, 'usdc'].sum():,.0f}, "
          f"shorts receberam US$ {fb.loc[fb['szi'] < 0, 'usdc'].sum():,.0f}")

    fig, ax = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    hp = h.loc[pos.index[0]:]
    ax[0].plot(hp.index, hp.values, color="#444", lw=1)
    ax[0].set_ylabel("BTC (US$)")
    ax[0].set_title("Preço do BTC e posição da carteira: perp (alavancado) e spot UBTC (sem alavancagem)")
    ax[1].fill_between(pos.index, 0, pos["spot"], step="post", color="#9ecae1", label="spot UBTC")
    ax[1].step(pos.index, pos["perp"], where="post", color="#08519c", lw=1.2, label="perp")
    neg = pos["perp"].clip(upper=0)
    ax[1].fill_between(pos.index, 0, neg, step="post", color="#cb181d", alpha=0.5, label="perp vendido")
    ax[1].axhline(0, color="#888", lw=0.6)
    ax[1].set_ylabel("BTC")
    ax[1].legend(loc="upper left", frameon=False, ncol=3)
    for a in ax:
        a.grid(alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = os.path.join(OUT, "img", "btc_perp_spot.png")
    fig.savefig(p, dpi=110)
    print("gráfico:", os.path.relpath(p, ROOT))

    title("Seção 4: episódios e alavancagem")
    em = episode_metrics(w, ex)
    av = pa["account_value"]
    lev = []
    for r in em.itertuples():
        t = r.start + pd.Timedelta(hours=6)
        eq = av.reindex(av.index.union([t])).interpolate("time").loc[t]
        lev.append(r.max_ntl / eq if eq == eq and eq > 0 else np.nan)
    em["equity_lev"] = lev
    cols = ["coin", "side", "start", "days", "max_ntl", "equity_lev", "r7d", "vs_30d_high", "vs_30d_low",
            "funding_ann_pre", "adverse_pct", "captured_pct", "realized"]
    print(em[cols].assign(start=em["start"].dt.strftime("%Y-%m-%d")).round(2).to_string(index=False))
    print(f"episódios: {len(em)}, lucro: {(em['realized'] > 0).sum()}, duração mediana {em['days'].median():.1f} d")
    print(f"realizado por ativo (US$ mil):", (em.groupby("coin")["realized"].sum() / 1e3).round(0).to_dict())
    days = pd.date_range("2025-10-24", "2026-10-12", freq="D")
    held = pd.Series(False, index=days)
    for c in f.loc[f["kind"] != "spot", "coin"].unique():
        x = f[f["coin"] == c].sort_values("time").set_index("t")["endPosition"]
        held |= (x.resample("1D").agg(lambda s: s.abs().max() if len(s) else np.nan).reindex(days)
                 .fillna(x.resample("1D").last().reindex(days).ffill().abs()).fillna(0) > 0)
    print(f"dias com posição em perp: {held.sum()} de {len(days)}")
    held |= (book["spot"].resample("1D").max().reindex(days).ffill().fillna(0) > 0.5)
    print(f"dias com alguma posição (perp ou spot): {held.sum()} de {len(days)}")
    print("primeira posição: 152 BTC × ~US$ 114k sobre ~US$ 3,0M =",
          f"{152.05 * 113962 / 3.0e6:.1f}x")

    title("Seção 6: a regra mecânica de 'fade' em BTC tem vantagem?")
    bd = klines_df("BTCUSDT", "1d", DATA)
    hl = candles_df("BTC", "1d", DATA)
    c, hi, lo = (bd[k].combine_first(hl[k]) for k in ("close", "high", "low"))
    r7, r3 = c.pct_change(7), c.pct_change(3)
    rng = (c - lo.rolling(7).min()) / (hi.rolling(7).max() - lo.rolling(7).min())
    rules = {"long: 7d ≤ −7% e fundo do range 7d (<0,15)": ((r7 <= -0.07) & (rng < 0.15), 1),
             "short: 3d ≥ +3% e topo do range 7d (>0,85)": ((r3 >= 0.03) & (rng > 0.85), -1)}
    periods = {"2020-01 → 2025-10-23": ("2020-01-01", "2025-10-23"),
               "2025-10-24 → hoje (período da carteira)": ("2025-10-24", "2026-10-13")}
    for per, (a, b) in periods.items():
        print("--", per)
        for name, (mask, sgn) in rules.items():
            ev, prev = [], None
            for t in mask.loc[a:b][mask.loc[a:b]].index:  # um evento a cada 7 dias no máximo
                if prev is None or (t - prev).days >= 7:
                    ev.append(t)
                    prev = t
            for k in (7, 14):
                fwd = sgn * (c.shift(-k) / c - 1)
                x = fwd.reindex(ev).dropna()
                base = fwd.loc[a:b].dropna()
                lo_, hi_ = boot_ci(x)
                print(f"  {name} | {k}d: n={len(x)} média {100 * x.mean():+.2f}% (IC95 {100 * lo_:+.1f} a "
                      f"{100 * hi_:+.1f}), acerto {100 * (x > 0).mean():.0f}% | base do mesmo lado "
                      f"{100 * base.mean():+.2f}%, acerto {100 * (base > 0).mean():.0f}%")


if __name__ == "__main__":
    main()
