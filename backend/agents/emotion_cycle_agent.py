"""情绪周期判断 Agent (V3)

V3 变更: 主逻辑已迁移到 ScoreEngine.compute_emotion_scores()。
本 Agent 保留为薄编排层，接受 MarketFeatures 输入。

向后兼容: 仍支持原始参数调用。
"""
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.score_engine.market_scores import compute_emotion_scores


class EmotionCycleAgent:
    """A股情绪周期六阶段判断器 — V3 薄编排层"""

    def judge(
        self,
        limit_up_count: int = 0,
        limit_down_count: int = 0,
        zhaban_rate: float | None = None,
        high_board_count: int | None = None,
        volume: float | None = None,
        market_features: MarketFeatures | None = None,
    ) -> dict[str, Any]:
        """判断当前情绪周期阶段

        优先使用预计算的 MarketFeatures，否则从原始参数构建。
        """
        if market_features is not None:
            scores = compute_emotion_scores(market_features)
            return {
                "stage": scores.stage,
                "score": scores.score / 100,  # 兼容旧版 0-1 范围
                "signals": scores.signals,
                "suggestion": scores.suggestion,
                "all_scores": scores.all_stage_scores,
                "confidence": scores.confidence,
            }

        # 向后兼容: 从原始参数构建临时 MarketFeatures
        mf = MarketFeatures(
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            zhaban_rate=zhaban_rate if zhaban_rate is not None else 0.0,
            max_board_height=high_board_count if high_board_count is not None else 0,
        )
        scores = compute_emotion_scores(mf)
        return {
            "stage": scores.stage,
            "score": scores.score / 100,
            "signals": scores.signals,
            "suggestion": scores.suggestion,
            "all_scores": scores.all_stage_scores,
            "confidence": scores.confidence,
        }
