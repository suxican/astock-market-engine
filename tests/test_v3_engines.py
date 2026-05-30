"""V3 引擎单元测试 — 赚钱效应 / 情绪评分 / 龙头强度 / 市场健康分

所有测试使用构造的 MarketFeatures，不依赖远程数据源。
"""
import pandas as pd
import pytest

from backend.feature_engine.market_features import MarketFeatures


def _make_market_features(**kwargs) -> MarketFeatures:
    """构造测试用 MarketFeatures"""
    defaults = dict(
        limit_up_count=50,
        limit_down_count=5,
        zhaban_rate=0.15,
        max_board_height=7,
        top_boards=[
            {"symbol": "000001", "name": "龙头A", "boards": 7, "industry": "AI", "fengdan": 5.0, "turnover": 8.0},
            {"symbol": "000002", "name": "龙头B", "boards": 5, "industry": "AI", "fengdan": 3.0, "turnover": 6.0},
            {"symbol": "000003", "name": "龙头C", "boards": 4, "industry": "机器人", "fengdan": 2.0, "turnover": 10.0},
        ],
        index_name="上证指数",
        index_close=3200.0,
        index_pct_change=0.8,
        up_down_ratio=3.5,
        board_distribution={"AI": 15, "机器人": 10, "新能源": 8, "医药": 5},
        limit_up_pool=pd.DataFrame({
            "代码": ["000001", "000002", "000003", "000004", "000005"],
            "名称": ["龙头A", "龙头B", "龙头C", "跟风D", "跟风E"],
            "连板数": [7, 5, 4, 2, 2],
            "所属行业": ["AI", "AI", "机器人", "新能源", "医药"],
            "封板资金": [5.0, 3.0, 2.0, 0.5, 0.3],
            "涨跌幅": [10.0, 10.0, 10.0, 10.0, 10.0],
        }),
        limit_down_pool=pd.DataFrame({
            "代码": ["600001"],
            "名称": ["跌停A"],
            "涨跌幅": [-10.0],
        }),
        computed_at="2025-01-01 10:00:00",
    )
    defaults.update(kwargs)
    return MarketFeatures(**defaults)


# ══════════════════════════════════════════════
# 赚钱效应
# ══════════════════════════════════════════════

class TestEarningEffect:
    def test_basic(self):
        from backend.earning_effect_engine import compute_earning_effect
        mf = _make_market_features()
        result = compute_earning_effect(mf)
        assert 0 <= result.composite <= 100
        assert result.level in ("强", "中", "弱", "极弱")
        assert isinstance(result.signals, list)
        assert result.suggestion

    def test_strong_market(self):
        from backend.earning_effect_engine import compute_earning_effect
        mf = _make_market_features(
            limit_up_count=80,
            limit_down_count=2,
            zhaban_rate=0.05,
            max_board_height=10,
        )
        result = compute_earning_effect(mf)
        assert result.composite >= 60  # 强市场应得高分

    def test_weak_market(self):
        from backend.earning_effect_engine import compute_earning_effect
        # 构造一个真正的弱市场: 涨停少、跌停多、炸板率高、连板低
        weak_pool = pd.DataFrame({
            "代码": ["000001", "000002"],
            "名称": ["跟风A", "跟风B"],
            "连板数": [1, 1],
            "所属行业": ["AI", "医药"],
            "封板资金": [0.1, 0.1],
            "涨跌幅": [-2.0, -3.0],  # 昨日涨停今日下跌（亏钱效应）
        })
        mf = _make_market_features(
            limit_up_count=10,
            limit_down_count=30,
            zhaban_rate=0.6,
            max_board_height=2,
            top_boards=[
                {"symbol": "000001", "name": "跟风A", "boards": 2, "industry": "AI", "fengdan": 0.1, "turnover": 15.0},
            ],
            limit_up_pool=weak_pool,
        )
        result = compute_earning_effect(mf)
        assert result.composite <= 55  # 弱市场应得分偏低

    def test_to_dict(self):
        from backend.earning_effect_engine import compute_earning_effect
        mf = _make_market_features()
        result = compute_earning_effect(mf)
        d = result.to_dict()
        assert "composite" in d
        assert "premium_score" in d
        assert "survival_score" in d
        assert "signals" in d


# ══════════════════════════════════════════════
# 情绪评分
# ══════════════════════════════════════════════

