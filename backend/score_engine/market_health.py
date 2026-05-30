"""统一市场评分引擎 — V3 核心

收敛路径: FeatureEngine → MarketScoreEngine → AI Explain Layer

MarketScoreEngine 一次性计算所有盘面维度评分，输出结构化结果:
  - EmotionScores       (情绪周期)
  - DragonIntensityScores (龙头强度)
  - RiskScores          (风险等级)
  - EarningEffectScores (赚钱效应)
  - EventScores         (事件面)
  - MarketHealthScore   (综合健康分 0-100)

纯规则计算，不调用 LLM。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.score_engine.market_scores import (
    DragonIntensityScores,
    EmotionScores,
    RiskScores,
    compute_dragon_intensity,
    compute_emotion_scores,
    compute_risk_scores,
)
from backend.earning_effect_engine.earning_effect import (
    EarningEffectScores,
    compute_earning_effect,
)


@dataclass
class EventScores:
    """事件面评分（从 EventEngine V2 结果中提取）"""
    event_score: int = 0
    sentiment_score: int = 50
    policy_score: int = 50
    signals: list[str] = field(default_factory=list)


@dataclass
class MarketHealthScore:
    """市场综合健康分 — 所有维度的统一视图

    composite: 0-100 综合分
      80+ : 市场极强，赚钱效应显著，可积极做多
      60-80: 市场偏强，跟随主线参与
      40-60: 市场中性，控制仓位
      20-40: 市场偏弱，谨慎参与
      0-20: 市场极弱，空仓观望
    """
    composite: int = 0
    level: str = ""       # 极强/偏强/中性/偏弱/极弱
    confidence: str = ""  # 高/中/低

    # ── 分维度评分 ──
    emotion: EmotionScores = field(default_factory=EmotionScores)
    dragon_intensity: DragonIntensityScores = field(default_factory=DragonIntensityScores)
    risk: RiskScores = field(default_factory=RiskScores)
    earning_effect: EarningEffectScores = field(default_factory=EarningEffectScores)
    event: EventScores = field(default_factory=EventScores)

    # ── 维度权重（动态调整） ──
    weights: dict[str, float] = field(default_factory=dict)

    # ── AI Explain 输入 ──
    explain_summary: str = ""
    signals: list[str] = field(default_factory=list)

    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite": self.composite,
            "level": self.level,
            "confidence": self.confidence,
            "emotion": self.emotion.to_dict() if hasattr(self.emotion, "to_dict") else {},
            "dragon_intensity": {
                "score": self.dragon_intensity.score,
                "top_leader_score": self.dragon_intensity.top_leader_score,
                "high_board_count": self.dragon_intensity.high_board_count,
            },
            "risk": {
                "score": self.risk.score,
                "level": self.risk.level,
                "factors": self.risk.factors,
            },
            "earning_effect": self.earning_effect.to_dict(),
            "event": {
                "event_score": self.event.event_score,
                "sentiment_score": self.event.sentiment_score,
                "policy_score": self.event.policy_score,
            },
            "weights": self.weights,
            "explain_summary": self.explain_summary,
            "signals": self.signals[:10],
            "computed_at": self.computed_at,
        }


# ── 默认权重 ──
_DEFAULT_WEIGHTS = {
    "emotion": 0.30,
    "dragon": 0.15,
    "risk_inv": 0.15,
    "earning": 0.25,
    "event": 0.15,
}


def compute_market_health(
    mf: MarketFeatures,
    include_event: bool = False,
    event_result: Any = None,
) -> MarketHealthScore:
    """一次性计算所有盘面维度评分

    Args:
        mf: 盘面特征快照
        include_event: 是否包含事件面评分（事件引擎调用较慢，可选）
        event_result: EventEngineV2Result（可选，传入避免重复调用）
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 各维度评分 ──
    emotion = compute_emotion_scores(mf)
    dragon = compute_dragon_intensity(mf)
    risk = compute_risk_scores(mf, emotion.stage)
    earning = compute_earning_effect(mf)

    # ── 事件面 (可选) ──
    event_scores = EventScores()
    if include_event and event_result is not None:
        event_scores = EventScores(
            event_score=getattr(event_result, "event_score", 0),
            sentiment_score=getattr(event_result, "sentiment_score", 50),
            policy_score=getattr(event_result, "policy_score", 50),
            signals=getattr(event_result, "signals", []),
        )

    # ── 动态权重调整 ──
    weights = dict(_DEFAULT_WEIGHTS)

    # 风险极高时，提高风险权重
    if risk.score >= 80:
        weights["risk_inv"] = 0.25
        weights["emotion"] = 0.20

    # 赚钱效应极强/极弱时，提高权重
    if earning.composite >= 80 or earning.composite <= 20:
        weights["earning"] = 0.30
        weights["emotion"] = 0.25

    # 归一化权重
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: round(v / total_w, 3) for k, v in weights.items()}

    # ── 加权综合分 ──
    risk_inv_score = max(0, 100 - risk.score)  # 风险取反

    dimensions = {
        "emotion": emotion.score,
        "dragon": dragon.score,
        "risk_inv": risk_inv_score,
        "earning": earning.composite,
        "event": event_scores.event_score if include_event else 50,
    }

    composite = 0.0
    for dim, score in dimensions.items():
        composite += score * weights.get(dim, 0)
    composite = max(0, min(100, int(composite)))

    # ── 等级 ──
    if composite >= 80:
        level = "极强"
    elif composite >= 60:
        level = "偏强"
    elif composite >= 40:
        level = "中性"
    elif composite >= 20:
        level = "偏弱"
    else:
        level = "极弱"

    # ── 置信度 ──
    # 所有子维度的信号一致性越高，置信度越高
    sub_scores = [emotion.score, dragon.score, risk_inv_score, earning.composite]
    score_std = _std(sub_scores)
    if score_std < 15:
        confidence = "高"
    elif score_std < 30:
        confidence = "中"
    else:
        confidence = "低"

    # ── 汇总信号 ──
    signals = []
    signals.extend(emotion.signals[:3])
    signals.extend(earning.signals[:3])
    if risk.factors:
        signals.extend(risk.factors[:2])
    if include_event and event_scores.signals:
        signals.extend(event_scores.signals[:2])

    # ── AI Explain 摘要 ──
    explain_summary = _build_explain_summary(
        composite, level, emotion, earning, risk, dragon
    )

    return MarketHealthScore(
        composite=composite,
        level=level,
        confidence=confidence,
        emotion=emotion,
        dragon_intensity=dragon,
        risk=risk,
        earning_effect=earning,
        event=event_scores,
        weights=weights,
        explain_summary=explain_summary,
        signals=signals,
        computed_at=now,
    )


def _std(values: list[float]) -> float:
    """标准差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def _build_explain_summary(
    composite: int,
    level: str,
    emotion: EmotionScores,
    earning: EarningEffectScores,
    risk: RiskScores,
    dragon: DragonIntensityScores,
) -> str:
    """构建 AI Explain Layer 的输入摘要"""
    parts = []
    parts.append(f"市场综合健康分 {composite} 分（{level}）。")
    parts.append(f"情绪周期处于 {emotion.stage}（{emotion.score}分），{emotion.suggestion}")
    parts.append(f"赚钱效应 {earning.level}（{earning.composite}分），{earning.suggestion}")
    parts.append(f"风险等级 {risk.level}（{risk.score}分）。")
    if dragon.high_board_count > 0:
        parts.append(f"龙头强度 {dragon.score} 分，{dragon.high_board_count} 只连板≥5的高标股。")
    return " ".join(parts)

