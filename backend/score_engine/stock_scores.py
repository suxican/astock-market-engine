"""个股评分 — 主力行为 / 技术健康度 / 综合评分

规则直接提取自 MainCapitalAgent + StockAnalysisAgent，纯数值计算。
输入: StockFeatures
输出: StockScores (结构化 0-100 分数)
"""
from dataclasses import dataclass, field
from typing import Any

from backend.feature_engine.stock_features import StockFeatures

from .score_utils import confidence_label

# ── 主力四阶段规则（与 MainCapitalAgent 完全一致）──
_CAPITAL_MAX = {"吸筹": 6, "洗盘": 5.5, "主升": 7.5, "出货": 9}

# 阶段 → 基础交易价值。阶段不是买卖建议，最终会被匹配度和风险项修正。
_CAPITAL_SCORE_MAP = {"主升": 84, "洗盘": 68, "吸筹": 58, "出货": 18}

_CAPITAL_ADVICE = {
    "吸筹": "中线关注，可小仓跟随主力建仓，设好止损。",
    "洗盘": "持股耐心等待，洗盘结束后大概率继续上行。",
    "主升": "趋势良好可持有，但注意不要追高加仓。",
    "出货": "建议减仓或离场，保住利润为主。",
}


@dataclass
class MainCapitalScores:
    """主力行为评分"""
    score: int                      # 0-100（主升=90，出货=15）
    stage: str                      # 吸筹/洗盘/主升/出货
    confidence: str                 # 高/中/低
    all_stage_scores: dict[str, float] = field(default_factory=dict)
    factors: list[str] = field(default_factory=list)
    advice: str = ""
    risk_flags: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class TechnicalScores:
    """技术面评分"""
    score: int                      # 0-100
    trend_score: int                # 趋势分（均线位置）
    volume_score: int               # 量能分
    position_score: int             # 位置分
    factors: list[str] = field(default_factory=list)


@dataclass
class StockScores:
    """个股评分汇总"""
    symbol: str
    name: str
    main_capital: MainCapitalScores
    technical: TechnicalScores
    composite: int = 0              # 综合评分 0-100

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "main_capital": {
                "score": self.main_capital.score,
                "stage": self.main_capital.stage,
                "confidence": self.main_capital.confidence,
                "all_stage_scores": self.main_capital.all_stage_scores,
                "factors": self.main_capital.factors,
                "advice": self.main_capital.advice,
                "risk_flags": self.main_capital.risk_flags,
                "evidence": self.main_capital.evidence,
            },
            "technical": {
                "score": self.technical.score,
                "trend_score": self.technical.trend_score,
                "volume_score": self.technical.volume_score,
                "position_score": self.technical.position_score,
                "factors": self.technical.factors,
            },
            "composite": self.composite,
        }