class TestEmotionScores:
    def test_basic(self):
        from backend.score_engine.market_scores import compute_emotion_scores
        mf = _make_market_features()
        result = compute_emotion_scores(mf)
        assert 0 <= result.score <= 100
        assert result.stage in ("冰点期", "修复期", "主升期", "高潮期", "分歧期", "退潮期")
        assert result.confidence in ("高", "中", "低")

    def test_boiling_point(self):
        from backend.score_engine.market_scores import compute_emotion_scores
        mf = _make_market_features(
            limit_up_count=5,
            limit_down_count=20,
            zhaban_rate=0.7,
            max_board_height=1,
            up_down_ratio=0.3,
        )
        result = compute_emotion_scores(mf)
        assert result.stage in ("冰点期", "退潮期")

    def test_peak_stage(self):
        from backend.score_engine.market_scores import compute_emotion_scores
        mf = _make_market_features(
            limit_up_count=80,
            limit_down_count=2,
            zhaban_rate=0.08,
            max_board_height=10,
            up_down_ratio=15.0,
        )
        result = compute_emotion_scores(mf)
        assert result.stage in ("高潮期", "主升期")

    def test_has_signals(self):
        from backend.score_engine.market_scores import compute_emotion_scores
        mf = _make_market_features()
        result = compute_emotion_scores(mf)
        assert len(result.signals) > 0

    def test_has_suggestion(self):
        from backend.score_engine.market_scores import compute_emotion_scores
        mf = _make_market_features()
        result = compute_emotion_scores(mf)
        assert result.suggestion


# ══════════════════════════════════════════════
# 龙头强度
# ══════════════════════════════════════════════

class TestDragonIntensity:
    def test_basic(self):
        from backend.score_engine.market_scores import compute_dragon_intensity
        mf = _make_market_features()
        result = compute_dragon_intensity(mf)
        assert 0 <= result.score <= 100
        assert result.high_board_count >= 0

    def test_no_pool(self):
        from backend.score_engine.market_scores import compute_dragon_intensity
        mf = _make_market_features(limit_up_pool=pd.DataFrame())
        result = compute_dragon_intensity(mf)
        assert result.score == 0

    def test_strong_dragons(self):
        from backend.score_engine.market_scores import compute_dragon_intensity
        mf = _make_market_features()
        result = compute_dragon_intensity(mf)
        assert result.score > 0
        assert len(result.top_leaders) > 0


# ══════════════════════════════════════════════
# 风险评分
# ══════════════════════════════════════════════

class TestRiskScores:
    def test_basic(self):
        from backend.score_engine.market_scores import compute_risk_scores
        mf = _make_market_features()
        result = compute_risk_scores(mf, "主升期")
        assert 0 <= result.score <= 100
        assert result.level in ("低", "中", "高", "极高")

    def test_high_risk_peak(self):
        from backend.score_engine.market_scores import compute_risk_scores
        mf = _make_market_features()
        result = compute_risk_scores(mf, "高潮期")
        assert result.score >= 50  # 高潮期风险应偏高

    def test_low_risk_frost(self):
        from backend.score_engine.market_scores import compute_risk_scores
        mf = _make_market_features(limit_down_count=0, zhaban_rate=0.05)
        result = compute_risk_scores(mf, "冰点期")
        assert result.score <= 40  # 冰点期风险应偏低


# ══════════════════════════════════════════════
# 市场健康分
# ══════════════════════════════════════════════

class TestMarketHealth:
    def test_basic(self):
        from backend.score_engine import compute_market_health
        mf = _make_market_features()
        result = compute_market_health(mf)
        assert 0 <= result.composite <= 100
        assert result.level in ("极强", "偏强", "中性", "偏弱", "极弱")
        assert result.confidence in ("高", "中", "低")
        assert result.explain_summary

    def test_with_event(self):
        from backend.score_engine import compute_market_health
        from backend.score_engine.market_health import EventScores
        mf = _make_market_features()
        event = EventScores(event_score=80, sentiment_score=70, policy_score=60)
        result = compute_market_health(mf, include_event=True, event_result=event)
        assert 0 <= result.composite <= 100

    def test_to_dict(self):
        from backend.score_engine import compute_market_health
        mf = _make_market_features()
        result = compute_market_health(mf)
        d = result.to_dict()
        assert "composite" in d
        assert "emotion" in d
        assert "earning_effect" in d
        assert "weights" in d

    def test_strong_market_high_score(self):
        from backend.score_engine import compute_market_health
        # 高潮期风险高，所以 composite 不一定很高
        # 使用主升期参数 (更平衡)
        mf = _make_market_features(
            limit_up_count=60,
            limit_down_count=5,
            zhaban_rate=0.15,
            max_board_height=8,
            up_down_ratio=6.0,
            index_pct_change=1.5,
        )
        result = compute_market_health(mf)
        assert result.composite >= 55  # 主升市场应得较高分

    def test_weak_market_low_score(self):
        from backend.score_engine import compute_market_health
        mf = _make_market_features(
            limit_up_count=10,
            limit_down_count=40,
            zhaban_rate=0.7,
            max_board_height=2,
            up_down_ratio=0.3,
            index_pct_change=-3.0,
            board_distribution={"AI": 3, "医药": 2},
            top_boards=[
                {"symbol": "000001", "name": "跟风A", "boards": 2, "industry": "AI", "fengdan": 0.1, "turnover": 15.0},
            ],
        )
        result = compute_market_health(mf)
        assert result.composite <= 45  # 弱市场应得低分


