"""向量数据库客户端 — Qdrant 本地模式

使用 Qdrant 本地模式（无需外部服务器），提供：
- market_states (6维)：市场状态向量检索
- market_reviews (1536维)：语义向量检索

所有函数均包裹 try/except，失败时返回空值，永不抛异常。
"""
from typing import List, Dict, Any, Optional
import uuid
import numpy as np
import hashlib

from backend.config import RAG_QDRANT_PATH

# UUID namespace 用于生成确定性 UUID（保证同日期同 ID）
_UUID_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "astock-copilot.local")

_qdrant_client = None


def get_client():
    """获取 Qdrant 客户端（单例，惰性初始化）"""
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            import os
            os.makedirs(RAG_QDRANT_PATH, exist_ok=True)
            _qdrant_client = QdrantClient(path=RAG_QDRANT_PATH)
            _ensure_collections(_qdrant_client)
        except Exception:
            _qdrant_client = None
    return _qdrant_client


def _ensure_collections(client):
    """确保两个 Collection 存在"""
    from qdrant_client.http import models
    collections = [c.name for c in client.get_collections().collections]

    if "market_states" not in collections:
        client.create_collection(
            collection_name="market_states",
            vectors_config=models.VectorParams(size=6, distance=models.Distance.COSINE),
        )
    if "market_reviews" not in collections:
        client.create_collection(
            collection_name="market_reviews",
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )


def embed_text(text: str) -> List[float]:
    """将文本转为 1536 维向量

    优先使用 OpenAI text-embedding-3-small，无 API key 时使用 hash fallback。
    """
    try:
        from openai import OpenAI
        from backend.config import OPENAI_API_KEY, OPENAI_API_BASE
        if OPENAI_API_KEY:
            kwargs = {"api_key": OPENAI_API_KEY}
            if OPENAI_API_BASE:
                kwargs["base_url"] = OPENAI_API_BASE
            client = OpenAI(**kwargs)
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return resp.data[0].embedding
    except Exception:
        pass

    # Fallback: 确定性 hash 向量
    return _fallback_embed(text)


def _fallback_embed(text: str, dim: int = 1536) -> List[float]:
    """无 API key 时的确定性嵌入

    将文本的每个词哈希到向量维度上累加，保证相同文本产生相同向量。
    """
    vec = np.zeros(dim, dtype=np.float32)
    words = text.split()
    for word in words:
        h = hashlib.md5(word.encode()).hexdigest()
        idx = int(h[:8], 16) % dim
        val = (int(h[8:16], 16) / 0xFFFFFFFF) * 2 - 1
        vec[idx] += val
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def build_market_vector(
    limit_up_count: int = 0,
    limit_down_count: int = 0,
    zhaban_rate: float = 0.0,
    board_height: int = 0,
    index_change: float = 0.0,
    up_down_ratio: float = 0.0,
) -> List[float]:
    """构建 6 维市场状态向量，L2 归一化"""
    vec = np.array([
        min(limit_up_count / 100, 1.0),
        min(limit_down_count / 50, 1.0),
        zhaban_rate,  # already 0-1
        min(board_height / 15, 1.0),
        max(0, min((index_change + 5) / 10, 1.0)),
        min(up_down_ratio / 10, 1.0),
    ], dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def _date_to_uuid(date: str, prefix: str = "market") -> str:
    """用日期生成确定性 UUID"""
    return str(uuid.uuid5(_UUID_NS, f"{prefix}_{date}"))


def save_market_vector(date: str, vector: List[float], payload: dict) -> bool:
    """保存市场状态向量到 Qdrant"""
    try:
        client = get_client()
        if client is None:
            return False
        from qdrant_client.http import models
        client.upsert(
            collection_name="market_states",
            points=[models.PointStruct(
                id=_date_to_uuid(date, "market"),
                vector=vector,
                payload=payload,
            )],
        )
        return True
    except Exception:
        return False


def save_review_vector(date: str, review_text: str, payload: dict = None) -> bool:
    """保存复盘文本向量到 Qdrant"""
    try:
        vector = embed_text(review_text)
        client = get_client()
        if client is None:
            return False
        from qdrant_client.http import models
        client.upsert(
            collection_name="market_reviews",
            points=[models.PointStruct(
                id=_date_to_uuid(date, "review"),
                vector=vector,
                payload=payload or {"date": date, "text": review_text[:1000]},
            )],
        )
        return True
    except Exception:
        return False


def search_similar_market(vector: List[float], top_k: int = 5, exclude_date: str = None) -> List[Dict[str, Any]]:
    """搜索相似市场状态日"""
    try:
        client = get_client()
        if client is None:
            return []
        response = client.query_points(
            collection_name="market_states",
            query=vector,
            limit=top_k + 1,  # +1 in case we filter out exclude_date
        )
        hits = []
        for r in response.points:
            d = r.payload.get("date", "")
            if exclude_date and d == exclude_date:
                continue
            hits.append({
                "date": d,
                "score": round(r.score, 4),
                "emotion_stage": r.payload.get("emotion_stage", ""),
                "limit_up_count": r.payload.get("limit_up_count", 0),
                "limit_down_count": r.payload.get("limit_down_count", 0),
                "board_height": r.payload.get("board_height", 0),
                "index_change": r.payload.get("index_change", 0),
            })
            if len(hits) >= top_k:
                break
        return hits
    except Exception:
        return []


def search_similar_reviews(text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """搜索相似语义的复盘记录"""
    try:
        vector = embed_text(text)
        client = get_client()
        if client is None:
            return []
        response = client.query_points(
            collection_name="market_reviews",
            query=vector,
            limit=top_k,
        )
        return [
            {
                "date": r.payload.get("date", ""),
                "score": round(r.score, 4),
                "text": r.payload.get("text", "")[:300],
            }
            for r in response.points
        ]
    except Exception:
        return []