def compute_capital_scores(sf: StockFeatures) -> MainCapitalScores:
    """主力行为评分 — 规则打底，侧重连续性、结构和风险扣分。"""
    pr = sf.price_ratio_vs_ma60
    vr = sf.vol_ratio_vs_avg20
    turnover = sf.turnover
    pct = sf.pct_change
    high = sf.high
    close = sf.close
    low = sf.low
    cum60 = sf.cum_gain_60d or 0
    cum20 = sf.cum_gain_20d or 0

    scores: dict[str, float] = {}
    all_factors: dict[str, list[str]] = {}

    # ── 吸筹：低位 + 温和量 + 资金连续性。低位弱势不直接给高交易分。 ──
    s = 0; r = []
    if pr < 0.9: s += 1; r.append("股价低于60日均价90%，处于低位")
    if vr < 1.2: s += 1; r.append("量能温和，未异常放量")
    if 1 <= turnover <= 3: s += 1; r.append(f"换手率{turnover:.1f}%，温和换手")
    if pct > 0 and (high - close) < (close - low): s += 1; r.append("收盘接近最高价，有下影线")
    if sf.main_flow_5d > 0 and sf.main_flow_positive_days_5d >= 3:
        s += 1.5; r.append(f"5日主力净流入{sf.main_flow_5d:.0f}万，且{sf.main_flow_positive_days_5d}天为正")
    elif sf.main_flow > 0:
        s += 0.5; r.append(f"单日主力净流入{sf.main_flow:.0f}万")
    if sf.long_lower_shadow_days_5d >= 2:
        s += 0.5; r.append(f"近5日出现{sf.long_lower_shadow_days_5d}次长下影，承接有所体现")
    scores["吸筹"] = s / _CAPITAL_MAX["吸筹"]
    all_factors["吸筹"] = r

    # ── 洗盘：强势趋势中的缩量回撤更有意义，单纯低迷不高估。 ──
    s = 0; r = []
    if 0.8 <= pr <= 0.95: s += 1; r.append("股价在近期高点下方10%-20%")
    if vr < 0.6: s += 1; r.append("成交量萎缩至20日均量60%以下")
    if abs(pct) < 2: s += 1; r.append("涨跌幅较小，无方向性大阴线")
    if turnover < 1.5: s += 1; r.append("换手率低于1.5%")
    if cum20 > 5 and sf.pullback_10d > -12:
        s += 1; r.append(f"近20日有涨幅且10日回撤{sf.pullback_10d:.1f}%，回撤受控")
    if sf.ma_alignment == "bull" and close >= sf.ma_20:
        s += 0.5; r.append("均线保持多头，洗盘更可能是趋势中继")
    scores["洗盘"] = s / _CAPITAL_MAX["洗盘"]
    all_factors["洗盘"] = r

    # ── 主升：趋势连续性 + 资金连续性 + 相对强度。 ──
    s = 0; r = []
    if pr >= 1.05: s += 1; r.append("股价站上60日均线")
    if sf.ma_alignment == "bull" and close > sf.ma_20:
        s += 1; r.append("MA5/MA10/MA20 多头排列，趋势连续性较好")
    if vr >= 1.5: s += 1; r.append("成交量高于20日均量150%")
    if pct > 0: s += 1; r.append("今日上涨")
    if turnover > 3: s += 1; r.append(f"换手率{turnover:.1f}%，交易活跃")
    if close > 0 and (high - low) / close < 0.06: s += 1; r.append("振幅适中，上涨稳健")
    if sf.main_flow_5d > 0 and sf.main_flow_positive_days_5d >= 3:
        s += 1; r.append(f"5日主力持续流入{sf.main_flow_5d:.0f}万")
    elif sf.main_flow > 0:
        s += 0.5; r.append(f"单日主力净流入{sf.main_flow:.0f}万")
    if sf.relative_strength_vs_index_1d > 1:
        s += 0.5; r.append(f"相对指数强{sf.relative_strength_vs_index_1d:.1f}个百分点")
    scores["主升"] = s / _CAPITAL_MAX["主升"]
    all_factors["主升"] = r

    # ── 出货：高位、放量滞涨、长上影、突破失败、连续流出。 ──
    s = 0; r = []
    if pr >= 1.3 or cum60 > 35: s += 1; r.append(f"近60日涨幅{cum60:.1f}%，处于高位")
    if vr > 1.5 and pct < 1: s += 1; r.append("放量滞涨，量价背离")
    if turnover > 5: s += 1; r.append(f"换手率{turnover:.1f}%>5%，筹码大量交换")
    if pct < -3: s += 1; r.append(f"跌幅{pct:.1f}%，有出货迹象")
    if sf.main_flow_5d < 0: s += 1; r.append(f"5日主力净流出{abs(sf.main_flow_5d):.0f}万")
    elif sf.main_flow < 0: s += 0.5; r.append(f"单日主力净流出{abs(sf.main_flow):.0f}万")
    if pct < 0 and sf.main_flow < -500: s += 1; r.append("下跌+主力大幅流出，出货特征明显")
    if sf.long_upper_shadow_days_5d >= 2:
        s += 1; r.append(f"近5日{sf.long_upper_shadow_days_5d}次长上影，抛压较重")
    if sf.breakout_failed:
        s += 1; r.append("盘中突破后收回，存在假突破/诱多风险")
    scores["出货"] = s / _CAPITAL_MAX["出货"]
    all_factors["出货"] = r

    # 取最高分阶段
    best_stage = max(scores, key=scores.get)
    best_score = scores[best_stage]
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    base = _CAPITAL_SCORE_MAP.get(best_stage, 30)

    risk_flags = _build_risk_flags(sf, best_stage)
    adjusted = base + int((best_score - 0.45) * 30)
    if best_stage == "吸筹" and sf.ma_alignment == "bear":
        adjusted -= 8
    if best_stage == "主升" and (cum60 > 50 or sf.long_upper_shadow_days_5d >= 2):
        adjusted -= 10
    if best_stage != "出货" and scores.get("出货", 0) >= 0.55:
        adjusted -= 12
    adjusted -= min(18, len(risk_flags) * 5)
    if best_stage == "主升" and not risk_flags:
        adjusted = min(adjusted, 92)
    elif best_stage in ("吸筹", "洗盘") and not risk_flags:
        adjusted = min(adjusted, 82)
    adjusted = min(100, max(0, adjusted))

    confidence_base = best_score
    if best_score - second_score < 0.12:
        confidence_base = min(confidence_base, 0.49)

    return MainCapitalScores(
        score=adjusted,
        stage=best_stage,
        confidence=confidence_label(confidence_base),
        all_stage_scores={k: round(v, 2) for k, v in scores.items()},
        factors=_build_factors(all_factors[best_stage], best_score, second_score),
        advice=_CAPITAL_ADVICE.get(best_stage, "观望为主，等待明确信号。"),
        risk_flags=risk_flags,
        evidence=_build_evidence(sf),
    )