# ══════════════════════════════════════════════
# 主线评分
# ══════════════════════════════════════════════

class TestThemeScores:
    def test_basic(self):
        from backend.score_engine.theme_scores import compute_theme_scores
        mf = _make_market_features()
        result = compute_theme_scores(mf)
        assert len(result.themes) > 0
        assert result.main_line
        assert result.main_line_score > 0

    def test_themes_sorted(self):
        from backend.score_engine.theme_scores import compute_theme_scores
        mf = _make_market_features()
        result = compute_theme_scores(mf)
        scores = [t.composite for t in result.themes]
        assert scores == sorted(scores, reverse=True)

    def test_has_levels(self):
        from backend.score_engine.theme_scores import compute_theme_scores
        mf = _make_market_features()
        result = compute_theme_scores(mf)
        for t in result.themes:
            assert t.level in ("主线", "支线", "活跃", "弱势")

    def test_to_dict(self):
        from backend.score_engine.theme_scores import compute_theme_scores
        mf = _make_market_features()
        result = compute_theme_scores(mf)
        d = result.to_dict()
        assert "themes" in d
        assert "main_line" in d
        assert "signals" in d

    def test_no_distribution(self):
        from backend.score_engine.theme_scores import compute_theme_scores
        mf = _make_market_features(board_distribution={})
        result = compute_theme_scores(mf)
        assert len(result.themes) == 0


# ══════════════════════════════════════════════
# 市场宽度
# ══════════════════════════════════════════════

class TestMarketBreadth:
    def test_breadth_from_spot(self):
        """测试市场宽度计算（使用 mock spot 数据）"""
        from backend.services.market_breadth import MarketBreadth, _calc_breadth_score

        # 强市场
        score = _calc_breadth_score(
            up=3000, down=500, lu=80, ld=5, su=500, sd=50, total=4000
        )
        assert score >= 60

        # 弱市场
        score = _calc_breadth_score(
            up=500, down=3000, lu=10, ld=60, su=50, sd=500, total=4000
        )
        assert score <= 40

    def test_breadth_signals(self):
        from backend.services.market_breadth import _build_signals
        signals = _build_signals(
            up=3000, down=500, ratio=6.0, lu=80, ld=5, su=500, sd=50
        )
        assert len(signals) > 0
        assert any("普涨" in s or "上涨" in s for s in signals)


# ══════════════════════════════════════════════
# 评分工具函数
# ══════════════════════════════════════════════

class TestScoreUtils:
    def test_range_score(self):
        from backend.score_engine.score_utils import range_score
        # 在区间内
        assert range_score(5, (0, 10)) == 1.0
        # 区间外
        assert range_score(20, (0, 10)) < 1.0
        assert range_score(-5, (0, 10)) < 1.0

    def test_to_int_score(self):
        from backend.score_engine.score_utils import to_int_score
        assert to_int_score(0.0) == 0
        assert to_int_score(1.0) == 100
        assert to_int_score(0.5) == 50
        assert to_int_score(1.5) == 100  # 上限
        assert to_int_score(-0.5) == 0   # 下限

    def test_confidence_label(self):
        from backend.score_engine.score_utils import confidence_label
        assert confidence_label(0.9) == "高"
        assert confidence_label(0.6) == "中"
        assert confidence_label(0.3) == "低"

    def test_weighted_sum(self):
        from backend.score_engine.score_utils import weighted_sum
        dims = {"a": 0.8, "b": 0.6}
        weights = {"a": 0.6, "b": 0.4}
        result = weighted_sum(dims, weights)
        assert 0.6 < result < 0.8

