"""证据引擎 — 任何结论必须带证据，证据不足则拒绝输出

核心规则:
  - 每个结论必须有 >= 2 条证据
  - 每条证据必须引用真实数据字段
  - 证据不足 → 返回 INSUFFICIENT_EVIDENCE
  - 置信度 < 0.7 → 返回 INSUFFICIENT_EVIDENCE
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceType(Enum):
    """证据类型"""
    DATA = "data"           # 直接数据（涨停38家）
    COMPUTED = "computed"   # 计算指标（炸板率18%）
    EVENT = "event"         # 事件驱动（政策发布）
    PATTERN = "pattern"     # 模式匹配（符合龙头模型）


@dataclass
class Evidence:
    """单条证据"""
    etype: EvidenceType
    field: str          # 引用的数据字段
    value: Any          # 实际值
    description: str    # 人类可读描述
    weight: float = 1.0 # 权重 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.etype.value,
            "field": self.field,
            "value": self.value,
            "description": self.description,
            "weight": self.weight,
        }


@dataclass
class EvidenceBundle:
    """证据集合"""
    conclusion: str
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "OK"  # OK / INSUFFICIENT_EVIDENCE

    def add(self, evidence: Evidence):
        self.evidence.append(evidence)

    def validate(self, min_evidence: int = 2, min_confidence: float = 0.7) -> bool:
        """验证证据是否充分

        Returns:
            True = 证据充分，可输出结论
            False = 证据不足，必须返回 INSUFFICIENT_EVIDENCE
        """
        if len(self.evidence) < min_evidence:
            self.status = "INSUFFICIENT_EVIDENCE"
            self.confidence = 0.0
            return False

        # 计算加权置信度
        total_weight = sum(e.weight for e in self.evidence)
        if total_weight == 0:
            self.status = "INSUFFICIENT_EVIDENCE"
            self.confidence = 0.0
            return False

        # 置信度 = 证据数量因子 × 权重因子
        count_factor = min(1.0, len(self.evidence) / 3)  # 3条证据满分
        weight_factor = total_weight / len(self.evidence)
        self.confidence = round(count_factor * weight_factor, 3)

        if self.confidence < min_confidence:
            self.status = "INSUFFICIENT_EVIDENCE"
            return False

        self.status = "OK"
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "evidence": [e.to_dict() for e in self.evidence],
            "evidence_count": len(self.evidence),
            "confidence": self.confidence,
            "status": self.status,
        }


def build_emotion_evidence(mf) -> EvidenceBundle:
    """为情绪周期结论构建证据"""
    bundle = EvidenceBundle(conclusion="")

    if mf.limit_up_count is not None and mf.limit_up_count > 0:
        bundle.add(Evidence(
            etype=EvidenceType.DATA,
            field="limit_up_count",
            value=mf.limit_up_count,
            description=f"涨停{mf.limit_up_count}家",
            weight=1.0,
        ))

    if mf.limit_down_count is not None:
        bundle.add(Evidence(
            etype=EvidenceType.DATA,
            field="limit_down_count",
            value=mf.limit_down_count,
            description=f"跌停{mf.limit_down_count}家",
            weight=0.8,
        ))

    if mf.zhaban_rate is not None and mf.zhaban_rate >= 0:
        bundle.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="zhaban_rate",
            value=mf.zhaban_rate,
            description=f"炸板率{mf.zhaban_rate:.1%}",
            weight=0.9,
        ))

    if mf.max_board_height is not None and mf.max_board_height > 0:
        bundle.add(Evidence(
            etype=EvidenceType.DATA,
            field="max_board_height",
            value=mf.max_board_height,
            description=f"最高连板{mf.max_board_height}板",
            weight=0.9,
        ))

    if mf.up_down_ratio is not None and mf.up_down_ratio > 0:
        bundle.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="up_down_ratio",
            value=mf.up_down_ratio,
            description=f"涨跌比{mf.up_down_ratio:.1f}",
            weight=0.7,
        ))

    return bundle


def build_dragon_evidence(pool, top_boards: list) -> EvidenceBundle:
    """为龙头结论构建证据"""
    bundle = EvidenceBundle(conclusion="")

    if top_boards:
        top = top_boards[0]
        bundle.add(Evidence(
            etype=EvidenceType.DATA,
            field="max_board_height",
            value=top.get("boards", 0),
            description=f"最高板{top.get('name','')}({top.get('boards',0)}板)",
            weight=1.0,
        ))

        multi_board = [b for b in top_boards if b.get("boards", 0) >= 2]
        if multi_board:
            bundle.add(Evidence(
                etype=EvidenceType.DATA,
                field="multi_board_count",
                value=len(multi_board),
                description=f"连板股{len(multi_board)}只",
                weight=0.8,
            ))

    if pool is not None and not pool.empty:
        bundle.add(Evidence(
            etype=EvidenceType.DATA,
            field="limit_up_pool_size",
            value=len(pool),
            description=f"涨停池{len(pool)}只",
            weight=0.7,
        ))

    return bundle


def build_earning_evidence(scores) -> EvidenceBundle:
    """为赚钱效应结论构建证据"""
    bundle = EvidenceBundle(conclusion="")

    if scores.avg_premium_pct is not None:
        bundle.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="avg_premium_pct",
            value=scores.avg_premium_pct,
            description=f"涨停溢价{scores.avg_premium_pct:+.1f}%",
            weight=1.0,
        ))

    if scores.survival_rate is not None:
        bundle.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="survival_rate",
            value=scores.survival_rate,
            description=f"连板存活率{scores.survival_rate:.0%}",
            weight=0.9,
        ))

    if scores.dragon_premium_pct is not None:
        bundle.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="dragon_premium_pct",
            value=scores.dragon_premium_pct,
            description=f"龙头溢价{scores.dragon_premium_pct:+.1f}%",
            weight=0.8,
        ))

    return bundle
