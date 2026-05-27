"""AI 分析路由"""
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services import (
    get_stock_daily, get_stock_fund_flow, get_stock_name,
    get_realtime_quote, get_all_limit_up_today,
    get_zhaban_rate, get_top_boards,
    get_limit_up_pool, get_limit_down_pool,
)
from backend.services.analysis_service import analyze_stock, _local_rule_analysis
from limit_up_analysis import LimitUpAgent
from limit_down_analysis import LimitDownAgent
from market_reasoning_engine import ExpectationGapAgent
from review_engine import MarketReviewAgent
from backend.agents.emotion_cycle_agent import EmotionCycleAgent
from dragon_leader_engine import DragonLeaderAgent
from sector_rotation_engine import SectorRotationAgent
from backend.services.db_service import get_review_history, get_snapshot_by_date

router = APIRouter(prefix="/api/analysis", tags=["AI分析"])


class AnalysisQuery(BaseModel):
    symbol: str
    analysis_type: str = "comprehensive"  # comprehensive / main_capital / emotion


@router.post("/stock")
def stock_analysis(query: AnalysisQuery):
    """对个股进行AI综合分析"""
    symbol = query.symbol.strip()

    # 获取数据
    df = get_stock_daily(symbol)
    if df.empty:
        raise HTTPException(404, f"未找到股票 {symbol} 的数据")

    stock_name = get_stock_name(symbol)
    quote = get_realtime_quote(symbol)
    fund_flow = get_stock_fund_flow(symbol)

    # 行情数据文本化（最近60天）
    recent = df.tail(60)
    market_text = recent.to_csv(sep="\t", index=False)

    # 资金流向文本化
    flow_text = str(fund_flow) if fund_flow else "暂无资金流向数据"

    # AI分析
    result = analyze_stock(
        stock_name=stock_name,
        symbol=symbol,
        market_data=market_text,
        fund_flow_data=flow_text,
        analysis_type=query.analysis_type,
    )

    # 基础数据摘要
    latest = df.iloc[-1]
    summary = {
        "symbol": symbol,
        "name": stock_name,
        "close": float(latest["close"]),
        "pct_change": float(latest["pct_change"]),
        "volume": float(latest["volume"]),
        "turnover": float(latest["turnover"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
    }
    if quote:
        summary.update({
            "market_cap": quote.get("总市值", 0),
            "pe": quote.get("PE", 0),
        })

    return {
        "summary": summary,
        "analysis": result,
        "data_points": len(recent),
        "kline_data": recent.to_dict(orient="records"),
    }


@router.post("/local-analysis")
def local_analysis(query: AnalysisQuery):
    """本地规则引擎分析（不依赖 AI API）

    返回结构与 /stock 接口对齐（summary + analysis + kline_data），
    前端组件共用同一份渲染逻辑。
    """
    symbol = query.symbol.strip()
    df = get_stock_daily(symbol)
    if df.empty:
        raise HTTPException(404, f"未找到股票 {symbol} 的数据")

    stock_name = get_stock_name(symbol)
    fund_flow = get_stock_fund_flow(symbol)
    quote = get_realtime_quote(symbol)

    recent = df.tail(60)
    market_text = recent.to_csv(sep="\t", index=False)
    flow_text = str(fund_flow) if fund_flow else ""

    result = _local_rule_analysis(stock_name, market_text, flow_text, query.analysis_type)

    latest = df.iloc[-1]
    summary = {
        "symbol": symbol,
        "name": stock_name,
        "close": float(latest["close"]),
        "pct_change": float(latest["pct_change"]),
        "volume": float(latest["volume"]),
        "turnover": float(latest["turnover"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
    }
    if quote:
        summary["market_cap"] = quote.get("总市值", 0)
        summary["pe"] = quote.get("PE", 0)

    return {
        "summary": summary,
        "symbol": symbol,
        "name": stock_name,
        "analysis": result,
        "data_points": len(recent),
        "kline_data": recent.to_dict(orient="records"),
    }


@router.post("/limit-up")
def limit_up_analysis(query: AnalysisQuery):
    """个股涨停原因分析"""
    symbol = query.symbol.strip()
    agent = LimitUpAgent()
    result = agent.analyze(symbol)
    return {
        "symbol": symbol,
        "name": get_stock_name(symbol),
        "analysis": result,
    }


@router.post("/limit-down")
def limit_down_analysis(query: AnalysisQuery):
    """个股跌停原因分析"""
    symbol = query.symbol.strip()
    agent = LimitDownAgent()
    result = agent.analyze(symbol)
    return {
        "symbol": symbol,
        "name": get_stock_name(symbol),
        "analysis": result,
    }


@router.post("/expectation-gap")
def expectation_gap(query: AnalysisQuery):
    """个股预期差分析 — 利好不涨/利空不跌等反常现象"""
    symbol = query.symbol.strip()
    agent = ExpectationGapAgent()
    result = agent.analyze(symbol)
    return {
        "symbol": symbol,
        "name": get_stock_name(symbol),
        "analysis": result,
    }


@router.post("/dragon-leaders")
@router.get("/dragon-leaders")
def dragon_leaders():
    """全市场龙头股识别（GET/POST 均支持，便于前端 fetch 复用）"""
    agent = DragonLeaderAgent()
    result = agent.analyze()
    return result


@router.get("/sector-rotation")
def sector_rotation():
    """板块轮动分析"""
    agent = SectorRotationAgent()
    result = agent.analyze()
    return result


@router.get("/market-review")
def market_review():
    """市场复盘：情绪周期 + 涨停/跌停统计 + 连板排名 + AI复盘"""
    try:
        limit_up_count = get_all_limit_up_today()
        zhaban_rate = get_zhaban_rate()
        top_boards = get_top_boards(10)
        pool_down = get_limit_down_pool()
        limit_down_count = len(pool_down) if not pool_down.empty else 0

        # 情绪周期判断
        emotion_agent = EmotionCycleAgent()
        emotion = emotion_agent.judge(
            limit_up_count=limit_up_count if limit_up_count >= 0 else 0,
            limit_down_count=limit_down_count,
            zhaban_rate=zhaban_rate if zhaban_rate >= 0 else None,
            high_board_count=top_boards[0]["boards"] if top_boards else None,
        )

        # AI 复盘
        review_agent = MarketReviewAgent()
        review = review_agent.generate_review()

        return {
            "emotion": emotion,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "zhaban_rate": zhaban_rate,
            "top_boards": top_boards,
            "ai_review": review.get("ai_review", ""),
            "sector_rotation": review.get("sector", {}),
            "similar_days": review.get("similar_days", []),
            "rag_enabled": review.get("rag_enabled", False),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/emotion-cycle")
def emotion_cycle():
    """判断当前市场情绪周期阶段"""
    try:
        limit_up_count = get_all_limit_up_today()
        zhaban_rate = get_zhaban_rate()
        top_boards = get_top_boards(1)

        emotion_agent = EmotionCycleAgent()
        emotion = emotion_agent.judge(
            limit_up_count=limit_up_count if limit_up_count >= 0 else 0,
            zhaban_rate=zhaban_rate if zhaban_rate >= 0 else None,
            high_board_count=top_boards[0]["boards"] if top_boards else None,
        )

        return {
            "涨停数": limit_up_count if limit_up_count >= 0 else "未知",
            "炸板率": zhaban_rate if zhaban_rate >= 0 else "未知",
            "情绪周期": emotion["stage"],
            "分析": emotion["description"],
            "建议": emotion["suggestion"],
        }
    except Exception as e:
        return {"error": str(e)}


def _get_emotion_cycle_text(count: int) -> str:
    if count < 0:
        return "数据获取失败，无法判断情绪周期。"
    if count < 10:
        return "❄️ **冰点期** — 涨停不足10只，市场情绪极度低迷。左侧布局机会，小仓试探。"
    elif count < 20:
        return "🌱 **修复期** — 涨停10-20只，情绪开始回暖。逐步加仓，跟随龙头。"
    elif count < 30:
        return "📈 **修复至主升过渡期** — 涨停20只左右，情绪明显回暖。"
    elif count < 50:
        return "🚀 **主升期** — 涨停20-50只，主线明确。重仓跟随主线，快进快出。"
    elif count < 70:
        return "🔥 **高潮期** — 涨停超过50只，情绪亢奋。减仓警惕，见好就收。"
    else:
        return "⚡ **极度高潮期** — 涨停超过70只，市场过热。注意风险控制。"


# ===== V7 RAG 端点 =====

@router.get("/rag/history")
def rag_history(limit: int = 30):
    """获取历史复盘记录"""
    try:
        records = get_review_history(limit=limit)
        return {"records": records, "total": len(records)}
    except Exception as e:
        return {"records": [], "total": 0, "error": str(e)}


@router.get("/rag/similar")
def rag_similar(date: str = ""):
    """获取指定日期的相似行情"""
    if not date:
        return {"similar_days": [], "error": "date parameter required"}
    try:
        snapshot = get_snapshot_by_date(date)
        if not snapshot:
            return {"similar_days": [], "error": f"No data for {date}"}

        from rag.retriever import retrieve_similar_market_days
        similar = retrieve_similar_market_days(snapshot, exclude_date=date)
        return {"date": date, "similar_days": similar}
    except Exception as e:
        return {"similar_days": [], "error": str(e)}


@router.get("/rag/similar-today")
def rag_similar_today():
    """获取与今日市场行情相似的历史交易日"""
    try:
        from backend.services import get_all_limit_up_today, get_zhaban_rate, get_top_boards, get_market_overview, get_limit_down_pool

        overview = get_market_overview()
        limit_up_count = get_all_limit_up_today()
        zhaban_rate = get_zhaban_rate()
        top_boards = get_top_boards(1)
        pool_down = get_limit_down_pool()
        limit_down_count = len(pool_down) if not pool_down.empty else 0

        market_data = {
            "limit_up_count": limit_up_count if limit_up_count >= 0 else 0,
            "limit_down_count": limit_down_count,
            "zhaban_rate": zhaban_rate if zhaban_rate >= 0 else 0,
            "board_height": top_boards[0]["boards"] if top_boards else 0,
            "index_change": overview.get("涨跌幅", 0) if overview else 0,
            "up_down_ratio": limit_up_count / max(limit_down_count, 1) if limit_down_count > 0 else 0,
        }

        from rag.retriever import retrieve_similar_market_days
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        similar = retrieve_similar_market_days(market_data, exclude_date=today)
        return {"today": today, "similar_days": similar}
    except Exception as e:
        return {"similar_days": [], "error": str(e)}
