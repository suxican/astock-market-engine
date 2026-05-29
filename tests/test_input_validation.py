"""输入校验测试"""
import pytest


class TestStockCodeValidation:
    def test_valid_code(self, client, valid_symbol):
        resp = client.post("/api/stock/daily", json={"symbol": valid_symbol})
        assert resp.status_code == 200

    def test_reject_letters(self, client):
        resp = client.post("/api/stock/daily", json={"symbol": "abc"})
        assert resp.status_code == 400
        assert "格式错误" in resp.json()["detail"]

    def test_reject_too_short(self, client):
        resp = client.post("/api/stock/daily", json={"symbol": "12"})
        assert resp.status_code == 400

    def test_reject_too_long(self, client):
        resp = client.post("/api/stock/daily", json={"symbol": "1234567"})
        assert resp.status_code == 400

    def test_reject_sql_injection(self, client):
        resp = client.post("/api/stock/daily", json={"symbol": "1; DROP TABLE"})
        assert resp.status_code == 400

    def test_reject_empty(self, client):
        resp = client.post("/api/stock/daily", json={"symbol": ""})
        assert resp.status_code == 400


class TestHealthEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "市场认知引擎" in data["service"]
