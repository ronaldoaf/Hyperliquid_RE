"""Números do ANALISE.md desta carteira que não saem do relatório automático.

Uso (da raiz do repositório):
    python reports/0x8bae3527e5a33fa0cf184f37bc112d071463ab6d/analise_extra.py

Lê os arquivos em data/ e baixa (com cache em data/market/binance_1m/) os klines de 1 minuto da
Binance em volta de cada evento. Grava img/eventos.png e img/pnl_livros.png.
Cada bloco indica a seção do ANALISE.md que ele sustenta.
"""
from __future__ import annotations

import io
import os
import sys
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from hlre.analyze import Wallet, episodes, executions, position_gaps  # noqa: E402
from hlre.binance import COLS  # noqa: E402
from hlre.market import candles_df  # noqa: E402

USER = "0x8bae3527e5a33fa0cf184f37bc112d071463ab6d"
DATA = os.path.join(ROOT, "data")
OUT = os.path.dirname(os.path.abspath(__file__))
BN_CACHE = os.path.join(DATA, "market", "binance_1m")
# moeda na Hyperliquid -> (símbolo no Binance USDT-M, multiplicador de preço)
BN = {"kLUNC": ("1000LUNCUSDT", 1.0), "kNEIRO": ("NEIROUSDT", 1000.0), "kPEPE": ("1000PEPEUSDT", 1.0)}
MIN_EVENT_NTL = 600_000  # tamanho mínimo de um "evento"
MIN_DISCOUNT = 0.05      # entrada pelo menos 5% melhor que o fechamento 4h anterior
pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 300)


def title(s: str):
    print(f"\n{'=' * 8} {s}")


def bn_1m(coin: str, day: pd.Timestamp) -> pd.DataFrame:
    """Klines de 1 minuto da Binance (futuros USDT-M) para o dia e os vizinhos."""
    sym, mult = BN.get(coin, (coin + "USDT", 1.0))
    os.makedirs(BN_CACHE, exist_ok=True)
    frames = []
    for d in pd.date_range(day - pd.Timedelta(days=1), day + pd.Timedelta(days=1), freq="D"):
        p = os.path.join(BN_CACHE, f"{sym}-{d:%Y-%m-%d}.zip")
        if not os.path.exists(p):
            r = requests.get(f"https://data.binance.vision/data/futures/um/daily/klines/{sym}/1m/"
                             f"{sym}-1m-{d:%Y-%m-%d}.zip", timeout=60)
            with open(p, "wb") as fh:
                fh.write(r.content if r.status_code == 200 else b"")
        raw = open(p, "rb").read()
        if not raw:
            continue
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            txt = z.read(z.namelist()[0]).decode()
        hdr = 0 if txt.startswith("open_time") else None
        frames.append(pd.read_csv(io.StringIO(txt), header=hdr, names=None if hdr == 0 else COLS)[COLS])
    if not frames:
        return pd.DataFrame()
    k = pd.concat(frames)
    k["t"] = pd.to_datetime(k["open_time"], unit="ms")
    k = k.set_index("t")[["open", "high", "low", "close", "quote_volume"]].astype(float)
    k[["open", "high", "low", "close"]] *= mult
    return k[~k.index.duplicated()].sort_index()


