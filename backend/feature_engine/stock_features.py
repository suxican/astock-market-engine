"""个股特征 — 一次计算，所有 Agent 共享

MainCapitalAgent / ExpectationGapAgent / LimitUpAgent 不再各自
重复计算均线/量比/累计涨幅/资金流向，统一由此模块输出。
"""
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backend.services import (
    get_market_overview,
    get_stock_daily,
    get_stock_fund_flow,
    get_stock_fund_flow_history,
    get_stock_name,
)


@dataclass
class StockFeatures:
    """单只股票的结构化特征"""

    symbol: str
    name: str

    # 最新行情
    close: float = 0.0
    pct_change: float = 0.0
    volume: float = 0.0
    turnover: float = 0.0
    high: float = 0.0
    low: float = 0.0
    amplitude: float = 0.0  # (high - low) / close

    # 均线
    ma_5: float = 0.0
    ma_10: float = 0.0
    ma_20: float = 0.0
    ma_60: float = 0.0
    ma_alignment: str = "unknown"  # bull/bear/mixed
    avg_vol_20: float = 0.0
    range_high_60d: float = 0.0  # 60 日最高价

    # 量价比率
    price_ratio_vs_ma60: float = 1.0  # close / ma_60
    vol_ratio_vs_avg20: float = 1.0   # volume / avg_vol_20

    # 累计涨幅
    cum_gain_20d: float | None = None
    cum_gain_60d: float | None = None

    # 资金流向
    main_flow: float = 0.0   # 主力净流入（万元）
    large_order_flow: float = 0.0  # 大单净流入（万元）
    small_order_flow: float = 0.0  # 小单净流入（万元）
    main_flow_3d: float = 0.0
    main_flow_5d: float = 0.0
    main_flow_10d: float = 0.0
    main_flow_positive_days_5d: int = 0

    # 形态特征
    has_lower_shadow: bool = False  # 有下影线
    long_upper_shadow_days_5d: int = 0
    long_lower_shadow_days_5d: int = 0
    pullback_10d: float = 0.0  # 近 10 日最大回撤，负数
    breakout_failed: bool = False
    volume_price_divergence: bool = False
    relative_strength_vs_index_1d: float = 0.0

    # K 线数据（供图表渲染，不重复拉取）
    kline_records: list[dict[str, Any]] = field(default_factory=list, repr=False)

    @classmethod
    def compute(cls, symbol: str) -> "StockFeatures":
        """从 services 层拉取全部个股特征，一次组装"""
        df = get_stock_daily(symbol)
        name = get_stock_name(symbol)
        fund_flow = get_stock_fund_flow(symbol)
        fund_flow_hist = get_stock_fund_flow_history(symbol, days=20)

        if df.empty:
            return cls(symbol=symbol, name=name)

        latest = df.iloc[-1]
        recent_60 = df.tail(60)

        close = float(latest["close"])
        pct = float(latest["pct_change"])
        vol = float(latest["volume"])
        turnover = float(latest["turnover"])
        high = float(latest["high"])
        low = float(latest["low"])

        # 均线
        ma_5 = float(recent_60["close"].rolling(5).mean().iloc[-1]) if len(recent_60) >= 5 else float(recent_60["close"].mean())
        ma_10 = float(recent_60["close"].rolling(10).mean().iloc[-1]) if len(recent_60) >= 10 else float(recent_60["close"].mean())
        ma_20 = float(recent_60["close"].rolling(20).mean().iloc[-1]) if len(recent_60) >= 20 else float(recent_60["close"].mean())
        ma_60 = float(recent_60["close"].mean())
        avg_vol_20 = float(recent_60["volume"].tail(20).mean()) if len(recent_60) >= 20 else vol
        range_high = float(recent_60["high"].max())
        if ma_5 > ma_10 > ma_20:
            ma_alignment = "bull"
        elif ma_5 < ma_10 < ma_20:
            ma_alignment = "bear"
        else:
            ma_alignment = "mixed"

        # 量价比率
        price_ratio = close / ma_60 if ma_60 > 0 else 1.0
        vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

        # 振幅
        amplitude = (high - low) / close * 100 if close > 0 else 0.0

        # 累计涨幅
        cum_60d: float | None = None
        cum_20d: float | None = None
        if len(df) >= 2:
            cum_60d = _calc_cum_gain(df, 60)
            cum_20d = _calc_cum_gain(df, 20)

        # 下影线
        has_shadow = pct > 0 and (high - close) < (close - low)
        long_upper_days, long_lower_days = _count_shadow_days(recent_60.tail(5))
        pullback_10d = _calc_max_drawdown(recent_60.tail(10))
        breakout_failed = _detect_breakout_failed(recent_60)
        volume_price_divergence = vol_ratio > 1.5 and pct < 1

        # 资金流向
        main_flow = float(fund_flow.get("主力净流入", 0)) if fund_flow else 0.0
        large_flow = float(fund_flow.get("大单净流入", 0)) if fund_flow else 0.0
        small_flow = float(fund_flow.get("小单净流入", 0)) if fund_flow else 0.0
        flow_3d, flow_5d, flow_10d, positive_5d = _calc_flow_window_stats(fund_flow_hist, main_flow)

        # 相对指数强弱：目前使用当日大盘概况做轻量基准。
        try:
            overview = get_market_overview()
            index_pct = float(overview.get("涨跌幅", 0)) if overview else 0.0
        except Exception:
            index_pct = 0.0
        relative_strength = pct - index_pct

        return cls(
            symbol=symbol,
            name=name,
            close=close,
            pct_change=pct,
            volume=vol,
            turnover=turnover,
            high=high,
            low=low,
            amplitude=round(amplitude, 2),
            ma_5=round(ma_5, 2),
            ma_10=round(ma_10, 2),
            ma_20=round(ma_20, 2),
            ma_60=round(ma_60, 2),
            ma_alignment=ma_alignment,
            avg_vol_20=round(avg_vol_20, 0),
            range_high_60d=round(range_high, 2),
            price_ratio_vs_ma60=round(price_ratio, 3),
            vol_ratio_vs_avg20=round(vol_ratio, 3),
            cum_gain_20d=round(cum_20d, 2) if cum_20d is not None else None,
            cum_gain_60d=round(cum_60d, 2) if cum_60d is not None else None,
            main_flow=round(main_flow, 2),
            large_order_flow=round(large_flow, 2),
            small_order_flow=round(small_flow, 2),
            main_flow_3d=round(flow_3d, 2),
            main_flow_5d=round(flow_5d, 2),
            main_flow_10d=round(flow_10d, 2),
            main_flow_positive_days_5d=positive_5d,
            has_lower_shadow=has_shadow,
            long_upper_shadow_days_5d=long_upper_days,
            long_lower_shadow_days_5d=long_lower_days,
            pullback_10d=round(pullback_10d, 2),
            breakout_failed=breakout_failed,
            volume_price_divergence=volume_price_divergence,
            relative_strength_vs_index_1d=round(relative_strength, 2),
            kline_records=recent_60.to_dict(orient="records"),
        )

    def to_dict(self) -> dict[str, Any]:
        """转为 dict（不含 K 线数据，减少序列化体积）"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "close": self.close,
            "pct_change": self.pct_change,
            "volume": self.volume,
            "turnover": self.turnover,
            "high": self.high,
            "low": self.low,
            "amplitude": self.amplitude,
            "ma_5": self.ma_5,
            "ma_10": self.ma_10,
            "ma_20": self.ma_20,
            "ma_60": self.ma_60,
            "ma_alignment": self.ma_alignment,
            "avg_vol_20": self.avg_vol_20,
            "range_high_60d": self.range_high_60d,
            "price_ratio_vs_ma60": self.price_ratio_vs_ma60,
            "vol_ratio_vs_avg20": self.vol_ratio_vs_avg20,
            "cum_gain_20d": self.cum_gain_20d,
            "cum_gain_60d": self.cum_gain_60d,
            "main_flow": self.main_flow,
            "large_order_flow": self.large_order_flow,
            "small_order_flow": self.small_order_flow,
            "main_flow_3d": self.main_flow_3d,
            "main_flow_5d": self.main_flow_5d,
            "main_flow_10d": self.main_flow_10d,
            "main_flow_positive_days_5d": self.main_flow_positive_days_5d,
            "has_lower_shadow": self.has_lower_shadow,
            "long_upper_shadow_days_5d": self.long_upper_shadow_days_5d,
            "long_lower_shadow_days_5d": self.long_lower_shadow_days_5d,
            "pullback_10d": self.pullback_10d,
            "breakout_failed": self.breakout_failed,
            "volume_price_divergence": self.volume_price_divergence,
            "relative_strength_vs_index_1d": self.relative_strength_vs_index_1d,
        }

    def to_agent_input(self) -> dict[str, Any]:
        """转为 MainCapitalAgent.analyze() 期望的 stock_data 字典格式

        保持与现有 Agent 接口的向后兼容。
        """
        return {
            "close": self.close,
            "ma_20": self.ma_20,
            "ma_60": self.ma_60,
            "volume": self.volume,
            "avg_volume_20": self.avg_vol_20,
            "turnover": self.turnover,
            "pct_change": self.pct_change,
            "high": self.high,
            "low": self.low,
            "range_high": self.range_high_60d,
        }

    def __repr__(self) -> str:
        return (
            f"StockFeatures({self.symbol} {self.name}, close={self.close}, "
            f"pct={self.pct_change:+.2f}%, price_ratio={self.price_ratio_vs_ma60:.2f}, "
            f"vol_ratio={self.vol_ratio_vs_avg20:.2f}, main_flow={self.main_flow:.0f})"
        )


def _calc_cum_gain(df: pd.DataFrame, days: int) -> float | None:
    """计算近 N 日累计涨跌幅"""
    recent = df.tail(min(days, len(df)))
    if len(recent) < 2:
        return None
    return (float(recent.iloc[-1]["close"]) / float(recent.iloc[0]["close"]) - 1) * 100


def _calc_flow_window_stats(flow_df: pd.DataFrame, fallback_main_flow: float) -> tuple[float, float, float, int]:
    """计算资金流 3/5/10 日连续性，失败时退化为单日值。"""
    if flow_df is None or flow_df.empty:
        positive_days = 1 if fallback_main_flow > 0 else 0
        return fallback_main_flow, fallback_main_flow, fallback_main_flow, positive_days

    col = "主力净流入-净额" if "主力净流入-净额" in flow_df.columns else "主力净流入"
    if col not in flow_df.columns:
        positive_days = 1 if fallback_main_flow > 0 else 0
        return fallback_main_flow, fallback_main_flow, fallback_main_flow, positive_days

    s = pd.to_numeric(flow_df[col], errors="coerce").fillna(0)
    return (
        float(s.tail(3).sum()),
        float(s.tail(5).sum()),
        float(s.tail(10).sum()),
        int((s.tail(5) > 0).sum()),
    )


def _count_shadow_days(df: pd.DataFrame) -> tuple[int, int]:
    """统计近几日长上影/长下影天数。"""
    upper = 0
    lower = 0
    for _, row in df.iterrows():
        close = float(row.get("close", 0))
        open_ = float(row.get("open", close))
        high = float(row.get("high", close))
        low = float(row.get("low", close))
        if close <= 0:
            continue
        body_top = max(open_, close)
        body_bottom = min(open_, close)
        if (high - body_top) / close > 0.025:
            upper += 1
        if (body_bottom - low) / close > 0.025:
            lower += 1
    return upper, lower


def _calc_max_drawdown(df: pd.DataFrame) -> float:
    """近窗口最大回撤，返回负百分比。"""
    if df.empty or "close" not in df.columns:
        return 0.0
    closes = pd.to_numeric(df["close"], errors="coerce").dropna()
    if closes.empty:
        return 0.0
    running_high = closes.cummax()
    drawdown = closes / running_high - 1
    return float(drawdown.min() * 100)


def _detect_breakout_failed(df: pd.DataFrame) -> bool:
    """识别近期突破失败：盘中创新高后收回前高下方。"""
    if len(df) < 20:
        return False
    recent = df.tail(20)
    prev = recent.iloc[:-1]
    latest = recent.iloc[-1]
    prev_high = float(prev["high"].max())
    high = float(latest.get("high", 0))
    close = float(latest.get("close", 0))
    return high > prev_high and close < prev_high
