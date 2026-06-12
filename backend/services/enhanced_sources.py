"""Enhanced direct data-source adapters inspired by simonlin1212/a-stock-data.

The adapters are optional and conservative: missing dependencies or upstream
failures return empty data so the existing fallback chain can keep working.
"""
from __future__ import annotations

import random
import threading
import time
from typing import Any

import pandas as pd

from .data_quality import DataSource, tag_kline_df

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
EM_MIN_INTERVAL = 1.05
_EM_LAST_CALL = 0.0
_EM_LOCK = threading.Lock()
_EM_SESSION = None


def _market_code(symbol: str) -> int:
    return 1 if str(symbol).startswith(("6", "9")) else 0


def _get_em_session():
    global _EM_SESSION
    if _EM_SESSION is not None:
        return _EM_SESSION
    try:
        import requests

        session = requests.Session()
        session.trust_env = False
        session.headers.update({
            "User-Agent": UA,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://data.eastmoney.com/",
        })
        _EM_SESSION = session
        return session
    except Exception:
        return None


def em_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
):
    """Eastmoney request entry: serial throttle + jitter + session reuse."""
    global _EM_LAST_CALL
    with _EM_LOCK:
        wait = EM_MIN_INTERVAL - (time.time() - _EM_LAST_CALL)
        if wait > 0:
            time.sleep(wait + random.uniform(0.1, 0.45))
        session = _get_em_session()
        try:
            if session is not None:
                try:
                    return session.get(url, params=params, headers=headers, timeout=timeout)
                except Exception:
                    pass
            return _curl_get(url, params=params, headers=headers, timeout=timeout)
        finally:
            _EM_LAST_CALL = time.time()


def _curl_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
):
    try:
        from curl_cffi import requests as curl_requests

        return curl_requests.get(
            url,
            params=params,
            headers=headers,
            impersonate="chrome",
            proxies={},
            timeout=timeout,
        )
    except Exception:
        return None


def fetch_mootdx_daily(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    count: int = 400,
) -> pd.DataFrame:
    """Fetch daily bars from TDX/mootdx and normalize to Chinese columns."""
    try:
        from mootdx.quotes import Quotes

        client = Quotes.factory(market="std")
        raw = client.bars(symbol=symbol, category=4, offset=max(count, 1))
        if raw is None or len(raw) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(raw)
        if df.empty:
            return pd.DataFrame()

        date_col = "datetime" if "datetime" in df.columns else "date"
        out = pd.DataFrame({
            "日期": pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d"),
            "股票代码": symbol,
            "开盘": pd.to_numeric(df.get("open"), errors="coerce"),
            "收盘": pd.to_numeric(df.get("close"), errors="coerce"),
            "最高": pd.to_numeric(df.get("high"), errors="coerce"),
            "最低": pd.to_numeric(df.get("low"), errors="coerce"),
            "成交量": pd.to_numeric(df.get("vol", df.get("volume", 0)), errors="coerce").fillna(0),
            "成交额": pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0),
        })
        prev_close = out["收盘"].shift(1)
        out["涨跌幅"] = ((out["收盘"] / prev_close - 1) * 100).round(2).fillna(0)
        out["涨跌额"] = (out["收盘"] - prev_close).round(2).fillna(0)
        out["振幅"] = ((out["最高"] - out["最低"]) / out["开盘"] * 100).round(2).fillna(0)
        out["换手率"] = 0.0
        out = out.dropna(subset=["日期", "开盘", "收盘"])
        if start_date:
            sd = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            out = out[out["日期"] >= sd]
        if end_date:
            ed = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            out = out[out["日期"] <= ed]
        return out[[
            "日期", "股票代码", "开盘", "收盘", "最高", "最低",
            "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率",
        ]]
    except Exception:
        return pd.DataFrame()


