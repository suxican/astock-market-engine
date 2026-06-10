"""个股资金流向 + 板块资金流向"""
from datetime import datetime
from typing import Any

import akshare as ak
import pandas as pd

from ._cache import _cache_get, _cache_set
from ._helpers import _try_akshare
from .data_quality import DataSource, quality_dict, tag_kline_df


SECTOR_TYPE_ALIASES = {
    "行业资金流": "行业资金流",
    "行业资金流向": "行业资金流",
    "概念资金流": "概念资金流",
    "概念资金流向": "概念资金流",
    "地域资金流": "地域资金流",
    "地域资金流向": "地域资金流",
}

_SECTOR_TYPE_CODES = {
    "行业资金流": "2",
    "概念资金流": "3",
    "地域资金流": "1",
}

_SECTOR_FLOW_FIELDS = (
    "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,"
    "f78,f81,f84,f87,f204,f205,f124"
)


def _empty_fund_flow(symbol: str, source: DataSource = DataSource.DEFAULT) -> dict[str, Any]:
    """资金流不可用时返回确定性空值，避免随机 mock 误导上层分析。"""
    return quality_dict({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "主力净流入": 0.0,
        "小单净流入": 0.0,
        "中单净流入": 0.0,
        "大单净流入": 0.0,
        "超大单净流入": 0.0,
        "data_available": False,
        "message": f"资金流数据源不可用: {symbol}",
    }, source, fallback_used=True)


def get_stock_fund_flow(symbol: str) -> dict[str, Any]:
    """获取个股资金流向（大单/小单净流入）"""
    df = _try_akshare(
        ak.stock_individual_fund_flow,
        None,
        stock=symbol,
        market="sh" if symbol.startswith("6") else "sz"
    )
    if df is None:
        return _empty_fund_flow(symbol)
    try:
        latest = df.iloc[-1]
        return quality_dict({
            "date": str(latest.iloc[0]),
            "主力净流入": float(latest.iloc[1]),
            "小单净流入": float(latest.iloc[2]) if len(latest) > 2 else 0,
            "中单净流入": float(latest.iloc[3]) if len(latest) > 3 else 0,
            "大单净流入": float(latest.iloc[4]) if len(latest) > 4 else 0,
            "超大单净流入": float(latest.iloc[5]) if len(latest) > 5 else 0,
            "data_available": True,
        }, DataSource.AKSHARE)
    except Exception:
        return _empty_fund_flow(symbol)


def _normalize_sector_type(sector_type: str) -> str:
    return SECTOR_TYPE_ALIASES.get(sector_type, sector_type)


def _fetch_sector_fund_flow_curl(sector_type: str) -> pd.DataFrame:
    """用 curl_cffi 直连东财板块资金接口，作为 akshare requests 失败时的兜底。"""
    try:
        from curl_cffi import requests as curl_requests
    except Exception:
        return pd.DataFrame()

    sector_code = _SECTOR_TYPE_CODES.get(sector_type)
    if not sector_code:
        return pd.DataFrame()

    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
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
            "fields": _SECTOR_FLOW_FIELDS,
        }
        r = curl_requests.get(url, params=params, impersonate="chrome", timeout=15)
        data = r.json().get("data") or {}
        rows = data.get("diff") or []
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
        numeric_cols = [c for c in df.columns if c not in ("代码", "名称", "领涨股票")]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def get_sector_fund_flow_by_type(sector_type: str = "行业资金流") -> pd.DataFrame:
    """获取板块资金流向（带 60s TTL 缓存）"""
    normalized_type = _normalize_sector_type(sector_type)
    cache_key = f"sector_flow:{normalized_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    df = _try_akshare(
        ak.stock_sector_fund_flow_rank,
        pd.DataFrame(),
        indicator="今日",
        sector_type=normalized_type,
    )
    source = DataSource.AKSHARE if df is not None and not df.empty else DataSource.DEFAULT
    if source == DataSource.DEFAULT:
        df = _fetch_sector_fund_flow_curl(normalized_type)
        source = DataSource.CURL_EASTMONEY if df is not None and not df.empty else DataSource.DEFAULT
    df = tag_kline_df(df if df is not None else pd.DataFrame(), source, fallback_used=source != DataSource.AKSHARE)
    df.attrs["_sector_type"] = normalized_type
    _cache_set(cache_key, df, ttl=60)
    return df


def get_sector_fund_flow() -> pd.DataFrame:
    """获取行业板块资金流向（get_sector_fund_flow_by_type 快捷方式）"""
    return get_sector_fund_flow_by_type("行业资金流")
