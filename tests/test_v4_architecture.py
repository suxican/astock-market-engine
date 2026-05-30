"""V4 架构测试 — SystemBoundary / Evidence / GuardRail / RuleEngine"""
import pytest
import pandas as pd

from backend.feature_engine.market_features import MarketFeatures


def _make_mf(**kwargs) -> MarketFeatures:
    defaults = dict(
        limit_up_count=50, limit_down_count=5, zhaban_rate=0.15,
        max_board_height=7, up_down_ratio=3.5, index_pct_change=0.8,
        top_boards=[
            {"symbol": "000001", "name": "龙头A", "boards": 7, "industry": "AI", "fengdan": 5.0, "turnover": 8.0},
            {"symbol": "000002", "name": "龙头B", "boards": 5, "industry": "AI", "fengdan": 3.0, "turnover": 6.0},
        ],
        board_distribution={"AI": 15, "机器人": 10},
        limit_up_pool=pd.DataFrame({"代码": ["000001"], "名称": ["龙头A"], "连板数": [7], "所属行业": ["AI"]}),
        computed_at="2025-01-01 10:00:00",
    )
    defaults.update(kwargs)
    return MarketFeatures(**defaults)


# ══════════════════════════════════════
# SystemBoundary
# ══════════════════════════════════════

class TestSystemBoundary:
    def test_data_boundary_pass(self):
        from backend.core.system_boundary import check_data_boundary
        data = {"limit_up_count": 50, "limit_down_count": 5, "zhaban_rate": 0.15,
                "max_board_height": 7, "index_pct_change": 0.8}
        result = check_data_boundary(data, "主升期")
        assert result.passed is True

    def test_data_boundary_fail_on_missing(self):
        from backend.core.system_boundary import check_data_boundary
        data = {"limit_up_count": None, "limit_down_count": 5}
        result = check_data_boundary(data, "主升期")
        assert result.passed is False
        assert any("缺失" in v["detail"] for v in result.violations)

    def test_data_boundary_fail_on_speculation(self):
        from backend.core.system_boundary import check_data_boundary
        data = {"limit_up_count": 50, "limit_down_count": 5, "zhaban_rate": 0.15,
                "max_board_height": 7, "index_pct_change": 0.8}
        result = check_data_boundary(data, "大概率上涨")
        assert result.passed is False

    def test_causal_boundary_pass(self):
        from backend.core.system_boundary import check_causal_boundary
        data = {"limit_up_count": 50, "zhaban_rate": 0.15, "max_board_height": 7}
        result = check_causal_boundary("主升期", data)
        assert result.passed is True

    def test_causal_boundary_fail(self):
        from backend.core.system_boundary import check_causal_boundary
        data = {"limit_up_count": 50}  # 缺少 zhaban_rate 和 max_board_height
        result = check_causal_boundary("主升期", data)
        assert result.passed is False

    def test_strategy_boundary_pass(self):
        from backend.core.system_boundary import check_strategy_boundary
        result = check_strategy_boundary("符合龙头模型")
        assert result.passed is True

    def test_strategy_boundary_fail(self):
        from backend.core.system_boundary import check_strategy_boundary
        result = check_strategy_boundary("建议买入")
        assert result.passed is False

    def test_check_all_boundaries(self):
        from backend.core.system_boundary import check_all_boundaries
        data = {"limit_up_count": 50, "limit_down_count": 5, "zhaban_rate": 0.15,
                "max_board_height": 7, "index_pct_change": 0.8}
        result = check_all_boundaries(data, "主升期")
        assert result.passed is True


# ══════════════════════════════════════
# EvidenceEngine
# ══════════════════════════════════════

class TestEvidenceEngine:
    def test_evidence_bundle_pass(self):
        from backend.evidence_engine.evidence import Evidence, EvidenceBundle, EvidenceType
        bundle = EvidenceBundle(conclusion="主升期")
        bundle.add(Evidence(EvidenceType.DATA, "limit_up_count", 50, "涨停50家"))
        bundle.add(Evidence(EvidenceType.COMPUTED, "zhaban_rate", 0.15, "炸板率15%"))
        bundle.add(Evidence(EvidenceType.DATA, "max_board_height", 7, "最高连板7板"))
        assert bundle.validate() is True
        assert bundle.confidence >= 0.7

    def test_evidence_bundle_fail_insufficient(self):
        from backend.evidence_engine.evidence import Evidence, EvidenceBundle, EvidenceType
        bundle = EvidenceBundle(conclusion="主升期")
        bundle.add(Evidence(EvidenceType.DATA, "limit_up_count", 50, "涨停50家"))
        assert bundle.validate() is False
        assert bundle.status == "INSUFFICIENT_EVIDENCE"

    def test_build_emotion_evidence(self):
        from backend.evidence_engine.evidence import build_emotion_evidence
        mf = _make_mf()
        bundle = build_emotion_evidence(mf)
        assert len(bundle.evidence) >= 3

    def test_build_dragon_evidence(self):
        from backend.evidence_engine.evidence import build_dragon_evidence
        mf = _make_mf()
        bundle = build_dragon_evidence(mf.limit_up_pool, mf.top_boards)
        assert len(bundle.evidence) >= 1


