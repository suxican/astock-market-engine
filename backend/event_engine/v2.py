"""EventEngine V2 — 事件驱动引擎升级版

在 V1 基础上新增:
  1. 事件聚类 — 相似事件自动归组，避免重复计数
  2. 影响衰减 — 事件影响力随时间递减
  3. 市场关联 — 事件与涨跌停/板块资金的因果关联
  4. 综合事件评分 — 结构化 0-100 分供前端和 AI Explain Layer

不新增 Agent，作为 FeatureEngine/ScoreEngine 的扩展模块。
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .event_extractor import (
    classify_event,
    compute_sentiment,
    extract_event,
    extract_keywords,
    get_affected_sectors,
)
from .event_types import Event, HotTopic, NewsItem, TimelineEntry
from .hot_tracker import get_trending_topics
from .news_fetcher import fetch_finance_news
from .stock_linker import enrich_event, link_news_to_stocks
from .timeline import build_today_timeline, get_market_drivers


@dataclass
class EventCluster:
    """事件簇 — 一组相似事件的聚合"""
    cluster_id: str
    title: str                # 簇标题（取最具代表性的事件）
    event_type: str           # 政策/财报/行业/市场
    count: int = 0            # 事件数量
    events: list[Event] = field(default_factory=list)
    affected_sectors: list[str] = field(default_factory=list)
    affected_stocks: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    raw_impact: float = 0.0   # 原始影响分 (0-1)
    decayed_impact: float = 0.0  # 衰减后影响分
    latest_time: str = ""


@dataclass
class EventEngineV2Result:
    """EventEngine V2 综合输出"""
    # ── 事件簇 ──
    clusters: list[EventCluster] = field(default_factory=list)

    # ── 热门话题 ──
    trending_topics: list[HotTopic] = field(default_factory=list)

    # ── 市场驱动因素 ──
    market_drivers: list[dict] = field(default_factory=list)

    # ── 综合评分 (0-100) ──
    event_score: int = 0       # 事件活跃度/影响力分
    sentiment_score: int = 0   # 综合情绪分 (50=中性)
    policy_score: int = 0      # 政策面分

    # ── 信号 ──
    signals: list[str] = field(default_factory=list)

    # ── 事件时间线 ──
    timeline: list[TimelineEntry] = field(default_factory=list)

    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "title": c.title,
                    "event_type": c.event_type,
                    "count": c.count,
                    "affected_sectors": c.affected_sectors[:5],
                    "sentiment": c.sentiment,
                    "raw_impact": round(c.raw_impact, 2),
                    "decayed_impact": round(c.decayed_impact, 2),
                    "latest_time": c.latest_time,
                }
                for c in self.clusters[:10]
            ],
            "trending_topics": [
                {
                    "keyword": t.keyword,
                    "count": t.count,
                    "trend": t.trend,
                    "related_sectors": t.related_sectors,
                }
                for t in self.trending_topics[:10]
            ],
            "market_drivers": self.market_drivers[:8],
            "event_score": self.event_score,
            "sentiment_score": self.sentiment_score,
            "policy_score": self.policy_score,
            "signals": self.signals,
            "timeline_count": len(self.timeline),
            "computed_at": self.computed_at,
        }


# ── 影响衰减参数 ──
_HALF_LIFE_HOURS = 4.0  # 事件影响力半衰期(小时)


def compute_event_v2() -> EventEngineV2Result:
    """EventEngine V2 主入口

    流程:
      1. 获取原始新闻 → 提取事件
      2. 事件聚类（按标题相似度 + 类型分组）
      3. 计算每个簇的衰减后影响力
      4. 综合评分
    """
    now = datetime.now()

    # ── 1. 获取原始新闻并提取事件 ──
    news_list = fetch_finance_news(limit=80)
    events: list[Event] = []
    for news in news_list:
        event = extract_event(news)
        event = enrich_event(event, news)
        events.append(event)

    # ── 2. 事件聚类 ──
    clusters = _cluster_events(events, now)

    # ── 3. 计算衰减影响力 ──
    for cluster in clusters:
        cluster.decayed_impact = _apply_decay(cluster.raw_impact, cluster.latest_time, now)

    # ── 4. 热门话题 ──
    trending = get_trending_topics(top_k=15)

    # ── 5. 市场驱动因素 ──
    drivers = get_market_drivers()

    # ── 6. 时间线 ──
    timeline = build_today_timeline()

    # ── 7. 综合评分 ──
    event_score = _calc_event_score(clusters, trending)
    sentiment_score = _calc_sentiment_score(clusters)
    policy_score = _calc_policy_score(clusters)

    # ── 8. 信号 ──
    signals = _build_signals(clusters, trending, drivers)

    return EventEngineV2Result(
        clusters=clusters,
        trending_topics=trending,
        market_drivers=drivers,
        event_score=event_score,
        sentiment_score=sentiment_score,
        policy_score=policy_score,
        signals=signals,
        timeline=timeline,
        computed_at=now.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _cluster_events(events: list[Event], now: datetime) -> list[EventCluster]:
    """事件聚类 — 按类型 + 关键词重叠度分组"""
    # 简单聚类: 同类型 + 共享关键词 >= 2 的事件归为一簇
    used: set[int] = set()
    clusters: list[EventCluster] = []

    for i, ev in enumerate(events):
        if i in used:
            continue
        cluster_events = [ev]
        used.add(i)

        # 查找相似事件
        for j, other in enumerate(events):
            if j in used:
                continue
            if _events_similar(ev, other):
                cluster_events.append(other)
                used.add(j)

        # 构建簇
        all_sectors: set[str] = set()
        all_stocks: set[str] = set()
        sentiments: list[str] = []
        for ce in cluster_events:
            all_sectors.update(ce.affected_sectors)
            all_stocks.update(ce.affected_stocks)
            sentiments.append(ce.sentiment)

        # 取最具代表性的事件作为标题 (影响分最高的)
        representative = max(cluster_events, key=lambda e: e.impact_score)

        # 簇的综合情绪
        pos = sentiments.count("positive")
        neg = sentiments.count("negative")
        if pos > neg:
            sent = "positive"
        elif neg > pos:
            sent = "negative"
        else:
            sent = "neutral"

        clusters.append(EventCluster(
            cluster_id=f"cluster_{i:03d}",
            title=representative.title,
            event_type=representative.event_type,
            count=len(cluster_events),
            events=cluster_events,
            affected_sectors=list(all_sectors)[:5],
            affected_stocks=list(all_stocks)[:10],
            sentiment=sent,
            raw_impact=max(e.impact_score for e in cluster_events),
            latest_time=max(
                (e.publish_time for e in cluster_events if e.publish_time),
                default="",
            ),
        ))

    # 按衰减后影响力排序
    clusters.sort(key=lambda c: c.raw_impact, reverse=True)
    return clusters


def _events_similar(a: Event, b: Event) -> bool:
    """判断两个事件是否相似 (类型相同 + 关键词重叠 >= 2)"""
    if a.event_type != b.event_type:
        return False
    overlap = set(a.keywords) & set(b.keywords)
    return len(overlap) >= 2


def _apply_decay(impact: float, time_str: str, now: datetime) -> float:
    """影响衰减 — 半衰期模型"""
    if not time_str:
        return impact * 0.7  # 无时间信息，打7折

    try:
        # 尝试解析时间
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                event_time = datetime.strptime(str(time_str)[:19], fmt)
                break
            except ValueError:
                continue
        else:
            return impact * 0.7

        hours_ago = (now - event_time).total_seconds() / 3600
        if hours_ago < 0:
            hours_ago = 0

        # 指数衰减: impact * (0.5 ^ (hours / half_life))
        decayed = impact * (0.5 ** (hours_ago / _HALF_LIFE_HOURS))
        return max(0.0, decayed)
    except Exception:
        return impact * 0.7


def _calc_event_score(clusters: list[EventCluster], trending: list[HotTopic]) -> int:
    """事件活跃度评分 (0-100)"""
    if not clusters:
        return 10

    # 簇数量贡献 (0-30)
    count_score = min(30, len(clusters) * 3)

    # 影响力贡献 (0-40)
    top_impacts = sorted([c.decayed_impact for c in clusters], reverse=True)[:5]
    impact_score = sum(top_impacts) / max(len(top_impacts), 1) * 40

    # 热词活跃度 (0-30)
    hot_score = min(30, len(trending) * 2)

    return min(100, int(count_score + impact_score + hot_score))


def _calc_sentiment_score(clusters: list[EventCluster]) -> int:
    """综合情绪分: 50=中性, >50=偏多, <50=偏空"""
    if not clusters:
        return 50

    pos = sum(1 for c in clusters if c.sentiment == "positive")
    neg = sum(1 for c in clusters if c.sentiment == "negative")
    total = pos + neg
    if total == 0:
        return 50

    # 按影响力加权
    pos_impact = sum(c.decayed_impact for c in clusters if c.sentiment == "positive")
    neg_impact = sum(c.decayed_impact for c in clusters if c.sentiment == "negative")
    total_impact = pos_impact + neg_impact
    if total_impact == 0:
        return 50

    ratio = pos_impact / total_impact
    # 0 → 20 (极度悲观), 0.5 → 50 (中性), 1.0 → 80 (极度乐观)
    return max(0, min(100, int(20 + ratio * 60)))


def _calc_policy_score(clusters: list[EventCluster]) -> int:
    """政策面评分 (0-100)"""
    policy_clusters = [c for c in clusters if c.event_type == "政策"]
    if not policy_clusters:
        return 50  # 无政策事件

    pos = sum(1 for c in policy_clusters if c.sentiment == "positive")
    neg = sum(1 for c in policy_clusters if c.sentiment == "negative")
    total = pos + neg

    if total == 0:
        return 50

    # 利好政策多 → 分高, 利空政策多 → 分低
    ratio = pos / total
    return max(0, min(100, int(30 + ratio * 50)))


def _build_signals(
    clusters: list[EventCluster],
    trending: list[HotTopic],
    drivers: list[dict],
) -> list[str]:
    """构建事件信号"""
    signals = []

    # 高影响力事件
    high_impact = [c for c in clusters if c.decayed_impact > 0.6]
    if high_impact:
        signals.append(f"{len(high_impact)} 个高影响力事件簇活跃")
        for c in high_impact[:3]:
            signals.append(f"  [{c.event_type}] {c.title[:30]}...")

    # 政策面
    policy = [c for c in clusters if c.event_type == "政策" and c.decayed_impact > 0.3]
    if policy:
        pos = sum(1 for c in policy if c.sentiment == "positive")
        neg = sum(1 for c in policy if c.sentiment == "negative")
        if pos > neg:
            signals.append(f"政策面偏暖: {len(policy)} 个政策事件中 {pos} 个利好")
        elif neg > pos:
            signals.append(f"政策面偏冷: {len(policy)} 个政策事件中 {neg} 个利空")

    # 热门概念
    rising_topics = [t for t in trending if t.trend == "rising"]
    if rising_topics:
        names = ", ".join(t.keyword for t in rising_topics[:3])
        signals.append(f"上升热词: {names}")

    # 行业事件密集
    industry_events = [c for c in clusters if c.event_type == "行业"]
    if len(industry_events) >= 3:
        sectors = set()
        for c in industry_events:
            sectors.update(c.affected_sectors[:2])
        signals.append(f"行业事件密集: {', '.join(list(sectors)[:4])}")

    return signals
