"""事件驱动引擎 — A股的市场驱动因素分析

回答"为什么今天这个板块突然爆"。
不是相似K线的事后复盘，而是实时事件驱动的因果分析。

模块:
    news_fetcher       — 财经新闻获取 (akshare)
    event_extractor    — 关键词提取 + 事件分类 + 情绪判断
    concept_mapper     — 概念/政策 → 板块 → 个股映射
    stock_linker       — 新闻 → 受影响的个股评分
    hot_tracker        — 热词追踪 + 趋势判断
    timeline           — 事件时间线 + 市场驱动因素
"""
from .event_types import Event, NewsItem, HotTopic, TimelineEntry
from .news_fetcher import fetch_finance_news, fetch_today_events, fetch_sector_news
from .event_extractor import extract_event, extract_keywords, classify_event
from .concept_mapper import (
    concept_to_sectors, concept_to_stocks,
    sector_to_concepts, keyword_to_stocks,
    get_hot_sectors_from_flow,
)
from .stock_linker import link_news_to_stocks, batch_link, get_today_linked_stocks
from .hot_tracker import get_trending_topics, get_word_trend
from .timeline import (
    build_today_timeline, query_timeline,
    get_events_by_sector, get_market_drivers,
)

__all__ = [
    "Event", "NewsItem", "HotTopic", "TimelineEntry",
    "fetch_finance_news", "fetch_today_events", "fetch_sector_news",
    "extract_event", "extract_keywords", "classify_event",
    "concept_to_sectors", "concept_to_stocks",
    "sector_to_concepts", "keyword_to_stocks",
    "get_hot_sectors_from_flow",
    "link_news_to_stocks", "batch_link", "get_today_linked_stocks",
    "get_trending_topics", "get_word_trend",
    "build_today_timeline", "query_timeline",
    "get_events_by_sector", "get_market_drivers",
]
