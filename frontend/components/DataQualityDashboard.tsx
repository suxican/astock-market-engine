'use client'

import { useState, useEffect } from 'react'
import { Database, Wifi, WifiOff, Clock, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner, ErrorState } from '@/components/ui/states'
import { api } from '@/lib/api'
import type { QualityDashboard, SourceHealth } from '@/lib/types'

const STATUS_CONFIG: Record<string, { icon: typeof Wifi; color: string; label: string }> = {
  healthy: { icon: CheckCircle, color: 'text-emerald-400', label: '正常' },
  degraded: { icon: AlertTriangle, color: 'text-amber-400', label: '降级' },
  unhealthy: { icon: WifiOff, color: 'text-red-400', label: '不可用' },
  unknown: { icon: Clock, color: 'text-gray-500', label: '未知' },
}

function SourceRow({ name, health }: { name: string; health: SourceHealth }) {
  const cfg = STATUS_CONFIG[health.health_status] ?? STATUS_CONFIG.unknown
  const Icon = cfg.icon
  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-border last:border-0">
      <Icon className={`w-3 h-3 ${cfg.color} shrink-0`} />
      <span className="text-[11px] font-medium w-28 truncate">{name}</span>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{
          width: `${health.success_rate * 100}%`,
          background: health.success_rate >= 0.9 ? '#22c55e' : health.success_rate >= 0.5 ? '#eab308' : '#ef4444'
        }} />
      </div>
      <span className="text-[10px] font-mono w-10 text-right text-muted-foreground">
        {(health.success_rate * 100).toFixed(0)}%
      </span>
      <span className="text-[10px] font-mono w-14 text-right text-muted-foreground">
        {health.avg_latency_ms.toFixed(0)}ms
      </span>
    </div>
  )
}

export default function DataQualityDashboard() {
  const [data, setData] = useState<QualityDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = () => {
    setLoading(true)
    setError('')
    api.getQualityDashboard()
      .then(setData)
      .catch(err => setError(err.message || '加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8 flex items-center justify-center">
          <Spinner size="sm" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return <ErrorState message={`数据质量加载失败: ${error}`} onRetry={fetchData} />
  }

  if (!data) return null

  const overallCfg = STATUS_CONFIG[data.overall_status] ?? STATUS_CONFIG.unknown
  const OverallIcon = overallCfg.icon

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-muted-foreground" />
            <CardTitle className="text-sm">数据质量监控</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <OverallIcon className={`w-3.5 h-3.5 ${overallCfg.color}`} />
            <span className={`text-xs font-medium ${overallCfg.color}`}>{overallCfg.label}</span>
            <span className="text-[10px] text-muted-foreground font-mono">
              {(data.overall_confidence * 100).toFixed(0)}%
            </span>
            <button onClick={fetchData} className="p-1 rounded hover:bg-muted transition-colors">
              <RefreshCw className="w-3 h-3 text-muted-foreground" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 告警 */}
        {data.alerts.length > 0 && (
          <div className="space-y-1">
            {data.alerts.map((alert, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-amber-400">
                <AlertTriangle className="w-3 h-3 shrink-0" />
                {alert}
              </div>
            ))}
          </div>
        )}

        {/* 数据源列表 */}
        <div>
          <div className="flex items-center gap-2 py-1 border-b border-border mb-1">
            <span className="text-[10px] text-muted-foreground w-28">数据源</span>
            <span className="flex-1 text-[10px] text-muted-foreground">成功率</span>
            <span className="text-[10px] text-muted-foreground w-10 text-right">率</span>
            <span className="text-[10px] text-muted-foreground w-14 text-right">延迟</span>
          </div>
          {Object.entries(data.source_health).length === 0 ? (
            <div className="text-xs text-muted-foreground py-2 text-center">暂无数据源记录</div>
          ) : (
            Object.entries(data.source_health).map(([name, health]) => (
              <SourceRow key={name} name={name} health={health} />
            ))
          )}
        </div>

        {/* 最近请求 */}
        {data.recent_snapshots.length > 0 && (
          <div className="border-t border-border pt-2">
            <div className="text-[10px] text-muted-foreground mb-1">最近请求</div>
            <div className="flex flex-wrap gap-1">
              {data.recent_snapshots.slice(-15).map((s, i) => (
                <div
                  key={i}
                  className="w-3 h-3 rounded-sm"
                  style={{
                    background: s.is_valid ? '#22c55e' : s.fallback_used ? '#eab308' : '#ef4444'
                  }}
                  title={`${s.timestamp} - ${s.system_status}`}
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
