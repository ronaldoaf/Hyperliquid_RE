"""Static report charts (matplotlib, PNG).

Visual conventions: light chart surface, hairline solid grid, 2px lines,
categorical colours in a fixed order, a blue/red diverging pair for signed
quantities (long/short, gain/loss), and never two y-scales on one plot
(price and position go in stacked panels that share the time axis).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
POS = "#2a78d6"   # diverging pole: long / gain
NEG = "#e34948"   # diverging pole: short / loss

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "grid.linestyle": "-", "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.prop_cycle": matplotlib.cycler(color=SERIES),
    "axes.axisbelow": True,
})


def _trim(v: float) -> str:
    # up to two decimals, no trailing zeros: 1.25, 1.5, 2 (keeps 1,250 and 1,500 ticks distinct)
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _money(x, _=None):
    a = abs(x)
    s = "-" if x < 0 else ""
    if a >= 1e9:
        return f"{s}${_trim(a / 1e9)}B"
    if a >= 1e6:
        return f"{s}${_trim(a / 1e6)}M"
    if a >= 1e3:
        return f"{s}${_trim(a / 1e3)}K"
    return f"{s}${a:.0f}"


def _compact(x, _=None):
    a = abs(x)
    s = "-" if x < 0 else ""
    if a >= 1e6:
        return f"{s}{_trim(a / 1e6)}M"
    if a >= 1e3:
        return f"{s}{_trim(a / 1e3)}K"
    return f"{s}{a:g}"


def _dates(ax):
    loc = mdates.AutoDateLocator(minticks=4, maxticks=9)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def _save(fig, path):
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def pnl_curve(series: dict[str, pd.Series], events: list[tuple] | None, path: str, title: str):
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for name, s in series.items():
        ax.plot(s.index, s.values, label=name)
    merged: dict = {}
    for t, label in events or []:
        merged.setdefault(pd.Timestamp(t).floor("D"), []).append(label)
    for t, labels in merged.items():
        label = " + ".join(labels).replace("$", r"\$")  # keep matplotlib from reading $..$ as math
        ax.axvline(t, color=AXIS, lw=1)
        ax.annotate(label, (t, 1), xycoords=("data", "axes fraction"), xytext=(3, -2),
                    textcoords="offset points", va="top", fontsize=8, color=INK2)
    ax.axhline(0, color=AXIS, lw=1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_money))
    _dates(ax)
    ax.set_title(title)
    if len(series) > 1:
        ax.legend(loc="upper left", bbox_to_anchor=(0, 0.92))
    return _save(fig, path)


def attribution_bars(df: pd.DataFrame, path: str, title: str):
    """df: index=coin, columns=components (e.g. price, funding); horizontal grouped bars."""
    n, k = len(df), len(df.columns)
    fig, ax = plt.subplots(figsize=(10, 0.42 * n * max(k, 1) / 1.6 + 1.6))
    h = 0.8 / k
    y = np.arange(n)
    for j, col in enumerate(df.columns):
        ax.barh(y + (j - (k - 1) / 2) * h, df[col].values, height=h * 0.85, color=SERIES[j], label=col)
    ax.set_yticks(y, df.index)
    ax.invert_yaxis()
    ax.axvline(0, color=AXIS, lw=1)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_money))
    ax.grid(axis="y", visible=False)
    ax.set_title(title)
    if k > 1:
        ax.legend(loc="lower right")
    return _save(fig, path)


def signed_bars(s: pd.Series, path: str, title: str, money: bool = True):
    """One bar per category, coloured by sign (blue gain / red loss), value at the tip."""
    fig, ax = plt.subplots(figsize=(10, 0.38 * len(s) + 1.4))
    y = np.arange(len(s))
    ax.barh(y, s.values, height=0.6, color=[POS if v >= 0 else NEG for v in s.values])
    ax.set_yticks(y, s.index)
    ax.invert_yaxis()
    ax.axvline(0, color=AXIS, lw=1)
    fmt = _money if money else _compact
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    span = (s.max() - min(s.min(), 0)) or 1
    for yi, v in zip(y, s.values):
        ax.annotate(fmt(v), (v, yi), xytext=(4 if v >= 0 else -4, 0), textcoords="offset points",
                    ha="left" if v >= 0 else "right", va="center", fontsize=8, color=INK2)
    ax.set_xlim(min(s.min(), 0) - 0.18 * span, max(s.max(), 0) + 0.18 * span)
    ax.grid(axis="y", visible=False)
    ax.set_title(title)
    return _save(fig, path)


def price_and_position(price: pd.Series, pos_daily: pd.Series | None, pos_fills: pd.Series | None,
                       path: str, coin: str, unit: str | None = None):
    """Two stacked panels sharing the time axis: price on top, signed position below."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw={"height_ratios": [1, 1.1]})
    a1.plot(price.index, price.values, color=INK, lw=1.4)
    a1.set_title(f"{coin}: preço (acima) e posição da carteira (abaixo)")
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.2f}"))
    if pos_daily is not None and len(pos_daily):
        p = pos_daily
        a2.fill_between(p.index, p.clip(lower=0).values, step="post", color=POS, alpha=0.18, lw=0)
        a2.fill_between(p.index, p.clip(upper=0).values, step="post", color=NEG, alpha=0.18, lw=0)
        early = p if pos_fills is None or not len(pos_fills) else p.loc[:pos_fills.index.min()]
        a2.step(early.index, early.clip(lower=0).values, where="post", color=POS, lw=0.9)
        a2.step(early.index, early.clip(upper=0).values, where="post", color=NEG, lw=0.9)
    if pos_fills is not None and len(pos_fills):
        q = pos_fills
        a2.step(q.index, q.clip(lower=0).values, where="post", color=POS, lw=1.2)
        a2.step(q.index, q.clip(upper=0).values, where="post", color=NEG, lw=1.2)
    a2.axhline(0, color=AXIS, lw=1)
    a2.set_ylabel(f"posição ({unit or coin})")
    a2.yaxis.set_major_formatter(mticker.FuncFormatter(_compact))
    a2.annotate("long", (0.005, 0.97), xycoords="axes fraction", va="top", fontsize=8, color=INK2)
    a2.annotate("short", (0.005, 0.03), xycoords="axes fraction", va="bottom", fontsize=8, color=INK2)
    _dates(a2)
    fig.tight_layout()
    return _save(fig, path)


