"""TTL 缓存 + mock 状态追踪

双层缓存策略:
  1. REDIS_URL 配置时: Redis (L2) + 内存 (L1, 5s TTL 作为热缓存)
  2. 未配置时: 纯内存 TTL 缓存

所有服务模块共享，零内部依赖。
"""
import logging
import threading
import time

logger = logging.getLogger("market_engine.cache")

_DEFAULT_TTL = 60  # 秒
_L1_TTL = 5       # 内存热缓存 TTL (Redis 模式下)

# ── 内存缓存 ──
_CACHE: dict[str, tuple] = {}
_CACHE_LOCK = threading.Lock()

_MOCK_USED_SYMBOLS: set = set()
_MOCK_LOCK = threading.Lock()

# ── 缓存统计 ──
_stats = {"l1_hits": 0, "l2_hits": 0, "misses": 0, "sets": 0}


def _cache_get(key: str):
    """获取缓存值 — L1(内存) → L2(Redis)"""
    # L1: 内存
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item is not None:
            value, expire_at = item
            if time.time() <= expire_at:
                _stats["l1_hits"] += 1
                return value
            _CACHE.pop(key, None)

    # L2: Redis (如果可用)
    try:
        from backend.services.redis_cache import redis_get, is_redis_available
        if is_redis_available():
            val = redis_get(f"astock:{key}")
            if val is not None:
                _stats["l2_hits"] += 1
                # 回填 L1
                with _CACHE_LOCK:
                    _CACHE[key] = (val, time.time() + _L1_TTL)
                return val
    except ImportError:
        pass

    _stats["misses"] += 1
    return None


def _cache_set(key: str, value, ttl: int = _DEFAULT_TTL):
    """设置缓存值 — 同时写 L1 + L2"""
    # L1: 内存
    with _CACHE_LOCK:
        _CACHE[key] = (value, time.time() + ttl)
    _stats["sets"] += 1

    # L2: Redis (如果可用)
    try:
        from backend.services.redis_cache import redis_set, is_redis_available
        if is_redis_available():
            redis_set(f"astock:{key}", value, ttl=ttl)
    except ImportError:
        pass


def get_cache_stats() -> dict:
    """获取缓存统计"""
    with _CACHE_LOCK:
        l1_size = len(_CACHE)
    try:
        from backend.services.redis_cache import is_redis_available, get_cache_stats as redis_stats
        redis_ok = is_redis_available()
    except ImportError:
        redis_ok = False

    return {
        "l1_memory_size": l1_size,
        "l2_redis_available": redis_ok,
        "l1_hits": _stats["l1_hits"],
        "l2_hits": _stats["l2_hits"],
        "misses": _stats["misses"],
        "sets": _stats["sets"],
        "hit_rate": round(
            (_stats["l1_hits"] + _stats["l2_hits"]) /
            max(_stats["l1_hits"] + _stats["l2_hits"] + _stats["misses"], 1),
            3,
        ),
    }


def mark_mock_used(symbol: str):
    with _MOCK_LOCK:
        _MOCK_USED_SYMBOLS.add(symbol)


def pop_mock_used() -> bool:
    with _MOCK_LOCK:
        if _MOCK_USED_SYMBOLS:
            _MOCK_USED_SYMBOLS.clear()
            return True
        return False
