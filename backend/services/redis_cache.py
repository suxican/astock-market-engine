"""Redis 缓存层 — 可选的分布式缓存后端

当 REDIS_URL 环境变量配置时启用 Redis 缓存。
未配置时自动回退到现有的内存 TTL 缓存（_cache.py）。

特性:
  - 与现有 _cache.py 接口兼容（get/set/delete）
  - 支持 TTL 过期
  - 支持 JSON 序列化
  - 连接池管理
  - 优雅降级: Redis 不可用时回退到内存缓存
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("market_engine.redis_cache")

REDIS_URL = os.getenv("REDIS_URL", "")

_redis_client = None
_redis_available = False


def _get_redis():
    """获取 Redis 客户端（延迟初始化）"""
    global _redis_client, _redis_available

    if not REDIS_URL:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis 连接成功: %s", REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL)
        return _redis_client
    except Exception as e:
        logger.warning("Redis 连接失败，回退到内存缓存: %s", e)
        _redis_available = False
        return None


def redis_get(key: str) -> Any | None:
    """从 Redis 获取值"""
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            return json.loads(val)
        return None
    except Exception as e:
        logger.debug("Redis GET %s 失败: %s", key, e)
        return None


def redis_set(key: str, value: Any, ttl: int = 60) -> bool:
    """向 Redis 写入值（带 TTL）"""
    r = _get_redis()
    if r is None:
        return False
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        r.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.debug("Redis SET %s 失败: %s", key, e)
        return False


def redis_delete(key: str) -> bool:
    """从 Redis 删除键"""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.delete(key)
        return True
    except Exception as e:
        logger.debug("Redis DEL %s 失败: %s", key, e)
        return False


def redis_clear_pattern(pattern: str) -> int:
    """清除匹配模式的所有键"""
    r = _get_redis()
    if r is None:
        return 0
    try:
        keys = r.keys(pattern)
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as e:
        logger.debug("Redis CLEAR %s 失败: %s", pattern, e)
        return 0


def is_redis_available() -> bool:
    """检查 Redis 是否可用"""
    if not REDIS_URL:
        return False
    r = _get_redis()
    return r is not None and _redis_available


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息"""
    if not is_redis_available():
        return {"backend": "memory", "redis_available": False}

    r = _get_redis()
    try:
        info = r.info("memory")
        return {
            "backend": "redis",
            "redis_available": True,
            "used_memory": info.get("used_memory_human", "N/A"),
            "connected_clients": r.info("clients").get("connected_clients", 0),
            "keys": r.dbsize(),
        }
    except Exception:
        return {"backend": "redis", "redis_available": True, "error": "无法获取统计"}
