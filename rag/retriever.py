"""RAG 检索与注入

提供历史相似行情检索、Prompt 增强注入、复盘持久化。
"""
from datetime import datetime, timezone
from typing import Any

from backend.config import RAG_SIMILAR_DAYS_COUNT
from vector_db.client import (
    build_market_vector,
    save_market_vector,
    save_review_vector,
    search_similar_market,
)


def retrieve_similar_market_days(
    market_data: dict,
    top_k: int = None,
    exclude_date: str = None,
) -> list[dict[str, Any]]:
    """检索与当前市场状态相似的历史交易日"""
    if top_k is None:
        top_k = RAG_SIMILAR_DAYS_COUNT

    vector = build_market_vector(
        limit_up_count=market_data.get("limit_up_count", 0),
        limit_down_count=market_data.get("limit_down_count", 0),
        zhaban_rate=market_data.get("zhaban_rate", 0),
        board_height=market_data.get("board_height", 0),
        index_change=market_data.get("index_change", 0),
        up_down_ratio=market_data.get("up_down_ratio", 0),
    )
    return search_similar_market(vector, top_k=top_k, exclude_date=exclude_date)


def inject_similar_days_context(prompt: str, similar_days: list[dict[str, Any]]) -> str:
    """在 prompt 中插入历史相似日参考"""
    if not similar_days:
        return prompt

    # 从 backend/services/db_service 获取相似日的复盘文本
    review_texts = {}
    try:
        from backend.services.db_service import get_snapshots_by_dates
        dates = [d["date"] for d in similar_days[:3]]
        snapshots = get_snapshots_by_dates(dates)
    except Exception:
        snapshots = {}

    context_lines = [
        "",
        "## 历史相似日参考",
        "以下是与今日市场状态最相似的几个历史交易日，请参考当时的情况进行分析：",
        "",
    ]
    for i, day in enumerate(similar_days[:3], 1):
        snap = snapshots.get(day["date"], {})
        context_lines.append(f"{i}. **{day['date']}**（相似度 {day['score']:.0%}）")
        context_lines.append(f"   - 情绪阶段：{day.get('emotion_stage', '未知')}")
        context_lines.append(f"   - 涨停 {day.get('limit_up_count', '?')} 只 / 跌停 {day.get('limit_down_count', '?')} 只")
        context_lines.append(f"   - 连板高度：{day.get('board_height', '?')} 板")
        context_lines.append("")

    context = "\n".join(context_lines)

    # 在 prompt 的 "请输出复盘分析" 前插入
    marker = "请输出复盘分析（用中文，大白话）："
    if marker in prompt:
        return prompt.replace(marker, context + "\n" + marker)
    return prompt + context


class ReviewEnhancer:
    """复盘增强器：检索相似历史 → 增强 prompt → 持久化结果"""

    def __init__(self):
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def enhance_review_prompt(self, market_data: dict, original_prompt: str) -> tuple[str, list[dict]]:
        """增强复盘 prompt

        Returns:
            (enhanced_prompt, similar_days_list)
        """
        similar_days = retrieve_similar_market_days(market_data, exclude_date=self.today)
        enhanced = inject_similar_days_context(original_prompt, similar_days)
        return enhanced, similar_days

    def persist_review(
        self,
        date: str,
        review_text: str,
        market_data: dict,
        emotion_stage: str = "",
    ) -> dict[str, bool]:
        """持久化复盘结果到 Qdrant + SQLite

        Returns:
            {"qdrant": bool, "sqlite": bool}
        """
        result = {"qdrant": False, "sqlite": False}

        # 1. 存市场状态向量到 Qdrant
        vector = build_market_vector(
            limit_up_count=market_data.get("limit_up_count", 0),
            limit_down_count=market_data.get("limit_down_count", 0),
            zhaban_rate=market_data.get("zhaban_rate", 0),
            board_height=market_data.get("board_height", 0),
            index_change=market_data.get("index_change", 0),
            up_down_ratio=market_data.get("up_down_ratio", 0),
        )
        market_payload = {
            "date": date,
            "emotion_stage": emotion_stage,
            "limit_up_count": market_data.get("limit_up_count", 0),
            "limit_down_count": market_data.get("limit_down_count", 0),
            "board_height": market_data.get("board_height", 0),
            "index_change": market_data.get("index_change", 0),
        }
        result["qdrant"] = bool(
            save_market_vector(date, vector, market_payload)
            and save_review_vector(date, review_text, {"date": date, "text": review_text[:1000]})
        )

        # 2. 存 SQLite
        try:
            from backend.services.db_service import save_market_snapshot, save_review_record
            snapshot_data = {
                "limit_up_count": market_data.get("limit_up_count", 0),
                "limit_down_count": market_data.get("limit_down_count", 0),
                "zhaban_rate": market_data.get("zhaban_rate", 0),
                "board_height": market_data.get("board_height", 0),
                "index_change": market_data.get("index_change", 0),
                "up_down_ratio": market_data.get("up_down_ratio", 0),
                "emotion_stage": emotion_stage,
            }
            save_market_snapshot(date, snapshot_data)
            save_review_record(date, review_text, emotion_stage)
            result["sqlite"] = True
        except Exception:
            pass

        return result