def exposure_leverage(net: pd.Series, gross: pd.Series, lev: pd.Series, path: str):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
    a1.plot(gross.index, gross.values, label="exposição bruta (|long|+|short|)", color=SERIES[0])
    a1.plot(net.index, net.values, label="exposição líquida (long-short)", color=SERIES[1])
    a1.axhline(0, color=AXIS, lw=1)
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(_money))
    a1.legend(loc="lower left")
    a1.set_title("Exposição nocional em perps (média diária) e alavancagem")
    a2.plot(lev.index, lev.values, color=SERIES[0], lw=1.5)
    a2.set_ylabel("bruta / equity perp (x)")
    a2.set_ylim(bottom=0)
    _dates(a2)
    fig.tight_layout()
    return _save(fig, path)


def hbar_panels(panels: dict[str, pd.Series], path: str, title: str, fmt=None, baseline_label: str | None = None):
    """Small multiples of horizontal bars sharing category order; one colour,
    with the optional baseline category drawn in muted gray."""
    k = len(panels)
    first = next(iter(panels.values()))
    fig, axes = plt.subplots(1, k, figsize=(3.6 * k, 0.42 * len(first) + 1.5), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (name, s) in zip(axes, panels.items()):
        y = np.arange(len(s))
        cols = [MUTED if (baseline_label and i == baseline_label) else SERIES[0] for i in s.index]
        ax.barh(y, s.values, height=0.6, color=cols)
        ax.axvline(0, color=AXIS, lw=1)
        ax.set_title(name, fontsize=10)
        ax.grid(axis="y", visible=False)
        if fmt:
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt))
        for yi, v in zip(y, s.values):
            ax.annotate(fmt(v) if fmt else f"{v:.2f}", (v, yi), xytext=(3 if v >= 0 else -3, 0),
                        textcoords="offset points", ha="left" if v >= 0 else "right", va="center",
                        fontsize=8, color=INK2)
        lo, hi = min(s.min(), 0), max(s.max(), 0)
        pad = (hi - lo) * 0.35 or 1
        ax.set_xlim(lo - (pad if lo < 0 else 0), hi + pad)
    axes[0].set_yticks(np.arange(len(first)), first.index)
    axes[0].invert_yaxis()
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout()
    return _save(fig, path)


