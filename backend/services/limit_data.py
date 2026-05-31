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


def _try_pool_with_fallback(fetch_fn, cache_key: str, fallback_days: int = 7) -> pd.DataFrame:
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
        _cache_set(cache_key, df, ttl=60)
        _current_data_date = today_str
        return df

    # 3. 今天无数据 → 逐日回退查找最近交易日
    for i in range(1, fallback_days + 1):
        past = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        df = _try_akshare(fetch_fn, pd.DataFrame(), date=past)
        if df is not None and not df.empty:
            df = tag_kline_df(df, DataSource.AKSHARE)
            # 非交易日数据用较长 TTL 缓存（1小时），避免反复回退查询
            _cache_set(cache_key, df, ttl=3600)
            _current_data_date = past
            logger.info("非交易日回退: 使用 %s 的涨停/跌停数据", past)
            return df

    # 4. 都没有 → 返回空
    df = tag_kline_df(pd.DataFrame(), DataSource.MOCK, fallback_used=True)
    _cache_set(cache_key, df, ttl=60)
    _current_data_date = None
    return df


def get_limit_up_pool() -> pd.DataFrame:
    """获取涨停股池（非交易日自动回退到最近交易日）"""
    return _try_pool_with_fallback(ak.stock_zt_pool_em, "limit_up_pool")


def get_limit_down_pool() -> pd.DataFrame:
    """获取跌停股池（非交易日自动回退到最近交易日）"""
    return _try_pool_with_fallback(ak.stock_zt_pool_dtgc_em, "limit_down_pool")


def get_lhb_detail(date: str | None = None) -> pd.DataFrame:
    """获取龙虎榜详情"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    df = _try_akshare(ak.stock_lhb_detail_em, pd.DataFrame(), date=date)
    if df is not None and not df.empty:
        return tag_kline_df(df, DataSource.AKSHARE)
    return tag_kline_df(pd.DataFrame(), DataSource.MOCK, fallback_used=True)
