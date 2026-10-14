"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0xd260b2216b735277da6771564a01c04856e78321/analise_extra.py

Lê só os arquivos em data/ (os mesmos do relatório) e grava img/hype_book.png e img/btc_2026.png.
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

from hlre.analyze import Wallet, approx_price_pnl, daily_exposure, position_gaps  # noqa: E402
from hlre.market import candles_df  # noqa: E402

USER = "0xd260b2216b735277da6771564a01c04856e78321"
DATA = os.path.join(ROOT, "data")
OUT = os.path.dirname(os.path.abspath(__file__))
SPOT_HYPE, SPOT_BTC = "@107", "@142"
SERVICE = "0x6b9e773128f453f5c2c60935ee2de2cbc5390a24"  # hot wallet de exchange/ponte (ver report.KNOWN)
HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
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


def gap_prices(w: Wallet, gaps: pd.DataFrame) -> pd.DataFrame:
    """Preço de cada salto de posição sem fill. Saltos curtos: média dos fechamentos de 4h do
    intervalo. Saltos de vários dias: a posição média diária do funding diz em que dias o tamanho
    mudou; o salto é marcado na média de 4h desses dias, ponderada pela mudança."""
    fu = w.funding
    px = []
    for _, gp in gaps.iterrows():
        k = candles_df(gp["coin"], "4h", DATA)["close"]
        a, b = gp["after"], gp["before"]
        p = np.nan
        if b - a >= pd.Timedelta(days=1):
            d = fu[(fu["coin"] == gp["coin"]) & (fu["t"] >= a.floor("D")) & (fu["t"] <= b.floor("D"))]
            dd = d.set_index("day")["szi"].diff().iloc[1:]
            wts: dict = {}
            for day, v in dd.items():  # o passo da média de d-1 para d se espalha por d-1 e d
                for x in (day - pd.Timedelta(days=1), day):
                    wts[x] = wts.get(x, 0.0) + v / 2
            s = pd.Series(wts, dtype=float)
            s = s[np.sign(s) == np.sign(gp["jump"])]
            if len(s):
                pxd = {x: k.loc[x:x + pd.Timedelta(hours=23)].mean() for x in s.index}
                p = sum(s[x] * pxd[x] for x in s.index) / s.sum()
        if np.isnan(p):
            p = k.loc[a - pd.Timedelta(hours=4):b].mean()
        px.append(p)
    return gaps.assign(px=px)


def coin_cash_pnl(w: Wallet, gaps: pd.DataFrame) -> pd.DataFrame:
    """PnL por moeda no período dos fills, por fluxo de caixa: fills + saltos sem fill + posição
    que já existia no 1º fill (marcada no preço dele) + posição aberta hoje + funding."""
    f = w.fills[w.fills["kind"].isin(("perp", "hip3"))]
    t0 = f["t"].min().floor("D")
    pos = {p["position"]["coin"]: p["position"] for p in w.snapshot["clearinghouseState"]["assetPositions"]}
    fund = w.funding[w.funding["t"] >= t0].groupby("coin")["usdc"].sum()
    rows = []
    for coin, g in f.groupby("coin"):
        g = g.sort_values("time", kind="mergesort")
        gg = gaps[gaps["coin"] == coin]
        p = pos.get(coin)
        rows.append({
            "coin": coin,
            "fills": float((-g["q"] * g["px"]).sum() - g["fee"].sum()),
            "saltos": float((-gg["jump"] * gg["px"]).sum()),
            "inicial": float(-g["startPosition"].iloc[0] * g["px"].iloc[0]),
            "aberto": float(p["positionValue"]) * np.sign(float(p["szi"])) if p else 0.0,
            "funding": float(fund.get(coin, 0.0)),
        })
    out = pd.DataFrame(rows).set_index("coin")
    out["total"] = out.sum(axis=1)
    return out.sort_values("total")


