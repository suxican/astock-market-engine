"""系统边界层 — 硬规则约束，禁止 AI 自由发挥

三层边界:
  Level 1 数据边界: 数据缺失 → 直接拒绝，禁止猜测
  Level 2 因果边界: 结论必须有数据支撑，禁止空洞归因
  Level 3 策略边界: AI 只能输出模型匹配结果，禁止投资建议
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BoundaryViolation(Enum):
    """边界违规类型"""
    DATA_MISSING = "data_missing"           # 数据缺失仍输出结论
    CAUSAL_UNGROUNDED = "causal_ungrounded" # 因果无数据支撑
    STRATEGY_FORBIDDEN = "strategy_forbidden" # 输出了投资建议
    HALLUCINATION = "hallucination"         # AI 幻觉


@dataclass
class BoundaryResult:
    """边界检查结果"""
    passed: bool = True
    violations: list[dict[str, str]] = field(default_factory=list)

    def add_violation(self, level: str, vtype: BoundaryViolation, detail: str):
        self.passed = False
        self.violations.append({
            "level": level,
            "type": vtype.value,
            "detail": detail,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "violation_count": len(self.violations),
        }


# ── Level 1: 数据边界 ──

# 禁止出现在推理链中的猜测性词汇
_FORBIDDEN_SPECULATIVE = [
    r"可能[会是]", r"大概率", r"应该[会是]", r"预计[将会]",
    r"有望[突破上涨]", r"或将[迎]", r"不排除",
    r"市场[预期猜测]", r"投资者[预期认为]",
]


def check_data_boundary(data: dict[str, Any], conclusion: str) -> BoundaryResult:
    """Level 1: 数据边界检查

    规则:
      - 数据字段为 None/0/空 → 禁止输出对应结论
      - 结论中禁止出现猜测性词汇
    """
    result = BoundaryResult()

    # 检查关键数据缺失
    critical_fields = {
        "limit_up_count": "涨停数",
        "limit_down_count": "跌停数",
        "zhaban_rate": "炸板率",
        "max_board_height": "连板高度",
        "index_pct_change": "大盘涨跌",
    }
    for field_name, label in critical_fields.items():
        val = data.get(field_name)
        if val is None or (isinstance(val, (int, float)) and val == 0 and field_name != "zhaban_rate"):
            # zhaban_rate=0 是合法值，其他字段为0可能表示数据缺失
            if field_name == "zhaban_rate" and val is not None:
                continue
            result.add_violation(
                "L1-数据", BoundaryViolation.DATA_MISSING,
                f"{label}({field_name})缺失，禁止输出相关结论",
            )

    # 检查猜测性词汇
    for pattern in _FORBIDDEN_SPECULATIVE:
        if re.search(pattern, conclusion):
            result.add_violation(
                "L1-推理", BoundaryViolation.HALLUCINATION,
                f"结论包含猜测性表述: {pattern}",
            )

    return result


# ── Level 2: 因果边界 ──

# 结论 → 必须具备的证据字段
_CAUSAL_REQUIREMENTS: dict[str, list[str]] = {
    "主升期": ["limit_up_count", "zhaban_rate", "max_board_height"],
    "高潮期": ["limit_up_count", "zhaban_rate", "up_down_ratio"],
    "冰点期": ["limit_up_count", "limit_down_count", "zhaban_rate"],
    "主力出货": ["main_flow", "pct_change", "turnover"],
    "主力吸筹": ["main_flow", "turnover", "price_ratio"],
    "龙头效应": ["max_board_height", "top_boards"],
    "赚钱效应强": ["limit_up_count", "limit_down_count", "zhaban_rate"],
    "亏钱效应": ["limit_down_count", "limit_up_count"],
}


def check_causal_boundary(conclusion: str, available_data: dict[str, Any]) -> BoundaryResult:
    """Level 2: 因果边界检查

    规则:
      - 结论必须有对应的数据字段支撑
      - 禁止空洞归因（如"资金看好"但没有 fund_flow 数据）
    """
    result = BoundaryResult()

    # 匹配结论对应的证据要求
    for key, required_fields in _CAUSAL_REQUIREMENTS.items():
        if key in conclusion:
            missing = []
            for f in required_fields:
                val = available_data.get(f)
                if val is None:
                    missing.append(f)
            if missing:
                result.add_violation(
                    "L2-因果", BoundaryViolation.CAUSAL_UNGROUNDED,
                    f"结论'{key}'缺少证据字段: {', '.join(missing)}",
                )

    return result


# ── Level 3: 策略边界 ──

# 禁止 AI 输出的投资建议
_FORBIDDEN_ADVICE = [
    r"建议[买入卖出加仓减仓重仓清仓]",
    r"推荐[买入持有]",
    r"[明后]天[涨停跌停大涨大跌]",
    r"目标价\d+",
    r"[必确]定[会能]涨",
    r"赶紧[买入上车]",
    r"止损\d+",
]

# 只允许输出的模型匹配结论
_ALLOWED_CONCLUSIONS = [
    "符合龙头模型", "符合主升模型", "符合预期差模型",
    "符合吸筹模型", "符合洗盘模型", "符合出货模型",
    "情绪冰点", "情绪修复", "情绪主升", "情绪高潮", "情绪分歧", "情绪退潮",
    "赚钱效应强", "赚钱效应中", "赚钱效应弱", "赚钱效应极弱",
    "INSUFFICIENT_EVIDENCE",
]


def check_strategy_boundary(ai_output: str) -> BoundaryResult:
    """Level 3: 策略边界检查

    规则:
      - 禁止输出投资建议
      - 只允许输出模型匹配结论
    """
    result = BoundaryResult()

    for pattern in _FORBIDDEN_ADVICE:
        matches = re.findall(pattern, ai_output)
        if matches:
            for m in matches:
                result.add_violation(
                    "L3-策略", BoundaryViolation.STRATEGY_FORBIDDEN,
                    f"禁止输出投资建议: {m}",
                )

    return result


def check_all_boundaries(
    data: dict[str, Any],
    conclusion: str,
    ai_output: str = "",
) -> BoundaryResult:
    """一次性检查所有三层边界"""
    r1 = check_data_boundary(data, conclusion)
    r2 = check_causal_boundary(conclusion, data)
    r3 = check_strategy_boundary(ai_output or conclusion)

    merged = BoundaryResult()
    merged.violations = r1.violations + r2.violations + r3.violations
    merged.passed = r1.passed and r2.passed and r3.passed
    return merged