def compute_technical_scores(sf: StockFeatures) -> TechnicalScores:
    """技术面评分"""
    factors: list[str] = []

    # ── 趋势分 (0-40) — 基于均线位置 ──
    trend = 20
    above_ma20 = sf.close > sf.ma_20 if sf.ma_20 else False
    above_ma60 = sf.close > sf.ma_60 if sf.ma_60 else False
    if sf.ma_alignment == "bull" and above_ma20 and above_ma60:
        trend = 38
        factors.append("MA5/MA10/MA20 多头排列，且股价站上主要均线")
    elif above_ma20 and above_ma60:
        trend = 32
        factors.append("股价站上 MA20/MA60，趋势偏强")
    elif sf.ma_alignment == "bear" and not above_ma20 and not above_ma60:
        trend = 10
        factors.append("均线空头排列且股价跌破主要均线，趋势偏弱")
    elif not above_ma20 and not above_ma60:
        trend = 14
        factors.append("股价跌破 MA20/MA60，趋势偏弱")
    else:
        trend = 22
        factors.append("股价在均线之间，方向不明")

    # ── 量能分 (0-30) ──
    vr = sf.vol_ratio_vs_avg20
    if 0.8 <= vr <= 1.5:
        volume = 25
        factors.append("成交量正常，未异常缩/放量")
    elif vr > 1.5:
        volume = 20
        factors.append(f"放量{vr:.1f}倍，关注放量方向")
    else:
        volume = 15
        factors.append(f"缩量至{vr:.1f}倍，交投清淡")

    # ── 位置分 (0-30) — 基于近期累计涨幅 ──
    cg = sf.cum_gain_60d
    if cg is None:
        position = 15
    elif cg > 50:
        position = 5
        factors.append(f"近60日涨幅{cg:.1f}%，处于高位区间，追高风险大")
    elif cg > 20:
        position = 15
        factors.append(f"近60日涨幅{cg:.1f}%，已有一定盈利盘")
    elif cg > 0:
        position = 25
        factors.append(f"近60日涨幅{cg:.1f}%，位置适中偏强")
    elif cg > -20:
        position = 20
        factors.append(f"近60日跌幅{cg:.1f}%，处于回调位")
    else:
        position = 10
        factors.append(f"近60日跌幅{cg:.1f}%，处于低位")

    # 资金流向修正
    flow_bonus = 0
    if sf.main_flow_5d > 10000:
        flow_bonus = 10
        factors.append(f"5日主力净流入{sf.main_flow_5d:.0f}万元，资金连续性较好")
    elif sf.main_flow > 5000:
        flow_bonus = 8
        factors.append(f"主力净流入{sf.main_flow:.0f}万元，资金看好")
    elif sf.main_flow_5d > 3000 or sf.main_flow > 1000:
        flow_bonus = 4
    elif sf.main_flow_5d < -10000:
        flow_bonus = -10
        factors.append(f"5日主力净流出{abs(sf.main_flow_5d):.0f}万元，资金连续离场")
    elif sf.main_flow < -5000:
        flow_bonus = -8
        factors.append(f"主力净流出{abs(sf.main_flow):.0f}万元，资金离场")
    elif sf.main_flow_5d < -3000 or sf.main_flow < -1000:
        flow_bonus = -4

    if sf.relative_strength_vs_index_1d > 2:
        flow_bonus += 3
        factors.append(f"相对指数强{sf.relative_strength_vs_index_1d:.1f}个百分点")
    elif sf.relative_strength_vs_index_1d < -2:
        flow_bonus -= 3
        factors.append(f"相对指数弱{abs(sf.relative_strength_vs_index_1d):.1f}个百分点")

    total = max(0, min(100, trend + volume + position + flow_bonus))

    return TechnicalScores(
        score=total,
        trend_score=trend,
        volume_score=volume,
        position_score=position,
        factors=factors,
    )