def fetch_mootdx_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch realtime quotes from mootdx when available."""
    if not symbols:
        return {}
    try:
        from mootdx.quotes import Quotes

        client = Quotes.factory(market="std")
        df = client.quotes(symbol=symbols)
        if df is None or len(df) == 0:
            return {}
        df = pd.DataFrame(df)
        result: dict[str, dict[str, Any]] = {}
        for idx, row in df.iterrows():
            code = str(row.get("code", row.get("symbol", "")) or idx).zfill(6)[-6:]
            price = _safe_float(row.get("price", row.get("now", 0)))
            last_close = _safe_float(row.get("last_close", row.get("pre_close", 0)))
            change = price - last_close if price and last_close else 0.0
            pct = change / last_close * 100 if last_close else 0.0
            result[code] = {
                "名称": str(row.get("name", "")),
                "最新价": price,
                "昨收": last_close,
                "今开": _safe_float(row.get("open", 0)),
                "涨跌额": round(change, 2),
                "涨跌幅": round(pct, 2),
                "最高": _safe_float(row.get("high", 0)),
                "最低": _safe_float(row.get("low", 0)),
                "成交量": _safe_float(row.get("vol", row.get("volume", 0))),
                "成交额": _safe_float(row.get("amount", 0)),
                "换手率": 0.0,
                "总市值": 0.0,
                "PE": 0.0,
            }
        return {k: v for k, v in result.items() if k in symbols}
    except Exception:
        return {}


def fetch_eastmoney_stock_fund_flow(symbol: str) -> pd.DataFrame:
    """Eastmoney 120-day individual fund-flow direct endpoint."""
    try:
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            "lmt": "0",
            "klt": "101",
            "secid": f"{_market_code(symbol)}.{symbol}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "_": int(time.time() * 1000),
        }
        resp = em_get(url, params=params, headers={"Referer": "https://data.eastmoney.com/"})
        if resp is None:
            return pd.DataFrame()
        data = resp.json().get("data") or {}
        klines = data.get("klines") or []
        if not klines:
            return pd.DataFrame()
        df = pd.DataFrame([item.split(",") for item in klines])
        df.columns = [
            "日期", "主力净流入-净额", "小单净流入-净额", "中单净流入-净额",
            "大单净流入-净额", "超大单净流入-净额", "主力净流入-净占比",
            "小单净流入-净占比", "中单净流入-净占比", "大单净流入-净占比",
            "超大单净流入-净占比", "收盘价", "涨跌幅", "_1", "_2",
        ]
        for col in df.columns:
            if col != "日期":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def fetch_sector_fund_flow_em(sector_type: str) -> pd.DataFrame:
    """Eastmoney sector fund-flow rank through throttled em_get."""
    type_map = {"行业资金流": "2", "概念资金流": "3", "地域资金流": "1"}
    sector_code = type_map.get(sector_type)
    if not sector_code:
        return pd.DataFrame()
    try:
        urls = [
            "https://push2.eastmoney.com/api/qt/clist/get",
            "https://82.push2.eastmoney.com/api/qt/clist/get",
            "https://17.push2.eastmoney.com/api/qt/clist/get",
            "https://25.push2.eastmoney.com/api/qt/clist/get",
        ]
        params = {
            "pn": "1",
            "pz": "100",
            "po": "1",
            "np": "1",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "fltt": "2",
            "invt": "2",
            "fid0": "f62",
            "fs": f"m:90 t:{sector_code}",
            "stat": "1",
            "fields": (
                "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,"
                "f78,f81,f84,f87,f204,f205,f124"
            ),
            "_": int(time.time() * 1000),
        }
        rows = []
        for url in urls:
            resp = em_get(url, params=params, headers={"Referer": "https://data.eastmoney.com/"})
            if resp is None or getattr(resp, "status_code", 0) != 200:
                continue
            try:
                rows = (resp.json().get("data") or {}).get("diff") or []
            except Exception:
                rows = []
            if rows:
                break
        if not rows:
            return pd.DataFrame()
        records = []
        for idx, row in enumerate(rows, start=1):
            records.append({
                "序号": idx,
                "代码": row.get("f12", ""),
                "名称": row.get("f14", ""),
                "最新价": row.get("f2", 0),
                "今日涨跌幅": row.get("f3", 0),
                "主力净流入-净额": row.get("f62", 0),
                "主力净流入-净占比": row.get("f184", 0),
                "超大单净流入-净额": row.get("f66", 0),
                "超大单净流入-净占比": row.get("f69", 0),
                "大单净流入-净额": row.get("f72", 0),
                "大单净流入-净占比": row.get("f75", 0),
                "中单净流入-净额": row.get("f78", 0),
                "中单净流入-净占比": row.get("f81", 0),
                "小单净流入-净额": row.get("f84", 0),
                "小单净流入-净占比": row.get("f87", 0),
                "领涨股票": row.get("f204", ""),
                "领涨股票-涨跌幅": row.get("f205", 0),
                "更新时间": row.get("f124", 0),
            })
        df = pd.DataFrame(records)
        for col in [c for c in df.columns if c not in ("代码", "名称", "领涨股票")]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def fetch_ths_hotspot() -> pd.DataFrame:
    """Fetch THS hot stocks/reason tags if the zero-auth endpoint is reachable."""
    try:
        import requests

        url = "https://eq.10jqka.com.cn/open/api/hot_list/v1/hot_stock/a"
        params = {"type": "hour", "page": "1", "size": "100"}
        headers = {"User-Agent": UA, "Referer": "https://eq.10jqka.com.cn/"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        rows = data.get("data") or data.get("list") or []
        if isinstance(rows, dict):
            rows = rows.get("stock_list") or rows.get("list") or []
        if not rows:
            return tag_kline_df(pd.DataFrame(), DataSource.DEFAULT, fallback_used=True)
        df = pd.DataFrame(rows)
        return tag_kline_df(df, DataSource.THS)
    except Exception:
        return tag_kline_df(pd.DataFrame(), DataSource.DEFAULT, fallback_used=True)


def eastmoney_concept_blocks(symbol: str) -> pd.DataFrame:
    """Fetch Eastmoney sector/concept membership for one stock via slist."""
    try:
        url = "https://push2.eastmoney.com/api/qt/slist/get"
        params = {
            "fltt": "2",
            "invt": "2",
            "spt": "3",
            "pi": "0",
            "pz": "100",
            "fields": "f12,f14,f3,f128,f140,f141",
            "secid": f"{_market_code(symbol)}.{symbol}",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
        }
        resp = em_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
        if resp is None:
            return pd.DataFrame()
        rows = (resp.json().get("data") or {}).get("diff") or []
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
