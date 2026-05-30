"""赚钱效应计算 — 纯规则，不调用 LLM

输入: MarketFeatures (盘面级特征快照)
输出: EarningEffectScores (结构化 0-100 分数)

计算逻辑:
  - 从涨停池获取昨日涨停股列表，查询今日行情计算溢价率
  - 连板股存活率 = 今日仍涨停的连板股 / 昨日连板股总数
  - 龙头溢价 = 最高连板股次日涨幅
  - 跌停扩散度 = 近3日跌停数趋势
  - 综合分 = 40% 溢价率 + 25% 连板存活 + 20% 龙头溢价 + 15% 跌停扩散(反向)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from backend.feature_engine.market_features import MarketFeatures
from backend.score_engine.score_utils import confidence_label, range_score, to_int_score, weighted_sum

logger = logging.getLogger("market_engine.earning_effect")


@dataclass
class EarningEffectScores:
    """赚钱效应评分"""

    # ── 分项分数 (0-100) ──
    premium_score: int = 0          # 涨停次日溢价率得分
    survival_score: int = 0         # 连板存活率得分
    dragon_premium_score: int = 0   # 龙头溢价得分
    loss_spread_score: int = 0      # 跌停扩散得分（越高=亏钱效应越强）
    zhaban_reflow_score: int = 0    # 炸板回封率得分

    # ── 原始指标 ──
    avg_premium_pct: float = 0.0    # 涨停股次日平均涨幅 %
    survival_rate: float = 0.0      # 连板存活率 0-1
    dragon_premium_pct: float = 0.0 # 龙头次日涨幅 %
    loss_spread_ratio: float = 0.0  # 跌停扩散比（近3日趋势）
    zhaban_reflow_rate: float = 0.0 # 炸板回封率 0-1

    # ── 综合分 (0-100, 越高赚钱效应越强) ──
    composite: int = 0

    # ── 信号与建议 ──
    signals: list[str] = field(default_factory=list)
    suggestion: str = ""
    level: str = ""  # 强/中/弱/极弱

    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "premium_score": self.premium_score,
            "survival_score": self.survival_score,
            "dragon_premium_score": self.dragon_premium_score,
            "loss_spread_score": self.loss_spread_score,
            "zhaban_reflow_score": self.zhaban_reflow_score,
            "avg_premium_pct": round(self.avg_premium_pct, 2),
            "survival_rate": round(self.survival_rate, 3),
            "dragon_premium_pct": round(self.dragon_premium_pct, 2),
            "loss_spread_ratio": round(self.loss_spread_ratio, 3),
            "zhaban_reflow_rate": round(self.zhaban_reflow_rate, 3),
            "composite": self.composite,
            "signals": self.signals,
            "suggestion": self.suggestion,
            "level": self.level,
            "computed_at": self.computed_at,
        }


# ── 权重配置 ──
_WEIGHTS = {
    "premium": 0.35,
    "survival": 0.25,
    "dragon": 0.20,
    "loss": 0.10,
    "zhaban_reflow": 0.10,
}

_LEVEL_THRESHOLDS = [
    (80, "强"),
    (55, "中"),
    (30, "弱"),
    (0, "极弱"),
]

_LEVEL_SUGGESTIONS = {
    "强": "市场赚钱效应强烈，积极参与主线方向，可适当追涨龙头。",
    "中": "赚钱效应中性偏暖，跟随主线轻仓参与，注意控制仓位。",
    "弱": "赚钱效应偏弱，谨慎参与，避免追高，现金为王。",
    "极弱": "市场亏钱效应显著，建议空仓观望，等待赚钱效应回归。",
}


def compute_earning_effect(mf: MarketFeatures) -> EarningEffectScores:
    """计算赚钱效应 — 输入 MarketFeatures，输出 EarningEffectScores

    在请求上下文中，MarketFeatures 已包含涨停池/跌停池原始 DataFrame，
    直接使用避免二次远程调用。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 1. 涨停次日溢价率 ──
    premium_pct, premium_raw = _calc_premium_rate(mf)

    # ── 2. 连板存活率 ──
    survival_rate, survival_raw = _calc_survival_rate(mf)

    # ── 3. 龙头溢价 ──
    dragon_pct, dragon_raw = _calc_dragon_premium(mf)

    # ── 4. 跌停扩散比 ──
    loss_ratio, loss_raw = _calc_loss_spread(mf)

    # ── 5. 炸板回封率 ──
    reflow_rate, reflow_raw = _calc_zhaban_reflow(mf)

    # ── 归一化为 0-100 分 ──
    premium_score = to_int_score(premium_raw)
    survival_score = to_int_score(survival_raw)
    dragon_score = to_int_score(dragon_raw)
    # 跌停扩散: 反向 (扩散越大，分越低)
    loss_score = to_int_score(1.0 - loss_raw)
    reflow_score = to_int_score(reflow_raw)

    # ── 加权综合 ──
    dims = {
        "premium": premium_raw,
        "survival": survival_raw,
        "dragon": dragon_raw,
        "loss": 1.0 - loss_raw,
        "zhaban_reflow": reflow_raw,
    }
    composite_raw = weighted_sum(dims, _WEIGHTS)
    composite = to_int_score(composite_raw)

    # ── 等级与建议 ──
    level = "极弱"
    for threshold, name in _LEVEL_THRESHOLDS:
        if composite >= threshold:
            level = name
            break

    signals = _build_signals(
        mf, premium_pct, survival_rate, dragon_pct, loss_ratio, reflow_rate
    )
    suggestion = _LEVEL_SUGGESTIONS.get(level, "")

    return EarningEffectScores(
        premium_score=premium_score,
        survival_score=survival_score,
        dragon_premium_score=dragon_score,
        loss_spread_score=loss_score,
        zhaban_reflow_score=reflow_score,
        avg_premium_pct=premium_pct,
        survival_rate=survival_rate,
        dragon_premium_pct=dragon_pct,
        loss_spread_ratio=loss_ratio,
        zhaban_reflow_rate=reflow_rate,
        composite=composite,
        signals=signals,
        suggestion=suggestion,
        level=level,
        computed_at=now,
    )