def compute_stock_scores(sf: StockFeatures) -> StockScores:
    """一次计算全部个股评分"""
    capital = compute_capital_scores(sf)
    technical = compute_technical_scores(sf)
    # 综合分: 主力行为 60% + 技术面 40%
    composite = min(100, max(0, round(capital.score * 0.6 + technical.score * 0.4)))
    return StockScores(
        symbol=sf.symbol,
        name=sf.name,
        main_capital=capital,
        technical=technical,
        composite=composite,
    )


def _build_factors(stage_factors: list[str], best_score: float, second_score: float) -> list[str]:
    factors = list(stage_factors) if stage_factors else ["信号不明确"]
    if best_score - second_score < 0.12:
        factors.append("多阶段信号接近，主力行为存在分歧，需等待确认")
    return factors


def _build_risk_flags(sf: StockFeatures, stage: str) -> list[str]:
    flags: list[str] = []
    cum60 = sf.cum_gain_60d or 0
    if cum60 > 50:
        flags.append(f"近60日涨幅{cum60:.1f}%，高位追涨风险较大")
    if sf.long_upper_shadow_days_5d >= 2:
        flags.append(f"近5日{sf.long_upper_shadow_days_5d}次长上影，抛压偏重")
    if sf.main_flow_5d < 0 and stage != "出货":
        flags.append(f"5日主力净流出{abs(sf.main_flow_5d):.0f}万，与{stage}判断存在冲突")
    if sf.breakout_failed:
        flags.append("近期出现突破失败，需警惕假突破")
    if sf.volume_price_divergence:
        flags.append("放量但涨幅不足，量价配合一般")
    if sf.relative_strength_vs_index_1d < -2:
        flags.append(f"相对指数弱{abs(sf.relative_strength_vs_index_1d):.1f}个百分点")
    return flags


def _build_evidence(sf: StockFeatures) -> dict[str, Any]:
    """供 AI 解释层和前端复核的结构化证据。"""
    return {
        "trend": {
            "ma_alignment": sf.ma_alignment,
            "ma_5": sf.ma_5,
            "ma_10": sf.ma_10,
            "ma_20": sf.ma_20,
            "ma_60": sf.ma_60,
            "price_ratio_vs_ma60": sf.price_ratio_vs_ma60,
            "pullback_10d": sf.pullback_10d,
        },
        "fund_flow": {
            "main_flow_1d": sf.main_flow,
            "main_flow_3d": sf.main_flow_3d,
            "main_flow_5d": sf.main_flow_5d,
            "main_flow_10d": sf.main_flow_10d,
            "positive_days_5d": sf.main_flow_positive_days_5d,
        },
        "price_action": {
            "pct_change": sf.pct_change,
            "vol_ratio_vs_avg20": sf.vol_ratio_vs_avg20,
            "turnover": sf.turnover,
            "long_upper_shadow_days_5d": sf.long_upper_shadow_days_5d,
            "long_lower_shadow_days_5d": sf.long_lower_shadow_days_5d,
            "breakout_failed": sf.breakout_failed,
            "volume_price_divergence": sf.volume_price_divergence,
        },
        "relative_strength": {
            "vs_index_1d": sf.relative_strength_vs_index_1d,
        },
    }
