"""评分工具函数 — 归一化、范围评分、置信度标签"""


def range_score(value: float, ideal_range: tuple, min_denom: float = 1.0) -> float:
    """值落入理想区间得 1.0，越远越接近 0（线性衰减）"""
    lo, hi = ideal_range
    if lo <= value <= hi:
        return 1.0
    if value < lo:
        return max(0.0, 1.0 - (lo - value) / max(lo, min_denom))
    return max(0.0, 1.0 - (value - hi) / max(hi, min_denom))


def normalize_score(raw: float, max_raw: float) -> float:
    """原始分 → [0, 1] 归一化"""
    if max_raw <= 0:
        return 0.0
    return min(1.0, max(0.0, raw / max_raw))


def confidence_label(score: float) -> str:
    """0-1 分数 → 高/中/低 置信度"""
    if score >= 0.75:
        return "高"
    if score >= 0.5:
        return "中"
    return "低"


def to_int_score(normalized: float) -> int:
    """[0, 1] → [0, 100] 整数分"""
    return max(0, min(100, round(normalized * 100)))


def weighted_sum(dimensions: dict, weights: dict) -> float:
    """多维加权求和（维度与权重 key 对齐）"""
    total = 0.0
    weight_sum = 0.0
    for key, w in weights.items():
        if key in dimensions:
            total += dimensions[key] * w
            weight_sum += w
    if weight_sum == 0:
        return 0.0
    return total / weight_sum