def histogram_bars(s: pd.Series, path: str, title: str, xlabel: str):
    fig, ax = plt.subplots(figsize=(10, 3.4))
    x = np.arange(len(s))
    ax.bar(x, s.values, width=0.65, color=SERIES[0])
    ax.set_xticks(x, s.index, rotation=0)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", visible=False)
    ax.set_title(title)
    return _save(fig, path)


def lines_panels(top: dict[str, pd.Series], bottom: dict[str, pd.Series], path: str,
                 title_top: str, title_bottom: str, money_bottom: bool = True, unit_top: str = ""):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for j, (name, s) in enumerate(top.items()):
        a1.plot(s.index, s.values, label=name, color=SERIES[j], lw=1.5 if j else 2)
    a1.axhline(0, color=AXIS, lw=1)
    a1.set_title(title_top)
    a1.set_ylabel(unit_top)
    a1.legend(loc="lower left")
    for j, (name, s) in enumerate(bottom.items()):
        a2.plot(s.index, s.values, label=name, color=SERIES[j], lw=1.5 if j else 2)
    a2.axhline(0, color=AXIS, lw=1)
    a2.set_title(title_bottom)
    if money_bottom:
        a2.yaxis.set_major_formatter(mticker.FuncFormatter(_money))
    a2.legend(loc="upper left")
    _dates(a2)
    fig.tight_layout()
    return _save(fig, path)


def episode_timeline(em: pd.DataFrame, path: str, title: str):
    """One row per coin, one bar per position episode (start to end), coloured
    by realised PnL sign; each row ends with the coin's total realised PnL."""
    em = em.sort_values("start")
    coins = list(dict.fromkeys(em["coin"]))
    fig, ax = plt.subplots(figsize=(11, 0.32 * len(coins) + 1.6))
    y = {c: i for i, c in enumerate(coins)}
    for _, e in em.iterrows():
        start, end = mdates.date2num(e["start"]), mdates.date2num(max(e["end"], e["start"] + pd.Timedelta(days=1)))
        col = POS if e["realized"] >= 0 else NEG
        ax.barh(y[e["coin"]], end - start, left=start, height=0.62, color=col, alpha=0.45 if e["open"] else 0.9)
    tot = em.groupby("coin")["realized"].sum()
    n = em.groupby("coin").size()
    for c in coins:
        v = tot[c]
        txt = ("+" if v > 0 else "") + _money(v).replace("$", r"\$") + (f"  ({n[c]})" if n[c] > 1 else "")
        ax.annotate(txt, (1.0, y[c]), xycoords=("axes fraction", "data"), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=POS if v >= 0 else NEG, annotation_clip=False)
    ax.set_yticks(range(len(coins)), coins)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.xaxis_date()
    _dates(ax)
    ax.set_title(title)
    ax.set_xlabel("azul = lucro realizado, vermelho = prejuízo, claro = ainda aberta; à direita, o total realizado "
                  "por ativo (nº de episódios)", color=MUTED, fontsize=8)
    fig.tight_layout()
    return _save(fig, path)


def flows_and_exposure(gross: pd.Series, flows: pd.Series, path: str, title: str):
    """Gross exposure on top; daily net deposits (up) and withdrawals (down) below."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    a1.fill_between(gross.index, gross.values, color=SERIES[0], alpha=0.18, lw=0)
    a1.plot(gross.index, gross.values, color=SERIES[0], lw=1.5)
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(_money))
    a1.set_title(title)
    a1.set_ylabel("exposição bruta")
    f = flows[flows != 0]
    a2.bar(f.index, f.clip(lower=0).values, width=1.0, color=POS, label="depósitos")
    a2.bar(f.index, f.clip(upper=0).values, width=1.0, color=NEG, label="saques")
    a2.axhline(0, color=AXIS, lw=1)
    a2.yaxis.set_major_formatter(mticker.FuncFormatter(_money))
    a2.set_ylabel("fluxo líquido do dia")
    a2.legend(loc="lower left")
    _dates(a2)
    fig.tight_layout()
    return _save(fig, path)
