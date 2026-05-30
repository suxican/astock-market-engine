"""AI 幻觉防火墙 — 验证 AI 输出的真实性

每次 AI 输出后必须经过 GuardRail:
  1. 引用真实数据检查
  2. 引用真实事件检查
  3. 投资建议过滤
  4. 证据充分性检查

不通过 → 删除结论，返回 INSUFFICIENT_EVIDENCE
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.core.system_boundary import BoundaryResult, check_strategy_boundary
from backend.evidence_engine.evidence import EvidenceBundle


@dataclass
class GuardRailResult:
    """GuardRail 检查结果"""
    passed: bool = True
    original_output: str = ""
    sanitized_output: str = ""
    removed_clauses: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "sanitized_output": self.sanitized_output,
            "removed_count": len(self.removed_clauses),
            "removed_clauses": self.removed_clauses,
            "reason": self.reason,
        }


# ── 数据引用检查 ──

# AI 输出中引用的数据字段必须在真实数据中存在
_DATA_CLAIMS = {
    r"涨停(\d+)家?": "limit_up_count",
    r"跌停(\d+)家?": "limit_down_count",
    r"炸板率(\d+\.?\d*)%?": "zhaban_rate",
    r"连板[高度]+(\d+)板?": "max_board_height",
    r"主力净?(?:流入|流出)(\d+)": "main_flow",
    r"换手率(\d+\.?\d*)%?": "turnover",
}


def verify_data_claims(ai_output: str, real_data: dict[str, Any]) -> list[str]:
    """检查 AI 输出中引用的数据是否真实存在

    Returns:
        违规列表（空 = 全部通过）
    """
    violations = []
    for pattern, field_name in _DATA_CLAIMS.items():
        matches = re.findall(pattern, ai_output)
        if matches:
            real_val = real_data.get(field_name)
            if real_val is None:
                violations.append(f"AI引用了{field_name}但数据不存在")
    return violations


# ── 事件引用检查 ──

_EVENT_CLAIMS = [
    (r"政策[刺激利好推动]", "policy"),
    (r"[国务工信]委", "government"),
    (r"行业[协协]会", "industry"),
    (r"资金[大量大幅][流入进场]", "fund_flow"),
]


def verify_event_claims(ai_output: str, event_data: dict[str, Any] | None) -> list[str]:
    """检查 AI 输出中引用的事件是否真实存在"""
    violations = []
    if event_data is None:
        for pattern, _ in _EVENT_CLAIMS:
            if re.search(pattern, ai_output):
                violations.append(f"AI引用了事件但无事件数据")
                break
    return violations


# ── 主力行为验证 ──

_CAPITAL_CLAIMS = {
    r"主力(?:出货|派发)": lambda d: d.get("main_flow", 0) < 0,
    r"主力(?:吸筹|建仓)": lambda d: d.get("main_flow", 0) > 0,
    r"主力(?:大幅)?(?:净)?流入": lambda d: d.get("main_flow", 0) > 0,
    r"主力(?:大幅)?(?:净)?流出": lambda d: d.get("main_flow", 0) < 0,
}


def verify_capital_claims(ai_output: str, fund_data: dict[str, Any]) -> list[str]:
    """检查主力行为结论是否有资金流数据支撑"""
    violations = []
    for pattern, check_fn in _CAPITAL_CLAIMS.items():
        if re.search(pattern, ai_output):
            if not check_fn(fund_data):
                violations.append(f"主力行为结论无资金流数据支撑: {pattern}")
    return violations


# ── 投资建议过滤 ──

_ADVICE_PATTERNS = [
    r"建议[买入卖出加仓减仓重仓清仓]",
    r"推荐[买入持有]",
    r"[明后]天[涨停跌停]",
    r"目标价\d+",
    r"[必确]定[会能]涨",
    r"止损\d+[元%]",
]


def filter_advice(ai_output: str) -> tuple[str, list[str]]:
    """过滤投资建议，返回 (清理后文本, 被删除的片段)"""
    removed = []
    result = ai_output
    for pattern in _ADVICE_PATTERNS:
        matches = re.findall(pattern, result)
        if matches:
            removed.extend(matches)
            result = re.sub(pattern, "[已过滤]", result)
    return result, removed


# ── 综合检查 ──

def run_guardrail(
    ai_output: str,
    real_data: dict[str, Any] | None = None,
    event_data: dict[str, Any] | None = None,
    fund_data: dict[str, Any] | None = None,
    evidence: EvidenceBundle | None = None,
) -> GuardRailResult:
    """综合 GuardRail 检查

    流程:
      1. 证据充分性检查
      2. 数据引用检查
      3. 事件引用检查
      4. 主力行为检查
      5. 投资建议过滤
    """
    result = GuardRailResult(original_output=ai_output)

    # 1. 证据充分性
    if evidence is not None and not evidence.validate():
        result.passed = False
        result.sanitized_output = ""
        result.reason = f"INSUFFICIENT_EVIDENCE: {evidence.confidence}"
        return result

    # 2. 数据引用检查
    if real_data:
        data_violations = verify_data_claims(ai_output, real_data)
        result.removed_clauses.extend(data_violations)

    # 3. 事件引用检查
    event_violations = verify_event_claims(ai_output, event_data)
    result.removed_clauses.extend(event_violations)

    # 4. 主力行为检查
    if fund_data:
        capital_violations = verify_capital_claims(ai_output, fund_data)
        result.removed_clauses.extend(capital_violations)

    # 5. 投资建议过滤
    sanitized, advice_removed = filter_advice(ai_output)
    result.removed_clauses.extend([f"投资建议: {a}" for a in advice_removed])
    result.sanitized_output = sanitized

    # 策略边界
    boundary = check_strategy_boundary(ai_output)
    if not boundary.passed:
        for v in boundary.violations:
            result.removed_clauses.append(f"策略违规: {v['detail']}")

    # 判断是否通过
    critical_violations = [v for v in result.removed_clauses
                           if "投资建议" in v or "策略违规" in v]
    if critical_violations:
        result.passed = False
        result.reason = f"包含{len(critical_violations)}条违规内容"

    if not result.sanitized_output:
        result.passed = False
        result.reason = result.reason or "清理后无有效内容"

    return result
