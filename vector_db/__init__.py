"""向量数据库 — Qdrant 本地模式"""
from .client import (
    get_client, embed_text, build_market_vector,
    save_market_vector, save_review_vector,
    search_similar_market, search_similar_reviews,
)

__all__ = [
    "get_client", "embed_text", "build_market_vector",
    "save_market_vector", "save_review_vector",
    "search_similar_market", "search_similar_reviews",
]
