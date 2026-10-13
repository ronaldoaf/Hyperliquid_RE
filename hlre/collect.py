"""Download everything the public Info API exposes about a wallet.

Usage:
    python -m hlre.collect 0xWALLET [--data-dir data]

Writes data/<wallet>/{snapshot.json, fills.json.gz, funding.json.gz,
ledger.json.gz, orders.json.gz, twap_fills.json.gz}.

The API only serves the most recent 10k fills and 2k historical orders, so
new downloads are merged into whatever is already on disk: re-running the
collector later extends the history instead of replacing it.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import time

from .api import InfoClient


def _load(path: str) -> list:
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt") as f:
        return json.load(f)


def _save(path: str, rows: list) -> None:
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as f:
        json.dump(rows, f, separators=(",", ":"))
    os.replace(tmp, path)


def _merge(old: list, new: list, key, time_of) -> list:
    seen = {}
    for r in old + new:
        seen[key(r)] = r
    return sorted(seen.values(), key=time_of)


def fill_key(f: dict):
    return (f["tid"], f["oid"], f["time"], f["sz"], f["px"])


def funding_key(f: dict):
    return (f["time"], f["delta"]["coin"])


def ledger_key(f: dict):
    return (f["time"], f["hash"], json.dumps(f["delta"], sort_keys=True))


def order_key(o: dict):
    return (o["order"]["oid"], o["status"], o["statusTimestamp"])


SYSTEM_PREFIXES = ("0x2000000000000000000000000000000000000", "0x2222222222222222222222222222222222222222")


def related_wallets(c: InfoClient, user: str, ledger: list, snapshot: dict, top: int = 6) -> list[dict]:
    """Wallets tied to this one: the staking account linked for fee discounts
    and the largest transfer counterparties (system/bridge addresses excluded)."""
    vol: dict[str, list] = {}
    for r in ledger:
        d = r["delta"]
        if d["type"] not in ("send", "spotTransfer", "internalTransfer") or "destination" not in d:
            continue
        other = (d["destination"] if d["user"].lower() == user else d["user"]).lower()
        if other == user or other.startswith(SYSTEM_PREFIXES):
            continue
        v = float(d.get("usdcValue") or d.get("usdc") or 0.0)
        vol.setdefault(other, [0, 0.0])
        vol[other][0] += 1
        vol[other][1] += v
    # zero-value counterparties are unsolicited spam-token airdrops, not relationships
    vol = {a: x for a, x in vol.items() if x[1] > 0}
    cands = {a: {"relation": "transfers", "n_transfers": n, "transfer_usd": v}
             for a, (n, v) in sorted(vol.items(), key=lambda kv: -kv[1][1])[:top]}
    link = ((snapshot.get("userFees") or {}).get("stakingLink") or {})
    if link.get("stakingUser"):
        a = link["stakingUser"].lower()
        cands.setdefault(a, {"n_transfers": vol.get(a, [0])[0], "transfer_usd": vol.get(a, [0, 0.0])[1]})
        cands[a]["relation"] = "staking link" + (" + transfers" if a in vol else "")
    out = []
    for a, info in cands.items():
        row = {"address": a, **info}
        try:
            row["role"] = c.post({"type": "userRole", "user": a}).get("role")
            ch = c.post({"type": "clearinghouseState", "user": a})
            row["perp_account_value"] = float(ch["marginSummary"]["accountValue"])
            pf = dict(c.post({"type": "portfolio", "user": a}))
            at = pf.get("allTime", {})
            row["all_time_pnl"] = float(at["pnlHistory"][-1][1]) if at.get("pnlHistory") else None
            row["all_time_volume"] = float(at.get("vlm") or 0.0)
            row["account_value"] = float(at["accountValueHistory"][-1][1]) if at.get("accountValueHistory") else None
            row["hype_staked"] = float(c.post({"type": "delegatorSummary", "user": a}).get("delegated") or 0.0)
            sp = c.post({"type": "spotClearinghouseState", "user": a})
            row["top_spot"] = sorted(((b["coin"], float(b["total"])) for b in sp.get("balances", []) if float(b["total"]) > 0),
                                     key=lambda x: -x[1])[:3]
        except Exception as e:  # informative only
            row["error"] = str(e)[:120]
        out.append(row)
    return out


def collect(user: str, data_dir: str = "data", verbose: bool = True) -> str:
    user = user.lower()
    out = os.path.join(data_dir, user)
    os.makedirs(out, exist_ok=True)
    c = InfoClient()
    now = int(time.time() * 1000)

    def log(msg):
        if verbose:
            print(msg, flush=True)

    # ---------------------------------------------------------------- snapshot
    snap = {"user": user, "collected_at": now}
    for t in [
        "userRole", "clearinghouseState", "spotClearinghouseState", "frontendOpenOrders",
        "userFees", "userRateLimit", "referral", "subAccounts", "userVaultEquities",
        "delegatorSummary", "extraAgents", "portfolio",
    ]:
        try:
            snap[t] = c.post({"type": t, "user": user})
        except Exception as e:  # keep going; some endpoints may be absent
            snap[t] = {"error": str(e)}
        log(f"snapshot {t}")
    with open(os.path.join(out, "snapshot.json"), "w") as f:
        json.dump(snap, f, indent=1)

    # ------------------------------------------------------------------- fills
    p = os.path.join(out, "fills.json.gz")
    old = _load(p)
    start = (old[-1]["time"] if old else 0)
    log(f"fills: {len(old)} on disk, fetching from {start}")
    new = c.paginate_time(
        {"type": "userFillsByTime", "user": user, "aggregateByTime": False},
        start, now, key=fill_key, page_limit=2000, verbose=verbose,
    )
    new += c.post({"type": "userFills", "user": user, "aggregateByTime": False})
    fills = _merge(old, new, fill_key, lambda r: r["time"])
    _save(p, fills)
    log(f"fills: {len(fills)} total")

    # ----------------------------------------------------------------- funding
    p = os.path.join(out, "funding.json.gz")
    old = _load(p)
    start = (old[-1]["time"] if old else 0)
    new = c.paginate_time({"type": "userFunding", "user": user}, start, now,
                          key=funding_key, page_limit=500, verbose=verbose)
    funding = _merge(old, new, funding_key, lambda r: r["time"])
    _save(p, funding)
    log(f"funding: {len(funding)} total")

    # ------------------------------------------------------------------ ledger
    p = os.path.join(out, "ledger.json.gz")
    old = _load(p)
    start = (old[-1]["time"] if old else 0)
    new = c.paginate_time({"type": "userNonFundingLedgerUpdates", "user": user}, start, now,
                          key=ledger_key, page_limit=2000, verbose=verbose)
    ledger = _merge(old, new, ledger_key, lambda r: r["time"])
    _save(p, ledger)
    log(f"ledger: {len(ledger)} total")

    # ------------------------------------------------------------------ orders
    p = os.path.join(out, "orders.json.gz")
    old = _load(p)
    new = c.post({"type": "historicalOrders", "user": user})
    orders = _merge(old, new, order_key, lambda r: r["statusTimestamp"])
    _save(p, orders)
    log(f"orders: {len(orders)} total")

    snap["related"] = related_wallets(c, user, ledger, snap)
    with open(os.path.join(out, "snapshot.json"), "w") as f:
        json.dump(snap, f, indent=1)
    log(f"related wallets: {len(snap['related'])}")

    p = os.path.join(out, "twap_fills.json.gz")
    old = _load(p)
    new = c.post({"type": "userTwapSliceFills", "user": user})
    twap = _merge(old, new, lambda r: fill_key(r["fill"]), lambda r: r["fill"]["time"])
    _save(p, twap)
    log(f"twap slice fills: {len(twap)} total")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    collect(a.user, a.data_dir)


if __name__ == "__main__":
    main()
