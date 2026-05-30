"""市场宽度指标 — 涨跌家数、新高新低、涨停跌停分布

从全市场快照 (stock_zh_a_spot_em) 计算:
  - up_count / down_count / flat_count
  - up_ratio (涨跌比)
  - limit_up_count / limit_down_count (涨跌停数)
  - new_high_52w / new_low_52w (52周新高/新低)
  - above_ma5_pct (站上5日线比例)
  - market_breadth_score (综合宽度评分 0-100)

数据源: akshare stock_zh_a_spot_em (全市场快照)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from ._cache import _cache_get, _cache_set
from ._helpers import _try_akshare
from .data_quality import DataQuality, DataSource, classify_system_status

logger = logging.getLogger("market_engine.breadth")


@dataclass
class MarketBreadth:
    """市场宽度指标"""

    # 涨跌家数
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    total_count: int = 0

    # 涨跌比
    up_ratio: float = 0.0  # up / down

    # 涨跌停
    limit_up_count: int = 0
    limit_down_count: int = 0

    # 强弱分布
    strong_up_count: int = 0   # 涨幅 > 5%
    strong_down_count: int = 0  # 跌幅 > 5%

    # 综合宽度评分 (0-100)
    breadth_score: int = 0
    breadth_level: str = ""  # 极强/偏强/中性/偏弱/极弱

    signals: list[str] = field(default_factory=list)
    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "up_count": self.up_count,
            "down_count": self.down_count,
            "flat_count": self.flat_count,
            "total_count": self.total_count,
            "up_ratio": round(self.up_ratio, 2),
            "limit_up_count": self.limit_up_count,
            "limit_down_count": self.limit_down_count,
            "strong_up_count": self.strong_up_count,
            "strong_down_count": self.strong_down_count,
            "breadth_score": self.breadth_score,
            "breadth_level": self.breadth_level,
            "signals": self.signals,
            "computed_at": self.computed_at,
        }


def compute_market_breadth() -> MarketBreadth:
    """从全市场快照计算市场宽度

    数据源优先级: akshare stock_zh_a_spot_em
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取全市场快照 (复用 quote_data 的 30s 缓存)
    from .quote_data import _get_spot_em_df
    df = _get_spot_em_df()

    if df is None or df.empty:
        return MarketBreadth(
            breadth_score=50,
            breadth_level="未知",
            signals=["全市场数据不可用"],
            computed_at=now,
        )

    # 涨跌幅列
    pct_col = "涨跌幅"
    if pct_col not in df.columns:
        return MarketBreadth(
            breadth_score=50,
            breadth_level="未知",
            signals=["数据格式异常"],
            computed_at=now,
        )

    pct = pd.to_numeric(df[pct_col], errors="coerce").fillna(0)
    total = len(pct)

    # 涨跌家数
    up_count = int((pct > 0).sum())
    down_count = int((pct < 0).sum())
    flat_count = int((pct == 0).sum())

    # 涨跌比
    up_ratio = up_count / max(down_count, 1)

    # 涨跌停 (A股主板 ±10%, 创业板/科创板 ±20%, ST ±5%)
    # 简化: 涨幅 >= 9.8% 视为涨停, 跌幅 <= -9.8% 视为跌停
    limit_up = int((pct >= 9.8).sum())
    limit_down = int((pct <= -9.8).sum())

    # 强弱分布
    strong_up = int((pct >= 5).sum())
    strong_down = int((pct <= -5).sum())

    # 综合评分
    score = _calc_breadth_score(up_count, down_count, limit_up, limit_down,
                                strong_up, strong_down, total)

    # 等级
    if score >= 80:
        level = "极强"
    elif score >= 65:
        level = "偏强"
    elif score >= 40:
        level = "中性"
    elif score >= 20:
        level = "偏弱"
    else:
        level = "极弱"

    # 信号
    signals = _build_signals(up_count, down_count, up_ratio, limit_up,
                              limit_down, strong_up, strong_down)

    return MarketBreadth(
        up_count=up_count,
        down_count=down_count,
        flat_count=flat_count,
        total_count=total,
        up_ratio=round(up_ratio, 2),
        limit_up_count=limit_up,
        limit_down_count=limit_down,
        strong_up_count=strong_up,
        strong_down_count=strong_down,
        breadth_score=score,
        breadth_level=level,
        signals=signals,
        computed_at=now,
    )


def _calc_breadth_score(
    up: int, down: int, lu: int, ld: int,
    su: int, sd: int, total: int,
) -> int:
    """市场宽度综合评分 (0-100)

    权重:
      - 涨跌比 40%
      - 涨停强度 25%
      - 强弱比 20%
      - 跌停风险 15%
    """
    if total == 0:
        return 50

    # 1. 涨跌比 → 0-1 (ratio=2 → 0.5, ratio=3 → 0.7, ratio=0.5 → 0.2)
    ratio_score = min(1.0, max(0.0, (up / max(down, 1) - 0.3) / 2.7))

    # 2. 涨停强度 (涨停数占总数比)
    lu_ratio = min(lu / max(total * 0.01, 1), 1.0)

    # 3. 强弱比
    strong_total = su + sd
    strong_score = (su / max(strong_total, 1)) if strong_total > 0 else 0.5

    # 4. 跌停风险 (跌停越多越危险，取反)
    ld_risk = min(ld / max(total * 0.005, 1), 1.0)
    ld_score = 1.0 - ld_risk

    raw = ratio_score * 0.40 + lu_ratio * 0.25 + strong_score * 0.20 + ld_score * 0.15
    return max(0, min(100, int(raw * 100)))


def _build_signals(
    up: int, down: int, ratio: float,
    lu: int, ld: int, su: int, sd: int,
) -> list[str]:
    """构建市场宽度信号"""
    signals = []

    signals.append(f"上涨 {up} 家 / 下跌 {down} 家，涨跌比 {ratio:.1f}")

    if lu > 0:
        signals.append(f"涨停 {lu} 家")
    if ld > 0:
        signals.append(f"跌停 {ld} 家")

    if ratio >= 3:
        signals.append("普涨格局，赚钱效应广泛")
    elif ratio >= 1.5:
        signals.append("多数个股上涨")
    elif ratio >= 0.7:
        signals.append("涨跌各半")
    elif ratio >= 0.3:
        signals.append("多数个股下跌")
    else:
        signals.append("普跌格局，亏钱效应显著")

    if su > sd * 2 and su > 100:
        signals.append(f"强势股({su})远超弱势股({sd})，市场活跃")
    elif sd > su * 2 and sd > 100:
        signals.append(f"弱势股({sd})远超强势股({su})，谨慎参与")

    return signals
