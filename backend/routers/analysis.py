"""AI 分析路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services import (
    get_stock_daily, get_stock_fund_flow, get_stock_name,
    get_realtime_quote, pop_mock_used,
)
from backend.services.analysis_service import analyze_stock, _local_rule_analysis
from limit_up_analysis import LimitUpAgent
from limit_down_analysis import LimitDownAgent
from market_reasoning_engine import ExpectationGapAgent
from review_engine import MarketReviewAgent
from dragon_leader_engine import DragonLeaderAgent
from sector_rotation_engine import SectorRotationAgent
from backend.services.db_service import get_review_history, get_snapshot_by_date
from backend.schemas import (
    MarketScoresResponse,
    StockScoresResponse,
    StockScoresQuery as StockScoresQuerySchema,
)

router = APIRouter(prefix="/api/analysis", tags=["AI分析"])


class AnalysisQuery(BaseModel):
    symbol: str
    analysis_type: str = "comprehensive"  # comprehensive / main_capital / emotion


@router.get("/kline/{symbol}")
def kline_data(symbol: str, period: str = "3m"):
    """返回个股日K线数据（供前端 KLineChart 使用）"""
    period_days = {"5d": 5, "1m": 30, "3m": 90, "1y": 250}
    days = period_days.get(period, 90)

    df = get_stock_daily(symbol)
    if df.empty:
        raise HTTPException(404, f"未找到股票 {symbol} 的数据")

    recent = df.tail(days)
    return {"data": recent.to_dict(orient="records"), "symbol": symbol}


@router.post("/stock")
def stock_analysis(query: AnalysisQuery):
    """对个股进行AI综合分析（V8: 附加结构化评分）"""
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

    # V8: 附加结构化评分
    try:
        from backend.feature_engine import StockFeatures
        from backend.score_engine import compute_stock_scores
        sf = StockFeatures.compute(symbol)
        scores = compute_stock_scores(sf)
        structured_scores = scores.to_dict()
    except Exception:
        structured_scores = None

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

    is_mock = pop_mock_used()

    return {
        "summary": summary,
        "analysis": result,
        "structured_scores": structured_scores,
        "data_points": len(recent),
        "kline_data": recent.to_dict(orient="records"),
        "is_mock_data": is_mock,
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

    is_mock = pop_mock_used()

    return {
        "summary": summary,
        "symbol": symbol,
        "name": stock_name,
        "analysis": result,
        "data_points": len(recent),
        "kline_data": recent.to_dict(orient="records"),
        "is_mock_data": is_mock,
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
    """市场复盘：情绪周期 + 结构化评分 + AI复盘"""
    try:
        from backend.feature_engine import MarketFeatures
        from backend.score_engine import compute_market_scores

        # V8: 一次拉取 + 结构化评分，消除 N+1
        mf = MarketFeatures.compute()
        scores = compute_market_scores(mf)

        # AI 复盘
        review_agent = MarketReviewAgent()
        review = review_agent.generate_review()

        return {
            "market_scores": scores.to_dict(),
            "limit_up_count": mf.limit_up_count,
            "limit_down_count": mf.limit_down_count,
            "zhaban_rate": mf.zhaban_rate,
            "top_boards": mf.top_boards,
            "ai_review": review.get("ai_review", ""),
            "sector_rotation": review.get("sector", {}),
            "similar_days": review.get("similar_days", []),
            "rag_enabled": review.get("rag_enabled", False),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/emotion-cycle")
def emotion_cycle():
    """判断当前市场情绪周期阶段（V8: 走 score_engine）"""
    try:
        from backend.feature_engine import MarketFeatures
        from backend.score_engine import compute_emotion_scores

        mf = MarketFeatures.compute()
        emotion = compute_emotion_scores(mf)

        return {
            "emotion_score": emotion.score,
            "emotion_stage": emotion.stage,
            "confidence": emotion.confidence,
            "all_stage_scores": emotion.all_stage_scores,
            "signals": emotion.signals,
            "suggestion": emotion.suggestion,
            "涨停数": mf.limit_up_count if mf.limit_up_count >= 0 else "未知",
            "炸板率": f"{mf.zhaban_rate:.1%}" if mf.zhaban_rate >= 0 else "未知",
            "连板高度": mf.max_board_height,
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


# ===== V8 结构化评分端点 =====


@router.get("/market-scores", response_model=MarketScoresResponse)
def market_scores():
    """返回结构化市场评分（0-100分数）

    所有评分由规则引擎计算，不依赖 LLM。
    前端可直接基于分数做可视化/仪表盘。
    """
    from backend.feature_engine import MarketFeatures
    from backend.score_engine import compute_market_scores

    mf = MarketFeatures.compute()
    scores = compute_market_scores(mf)
    return scores.to_dict()


@router.post("/stock-scores", response_model=StockScoresResponse)
def stock_scores(query: StockScoresQuerySchema):
    """返回结构化个股评分（0-100分数）

    包含主力行为分析、技术面、综合评分。
    不依赖 LLM，纯规则计算。
    """
    from backend.feature_engine import StockFeatures
    from backend.score_engine import compute_stock_scores

    symbol = query.symbol.strip()
    sf = StockFeatures.compute(symbol)
    scores = compute_stock_scores(sf)
    return scores.to_dict()


# ===== V8 事件驱动引擎 =====


@router.get("/events/timeline")
def events_timeline():
    """今日事件时间线（回答"为什么今天这个板块突然爆"）

    按时间排列的政策/行业/财报事件，标注重要性和影响标的。
    """
    from backend.event_engine.timeline import build_today_timeline

    entries = build_today_timeline()
    return {
        "count": len(entries),
        "events": [
            {
                "time": e.time,
                "title": e.title,
                "type": e.event_type,
                "importance": e.importance,
                "affected": e.affected_markets,
            }
            for e in entries
        ],
    }


@router.get("/events/drivers")
def events_drivers():
    """今日市场驱动因素（高/中重要性事件聚合）"""
    from backend.event_engine.timeline import get_market_drivers

    drivers = get_market_drivers()
    return {"drivers": drivers}


@router.get("/events/trending")
def events_trending():
    """今日热词/热门话题 + 趋势 + 关联个股"""
    from backend.event_engine.hot_tracker import get_trending_topics

    topics = get_trending_topics()
    return {
        "topics": [
            {
                "keyword": t.keyword,
                "count": t.count,
                "trend": t.trend,
                "related_sectors": t.related_sectors,
                "related_stocks": t.related_stocks,
            }
            for t in topics
        ],
    }


@router.get("/events/linked-stocks")
def events_linked_stocks():
    """今日事件→个股联动（哪些股票受今日事件影响）"""
    from backend.event_engine.stock_linker import get_today_linked_stocks

    linked = get_today_linked_stocks()
    return {
        "stock_events": {
            symbol: events
            for symbol, events in sorted(linked.items(), key=lambda x: len(x[1]), reverse=True)[:30]
        },
    }


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


# ===== Phase 2: 工作台数据端点 =====


@router.get("/sector-stats")
def sector_stats():
    """板块维度统计（供炸板热力图/板块轮动使用）"""
    try:
        from backend.services import get_limit_up_pool

        up_pool = get_limit_up_pool()
        if up_pool.empty:
            return {"sectors": []}

        sectors = {}
        for _, row in up_pool.iterrows():
            industry = str(row.get("industry", "其他") or "其他")
            if industry not in sectors:
                sectors[industry] = {"up": 0, "zhaban": 0, "total_boards": 0, "stock_count": 0}
            sec = sectors[industry]
            sec["stock_count"] += 1
            status = str(row.get("status", ""))
            if "炸" in status:
                sec["zhaban"] += 1
            else:
                sec["up"] += 1
            sec["total_boards"] += int(row.get("boards", 0) or 0)

        result = []
        for name, s in sorted(sectors.items(), key=lambda x: x[1]["stock_count"], reverse=True):
            total = s["up"] + s["zhaban"]
            result.append({
                "sector": name,
                "limit_up": s["up"],
                "zhaban": s["zhaban"],
                "total": total,
                "zhaban_rate": round(s["zhaban"] / total, 3) if total > 0 else 0,
                "avg_boards": round(s["total_boards"] / total, 1) if total > 0 else 0,
            })

        return {"sectors": result[:20]}
    except Exception as e:
        return {"sectors": [], "error": str(e)}


# ===== Phase 3: 回测引擎 =====


@router.post("/backtest")
def run_backtest_endpoint(
    symbol: str,
    strategy: str = "ma_cross",
    initial_capital: float = 100000,
):
    """对个股执行策略回测

    支持策略: ma_cross / volume_breakout / dragon_follow
    返回: 收益曲线、交易记录、绩效指标
    """
    from backend.backtest import run_backtest, STRATEGIES

    if strategy not in STRATEGIES:
        raise HTTPException(400, f"未知策略: {strategy}，支持: {list(STRATEGIES.keys())}")

    df = get_stock_daily(symbol)
    if df.empty:
        raise HTTPException(404, f"未找到股票 {symbol} 的数据")

    result = run_backtest(df, symbol, strategy_name=strategy, initial_capital=initial_capital)
    return {
        "symbol": result.symbol,
        "strategy": result.strategy,
        "period": f"{result.start_date} ~ {result.end_date}",
        "metrics": {
            "total_trades": result.total_trades,
            "win_count": result.win_count,
            "lose_count": result.lose_count,
            "win_rate": result.win_rate,
            "total_return": result.total_return,
            "annual_return": result.annual_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "avg_pnl": result.avg_pnl,
            "avg_hold_days": result.avg_hold_days,
        },
        "trades": result.trades,
        "equity_curve": result.equity_curve,
    }


@router.get("/backtest/strategies")
def list_strategies():
    """返回可用策略列表"""
    from backend.backtest import STRATEGIES
    return {
        "strategies": [
            {"key": k, "name": v["name"], "desc": v["desc"], "default_params": v["params"]}
            for k, v in STRATEGIES.items()
        ],
    }


# ===== Phase 3: 策略市场 =====


@router.get("/strategy-market")
def strategy_market(sort_by: str = "sharpe"):
    """策略市场 — 对所有内置策略 × 所有热门股票执行回测排名

    sort_by: sharpe / return / win_rate
    """
    from backend.backtest import run_backtest, STRATEGIES

    symbols = ["000001", "600519", "000858", "300750", "002594", "601318",
               "000333", "600036", "601166", "002415"]

    results = []
    for sym in symbols:
        try:
            df = get_stock_daily(sym)
            if df.empty or len(df) < 60:
                continue
        except Exception:
            continue

        for skey, sval in STRATEGIES.items():
            try:
                r = run_backtest(df, sym, strategy_name=skey)
                if r.total_trades > 0:
                    results.append({
                        "symbol": sym,
                        "name": get_stock_name(sym),
                        "strategy": sval["name"],
                        "strategy_key": skey,
                        "total_return": r.total_return,
                        "sharpe_ratio": r.sharpe_ratio,
                        "win_rate": r.win_rate,
                        "max_drawdown": r.max_drawdown,
                        "total_trades": r.total_trades,
                    })
            except Exception:
                pass

    sort_key = {"sharpe": "sharpe_ratio", "return": "total_return", "win_rate": "win_rate"}.get(sort_by, "sharpe_ratio")
    results.sort(key=lambda x: x[sort_key], reverse=True)

    return {"rankings": results[:30], "sort_by": sort_by, "updated": __import__("datetime").datetime.now().isoformat()}
