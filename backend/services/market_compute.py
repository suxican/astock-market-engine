"""盘面级计算指标：涨停总数 / 炸板率 / 连板高度 / 封板强度

这些函数基于 limit_data + quote_data 的原始数据做聚合计算，
不发起新的 akshare 请求。
"""
import pandas as pd

from ._cache import _cache_get, _cache_set
from ._helpers import _try_akshare
from .limit_data import get_limit_up_pool


def get_all_limit_up_today() -> int:
    """获取今日涨停总数"""
    pool = get_limit_up_pool()
    return len(pool) if not pool.empty else -1


def get_zhaban_rate() -> float:
    """计算当日炸板率

    炸板率 = (当日炸板股数含回封 + 真正炸板未回封股数) /
              (涨停股数 + 真正炸板未回封股数)
    """
    pool = get_limit_up_pool()
    if pool.empty:
        return -1.0

    total_sealed = len(pool)
    if total_sealed == 0:
        return 0.0

    try:
        zhaban_in_pool = pool["炸板次数"].apply(
            lambda x: float(x) if str(x).replace(".", "").replace("-", "").isdigit() else 0
        ).gt(0).sum()
    except Exception:
        zhaban_in_pool = 0

    cached = _cache_get("zhaban_pool")
    if cached is None:
        import akshare as ak
        zhaban_only = _try_akshare(ak.stock_zt_pool_zbgc_em, pd.DataFrame())
        _cache_set("zhaban_pool", zhaban_only, ttl=60)
    else:
        zhaban_only = cached
    zhaban_only_count = len(zhaban_only) if zhaban_only is not None and not zhaban_only.empty else 0

    denominator = total_sealed + zhaban_only_count
    if denominator == 0:
        return 0.0
    numerator = int(zhaban_in_pool) + zhaban_only_count
    return round(numerator / denominator, 4)


def get_top_boards(n: int = 10) -> list:
    """获取连板高度排名 Top N"""
    pool = get_limit_up_pool()
    if pool.empty:
        return []
    try:
        df = pool.copy()
        df["连板数"] = pd.to_numeric(df["连板数"], errors="coerce").fillna(0)
        top = df.sort_values("连板数", ascending=False).head(n)
        result = []
        for _, row in top.iterrows():
            result.append({
                "symbol": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "boards": int(float(row.get("连板数", 0))),
                "industry": str(row.get("所属行业", "")),
                "fengdan": round(float(row.get("封板资金", 0)), 2),
                "turnover": round(float(row.get("换手率", 0)), 2),
            })
        return result
    except Exception:
        return []
