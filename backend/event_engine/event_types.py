"""事件引擎数据类型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class NewsItem:
    """单条新闻"""
    title: str
    content: str = ""
    source: str = ""
    publish_time: str = ""
    url: str = ""
    keywords: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"NewsItem({self.title[:40]}...)"


@dataclass
class Event:
    """聚合事件"""
    id: str  # hash of title
    title: str
    summary: str = ""
    event_type: str = ""          # 政策/财报/行业/市场/其他
    keywords: List[str] = field(default_factory=list)
    affected_sectors: List[str] = field(default_factory=list)
    affected_stocks: List[str] = field(default_factory=list)
    sentiment: str = "neutral"     # positive/negative/neutral
    impact_score: float = 0.0      # 0-1
    publish_time: str = ""
    related_events: List[str] = field(default_factory=list)


@dataclass
class HotTopic:
    """热词/热门话题"""
    keyword: str
    count: int = 0
    trend: str = "stable"        # rising/falling/stable
    related_sectors: List[str] = field(default_factory=list)
    related_stocks: List[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""


@dataclass
class TimelineEntry:
    """时间线条目"""
    time: str
    title: str
    event_type: str = ""
    affected_markets: List[str] = field(default_factory=list)
    importance: str = "low"       # high/medium/low