def coin_cash_pnl(w: Wallet, f: pd.DataFrame) -> pd.DataFrame:
    """PnL por moeda por fluxo de caixa: fills + saltos de posição sem fill (TWAPs antigas,
    marcados na média dos fechamentos 4h do intervalo) + posição aberta marcada + funding."""
    gaps = position_gaps(f)
    pos = {p["position"]["coin"]: p["position"] for p in w.snapshot["clearinghouseState"]["assetPositions"]}
    for dex in w.snapshot.get("perpDexStates", []) or []:
        for p in (dex.get("clearinghouseState") or {}).get("assetPositions", []):
            pos[p["position"]["coin"]] = p["position"]
    fund = w.funding.groupby("coin")["usdc"].sum() if len(w.funding) else pd.Series(dtype=float)
    rows = []
    for coin, g in f[f["kind"] != "spot"].groupby("coin"):
        fills_cash = float((-g["q"] * g["px"]).sum() - g["fee"].sum())
        gap_cash = 0.0
        for _, gp in gaps[gaps["coin"] == coin].iterrows():
            k = candles_df(coin, "4h", DATA)
            px = np.nan
            if len(k):
                win = k.loc[gp["after"] - pd.Timedelta(hours=4):gp["before"], "close"]
                px = win.mean() if len(win) else np.nan
            if np.isnan(px):
                px = float(g.loc[g["t"] <= gp["before"], "px"].iloc[-1])
            gap_cash += -gp["jump"] * px
        # posição que já existia no 1º fill (aberta por TWAP antiga) ou que sumiu depois do último
        g = g.sort_values("time", kind="mergesort")
        k = candles_df(coin, "4h", DATA)
        fu = w.funding[w.funding["coin"] == coin] if len(w.funding) else w.funding
        p = pos.get(coin)
        s0 = float(g["startPosition"].iloc[0])
        if abs(s0) > 1e-9:
            t_open = fu["t"].min() if len(fu) else g["t"].iloc[0]
            win = k.loc[t_open - pd.Timedelta(hours=8):g["t"].iloc[0], "close"] if len(k) else []
            px = win.mean() if len(win) else float(g["px"].iloc[0])
            gap_cash += -s0 * px
        s1 = float(g["endPosition"].iloc[-1]) - (float(p["szi"]) if p is not None else 0.0)
        if abs(s1) > 1e-9:
            t_close = fu["t"].max() if len(fu) else g["t"].iloc[-1]
            win = k.loc[g["t"].iloc[-1]:t_close + pd.Timedelta(hours=4), "close"] if len(k) else []
            px = win.mean() if len(win) else float(g["px"].iloc[-1])
            gap_cash += s1 * px
        mark = 0.0
        if p is not None:
            mark = float(p["positionValue"]) * np.sign(float(p["szi"]))
        rows.append({"coin": coin, "fills": fills_cash, "gaps": gap_cash, "open": mark,
                     "funding": -float(fund.get(coin, 0.0))})
    out = pd.DataFrame(rows).set_index("coin")
    out["total"] = out.sum(axis=1)
    return out


def find_events(w: Wallet, binance: bool = True) -> pd.DataFrame:
    """Episódios grandes cuja entrada saiu pelo menos MIN_DISCOUNT melhor que o fechamento 4h anterior."""
    f, o = w.fills, w.orders
    ex = executions(f)
    rows = []
    for coin in f.loc[f["kind"] == "perp", "coin"].unique():
        ep = episodes(ex, coin)
        k4 = candles_df(coin, "4h", DATA)
        for _, e in ep.iterrows():
            if e["max_ntl"] < MIN_EVENT_NTL or not len(k4) or pd.isna(e["entry_vwap"]):
                continue
            prev = k4.loc[k4.index <= e["start"], "close"]
            if not len(prev):
                continue
            d = e["entry_vwap"] / prev.iloc[-1] - 1
            disc = -d if e["side"] == "long" else d
            if disc < MIN_DISCOUNT:
                continue
            first = f[(f["coin"] == coin) & (f["t"] >= e["start"]) & (f["t"] < e["start"] + pd.Timedelta(seconds=2))]
            oo = o[o["oid"] == first["oid"].iloc[0]]
            lag = (first["t"].iloc[0] - oo["t"].min()).total_seconds() if len(oo) else np.nan
            # preço justo e mínimo/máximo da Binance no minuto do evento (±5 min)
            k = bn_1m(coin, e["start"].normalize()) if binance else pd.DataFrame()
            t0 = e["start"].floor("min")
            fair = bn_lo = bn_hi = np.nan
            if len(k) and t0 in k.index and k.loc[t0 - pd.Timedelta(minutes=30):t0, "quote_volume"].sum() > 0:
                fair = k.loc[t0, "open"]
                win = k.loc[t0 - pd.Timedelta(minutes=5):t0 + pd.Timedelta(minutes=5)]
                bn_lo, bn_hi = win["low"].min(), win["high"].max()
            first_px = first["px"].iloc[0] if e["side"] == "long" else first["px"].iloc[0]
            ref = fair if not np.isnan(fair) else prev.iloc[-1]
            disc_fair = (ref - e["entry_vwap"]) / ref * (1 if e["side"] == "long" else -1)
            rows.append({"coin": coin, "start": e["start"], "side": e["side"], "ntl": first["ntl"].sum(),
                         "max_ntl": e["max_ntl"], "entry": e["entry_vwap"], "fair": ref,
                         "src": "binance" if not np.isnan(fair) else "hl4h", "discount": disc_fair,
                         "bn_lo": bn_lo, "bn_hi": bn_hi, "first_px": first_px,
                         "maker": not bool(first["crossed"].any()), "lag_s": lag,
                         "captured": disc_fair * first["ntl"].sum() / (1 - disc_fair),
                         "realized_fills": e["realized"] - e["fees"], "hold_h": e["days"] * 24,
                         "hour_utc": e["start"].hour,
                         "hash": first["hash"].iloc[0]})
    ev = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
    ev["binance_never_there"] = np.where(ev["side"] == "long", ev["bn_lo"] > ev["first_px"],
                                         ev["bn_hi"] < ev["first_px"])
    return ev


