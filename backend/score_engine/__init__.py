"""评分引擎 — 结构化规则评分层

V2: MarketScores / StockScores (情绪/龙头/风险/主力/技术面)
V3: + EarningEffectScores (赚钱效应) + MarketHealthScore (综合健康分)

纯规则计算，不调用 LLM。输出 0-100 结构化分数供前端可视化和 LLM 翻译。

注意: market_health 和 earning_effect_engine 存在交叉引用，
     这里使用延迟导入避免循环依赖。
"""
from .market_scores import (
    DragonIntensityScores,
    EmotionScores,
    MarketScores,
    RiskScores,
    compute_dragon_intensity,
    compute_emotion_scores,
    compute_market_scores,
    compute_risk_scores,
)
from .stock_scores import (
    MainCapitalScores,
    StockScores,
    TechnicalScores,
    compute_capital_scores,
    compute_stock_scores,
    compute_technical_scores,
)

# 延迟导入 market_health 以避免与 earning_effect_engine 的循环依赖
def __getattr__(name: str):
    if name in ("MarketHealthScore", "EventScores", "compute_market_health"):
        from .market_health import MarketHealthScore, EventScores, compute_market_health
        return {"MarketHealthScore": MarketHealthScore, "EventScores": EventScores, "compute_market_health": compute_market_health}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MarketScores", "EmotionScores", "DragonIntensityScores", "RiskScores",
    "compute_market_scores", "compute_emotion_scores",
    "compute_dragon_intensity", "compute_risk_scores",
    "MarketHealthScore", "EventScores", "compute_market_health",
    "StockScores", "MainCapitalScores", "TechnicalScores",
    "compute_stock_scores", "compute_capital_scores", "compute_technical_scores",
]

# 主线识别
from .theme_scores import ThemeScore, ThemeScoresResult, compute_theme_scores