def _calc_premium_rate(mf: MarketFeatures) -> tuple[float, float]:
    """涨停次日溢价率: 昨日涨停股今日平均涨幅

    Returns:
        (raw_pct, normalized_0_1)
    """
    if mf.limit_up_pool is None or mf.limit_up_pool.empty:
        return 0.0, 0.3  # 无数据，给中间分

    pool = mf.limit_up_pool
    # 涨停池中连板数 >= 1 的股，它们今日涨幅的均值就是 "溢价率"
    # (涨停池本身就是今日涨停的股，所以溢价率用 "今日涨幅 > 0 的比例" 近似)
    if "涨跌幅" in pool.columns:
        pct_series = pd.to_numeric(pool["涨跌幅"], errors="coerce").dropna()
        if not pct_series.empty:
            avg_pct = float(pct_series.mean())
            # 涨停股今日平均涨幅 5% → 强溢价 (normalized ~1.0)
            # 涨停股今日平均涨幅 0% → 无溢价 (normalized ~0.5)
            # 涨停股今日平均涨幅 -5% → 亏钱 (normalized ~0.0)
            norm = max(0.0, min(1.0, (avg_pct + 5) / 10))
            return avg_pct, norm

    return 0.0, 0.3


def _calc_survival_rate(mf: MarketFeatures) -> tuple[float, float]:
    """连板存活率: 连板 >= 2 的股中，今日仍涨停的比例

    Returns:
        (rate_0_1, normalized_0_1)
    """
    if mf.top_boards:
        # top_boards 列表中的连板数
        multi_board = [b for b in mf.top_boards if b.get("boards", 0) >= 2]
        total_multi = len(multi_board)
        if total_multi > 0:
            # 简化: 连板股越多且连板高度越高，存活率越高
            max_h = mf.max_board_height
            # 存活率 ≈ 连板股数量 / (涨停数 * 0.3) 上限为1
            rate = min(1.0, total_multi / max(mf.limit_up_count * 0.2, 1))
            # 额外加成: 最高连板 >= 5 说明市场容错率高
            if max_h >= 5:
                rate = min(1.0, rate + 0.15)
            return rate, rate

    return 0.0, 0.2


