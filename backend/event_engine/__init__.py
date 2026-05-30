"""事件驱动引擎

V1: 基础事件提取、新闻获取、热词追踪、时间线
V2: 事件聚类、影响衰减、市场关联、综合评分
"""
from .event_types import Event, HotTopic, NewsItem, TimelineEntry
from .v2 import EventCluster, EventEngineV2Result, compute_event_v2

__all__ = [
    "Event", "HotTopic", "NewsItem", "TimelineEntry",
    "EventCluster", "EventEngineV2Result", "compute_event_v2",
]