def main():
    w = Wallet(USER, DATA)
    f = w.fills
    ex = executions(f)

    title("Seção 1: dinheiro, conta e quem opera")
    L = w.ledger
    print(L[["t", "type", "token", "amount", "counterparty"]].to_string(index=False))
    pa, pp = w.portfolio("allTime"), w.portfolio("perpAllTime")
    print(f"PnL all-time US$ {pa['pnl'].iloc[-1]:,.0f} | perps US$ {pp['pnl'].iloc[-1]:,.0f} | "
          f"conta hoje US$ {pa['account_value'].iloc[-1]:,.0f}")
    dep = L.loc[L["type"] == "deposit", "amount"].sum()
    wd = L.loc[L["type"] == "withdraw", "amount"].sum()
    evm = L.loc[(L["type"] == "send") & (L["counterparty"].astype(str).str.startswith("0x2000")), "amount"].sum()
    print(f"depósitos US$ {dep:,.0f} | saques pela ponte US$ {wd:,.0f} | enviados à HyperEVM US$ {evm:,.0f}")
    m = pa["pnl"].resample("1ME").last().diff()
    m.iloc[0] = pa["pnl"].resample("1ME").last().iloc[0]
    print("PnL mensal (US$ mil):", (m / 1e3).round(0).to_dict())
    rl = w.snapshot["userRateLimit"]
    print(f"requisições acumuladas: {rl['nRequestsUsed']} para US$ {float(rl['cumVlm']) / 1e6:,.0f}M de volume")
    o = w.orders
    last = o.sort_values("statusTimestamp").groupby("oid").last()
    print("ordens (últimas):", last["orderType"].value_counts().to_dict(), "| tif:", last["tif"].value_counts().to_dict())
    print("agentes de API:", w.snapshot.get("extraAgents"), "| referral:", w.snapshot["referral"]["referredBy"])
    hrs = ex["t"].dt.hour.value_counts().sort_index()
    print("execuções por hora UTC:", hrs.to_dict())

    title("Seção 2: eventos (entrada muito abaixo/acima do preço justo)")
    ev = find_events(w)
    print(ev[["coin", "start", "side", "ntl", "entry", "fair", "src", "discount", "maker", "lag_s",
              "binance_never_there", "captured", "realized_fills", "hold_h"]].round(3).to_string())
    print(f"\n{len(ev)} eventos em {ev['coin'].nunique()} moedas | {(ev['side'] == 'long').mean():.0%} compras | "
          f"desconto mediano {ev['discount'].median():.1%} (p10 {ev['discount'].quantile(.1):.1%}, "
          f"p90 {ev['discount'].quantile(.9):.1%}) | tamanho mediano US$ {ev['ntl'].median() / 1e6:.2f}M")
    print(f"ganho embutido no preço de entrada (desconto × tamanho): US$ {ev['captured'].sum() / 1e6:.2f}M")
    bnv = ev.dropna(subset=["bn_lo"])
    print(f"com dados da Binance: {len(bnv)}; em {bnv['binance_never_there'].mean():.0%} a Binance nunca chegou "
          f"ao preço de entrada (±5 min)")
    mk = ev[ev["maker"]]
    print(f"maker: {len(mk)} (latência ordem->fill mediana {mk['lag_s'].median():.2f}s, "
          f"{(mk['lag_s'] < 1).mean():.0%} abaixo de 1s) | taker: {(~ev['maker']).sum()}")
    ev["year_half"] = ev["start"].dt.to_period("Q")
    print(ev.groupby("year_half").agg(n=("coin", "size"), maker=("maker", "mean"), disc=("discount", "median"),
                                      captured=("captured", "sum")).round(3).to_string())
    print("hora UTC dos eventos:", ev["hour_utc"].value_counts().sort_index().to_dict())
    print("repetições por moeda:", ev["coin"].value_counts().to_dict())

    title("Seção 2: volume da Hyperliquid no evento (velas 5m recentes)")
    for coin, t in [("kNEIRO", "2026-10-07 07:33"), ("BSV", "2026-10-07 07:37")]:
        t = pd.Timestamp(t)
        r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "candleSnapshot", "req": {
            "coin": coin, "interval": "5m", "startTime": int((t - pd.Timedelta(hours=2)).value // 10**6),
            "endTime": int((t + pd.Timedelta(minutes=30)).value // 10**6)}}, timeout=30).json()
        c = pd.DataFrame(r)
        if c.empty:
            continue
        c["t"] = pd.to_datetime(c["t"], unit="ms")
        for col in "ohlcv":
            c[col] = c[col].astype(float)
        c["usd"] = c["v"] * c["c"]
        base = c.loc[c["t"] < t.floor("5min"), "usd"].median()
        at = c.loc[c["t"] == t.floor("5min")].iloc[0]
        print(f"{coin} {t}: vela 5m low {at['l']} vs close {at['c']} ({at['l'] / at['c'] - 1:.1%}); "
              f"volume US$ {at['usd'] / 1e6:.2f}M vs mediana de US$ {base:,.0f} nas 2h anteriores")

    title("Seção 3: PnL por livro (fluxo de caixa, inclui saídas por TWAP sem fill visível)")
    cp = coin_cash_pnl(w, f)
    ev_coins = set(ev["coin"])
    cp["livro"] = np.where(cp.index.str.contains(":"), "HIP-3 (ações, índices, commodities)",
                           np.where(cp.index.isin(ev_coins), "cripto com eventos", "cripto, outras"))
    print(cp.groupby("livro")[["fills", "gaps", "open", "funding", "total"]].sum().round(0).to_string())
    print(f"soma: US$ {cp['total'].sum():,.0f} vs portfolio perps US$ {pp['pnl'].iloc[-1]:,.0f}")
    print(cp.sort_values("total").round(0).to_string())
    gp = position_gaps(f)
    print(f"saltos de posição sem fill: {len(gp)} (US$ {gp['jump_ntl'].sum() / 1e6:.1f}M); "
          f"{gp['coin'].isin(ev_coins).mean():.0%} deles em moedas com eventos")

    title("Seção 4: livro HIP-3")
    h = f[f["kind"] == "hip3"]
    hx = ex[ex["kind"] == "hip3"]
    eps = []
    for coin in h["coin"].unique():
        e = episodes(hx, coin)
        e["coin"] = coin
        eps.append(e)
    he = pd.concat(eps)
    he["pnl"] = he["realized"] - he["fees"]
    he["under"] = he["coin"].str.split(":").str[1]
    by = he.groupby(["under", "side"]).agg(n=("pnl", "size"), pnl=("pnl", "sum"), ntl=("max_ntl", "max"),
                                           dias=("days", "median")).sort_values("pnl")
    print(by.round(1).to_string())
    print(f"episódios: {len(he)} | long {(he['side'] == 'long').mean():.0%} | acerto {(he['pnl'] > 0).mean():.0%} | "
          f"long US$ {he.loc[he['side'] == 'long', 'pnl'].sum():,.0f} short US$ {he.loc[he['side'] == 'short', 'pnl'].sum():,.0f}")
    print(f"maker no HIP-3: {(~h['crossed']).mean():.0%} dos fills; 'dex' usadas:", h["coin"].str.split(":").str[0].value_counts().to_dict())
    kr = ["SMSN", "SKHX", "SKHY", "HYUNDAI", "EWY", "KIOXIA", "DRAM", "CXMT"]
    print("asiáticas/memória:", he[he["under"].isin(kr)].groupby("under")["pnl"].sum().round(0).to_dict())
    print("top 10:", he.sort_values("pnl", ascending=False)[["coin", "side", "start", "days", "max_ntl", "entry_vwap",
                                                              "exit_vwap", "pnl"]].head(10).round(2).to_string())

    title("Seção 2: hashes das ordens da contraparte (entradas maker: o hash do fill é a transação do taker)")
    print(ev.loc[ev["maker"], ["coin", "start", "ntl", "discount", "hash"]].tail(8).to_string(index=False))

    title("Seção 1/6: a carteira que indicou esta (referral)")
    ref = w.snapshot["referral"]["referredBy"]["referrer"]
    if os.path.exists(os.path.join(DATA, ref)):
        r = Wallet(ref, DATA)
        rp = r.portfolio("allTime")
        rl_ = r.ledger
        print(f"{ref}: PnL all-time US$ {rp['pnl'].iloc[-1]:,.0f} | conta hoje US$ {rp['account_value'].iloc[-1]:,.0f} | "
              f"fills {r.fills['t'].min()} -> {r.fills['t'].max()}")
        print(f"depósitos US$ {rl_.loc[rl_['type'] == 'deposit', 'amount'].sum():,.0f} | "
              f"saques US$ {rl_.loc[rl_['type'] == 'withdraw', 'amount'].sum():,.0f}")
        print(f"último fill da indicadora: {r.fills['t'].max()} | 1º saque desta carteira: "
              f"{L.loc[L['type'] == 'withdraw', 't'].min()}")
        rev = find_events(r, binance=False)
        print(f"eventos na indicadora: {len(rev)} em {rev['coin'].nunique()} moedas, de {rev['start'].min():%d/%m/%Y} a "
              f"{rev['start'].max():%d/%m/%Y} | desconto mediano {rev['discount'].median():.1%} | "
              f"maker {rev['maker'].mean():.0%} | realizado nos fills US$ {rev['realized_fills'].sum() / 1e6:.2f}M | "
              f"embutido na entrada US$ {rev['captured'].sum() / 1e6:.2f}M")
        print("moedas:", rev["coin"].value_counts().to_dict())
        print("moedas em comum com esta carteira:", sorted(set(rev["coin"]) & set(ev["coin"])))
    else:
        print(f"(rode `python -m hlre.collect {ref}` para incluir a carteira indicadora)")

    title("Seção 5: o que sobra para copiar (eventos)")
    print(f"duração mediana de um evento: {ev['hold_h'].median():.1f} h; "
          f"{(ev['hold_h'] < 1).mean():.0%} fechados em menos de 1h")

    # gráficos
    os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for side, col in [("long", "#2a6fdb"), ("short", "#d64545")]:
        s = ev[ev["side"] == side]
        ax.scatter(s["start"], s["discount"] * 100, s=s["ntl"] / 2e4, color=col, alpha=.7, label=f"{side} (área = tamanho)")
    ax.axhline(0, color="#888", lw=.8)
    ax.set_ylabel("preço de entrada melhor que o justo (%)")
    ax.set_title("Eventos: entrada vs. preço da Binance no mesmo minuto")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "img", "eventos.png"), dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    tot = pa["pnl"]
    ax.plot(tot.index, tot / 1e6, color="#333", label="PnL total (portfolio)")
    ev_cum = ev.set_index("start")["captured"].cumsum() / 1e6
    ax.step(ev_cum.index, ev_cum, where="post", color="#2a6fdb", label="desconto embutido nos eventos (acumulado)")
    ax.set_ylabel("US$ milhões")
    ax.legend(loc="upper left")
    ax.set_title("PnL total vs. ganho embutido nas entradas dos eventos")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "img", "pnl_livros.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
