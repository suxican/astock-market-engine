"""涨停池 / 跌停池 / 龙虎榜数据

非交易日自动回退到最近交易日数据。
"""
from datetime import datetime, timedelta
import logging

import akshare as ak
import pandas as pd

from ._cache import _cache_get, _cache_set
from ._helpers import _try_akshare
from .data_quality import DataSource, tag_kline_df

logger = logging.getLogger("market_engine.limit_data")

# 记录当前返回数据的实际日期，供上层展示
_current_data_date: str | None = None


def get_data_date() -> str | None:
    """返回当前涨停/跌停数据对应的交易日期（YYYYMMDD 格式），None 表示今日实时"""
    return _current_data_date


def _attach_spot_cross_check(df: pd.DataFrame, pool_kind: str) -> pd.DataFrame:
    """用全市场快照粗校验涨跌停数量，供上层识别单源偏差。"""
    if df is None:
        return df
    check = {
        "enabled": False,
        "pool_kind": pool_kind,
        "pool_count": int(len(df)),
        "spot_count": None,
        "diff": None,
        "diff_ratio": None,
        "status": "unknown",
    }
    try:
        from .quote_data import _get_spot_em_df

        spot = _get_spot_em_df()
        if spot is None or spot.empty or "涨跌幅" not in spot.columns:
            df.attrs["_cross_check"] = check
            return df

        pct = pd.to_numeric(spot["涨跌幅"], errors="coerce")
        if pool_kind == "up":
            spot_count = int((pct >= 9.8).sum())
        else:
            spot_count = int((pct <= -9.8).sum())

        pool_count = int(len(df))
        diff = pool_count - spot_count
        base = max(pool_count, spot_count, 1)
        diff_ratio = abs(diff) / base
        check.update({
            "enabled": True,
            "spot_count": spot_count,
            "diff": diff,
            "diff_ratio": round(diff_ratio, 4),
            "status": "ok" if diff_ratio <= 0.15 else "warning",
        })
    except Exception as e:
        check["error"] = str(e)
    df.attrs["_cross_check"] = check
    return df


def _try_pool_with_fallback(
    fetch_fn,
    cache_key: str,
    pool_kind: str,
    fallback_days: int = 7,
) -> pd.DataFrame:
    """尝试获取今日数据，若为空则回退到最近交易日

    Args:
        fetch_fn: 接受 date 参数的 akshare 函数
        cache_key: 缓存键名
        fallback_days: 最多向前查找的天数
    """
    global _current_data_date

    # 1. 先查缓存
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # 2. 尝试今天
    today_str = datetime.now().strftime("%Y%m%d")
    df = _try_akshare(fetch_fn, pd.DataFrame(), date=today_str)
    if df is not None and not df.empty:
        df = tag_kline_df(df, DataSource.AKSHARE)
        df = _attach_spot_cross_check(df, pool_kind)
        _cache_set(cache_key, df, ttl=60)
        _current_data_date = today_str
        return df

    # 3. 今天无数据 → 逐日回退查找最近交易日
    for i in range(1, fallback_days + 1):
        past = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        df = _try_akshare(fetch_fn, pd.DataFrame(), date=past)
        if df is not None and not df.empty:
            df = tag_kline_df(df, DataSource.AKSHARE, fallback_used=True)
            df = _attach_spot_cross_check(df, pool_kind)
            # 非交易日数据用较长 TTL 缓存（1小时），避免反复回退查询
            _cache_set(cache_key, df, ttl=3600)
            _current_data_date = past
            logger.info("非交易日回退: 使用 %s 的涨停/跌停数据", past)
            return df

    # 4. 都没有 → 返回空
    df = tag_kline_df(pd.DataFrame(), DataSource.MOCK, fallback_used=True)
    df = _attach_spot_cross_check(df, pool_kind)
    _cache_set(cache_key, df, ttl=60)
    _current_data_date = None
    return df


def get_limit_up_pool() -> pd.DataFrame:
    """获取涨停股池（非交易日自动回退到最近交易日）"""
    return _try_pool_with_fallback(ak.stock_zt_pool_em, "limit_up_pool", "up")


def get_limit_down_pool() -> pd.DataFrame:
    """获取跌停股池（非交易日自动回退到最近交易日）"""
    return _try_pool_with_fallback(ak.stock_zt_pool_dtgc_em, "limit_down_pool", "down")


def get_lhb_detail(date: str | None = None) -> pd.DataFrame:
    """获取龙虎榜详情"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    df = _try_akshare(ak.stock_lhb_detail_em, pd.DataFrame(), date=date)
    if df is not None and not df.empty:
        return tag_kline_df(df, DataSource.AKSHARE)
    return tag_kline_df(pd.DataFrame(), DataSource.MOCK, fallback_used=True)
