"""测试公共 fixtures"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def valid_symbol():
    return "600519"


@pytest.fixture
def invalid_symbol():
    return "abc"
