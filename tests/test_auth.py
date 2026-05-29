"""认证模块测试"""


class TestPasswordHashing:
    def test_hash_and_verify(self):
        from backend.routers.auth import _hash_password, _verify_password
        password = "test123456"
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True

    def test_wrong_password(self):
        from backend.routers.auth import _hash_password, _verify_password
        hashed = _hash_password("correct_password")
        assert _verify_password("wrong_password", hashed) is False

    def test_different_hashes(self):
        from backend.routers.auth import _hash_password
        h1 = _hash_password("same_password")
        h2 = _hash_password("same_password")
        assert h1 != h2  # 每次 salt 不同


class TestJWT:
    def test_create_and_verify(self):
        from backend.routers.auth import _create_token, _verify_token
        token = _create_token("testuser")
        assert _verify_token(token) == "testuser"

    def test_invalid_token(self):
        from backend.routers.auth import _verify_token
        assert _verify_token("invalid.token.here") is None

    def test_tampered_token(self):
        from backend.routers.auth import _create_token, _verify_token
        token = _create_token("testuser")
        parts = token.split(".")
        parts[2] = "tampered"
        assert _verify_token(".".join(parts)) is None


class TestAuthEndpoints:
    def test_register_and_login(self, client):
        import time
        username = f"testuser_{int(time.time())}"
        # 注册
        resp = client.post("/api/auth/register", json={
            "username": username,
            "password": "test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == username

        # 登录
        resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "test123456",
        })
        assert resp.status_code == 200

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "testuser_short",
            "password": "123",
        })
        assert resp.status_code == 400