def hype_inventory(w: Wallet) -> pd.DataFrame:
    """HYPE em spot e em staking. O spot vem do saldo que cada fill do @107 traz (`startPosition`
    e `endPosition`), então inclui saídas sem fill visível; depois do último fill aplica as
    transferências de staking e termina no saldo de hoje. O staking é a soma das transferências."""
    f = w.fills
    s = f[f["coin"] == SPOT_HYPE].sort_values("time", kind="mergesort")
    spot = pd.concat([pd.Series(s["startPosition"].values, index=s["t"] - pd.Timedelta(milliseconds=1)),
                      pd.Series(s["endPosition"].values, index=s["t"])]).sort_index()
    st = w.ledger[w.ledger["type"] == "cStakingTransfer"].copy()
    st["a"] = st["raw"].map(lambda r: (1 if r["isDeposit"] else -1) * float(r["amount"]))
    staked = st.set_index("t")["a"].cumsum()
    last = spot.iloc[-1]
    for t, a in st.loc[st["t"] > s["t"].max()].set_index("t")["a"].items():
        last -= a
        spot.loc[t] = last
    now = pd.Timestamp(w.snapshot["collected_at"], unit="ms")
    bal = {b["coin"]: float(b["total"]) for b in w.snapshot["spotClearinghouseState"]["balances"]}
    spot.loc[now] = bal.get("HYPE", 0.0)
    idx = spot.index.union(staked.index)
    return pd.DataFrame({"spot": spot.groupby(level=0).last().reindex(idx).ffill().fillna(0.0),
                         "staked": staked.groupby(level=0).last().reindex(idx).ffill().fillna(0.0).clip(lower=0)})


def perp_position_daily(w: Wallet, coin: str) -> pd.Series:
    """Posição média diária do perp (funding), que cobre os saltos sem fill."""
    fu = w.funding[w.funding["coin"] == coin]
    return fu.groupby("day")["szi"].mean()


