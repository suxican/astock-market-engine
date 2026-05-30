"""V3 API 端点集成测试

测试新增的 V3 端点是否正确响应。
注意: 部分端点依赖远程数据源，在无网络时可能返回 mock/降级数据。
"""
import pytest


class TestV3Endpoints:
    """V3 新增 API 端点"""

    def test_earning_effect(self, client):
        resp = client.get("/api/analysis/earning-effect")
        assert resp.status_code == 200
        data = resp.json()
        assert "composite" in data
        assert "level" in data
        assert "signals" in data

    def test_market_health(self, client):
        resp = client.get("/api/analysis/market-health")
        assert resp.status_code == 200
        data = resp.json()
        assert "composite" in data
        assert "level" in data
        assert "emotion" in data
        assert "earning_effect" in data

    def test_market_breath(self, client):
        resp = client.get("/api/analysis/market-breath")
        assert resp.status_code == 200
        data = resp.json()
        assert "breadth_score" in data
        assert "breadth_level" in data
        assert "up_count" in data
        assert "down_count" in data

    def test_theme_scores(self, client):
        resp = client.get("/api/analysis/theme-scores")
        assert resp.status_code == 200
        data = resp.json()
        assert "themes" in data
        assert "main_line" in data

    def test_v3_market_dashboard(self, client):
        resp = client.get("/api/analysis/v3/market-dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "scores" in data
        assert "earning_effect" in data
        assert "health" in data

    def test_data_quality_envelope(self, client):
        """验证 data_quality 字段自动注入"""
        resp = client.get("/api/analysis/earning-effect")
        assert resp.status_code == 200
        data = resp.json()
        assert "data_quality" in data
        dq = data["data_quality"]
        assert "source" in dq
        assert "confidence" in dq
        assert "status" in dq

    def test_data_quality_envelope_on_health(self, client):
        """验证 market-health 也包含 data_quality"""
        resp = client.get("/api/analysis/market-health")
        assert resp.status_code == 200
        data = resp.json()
        assert "data_quality" in data


class TestExistingEndpoints:
    """已有端点仍然正常工作"""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "3.0.0"

    def test_market_scores(self, client):
        resp = client.get("/api/analysis/market-scores")
        assert resp.status_code == 200
        data = resp.json()
        assert "emotion" in data
        assert "dragon_intensity" in data
        assert "risk" in data

    def test_emotion_cycle(self, client):
        resp = client.get("/api/analysis/emotion-cycle")
        assert resp.status_code == 200
        data = resp.json()
        assert "emotion_score" in data
        assert "emotion_stage" in data
