"""V4 统一市场决策 — Feature → Rule → Evidence → GuardRail → AI Explain

这是 V4 架构的核心端点:
  1. Feature Engine 计算特征
  2. Rule Engine 做硬规则决策（不调 LLM）
  3. Evidence Engine 收集证据
  4. GuardRail 验证输出
  5. AI Explain Layer 只负责解释（可选）

输出:
  - 每个结论带证据
  - 证据不足 → INSUFFICIENT_EVIDENCE
  - 置信度 < 0.7 → INSUFFICIENT_EVIDENCE
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.core.system_boundary import check_all_boundaries
from backend.evidence_engine.evidence import EvidenceBundle
from backend.feature_engine.market_features import MarketFeatures
from backend.guardrails.guardrail import GuardRailResult, run_guardrail
from backend.rule_engine.rules import (
    RuleDecision,
    decide_dragon,
    decide_earning,
    decide_emotion,
)
from backend.score_engine.market_scores import (
    compute_dragon_intensity,
    compute_emotion_scores,
    compute_risk_scores,
)
from backend.earning_effect_engine import compute_earning_effect


@dataclass
class MarketDecision:
    """市场决策汇总"""
    timestamp: str = ""

    # 各维度决策
    emotion: RuleDecision | None = None
    dragon: RuleDecision | None = None
    earning: RuleDecision | None = None

    # 综合决策
    composite_conclusion: str = ""
    composite_confidence: float = 0.0
    composite_action: str = ""

    # 边界检查
    boundary_passed: bool = True
    boundary_violations: list[dict] = field(default_factory=list)

    # GuardRail 结果
    guardrail_passed: bool = True

    # 数据质量
    data_quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "emotion": self.emotion.to_dict() if self.emotion else None,
            "dragon": self.dragon.to_dict() if self.dragon else None,
            "earning": self.earning.to_dict() if self.earning else None,
            "composite": {
                "conclusion": self.composite_conclusion,
                "confidence": self.composite_confidence,
                "action": self.composite_action,
            },
            "boundary": {
                "passed": self.boundary_passed,
                "violations": self.boundary_violations,
            },
            "guardrail_passed": self.guardrail_passed,
            "data_quality": self.data_quality,
        }


def compute_market_decision(mf: MarketFeatures | None = None) -> MarketDecision:
    """V4 市场决策主入口

    流程: Feature → Rule → Evidence → Boundary → GuardRail
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if mf is None:
        mf = MarketFeatures.compute()

    # ── Step 1: 规则决策 ──
    emotion_decision = decide_emotion(mf)
    dragon_decision = decide_dragon(mf.top_boards or [], mf.limit_up_count)

    earning_scores = compute_earning_effect(mf)
    earning_decision = decide_earning(earning_scores)

    # ── Step 2: 边界检查 ──
    data_dict = mf.to_dict()
    boundary = check_all_boundaries(
        data=data_dict,
        conclusion=emotion_decision.conclusion,
    )

    # ── Step 3: 综合决策 ──
    sub_confidences = [
        emotion_decision.confidence,
        dragon_decision.confidence,
        earning_decision.confidence,
    ]
    valid_confidences = [c for c in sub_confidences if c > 0]

    if valid_confidences:
        composite_confidence = round(sum(valid_confidences) / len(valid_confidences), 3)
    else:
        composite_confidence = 0.0

    # 综合结论
    parts = []
    if emotion_decision.conclusion:
        parts.append(f"情绪{emotion_decision.conclusion}")
    if dragon_decision.conclusion and dragon_decision.conclusion != "无龙头":
        parts.append(dragon_decision.conclusion)
    if earning_decision.conclusion:
        parts.append(earning_decision.conclusion)

    composite_conclusion = "，".join(parts) if parts else "INSUFFICIENT_EVIDENCE"

    # 综合操作建议（只输出模型匹配，不输出投资建议）
    actions = []
    if emotion_decision.action:
        actions.append(emotion_decision.action)
    if dragon_decision.action:
        actions.append(dragon_decision.action)
    if earning_decision.action:
        actions.append(earning_decision.action)

    # ── Step 4: GuardRail 验证 ──
    guardrail = run_guardrail(
        ai_output=composite_conclusion,
        real_data=data_dict,
    )

    # 置信度不足 → 强制 INSUFFICIENT_EVIDENCE
    if composite_confidence < 0.7:
        composite_conclusion = "INSUFFICIENT_EVIDENCE"
        composite_action = "数据不足，无法做出可靠判断"
    elif not boundary.passed:
        composite_conclusion = f"边界违规: {len(boundary.violations)}项"
        composite_action = "存在数据或逻辑边界问题"
    else:
        composite_action = "；".join(actions[:3])

    return MarketDecision(
        timestamp=now,
        emotion=emotion_decision,
        dragon=dragon_decision,
        earning=earning_decision,
        composite_conclusion=composite_conclusion,
        composite_confidence=composite_confidence,
        composite_action=composite_action,
        boundary_passed=boundary.passed,
        boundary_violations=boundary.violations,
        guardrail_passed=guardrail.passed,
        data_quality=data_dict.get("_quality", {}),
    )
