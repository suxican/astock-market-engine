"""评分引擎 — 结构化规则评分层

MarketScores:  盘面评分（情绪/龙头/风险）
StockScores:   个股评分（主力/技术面/综合）

纯规则计算，不调用 LLM。输出 0-100 结构化分数供前端可视化和 LLM 翻译。
"""
from .market_scores import (
    MarketScores,
    EmotionScores,
    DragonIntensityScores,
    RiskScores,
    compute_market_scores,
    compute_emotion_scores,
    compute_dragon_intensity,
    compute_risk_scores,
)
from .stock_scores import (
    StockScores,
    MainCapitalScores,
    TechnicalScores,
    compute_stock_scores,
    compute_capital_scores,
    compute_technical_scores,
)

__all__ = [
    "MarketScores", "EmotionScores", "DragonIntensityScores", "RiskScores",
    "compute_market_scores", "compute_emotion_scores",
    "compute_dragon_intensity", "compute_risk_scores",
    "StockScores", "MainCapitalScores", "TechnicalScores",
    "compute_stock_scores", "compute_capital_scores", "compute_technical_scores",
]
