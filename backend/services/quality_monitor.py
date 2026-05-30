"""数据质量监控层 — 增强 data_quality.py 的监控和健康检查能力

在不修改现有 data_quality.py 的前提下，增加:
  1. 源级健康监控 — 每个数据源的可用性/延迟/错误率追踪
  2. 数据新鲜度 — 最近成功获取的时间戳
  3. 质量仪表盘 — 统一的健康状态汇总 API
  4. 质量历史 — 最近 N 次请求的质量记录

被 router 层的 /api/quality/* 端点调用。
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .data_quality import DataQuality, DataSource, classify_system_status


@dataclass
class SourceHealth:
    """单个数据源的健康状态"""
    source: DataSource
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_success_at: str = ""
    last_failure_at: str = ""
    avg_latency_ms: float = 0.0
    _latencies: list[float] = field(default_factory=list, repr=False)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def health_status(self) -> str:
        """healthy / degraded / unhealthy / unknown"""
        if self.total_requests < 3:
            return "unknown"
        if self.success_rate >= 0.9:
            return "healthy"
        if self.success_rate >= 0.5:
            return "degraded"
        return "unhealthy"

    def record_success(self, latency_ms: float):
        self.total_requests += 1
        self.success_count += 1
        self.last_success_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._latencies.append(latency_ms)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def record_failure(self):
        self.total_requests += 1
        self.failure_count += 1
        self.last_failure_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "total_requests": self.total_requests,
            "success_rate": round(self.success_rate, 3),
            "health_status": self.health_status,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
        }


@dataclass
class QualitySnapshot:
    """单次请求的数据质量快照"""
    timestamp: str
    endpoint: str
    sources_used: list[str]
    overall_confidence: float
    is_valid: bool
    fallback_used: bool
    system_status: str  # realtime / cache / stale / mock


@dataclass
class QualityDashboard:
    """数据质量仪表盘汇总"""
    overall_status: str         # realtime / cache / stale / mock
    overall_confidence: float   # 0-1
    source_health: dict[str, dict]
    recent_snapshots: list[dict]
    alerts: list[str]
    computed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "overall_confidence": round(self.overall_confidence, 2),
            "source_health": self.source_health,
            "recent_snapshots": self.recent_snapshots,
            "alerts": self.alerts,
            "computed_at": self.computed_at,
        }


class QualityMonitor:
    """全局数据质量监控器（单例）"""

    _instance: QualityMonitor | None = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._source_health: dict[DataSource, SourceHealth] = {}
                    inst._recent_snapshots: deque[QualitySnapshot] = deque(maxlen=50)
                    inst._initialized = True
                    cls._instance = inst
        return cls._instance

    def record_source_call(
        self,
        source: DataSource,
        success: bool,
        latency_ms: float = 0.0,
    ):
        """记录一次数据源调用结果"""
        if source not in self._source_health:
            self._source_health[source] = SourceHealth(source=source)

        health = self._source_health[source]
        if success:
            health.record_success(latency_ms)
        else:
            health.record_failure()

    def record_snapshot(self, quality: DataQuality, endpoint: str = ""):
        """记录一次请求的数据质量快照"""
        snapshot = QualitySnapshot(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            endpoint=endpoint,
            sources_used=[quality.source.value],
            overall_confidence=quality.confidence,
            is_valid=quality.is_valid(),
            fallback_used=quality.fallback_used,
            system_status=classify_system_status(quality),
        )
        self._recent_snapshots.append(snapshot)

    def get_dashboard(self) -> QualityDashboard:
        """生成数据质量仪表盘"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 源健康状态
        source_health = {}
        for src, health in self._source_health.items():
            source_health[src.value] = health.to_dict()

        # 最近快照
        recent = [s.__dict__ for s in list(self._recent_snapshots)[-20:]]

        # 整体状态
        overall_confidence = 0.0
        if self._source_health:
            # 加权平均: 成功率 * 源置信度
            total_weight = 0
            weighted_sum = 0
            from .data_quality import SOURCE_CONFIDENCE
            for src, health in self._source_health.items():
                if health.total_requests > 0:
                    weight = health.total_requests
                    src_conf = SOURCE_CONFIDENCE.get(src, 0.1)
                    weighted_sum += health.success_rate * src_conf * weight
                    total_weight += weight
            overall_confidence = weighted_sum / total_weight if total_weight > 0 else 0

        # 整体状态判定
        if overall_confidence >= 0.8:
            overall_status = "realtime"
        elif overall_confidence >= 0.5:
            overall_status = "cache"
        elif overall_confidence >= 0.3:
            overall_status = "stale"
        else:
            overall_status = "mock"

        # 告警
        alerts = self._check_alerts()

        return QualityDashboard(
            overall_status=overall_status,
            overall_confidence=overall_confidence,
            source_health=source_health,
            recent_snapshots=recent,
            alerts=alerts,
            computed_at=now,
        )

    def _check_alerts(self) -> list[str]:
        """检查告警条件"""
        alerts = []
        for src, health in self._source_health.items():
            if health.total_requests < 3:
                continue
            if health.health_status == "unhealthy":
                alerts.append(f"数据源 {src.value} 不可用 (成功率 {health.success_rate:.0%})")
            elif health.health_status == "degraded":
                alerts.append(f"数据源 {src.value} 降级 (成功率 {health.success_rate:.0%})")
            if health.avg_latency_ms > 5000:
                alerts.append(f"数据源 {src.value} 延迟过高 ({health.avg_latency_ms:.0f}ms)")
        return alerts

    def get_source_health_map(self) -> dict[str, SourceHealth]:
        """返回所有源的健康状态"""
        return {s.value: h for s, h in self._source_health.items()}


def get_quality_monitor() -> QualityMonitor:
    """获取全局质量监控器实例"""
    return QualityMonitor()
