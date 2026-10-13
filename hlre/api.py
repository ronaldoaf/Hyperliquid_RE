"""Minimal client for the public Hyperliquid Info API.

Only read-only `POST /info` endpoints are used; no keys are needed.
Handles throttling (the info endpoint is IP rate-limited by request
weight), retries with exponential backoff, and time-based pagination.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Iterable

import requests

API_URL = "https://api.hyperliquid.xyz/info"


class InfoClient:
    def __init__(self, url: str = API_URL, min_interval: float = 1.0, timeout: float = 60.0):
        self.url = url
        self.min_interval = min_interval
        self.base_interval = min_interval
        self.timeout = timeout
        self._last = 0.0
        self.session = requests.Session()

    def post(self, body: dict, retries: int = 8) -> Any:
        delay = 5.0
        for attempt in range(retries):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.session.post(self.url, json=body, timeout=self.timeout)
                if r.status_code == 429:
                    # heavy endpoints (fundingHistory, candles) weigh more per call: slow the pace,
                    # then let it creep back to the base interval as calls succeed
                    self.min_interval = min(self.min_interval * 1.5, 5.0)
                if r.status_code == 429 or r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}: {r.text[:200]}")
                r.raise_for_status()
                self.min_interval = max(self.base_interval, self.min_interval * 0.98)
                return r.json()
            except (requests.RequestException, ValueError):
                if attempt == retries - 1:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60.0)

    # ------------------------------------------------------------------ helpers
    def paginate_time(
        self,
        body: dict,
        start_ms: int,
        end_ms: int | None = None,
        key: Callable[[dict], Any] = lambda x: (x.get("time"), x.get("hash"), str(x)),
        time_of: Callable[[dict], int] = lambda x: int(x["time"]),
        page_limit: int = 500,
        verbose: bool = False,
    ) -> list[dict]:
        """Walk forward in time over an endpoint that accepts startTime/endTime
        and returns the *oldest* `page_limit` rows of the window, ascending.

        The next page starts at the last timestamp seen (not +1) so rows that
        share a timestamp across a page boundary are not lost; duplicates are
        removed with `key`.
        """
        end_ms = end_ms or int(time.time() * 1000)
        seen: set = set()
        out: list[dict] = []
        cur = start_ms
        while cur <= end_ms:
            page = self.post({**body, "startTime": cur, "endTime": end_ms})
            if not page:
                break
            new = 0
            for item in page:
                k = key(item)
                if k not in seen:
                    seen.add(k)
                    out.append(item)
                    new += 1
            last_t = max(time_of(x) for x in page)
            if verbose:
                print(f"  {body['type']}: +{new} (total {len(out)}) up to {last_t}", flush=True)
            if new == 0:
                if len(page) < page_limit:
                    break
                cur = last_t + 1  # a single timestamp holds a full page: skip it
                continue
            if len(page) < page_limit:
                break
            cur = last_t
        out.sort(key=time_of)
        return out


def chunks(seq: Iterable, n: int):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
