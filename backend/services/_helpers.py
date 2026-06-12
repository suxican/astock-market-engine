"""Safe akshare helpers + mock data generation.

All service modules should call akshare through _try_akshare so transient
network/proxy failures degrade cleanly instead of bubbling up to API handlers.
"""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from ._cache import mark_mock_used
from .data_quality import DataSource, tag_kline_df

logger = logging.getLogger("market_engine.data")

_AKSHARE_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
_AKSHARE_FAILURES: dict[str, tuple[int, float]] = {}
_AKSHARE_COOLDOWN_SECONDS = 20
_AKSHARE_RETRY_SLEEP_SECONDS = (0.35, 0.9)
_AKSHARE_ENV_LOCK = threading.RLock()


@contextmanager
def _akshare_network_env():
    """Temporarily disable proxy env vars for akshare's internal requests.

    Set ASTOCK_AKSHARE_USE_PROXY=1 if the runtime truly must access public
    data through a proxy.
    """
    if os.getenv("ASTOCK_AKSHARE_USE_PROXY") == "1":
        yield
        return

    with _AKSHARE_ENV_LOCK:
        previous = {key: os.environ.get(key) for key in _AKSHARE_PROXY_ENV_KEYS}
        previous_no_proxy = os.environ.get("NO_PROXY")
        try:
            for key in _AKSHARE_PROXY_ENV_KEYS:
                os.environ.pop(key, None)
            os.environ["NO_PROXY"] = "*"
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            if previous_no_proxy is None:
                os.environ.pop("NO_PROXY", None)
            else:
                os.environ["NO_PROXY"] = previous_no_proxy


def _in_akshare_cooldown(func_name: str) -> bool:
    failures, last_failure = _AKSHARE_FAILURES.get(func_name, (0, 0.0))
    return failures >= 3 and time.time() - last_failure < _AKSHARE_COOLDOWN_SECONDS


def _record_akshare_result(func_name: str, ok: bool) -> None:
    if ok:
        _AKSHARE_FAILURES.pop(func_name, None)
        return
    failures, _ = _AKSHARE_FAILURES.get(func_name, (0, 0.0))
    _AKSHARE_FAILURES[func_name] = (failures + 1, time.time())


def _try_akshare(func, default_return, *args, **kwargs):
    """Safely call akshare, returning default_return on failure or empty data."""
    func_name = getattr(func, "__name__", repr(func))
    if _in_akshare_cooldown(func_name):
        logger.warning("akshare skipped during cooldown (func=%s)", func_name)
        return default_return

    attempts = int(kwargs.pop("_retries", 1)) + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            with _akshare_network_env():
                result = func(*args, **kwargs)
            if result is None or (isinstance(result, pd.DataFrame) and result.empty):
                _record_akshare_result(func_name, ok=False)
                return default_return
            _record_akshare_result(func_name, ok=True)
            return result
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(random.uniform(*_AKSHARE_RETRY_SLEEP_SECONDS))

    _record_akshare_result(func_name, ok=False)
    logger.warning(
        "akshare call failed (func=%s, symbol=%s, args=%s, error=%s)",
        func_name,
        kwargs.get("symbol") or kwargs.get("stock") or "",
        str(args),
        last_error,
    )
    return default_return


def _generate_mock_data(symbol: str, days: int = 120) -> pd.DataFrame:
    """Generate deterministic mock OHLCV data for demo/development fallback."""
    mark_mock_used(symbol)
    logger.warning("Using mock market data; symbol=%s", symbol)
    np.random.seed(hash(symbol) % (2 ** 31))
    end = datetime.now()
    dates = [end - timedelta(days=i) for i in range(days, 0, -1)]

    base_price = 10.0 + (hash(symbol) % 200)
    prices = [base_price]
    for _ in range(days - 1):
        change = np.random.normal(0.001, 0.025)
        prices.append(prices[-1] * (1 + change))

    data = []
    for i, d in enumerate(dates):
        c = prices[i]
        o = c * (1 + np.random.normal(0, 0.01))
        h = max(o, c) * (1 + abs(np.random.normal(0, 0.005)))
        l = min(o, c) * (1 - abs(np.random.normal(0, 0.005)))
        v = np.random.exponential(500000)
        amt = v * c
        amp = (h - l) / o * 100
        pct = (c / prices[i - 1] - 1) * 100 if i > 0 else 0
        chg = c - prices[i - 1] if i > 0 else 0
        turn = np.random.uniform(0.5, 5)

        data.append({
            "date": d, "open": round(o, 2), "close": round(c, 2),
            "high": round(h, 2), "low": round(l, 2),
            "volume": int(v), "amount": round(amt, 2),
            "amplitude": round(amp, 2), "pct_change": round(pct, 2),
            "change": round(chg, 2), "turnover": round(turn, 2),
        })

    df = pd.DataFrame(data)
    return tag_kline_df(df, DataSource.MOCK, fallback_used=True)
