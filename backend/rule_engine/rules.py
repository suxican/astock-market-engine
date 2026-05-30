"""硬规则决策层 — AI 不参与，纯规则

决策流程:
  Feature Engine → Rule Engine → 结论

每条规则:
  - 有明确的阈值
  - 有回测数据支撑（TODO: BacktestLab）
  - 不依赖 LLM

输出格式:
  {
    "conclusion": "主升期",
    "evidence": [...],
    "confidence": 0.85,
    "rule": "emotion_rule_v1"
  }
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.evidence_engine.evidence import (
    Evidence,
    EvidenceBundle,
    EvidenceType,
    build_emotion_evidence,
)


@dataclass
class RuleDecision:
    """规则决策结果"""
    conclusion: str
    rule_name: str
    evidence: EvidenceBundle
    confidence: float = 0.0
    action: str = ""  # 匹配的模型名称

    def to_dict(self) -> dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "rule": self.rule_name,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict(),
            "action": self.action,
        }


def decide_emotion(mf) -> RuleDecision:
    """情绪阶段硬规则决策

    不调用 LLM，纯阈值判断。
    """
    evidence = build_emotion_evidence(mf)
    up = mf.limit_up_count or 0
    down = mf.limit_down_count or 0
    zhaban = mf.zhaban_rate or 0
    board = mf.max_board_height or 0
    ratio = mf.up_down_ratio or 0

    # 硬规则：按阈值直接判定阶段
    if up >= 60 and zhaban < 0.20 and board >= 8:
        stage = "高潮期"
        action = "减仓警惕，见好就收"
    elif up >= 30 and zhaban < 0.30 and board >= 5:
        stage = "主升期"
        action = "重仓跟随主线"
    elif up >= 20 and zhaban < 0.40:
        stage = "修复期"
        action = "逐步加仓，跟随龙头"
    elif up < 15 and down > up and zhaban > 0.50:
        stage = "冰点期"
        action = "小仓试探，等待企稳"
    elif 30 <= up <= 50 and 0.30 <= zhaban <= 0.50:
        stage = "分歧期"
        action = "轻仓观望，不追高"
    elif up < 20 and zhaban > 0.40 and board < 3:
        stage = "退潮期"
        action = "空仓等待冰点"
    else:
        stage = "修复期"
        action = "控制仓位，观察方向"

    evidence.conclusion = stage
    evidence.validate()

    return RuleDecision(
        conclusion=stage,
        rule_name="emotion_hard_rule_v1",
        evidence=evidence,
        confidence=evidence.confidence,
        action=action,
    )


def decide_dragon(top_boards: list, limit_up_count: int) -> RuleDecision:
    """龙头识别硬规则决策"""
    evidence = EvidenceBundle(conclusion="")

    if not top_boards:
        evidence.status = "INSUFFICIENT_EVIDENCE"
        return RuleDecision(
            conclusion="无龙头",
            rule_name="dragon_hard_rule_v1",
            evidence=evidence,
            confidence=0.0,
            action="无明确龙头，观望",
        )

    top = top_boards[0]
    boards = top.get("boards", 0)
    fengdan = top.get("fengdan", 0)
    name = top.get("name", "")

    evidence.add(Evidence(
        etype=EvidenceType.DATA,
        field="top_board_height",
        value=boards,
        description=f"最高板{name}({boards}板)",
        weight=1.0,
    ))

    if fengdan > 0:
        evidence.add(Evidence(
            etype=EvidenceType.DATA,
            field="fengdan",
            value=fengdan,
            description=f"封单{fengdan:.1f}亿",
            weight=0.8,
        ))

    multi = [b for b in top_boards if b.get("boards", 0) >= 2]
    if multi:
        evidence.add(Evidence(
            etype=EvidenceType.DATA,
            field="multi_board_count",
            value=len(multi),
            description=f"连板股{len(multi)}只",
            weight=0.8,
        ))

    # 硬规则
    if boards >= 7 and fengdan >= 3:
        conclusion = "总龙头确认"
        action = "符合龙头模型"
    elif boards >= 5:
        conclusion = "高标龙头"
        action = "符合龙头模型"
    elif boards >= 3 and len(multi) >= 3:
        conclusion = "板块龙头涌现"
        action = "关注板块方向"
    elif boards >= 2:
        conclusion = "连板梯队形成"
        action = "观察晋级情况"
    else:
        conclusion = "无明确龙头"
        action = "等待龙头出现"

    evidence.conclusion = conclusion
    evidence.validate()

    return RuleDecision(
        conclusion=conclusion,
        rule_name="dragon_hard_rule_v1",
        evidence=evidence,
        confidence=evidence.confidence,
        action=action,
    )


def decide_earning(earning_scores) -> RuleDecision:
    """赚钱效应硬规则决策"""
    evidence = EvidenceBundle(conclusion="")

    composite = earning_scores.composite or 0
    evidence.add(Evidence(
        etype=EvidenceType.COMPUTED,
        field="earning_effect_composite",
        value=composite,
        description=f"赚钱效应综合分{composite}",
        weight=1.0,
    ))

    if earning_scores.avg_premium_pct is not None:
        evidence.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="avg_premium_pct",
            value=earning_scores.avg_premium_pct,
            description=f"涨停溢价{earning_scores.avg_premium_pct:+.1f}%",
            weight=0.9,
        ))

    if earning_scores.survival_rate is not None:
        evidence.add(Evidence(
            etype=EvidenceType.COMPUTED,
            field="survival_rate",
            value=earning_scores.survival_rate,
            description=f"连板存活率{earning_scores.survival_rate:.0%}",
            weight=0.8,
        ))

    # 硬规则
    if composite >= 75:
        conclusion = "赚钱效应强"
        action = "积极参与主线"
    elif composite >= 50:
        conclusion = "赚钱效应中"
        action = "轻仓跟随"
    elif composite >= 30:
        conclusion = "赚钱效应弱"
        action = "谨慎参与"
    else:
        conclusion = "亏钱效应"
        action = "空仓观望"

    evidence.conclusion = conclusion
    evidence.validate()

    return RuleDecision(
        conclusion=conclusion,
        rule_name="earning_hard_rule_v1",
        evidence=evidence,
        confidence=evidence.confidence,
        action=action,
    )
