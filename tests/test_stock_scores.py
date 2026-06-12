"""个股主力行为评分测试 — 使用构造特征，不依赖远程数据源。"""

from backend.feature_engine.stock_features import StockFeatures
from backend.score_engine.stock_scores import compute_stock_scores


def _sf(**kwargs) -> StockFeatures:
    defaults = dict(
        symbol="000001",
        name="测试股票",
        close=10.0,
        pct_change=1.0,
        volume=1000000,
        turnover=3.0,
        high=10.3,
        low=9.8,
        ma_5=10.2,
        ma_10=10.0,
        ma_20=9.8,
        ma_60=9.3,
        ma_alignment="bull",
        avg_vol_20=700000,
        price_ratio_vs_ma60=1.075,
        vol_ratio_vs_avg20=1.45,
        cum_gain_20d=12.0,
        cum_gain_60d=18.0,
        main_flow=1500,
        main_flow_3d=4500,
        main_flow_5d=9000,
        main_flow_10d=13000,
        main_flow_positive_days_5d=4,
        relative_strength_vs_index_1d=1.8,
    )
    defaults.update(kwargs)
    return StockFeatures(**defaults)


def test_markup_requires_continuity_and_scores_high():
    scores = compute_stock_scores(_sf(pct_change=3.2, vol_ratio_vs_avg20=1.8, turnover=4.5))

    assert scores.main_capital.stage == "主升"
    assert scores.main_capital.score >= 70
    assert scores.main_capital.confidence in ("中", "高")
    assert "fund_flow" in scores.main_capital.evidence


def test_distribution_risk_overrides_high_position_markup():
    scores = compute_stock_scores(_sf(
        pct_change=-1.5,
        turnover=8.0,
        price_ratio_vs_ma60=1.35,
        vol_ratio_vs_avg20=1.9,
        cum_gain_60d=58.0,
        main_flow=-3000,
        main_flow_5d=-12000,
        main_flow_positive_days_5d=1,
        long_upper_shadow_days_5d=3,
        breakout_failed=True,
    ))

    assert scores.main_capital.stage == "出货"
    assert scores.main_capital.score <= 45
    assert len(scores.main_capital.risk_flags) >= 2


def test_weak_downtrend_accumulation_is_not_overrated():
    scores = compute_stock_scores(_sf(
        pct_change=0.4,
        turnover=1.2,
        price_ratio_vs_ma60=0.86,
        vol_ratio_vs_avg20=0.7,
        cum_gain_20d=-8.0,
        cum_gain_60d=-18.0,
        ma_5=8.6,
        ma_10=8.8,
        ma_20=9.0,
        ma_60=10.0,
        ma_alignment="bear",
        main_flow=300,
        main_flow_5d=500,
        main_flow_positive_days_5d=2,
    ))

    assert scores.main_capital.stage in ("吸筹", "洗盘")
    assert scores.main_capital.score < 65
