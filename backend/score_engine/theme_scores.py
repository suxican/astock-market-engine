"""主线识别引擎 — 板块/主题评分

基于职业短线交易体系的主线识别规则:
  板块涨停数 (40%) + 资金流入 (25%) + 龙头高度 (25%) + 板块集中度 (10%)

输入: MarketFeatures + 板块资金流向
输出: list[ThemeScore] — 按综合分排序的主题列表

纯规则计算，不调用 LLM。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from backend.feature_engine.market_features import MarketFeatures

logger = logging.getLogger("market_engine.theme_score")


@dataclass
class ThemeScore:
    """单个主题/板块评分"""
    name: str               # 板块名称
    limit_up_count: int = 0 # 板块内涨停数
    fund_flow: float = 0.0  # 今日资金净流入 (亿)
    dragon_boards: int = 0  # 板块内最高连板数
    concentration: float = 0.0  # 板块涨停集中度 (板块涨停数/总涨停数)

    composite: int = 0      # 综合评分 0-100
    level: str = ""         # 主线/支线/弱势

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "limit_up_count": self.limit_up_count,
            "fund_flow": round(self.fund_flow, 2),
            "dragon_boards": self.dragon_boards,
            "concentration": round(self.concentration, 3),
            "composite": self.composite,
            "level": self.level,
        }


@dataclass
class ThemeScoresResult:
    """主线识别结果"""
    themes: list[ThemeScore] = field(default_factory=list)
    main_line: str = ""     # 主线名称
    main_line_score: int = 0
    signals: list[str] = field(default_factory=list)
    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "themes": [t.to_dict() for t in self.themes[:15]],
            "main_line": self.main_line,
            "main_line_score": self.main_line_score,
            "signals": self.signals,
            "computed_at": self.computed_at,
        }


def compute_theme_scores(mf: MarketFeatures) -> ThemeScoresResult:
    """计算板块/主题评分

    Args:
        mf: 盘面特征快照 (包含涨停分布和连板信息)

    Returns:
        ThemeScoresResult: 按综合分排序的主题列表
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 板块涨停分布
    dist = mf.board_distribution
    if not dist:
        return ThemeScoresResult(
            signals=["暂无板块涨停数据"],
            computed_at=now,
        )

    total_limit_up = mf.limit_up_count or 1

    # 获取板块资金流向
    flow_map = _get_sector_flow_map()

    # 计算每个板块内最高连板数
    dragon_map = _calc_sector_dragon_height(mf)

    # 计算每个板块评分
    themes: list[ThemeScore] = []
    for sector, lu_count in dist.items():
        # 资金流入 (亿)
        flow = flow_map.get(sector, 0.0)
        # 龙头高度
        dragon_h = dragon_map.get(sector, 0)
        # 集中度
        concentration = lu_count / total_limit_up

        # 综合评分
        composite = _calc_theme_score(lu_count, total_limit_up, flow, dragon_h, concentration)

        # 等级
        if composite >= 75:
            level = "主线"
        elif composite >= 50:
            level = "支线"
        elif composite >= 30:
            level = "活跃"
        else:
            level = "弱势"

        themes.append(ThemeScore(
            name=sector,
            limit_up_count=lu_count,
            fund_flow=flow,
            dragon_boards=dragon_h,
            concentration=concentration,
            composite=composite,
            level=level,
        ))

    # 按综合分排序
    themes.sort(key=lambda t: t.composite, reverse=True)

    # 主线
    main_line = themes[0].name if themes else ""
    main_line_score = themes[0].composite if themes else 0

    # 信号
    signals = _build_signals(themes, total_limit_up)

    return ThemeScoresResult(
        themes=themes,
        main_line=main_line,
        main_line_score=main_line_score,
        signals=signals,
        computed_at=now,
    )


def _get_sector_flow_map() -> dict[str, float]:
    """获取板块资金流向映射 (板块名 → 净流入亿)"""
    try:
        from backend.services.flow_data import get_sector_fund_flow
        df = get_sector_fund_flow()
        if df is None or df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            name = str(row.get("名称", ""))
            # 净流入金额可能以不同单位存储
            flow = 0.0
            for col in ["主力净流入-净额", "今日主力净流入-净额"]:
                if col in df.columns:
                    try:
                        flow = float(row[col]) / 1e8  # 转亿
                    except (ValueError, TypeError):
                        pass
                    break
            if name:
                result[name] = flow
        return result
    except Exception as e:
        logger.debug("获取板块资金流向失败: %s", e)
        return {}


def _calc_sector_dragon_height(mf: MarketFeatures) -> dict[str, int]:
    """计算板块内最高连板数"""
    result: dict[str, int] = {}
    if mf.limit_up_pool is None or mf.limit_up_pool.empty:
        return result

    pool = mf.limit_up_pool
    if "所属行业" not in pool.columns or "连板数" not in pool.columns:
        return result

    try:
        boards = pd.to_numeric(pool["连板数"], errors="coerce").fillna(0)
        for idx, row in pool.iterrows():
            sector = str(row.get("所属行业", ""))
            if sector and sector != "nan":
                board_h = int(float(boards.get(idx, 0)))
                result[sector] = max(result.get(sector, 0), board_h)
    except Exception as e:
        logger.debug("计算板块龙头高度失败: %s", e)

    return result


def _calc_theme_score(
    lu_count: int,
    total_lu: int,
    fund_flow: float,
    dragon_h: int,
    concentration: float,
) -> int:
    """板块综合评分

    权重:
      - 涨停数量 40% (绝对数和占比)
      - 资金流入 25% (主力净流入)
      - 龙头高度 25% (板块内最高连板)
      - 集中度   10% (涨停占比)
    """
    # 1. 涨停数量分 (5个涨停=1.0, 10个=满分)
    lu_score = min(1.0, lu_count / 10)

    # 2. 资金流入分 (5亿=1.0, -5亿=0)
    flow_score = max(0.0, min(1.0, (fund_flow + 5) / 10))

    # 3. 龙头高度分 (5板=1.0, 10板=满分)
    dragon_score = min(1.0, dragon_h / 8)

    # 4. 集中度分 (20%占比=1.0)
    conc_score = min(1.0, concentration / 0.20)

    raw = lu_score * 0.40 + flow_score * 0.25 + dragon_score * 0.25 + conc_score * 0.10
    return max(0, min(100, int(raw * 100)))


def _build_signals(themes: list[ThemeScore], total_lu: int) -> list[str]:
    """构建主线信号"""
    signals = []

    main_lines = [t for t in themes if t.level == "主线"]
    branches = [t for t in themes if t.level == "支线"]

    if main_lines:
        names = ", ".join(t.name for t in main_lines[:3])
        signals.append(f"主线方向: {names}")
        for t in main_lines[:3]:
            parts = [f"{t.limit_up_count}个涨停"]
            if t.dragon_boards > 0:
                parts.append(f"最高{t.dragon_boards}板")
            if t.fund_flow > 0:
                parts.append(f"净流入{t.fund_flow:.1f}亿")
            signals.append(f"  {t.name}: {', '.join(parts)}")
    else:
        signals.append("无明确主线，市场热点分散")

    if branches:
        names = ", ".join(t.name for t in branches[:3])
        signals.append(f"支线方向: {names}")

    return signals
