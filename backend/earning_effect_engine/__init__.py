"""赚钱效应引擎 — 量化市场的赚钱/亏钱效应

EarningEffectEngine 不是新的 Agent，而是 ScoreEngine 的扩展模块。
输出结构化的 0-100 赚钱效应分数，供前端仪表盘和 AI Explain Layer 使用。

核心指标:
  1. 涨停次日溢价率 — 昨日涨停股今日平均涨幅
  2. 连板股赚钱效应 — 连板股存活率和平均溢价
  3. 龙头溢价效应   — 高度龙头次日表现
  4. 跌停亏钱效应   — 跌停股的连锁反应
  5. 炸板回封率     — 炸板后回封的比率
  6. 综合赚钱效应分 — 加权汇总 0-100
"""
from .earning_effect import (
    EarningEffectScores,
    compute_earning_effect,
)

__all__ = ["EarningEffectScores", "compute_earning_effect"]