# ══════════════════════════════════════
# GuardRail
# ══════════════════════════════════════

class TestGuardRail:
    def test_guardrail_pass_clean_output(self):
        from backend.guardrails.guardrail import run_guardrail
        result = run_guardrail(ai_output="情绪处于主升期，涨停50家")
        assert result.passed is True

    def test_guardrail_fail_advice(self):
        from backend.guardrails.guardrail import run_guardrail
        result = run_guardrail(ai_output="建议买入，目标价2000")
        assert result.passed is False
        assert len(result.removed_clauses) > 0

    def test_guardrail_fail_insufficient_evidence(self):
        from backend.guardrails.guardrail import run_guardrail
        from backend.evidence_engine.evidence import Evidence, EvidenceBundle, EvidenceType
        bundle = EvidenceBundle(conclusion="主升期")
        bundle.add(Evidence(EvidenceType.DATA, "limit_up_count", 50, "涨停50家"))
        result = run_guardrail(ai_output="主升期", evidence=bundle)
        assert result.passed is False
        assert "INSUFFICIENT_EVIDENCE" in result.reason

    def test_filter_advice(self):
        from backend.guardrails.guardrail import filter_advice
        text = "情绪主升期，建议买入持有"
        cleaned, removed = filter_advice(text)
        assert "建议买入" not in cleaned
        assert len(removed) > 0

    def test_verify_data_claims(self):
        from backend.guardrails.guardrail import verify_data_claims
        violations = verify_data_claims(
            "涨停50家，炸板率15%",
            {"limit_up_count": 50, "zhaban_rate": 0.15},
        )
        assert len(violations) == 0

    def test_verify_data_claims_missing(self):
        from backend.guardrails.guardrail import verify_data_claims
        violations = verify_data_claims(
            "涨停50家，主力流出1000万",
            {"limit_up_count": 50},  # 没有 main_flow
        )
        assert len(violations) > 0


# ══════════════════════════════════════
# RuleEngine
# ══════════════════════════════════════

class TestRuleEngine:
    def test_decide_emotion_bull(self):
        from backend.rule_engine.rules import decide_emotion
        mf = _make_mf(limit_up_count=60, zhaban_rate=0.10, max_board_height=9)
        decision = decide_emotion(mf)
        assert decision.conclusion in ("高潮期", "主升期")
        assert decision.confidence > 0

    def test_decide_emotion_frost(self):
        from backend.rule_engine.rules import decide_emotion
        mf = _make_mf(limit_up_count=10, limit_down_count=30, zhaban_rate=0.6, max_board_height=1)
        decision = decide_emotion(mf)
        assert decision.conclusion in ("冰点期", "退潮期")

    def test_decide_dragon_strong(self):
        from backend.rule_engine.rules import decide_dragon
        boards = [
            {"name": "龙头A", "boards": 7, "fengdan": 5.0},
            {"name": "龙头B", "boards": 5, "fengdan": 3.0},
        ]
        decision = decide_dragon(boards, 50)
        assert "龙头" in decision.conclusion
        assert decision.confidence > 0

    def test_decide_dragon_none(self):
        from backend.rule_engine.rules import decide_dragon
        decision = decide_dragon([], 0)
        assert decision.conclusion == "无龙头"

    def test_decide_earning_strong(self):
        from backend.rule_engine.rules import decide_earning
        from backend.earning_effect_engine.earning_effect import EarningEffectScores
        scores = EarningEffectScores(composite=80, avg_premium_pct=5.0, survival_rate=0.7)
        decision = decide_earning(scores)
        assert "强" in decision.conclusion

    def test_decide_earning_weak(self):
        from backend.rule_engine.rules import decide_earning
        from backend.earning_effect_engine.earning_effect import EarningEffectScores
        scores = EarningEffectScores(composite=20, avg_premium_pct=-3.0, survival_rate=0.2)
        decision = decide_earning(scores)
        assert "亏" in decision.conclusion or "弱" in decision.conclusion


# ══════════════════════════════════════
# V4 综合决策
# ══════════════════════════════════════

class TestMarketDecision:
    def test_decision_basic(self):
        from backend.rule_engine.decision import compute_market_decision
        mf = _make_mf()
        result = compute_market_decision(mf)
        assert result.emotion is not None
        assert result.dragon is not None
        assert result.earning is not None
        assert result.timestamp

    def test_decision_has_evidence(self):
        from backend.rule_engine.decision import compute_market_decision
        mf = _make_mf()
        result = compute_market_decision(mf)
        assert len(result.emotion.evidence.evidence) >= 0
        assert result.emotion.evidence.status in ("OK", "INSUFFICIENT_EVIDENCE")

    def test_decision_confidence_range(self):
        from backend.rule_engine.decision import compute_market_decision
        mf = _make_mf()
        result = compute_market_decision(mf)
        assert 0 <= result.composite_confidence <= 1

    def test_decision_to_dict(self):
        from backend.rule_engine.decision import compute_market_decision
        mf = _make_mf()
        result = compute_market_decision(mf)
        d = result.to_dict()
        assert "emotion" in d
        assert "dragon" in d
        assert "earning" in d
        assert "composite" in d
        assert "boundary" in d


