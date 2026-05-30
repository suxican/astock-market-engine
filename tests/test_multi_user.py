"""多用户体系 CRUD 测试 — 自选股 / 告警 / 偏好"""
import time
import pytest


def _register(client) -> str:
    """注册并返回 token"""
    username = f"test_{int(time.time() * 1000)}"
    r = client.post("/api/auth/register", json={
        "username": username,
        "password": "test123456",
    })
    assert r.status_code == 200, f"注册失败: {r.text}"
    return r.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestWatchlist:
    def test_add_and_list(self, client):
        token = _register(client)
        headers = _auth_header(token)

        # 添加
        r = client.post("/api/auth/watchlist", json={
            "symbol": "600519", "name": "贵州茅台", "note": "白酒龙头"
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["symbol"] == "600519"

        # 列表
        r = client.get("/api/auth/watchlist", headers=headers)
        assert r.status_code == 200
        assert r.json()["count"] == 1
        assert r.json()["items"][0]["symbol"] == "600519"

    def test_add_duplicate(self, client):
        token = _register(client)
        headers = _auth_header(token)
        client.post("/api/auth/watchlist", json={"symbol": "600519"}, headers=headers)
        r = client.post("/api/auth/watchlist", json={"symbol": "600519"}, headers=headers)
        assert r.status_code == 409

    def test_remove(self, client):
        token = _register(client)
        headers = _auth_header(token)
        client.post("/api/auth/watchlist", json={"symbol": "600519"}, headers=headers)
        r = client.delete("/api/auth/watchlist/600519", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/auth/watchlist", headers=headers)
        assert r.json()["count"] == 0

    def test_remove_not_found(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.delete("/api/auth/watchlist/999999", headers=headers)
        assert r.status_code == 404

    def test_invalid_symbol(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.post("/api/auth/watchlist", json={"symbol": "abc"}, headers=headers)
        assert r.status_code == 400


class TestAlerts:
    def test_create_and_list(self, client):
        token = _register(client)
        headers = _auth_header(token)

        r = client.post("/api/auth/alerts", json={
            "alert_type": "price",
            "symbol": "600519",
            "condition": {"above": 2000},
        }, headers=headers)
        assert r.status_code == 200
        alert_id = r.json()["id"]

        r = client.get("/api/auth/alerts", headers=headers)
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_invalid_type(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.post("/api/auth/alerts", json={
            "alert_type": "invalid",
            "condition": {},
        }, headers=headers)
        assert r.status_code == 400

    def test_toggle(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.post("/api/auth/alerts", json={
            "alert_type": "emotion",
            "condition": {"stage": "冰点期"},
        }, headers=headers)
        alert_id = r.json()["id"]

        r = client.patch(f"/api/auth/alerts/{alert_id}/toggle", headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_delete(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.post("/api/auth/alerts", json={
            "alert_type": "earning",
            "condition": {"below": 30},
        }, headers=headers)
        alert_id = r.json()["id"]

        r = client.delete(f"/api/auth/alerts/{alert_id}", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/auth/alerts", headers=headers)
        assert r.json()["count"] == 0


class TestPreferences:
    def test_get_default(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.get("/api/auth/preferences", headers=headers)
        assert r.status_code == 200
        assert r.json()["preferences"] == {}

    def test_update(self, client):
        token = _register(client)
        headers = _auth_header(token)
        r = client.put("/api/auth/preferences", json={
            "preferences": {"theme": "dark", "language": "zh"}
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["preferences"]["theme"] == "dark"

    def test_merge(self, client):
        token = _register(client)
        headers = _auth_header(token)
        client.put("/api/auth/preferences", json={
            "preferences": {"theme": "dark"}
        }, headers=headers)
        r = client.put("/api/auth/preferences", json={
            "preferences": {"language": "zh"}
        }, headers=headers)
        assert r.json()["preferences"]["theme"] == "dark"
        assert r.json()["preferences"]["language"] == "zh"
