"""股票数据路由"""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import (
    classify_system_status,
    get_all_limit_up_today,
    get_lhb_detail,
    get_limit_down_pool,
    get_limit_up_pool,
    get_market_overview,
    get_realtime_quote,
    get_sector_fund_flow,
    get_stock_daily,
    get_stock_fund_flow,
    get_stock_name,
    get_ths_hotspot,
)

router = APIRouter(prefix="/api/stock", tags=["股票数据"])


import re

_STOCK_CODE_RE = re.compile(r"^\d{6}$")

def _validate_symbol(symbol: str) -> str:
    """校验股票代码格式"""
    symbol = symbol.strip()
    if not _STOCK_CODE_RE.match(symbol):
        from fastapi import HTTPException
        raise HTTPException(400, f"股票代码格式错误: {symbol}，应为6位数字")
    return symbol


class StockQuery(BaseModel):
    symbol: str


@router.post("/daily")
def stock_daily(query: StockQuery):
    """获取个股日K数据"""
    symbol = _validate_symbol(query.symbol)
    df = get_stock_daily(symbol)
    if df.empty:
        raise HTTPException(404, f"未找到股票 {query.symbol} 的数据")
    return {
        "symbol": query.symbol,
        "name": get_stock_name(query.symbol),
        "records": df.tail(120).to_dict(orient="records")
    }


@router.post("/realtime")
def stock_realtime(query: StockQuery):
    """获取个股实时行情"""
    symbol = _validate_symbol(query.symbol)
    data = get_realtime_quote(symbol)
    if not data:
        raise HTTPException(404, f"未找到股票 {query.symbol}")
    return {"symbol": query.symbol, **data}


@router.post("/fund-flow")
def stock_fund_flow(query: StockQuery):
    """获取个股资金流向"""
    symbol = _validate_symbol(query.symbol)
    data = get_stock_fund_flow(symbol)
    return {"symbol": query.symbol, "fund_flow": data}


@router.get("/market-overview")
def market_overview():
    """获取大盘概况"""
    return get_market_overview()


@router.get("/limit-up-pool")
def limit_up_pool():
    """获取今日涨停池"""
    df = get_limit_up_pool()
    if df.empty:
        return {"count": 0, "stocks": []}
    return {"count": len(df), "stocks": df.head(50).to_dict(orient="records")}


@router.get("/limit-down-pool")
def limit_down_pool():
    """获取今日跌停池"""
    df = get_limit_down_pool()
    if df.empty:
        return {"count": 0, "stocks": []}
    return {"count": len(df), "stocks": df.head(50).to_dict(orient="records")}


@router.get("/sector-flow")
def sector_fund_flow():
    """获取板块资金流向"""
    df = get_sector_fund_flow()
    if df.empty:
        return {"sectors": []}
    return {"sectors": df.head(20).to_dict(orient="records")}


@router.get("/hotspot")
def ths_hotspot():
    """获取同花顺热点/强势股"""
    df = get_ths_hotspot()
    quality = df.attrs.get("_quality") if hasattr(df, "attrs") else None
    if df.empty:
        return {
            "count": 0,
            "items": [],
            "_quality": quality.to_dict() if quality else None,
        }
    return {
        "count": len(df),
        "items": df.head(50).to_dict(orient="records"),
        "_quality": quality.to_dict() if quality else None,
    }


@router.get("/lhb/{date}")
def lhb_detail(date: str):
    """获取龙虎榜"""
    df = get_lhb_detail(date)
    if df.empty:
        return {"items": []}
    return {"items": df.head(30).to_dict(orient="records")}


@router.get("/limit-up-count")
def limit_up_count():
    """获取今日涨停总数"""
    count = get_all_limit_up_today()
    return {"count": count}


@router.get("/system/status")
def system_status():
    """查询系统整体数据健康状态 (realtime/cache/stale/mock)"""

    daily = get_stock_daily("600519")
    dq = daily.attrs.get("_quality")

    quote = get_realtime_quote("600519")
    qd = quote.get("_quality", {})

    sources = []
    if dq:
        sources.append({"name": "stock_daily", **dq.to_dict()})
    if qd:
        sources.append({"name": "realtime_quote", **qd})

    status = classify_system_status(dq)

    # V3: 缓存统计
    from backend.services._cache import get_cache_stats
    cache = get_cache_stats()

    return {
        "status": status,
        "sources": sources,
        "cache": cache,
        "updated_at": datetime.now().isoformat(),
    }



# ===== V3: 数据质量仪表盘 =====


@router.get("/quality/dashboard")
def quality_dashboard():
    """数据质量仪表盘 — 全链路数据质量监控"""
    from backend.services.quality_monitor import get_quality_monitor

    monitor = get_quality_monitor()
    dashboard = monitor.get_dashboard()
    return dashboard.to_dict()


@router.get("/quality/sources")
def quality_sources():
    """各数据源健康状态"""
    from backend.services.quality_monitor import get_quality_monitor

    monitor = get_quality_monitor()
    health_map = monitor.get_source_health_map()
    return {
        "sources": {k: v.to_dict() for k, v in health_map.items()},
        "count": len(health_map),
    }