def main():
    w = Wallet(USER, DATA)
    f = w.fills
    gaps = gap_prices(w, position_gaps(f))
    pa, pp = w.portfolio("allTime"), w.portfolio("perpAllTime")
    t0 = f.loc[f["kind"] == "perp", "t"].min()

    # ------------------------------------------------------------ §3 de onde veio o PnL
    title("§3 PnL por moeda no período dos fills (fluxo de caixa, saltos marcados)")
    print(gaps[["coin", "after", "before", "jump", "px"]].round({"jump": 2, "px": 2}).to_string())
    cp = coin_cash_pnl(w, gaps)
    print(cp.round(0).to_string())
    print(f"soma: {cp['total'].sum():,.0f}")
    p_at = pp.loc[pp.index <= t0, "pnl"].iloc[-1]
    print(f"portfolio perp: {p_at:,.0f} até {t0:%Y-%m-%d} -> {pp['pnl'].iloc[-1]:,.0f} hoje "
          f"(variação {pp['pnl'].iloc[-1] - p_at:,.0f})")
    d = pd.DataFrame({"total": pa["pnl"], "perp": pp["pnl"].reindex(pa.index, method="nearest")})
    d["fora_do_perp"] = d["total"] - d["perp"]
    print("PnL all-time: total / perp / fora do perp (spot, staking, vault, juros):")
    print((d.iloc[[-1]] / 1e6).round(2).to_string())

    title("§3 PnL aproximado (posição média diária × movimento + funding), antes e depois dos fills")
    ex = daily_exposure(w.funding)
    ap = approx_price_pnl(ex, w.opens(ex.columns), w.closes(ex.columns))
    fu = w.funding.pivot_table(index="day", columns="coin", values="usdc", aggfunc="sum")
    tot = ap.add(fu.reindex(ap.index).fillna(0.0), fill_value=0.0)
    cut = t0.floor("D")
    by = pd.DataFrame({"antes": tot[tot.index < cut].sum(), "depois": tot[tot.index >= cut].sum()})
    print(by.round(0).sort_values("antes").to_string())
    print("por trimestre:", (tot.sum(axis=1).groupby(tot.index.to_period("Q")).sum() / 1e6).round(2).to_dict())
    print("por mês, BTC/HYPE/SOL/ETH:")
    print((tot.groupby(tot.index.to_period("M")).sum()[["BTC", "HYPE", "SOL", "ETH"]] / 1e3).round(0).to_string())

    # ------------------------------------------------------------ §4 o livro de HYPE
    title("§4 HYPE: perp + spot + staking")
    inv = hype_inventory(w)
    print("staking (cStakingTransfer):")
    st = w.ledger[w.ledger["type"] == "cStakingTransfer"]
    for _, r in st.iterrows():
        a = float(r["raw"]["amount"]) * (1 if r["raw"]["isDeposit"] else -1)
        print(f"  {r['t']:%Y-%m-%d %H:%M}  {a:+,.0f} HYPE")
    fs = w.snapshot["userFees"]
    print("desconto de staking ativo:", fs.get("activeStakingDiscount"))
    print("faixas (bps do supply máximo de 1B -> desconto):",
          [(float(x["bpsOfMaxSupply"]) * 1e5, x["discount"]) for x in fs["feeSchedule"]["stakingDiscountTiers"]])
    sp = f[f["coin"] == SPOT_HYPE]
    sm = sp.groupby(sp["t"].dt.to_period("M")).agg(
        qtd=("q", "sum"), compras=("q", lambda x: x[x > 0].sum()), vendas=("q", lambda x: x[x < 0].sum()),
        vwap=("px", lambda x: np.average(x, weights=sp.loc[x.index, "sz"])))
    print("spot @107 por mês:")
    print(sm.round(1).to_string())
    print("estoque spot/staking no fim de cada mês:")
    print(inv.resample("ME").last().ffill().round(0).to_string())
    vol = w.snapshot["userFees"]["dailyUserVlm"]
    print("volume diário do usuário (userFees), últimos dias:",
          {v["date"]: round(float(v["userCross"]) + float(v["userAdd"])) for v in vol if float(v["userCross"]) > 0})
    nt = f[f["twapId"].isna()] if "twapId" in f else f
    print(f"último fill fora de TWAP na API: {nt['t'].max()}")
    print(f"HYPE spot depois do último fill + unstake de 2/out: {inv['spot'].iloc[-2]:,.0f}; hoje: {inv['spot'].iloc[-1]:,.0f} "
          f"-> vendidos fora da API: {inv['spot'].iloc[-2] - inv['spot'].iloc[-1]:,.0f} HYPE")
    bl = w.ledger[(w.ledger["type"] == "borrowLend") & (w.ledger["t"] >= "2026-10-03") & (w.ledger["t"] < "2026-10-05")]
    print(f"USDC emprestado em 3–4/out: {bl['raw'].map(lambda r: float(r['amount'])).sum():,.0f}")
    hp = candles_df("HYPE", "1d", DATA)["close"]
    perp_h = perp_position_daily(w, "HYPE")
    daily_inv = inv.resample("D").last().ffill()
    book = pd.DataFrame({"perp": perp_h, "spot": daily_inv["spot"], "staked": daily_inv["staked"]})
    book = book.loc["2025-12-01":].ffill().fillna(0.0)
    book["perp"] = perp_h.reindex(book.index).fillna(0.0)
    book["total"] = book.sum(axis=1)
    px = hp.reindex(book.index).ffill()
    print("HYPE total (perp+spot+staking) no fim de cada mês, e em US$:")
    m = book.resample("ME").last()
    m["usd"] = m["total"] * px.resample("ME").last()
    print(m.round(0).to_string())
    hold = (daily_inv["spot"] + daily_inv["staked"]).reindex(px.index).ffill().fillna(0.0)
    spot_pnl = (hold.shift(1) * px.diff()).loc["2025-12-11":"2026-10-02"]
    print(f"PnL de carregar o HYPE spot+staking (fechamento diário, dez/2025 -> 2/out/2026): {spot_pnl.sum():,.0f}")
    print("  por mês:", (spot_pnl.groupby(spot_pnl.index.to_period("M")).sum() / 1e3).round(0).to_dict())

    fig, ax = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, height_ratios=[2, 1])
    ax[0].stackplot(book.index, book["perp"].clip(lower=0) / 1e3, book["spot"] / 1e3, book["staked"] / 1e3,
                    labels=["perp (long)", "spot", "staking"], colors=["#1f5fa8", "#6aa1d8", "#b9d3ee"])
    ax[0].plot(book.index, book["perp"].clip(upper=0) / 1e3, color="#c0392b", lw=1, label="perp (short)")
    ax[0].set_ylabel("mil HYPE")
    ax[0].legend(loc="upper left", fontsize=8)
    ax[0].set_title("HYPE: perp + spot + staking (100k em staking = faixa de 30% de desconto na taxa)")
    ax[1].plot(px.index, px, color="#333")
    ax[1].set_ylabel("HYPE (US$)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "img", "hype_book.png"), dpi=110)
    plt.close(fig)

    # ------------------------------------------------------------ §5 o long de BTC de 2026
    title("§5 BTC: o long de mai–ago/2026")
    b = perp_position_daily(w, "BTC").loc["2026-05-10":"2026-08-10"]
    bp = candles_df("BTC", "1d", DATA)["close"]
    bo = candles_df("BTC", "1d", DATA)["open"]
    tbl = pd.DataFrame({"posição": b, "btc": bp.reindex(b.index)})
    tbl["nocional"] = tbl["posição"] * tbl["btc"]
    tbl["pnl_dia"] = b * (bp - bo).reindex(b.index)
    print(tbl.round(0).to_string())
    g = f[(f["coin"] == "BTC") & (f["t"] >= "2026-05-17") & (f["t"] < "2026-08-04")]
    gg = gaps[(gaps["coin"] == "BTC") & (gaps["after"] >= "2026-05-17") & (gaps["after"] < "2026-08-04")]
    buys = g[g["q"] > 0]
    print(f"compras visíveis: {buys['q'].sum():,.1f} BTC a VWAP {np.average(buys['px'], weights=buys['sz']):,.0f}; "
          f"1ª compra {buys['t'].min():%Y-%m-%d} a {buys['px'].iloc[0]:,.0f}")
    sells = pd.concat([g.loc[g["q"] < 0, ["q", "px"]], gg.rename(columns={"jump": "q"})[["q", "px"]]])
    print(f"vendas (fills + saltos): {sells['q'].sum():,.1f} BTC a VWAP {np.average(sells['px'], weights=-sells['q']):,.0f}")
    cash = float((-g["q"] * g["px"]).sum() - g["fee"].sum() + (-gg["jump"] * gg["px"]).sum())
    s0 = float(g["startPosition"].iloc[0])
    s1 = float(g["endPosition"].iloc[-1])
    fu_b = w.funding[(w.funding["coin"] == "BTC") & (w.funding["t"] >= "2026-05-17") & (w.funding["t"] < "2026-08-04")]["usdc"].sum()
    print(f"posição no início {s0:.2f} e no fim {s1:.2f} BTC; caixa {cash:,.0f}; funding {fu_b:,.0f}; "
          f"resultado do episódio ~{cash - s0 * g['px'].iloc[0] + s1 * g['px'].iloc[-1] + fu_b:,.0f}")
    av = pa.loc["2026-05-20":"2026-07-01"]
    print("conta (allTime) no período:")
    print((av / 1e6).round(2).to_string())
    L = w.ledger
    inflow = L[(L["t"] >= "2026-05-20") & (L["t"] < "2026-06-08") & (L["usd"] > 0)]
    print(f"entradas de 20/mai a 7/jun/2026: {inflow['usd'].sum():,.0f} "
          f"(da hot wallet de serviço: {inflow.loc[inflow['counterparty'].str.lower() == SERVICE, 'usd'].sum():,.0f})")

    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True, height_ratios=[1, 1])
    pb = perp_position_daily(w, "BTC")
    pb = pb.reindex(pd.date_range("2025-10-15", pb.index.max(), freq="D")).fillna(0.0)  # dia sem funding = zerado
    ax[0].fill_between(pb.index, 0, pb.clip(lower=0), color="#1f5fa8", step="mid")
    ax[0].fill_between(pb.index, 0, pb.clip(upper=0), color="#c0392b", step="mid")
    ax[0].set_ylabel("BTC (posição média diária)")
    ax[0].set_title("BTC perp: compra quedas e aumenta contra o preço; o lote de 888 BTC de jun/2026")
    bpx = bp.loc["2025-10-15":]
    ax[1].plot(bpx.index, bpx / 1e3, color="#333")
    ax[1].set_ylabel("BTC (mil US$)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "img", "btc_2026.png"), dpi=110)
    plt.close(fig)

    # ------------------------------------------------------------ §1/§6 dinheiro, liquidação, cofres
    title("§1 fluxos")
    L = w.ledger
    kinds = L.groupby("type")["usd"].agg(["size", "sum"])
    print(kinds.round(0).to_string())
    snd = L[L["type"] == "send"]
    ext = snd[snd["usd"] != 0]
    print("sends por contraparte:", ext.groupby("counterparty")["usd"].agg(["size", "sum"]).round(0).to_dict("index"))
    vd = L[L["type"].isin(["vaultDeposit", "vaultWithdraw"])]
    print(f"HLP: {len(vd)} eventos, depositado {-vd.loc[vd['usd'] < 0, 'usd'].sum():,.0f}, "
          f"sacado {vd.loc[vd['usd'] > 0, 'usd'].sum():,.0f}, resultado {vd['usd'].sum():,.0f}")
    bl = L[L["type"] == "borrowLend"]
    sgn = bl["raw"].map(lambda r: 1 if r["operation"] == "supply" else -1)
    amt = bl["raw"].map(lambda r: float(r["amount"]))
    intr = bl["raw"].map(lambda r: float(r.get("interestAmount") or 0.0))
    print(f"empréstimo de USDC (borrowLend): {len(bl)} eventos de {bl['t'].min():%Y-%m-%d} a {bl['t'].max():%Y-%m-%d}; "
          f"líquido emprestado {(sgn * amt).sum():,.0f}; juros recebidos nos saques {intr.sum():,.0f}")
    big = L[(L["type"].isin(["deposit", "withdraw"])) & (L["usd"].abs() >= 1e6)]
    print(f"depósitos/saques >= US$1M: {len(big)}; valores redondos (x99.999 ou múltiplo de 1M ±1k): "
          f"{big['usd'].abs().map(lambda v: abs(v - round(v / 1e6) * 1e6) < 1.5e3).sum()}")

    title("§1 liquidação de 10/out/2025")
    lq = L[L["type"] == "liquidation"]
    for _, r in lq.iterrows():
        print(f"  {r['t']}  {r['raw']['liquidatedPositions']}  nocional {float(r['raw']['liquidatedNtlPos']):,.0f}  "
              f"margem {float(r['raw']['accountValue']):,.0f}  alav. {float(r['raw']['liquidatedNtlPos']) / float(r['raw']['accountValue']):.0f}x  "
              f"({r['raw']['leverageType']})")
    after = L[(L["t"] >= "2025-10-10 21:17") & (L["t"] < "2025-10-12") & (L["type"] == "deposit")]
    print(f"depósitos nas 24h seguintes: {after['usd'].sum():,.0f} em {len(after)} ({after['t'].min():%H:%M} a {after['t'].max():%d %H:%M})")
    for c in ["HYPE", "SOL"]:
        print(c, "posição média diária out/2025:", perp_position_daily(w, c).loc["2025-10-05":"2025-10-25"].round(0).to_dict())

    # ------------------------------------------------------------ §7 dá para replicar? teste de "comprar queda"
    title("§7 regra: comprar depois de queda de 24h (horário), retorno das 24h/72h seguintes")
    for coin in ["BTC", "HYPE", "SOL"]:
        k = candles_df(coin, "1h", DATA)["close"].loc["2025-12-11":]
        r24 = k.pct_change(24)
        fwd24, fwd72 = k.shift(-24) / k - 1, k.shift(-72) / k - 1
        lo = (k - k.rolling(168).min()) / (k.rolling(168).max() - k.rolling(168).min())
        sig = (r24 < -0.03) & (lo < 0.3)
        wk = k.index.to_period("W")
        res = {}
        for name, fw in (("24h", fwd24), ("72h", fwd72)):
            x = pd.DataFrame({"s": fw[sig], "w": wk[sig]}).dropna()
            base = fw.dropna().mean()
            wm = x.groupby("w")["s"].mean()  # uma observação por semana: horas seguidas não são independentes
            lo_ci, hi_ci = boot_ci(wm.values)
            res[name] = (f"{wm.mean() * 100:+.2f}% por semana com sinal (IC95 {lo_ci * 100:+.1f}%..{hi_ci * 100:+.1f}%; "
                         f"{len(wm)} semanas; {len(x)} horas) vs. base {base * 100:+.2f}%")
        print(coin, res)

    title("§7 cópia: HYPE vs BTC (ver relatório, tabela de atraso)")
    print("ver relatorio_auto.md §9")


if __name__ == "__main__":
    main()