def _calc_dragon_premium(mf: MarketFeatures) -> tuple[float, float]:
    """龙头溢价: 总龙头的强势程度

    用最高连板高度和龙头数量衡量。
    Returns:
        (dragon_pct_approx, normalized_0_1)
    """
    max_h = mf.max_board_height
    top_count = len([b for b in (mf.top_boards or []) if b.get("boards", 0) >= 3])

    # 最高连板 8+ → 强龙头溢价
    # 最高连板 5-7 → 中等龙头溢价
    # 最高连板 3-4 → 弱龙头溢价
    # 最高连板 0-2 → 无龙头
    if max_h >= 8:
        norm = 0.95
        pct = 8.0
    elif max_h >= 5:
        norm = 0.75
        pct = 5.0
    elif max_h >= 3:
        norm = 0.5
        pct = 3.0
    elif max_h >= 2:
        norm = 0.35
        pct = 1.5
    else:
        norm = 0.15
        pct = 0.0

    # 连板 >= 3 的股数越多，龙头效应越强
    if top_count >= 5:
        norm = min(1.0, norm + 0.1)
    elif top_count >= 3:
        norm = min(1.0, norm + 0.05)

    return pct, norm


def _calc_loss_spread(mf: MarketFeatures) -> tuple[float, float]:
    """跌停扩散比: 跌停数占涨跌停总数的比例

    Returns:
        (ratio, normalized_0_1, 越高=亏钱效应越强)
    """
    total = mf.limit_up_count + mf.limit_down_count
    if total == 0:
        return 0.0, 0.2  # 无数据

    ratio = mf.limit_down_count / total
    return ratio, min(1.0, ratio * 2)  # 放大: 30%跌停就已经很严重


def _calc_zhaban_reflow(mf: MarketFeatures) -> tuple[float, float]:
    """炸板回封率: 基于炸板率反推

    炸板率低 → 回封率高 → 赚钱效应强
    Returns:
        (reflow_rate_0_1, normalized_0_1)
    """
    zhaban = mf.zhaban_rate
    # 炸板率 0% → 回封率 100% (完美)
    # 炸板率 20% → 回封率 80%
    # 炸板率 50% → 回封率 50%
    # 炸板率 80%+ → 回封率 20%
    reflow = max(0.0, 1.0 - zhaban)
    return reflow, reflow


def _build_signals(
    mf: MarketFeatures,
    premium_pct: float,
    survival_rate: float,
    dragon_pct: float,
    loss_ratio: float,
    reflow_rate: float,
) -> list[str]:
    """构建核心信号列表"""
    signals = []

    if premium_pct > 3:
        signals.append(f"涨停股平均溢价 {premium_pct:+.1f}%，赚钱效应显著")
    elif premium_pct > 0:
        signals.append(f"涨停股平均溢价 {premium_pct:+.1f}%，赚钱效应温和")
    else:
        signals.append(f"涨停股平均溢价 {premium_pct:+.1f}%，亏钱效应显现")

    if survival_rate > 0.7:
        signals.append(f"连板存活率 {survival_rate:.0%}，市场容错率高")
    elif survival_rate > 0.4:
        signals.append(f"连板存活率 {survival_rate:.0%}，赚钱效应中性")
    else:
        signals.append(f"连板存活率 {survival_rate:.0%}，高位股风险大")

    if mf.max_board_height >= 5:
        signals.append(f"最高连板 {mf.max_board_height} 板，龙头效应强")
    elif mf.max_board_height >= 3:
        signals.append(f"最高连板 {mf.max_board_height} 板，有赚钱主线")
    else:
        signals.append(f"最高连板 {mf.max_board_height} 板，缺乏主线")

    if loss_ratio > 0.3:
        signals.append(f"跌停占比 {loss_ratio:.0%}，亏钱效应扩散")
    elif loss_ratio > 0.1:
        signals.append(f"跌停占比 {loss_ratio:.0%}，需警惕")

    if mf.zhaban_rate > 0.5:
        signals.append(f"炸板率 {mf.zhaban_rate:.0%}，封板资金不坚决")
    elif mf.zhaban_rate < 0.2:
        signals.append(f"炸板率 {mf.zhaban_rate:.0%}，封板资金坚决")

    return signals
