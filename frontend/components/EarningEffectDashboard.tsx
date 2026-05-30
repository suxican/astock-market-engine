'use client'

import { useState, useEffect } from 'react'
import { Banknote, TrendingUp, TrendingDown, Shield, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner, ErrorState } from '@/components/ui/states'
import { api } from '@/lib/api'
import { earningEffectColor } from '@/lib/types'
import type { EarningEffectScores } from '@/lib/types'

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-muted-foreground w-20 shrink-0 text-right">{label}</span>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-[11px] font-mono w-8 text-right" style={{ color }}>{score}</span>
    </div>
  )
}

function MetricCard({ label, value, icon: Icon, color }: {
  label: string; value: string; icon: typeof TrendingUp; color: string
}) {
  return (
    <div className="flex items-center gap-2 p-2 rounded border border-border">
      <Icon className="w-3.5 h-3.5" style={{ color }} />
      <div className="min-w-0">
        <div className="text-[10px] text-muted-foreground">{label}</div>
        <div className="text-sm font-semibold font-mono" style={{ color }}>{value}</div>
      </div>
    </div>
  )
}

export default function EarningEffectDashboard() {
  const [data, setData] = useState<EarningEffectScores | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = () => {
    setLoading(true)
    setError('')
    api.getEarningEffect()
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
    return <ErrorState message={`赚钱效应加载失败: ${error}`} onRetry={fetchData} />
  }

  if (!data) return null

  const levelColor = earningEffectColor(data.level)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Banknote className="w-3.5 h-3.5 text-muted-foreground" />
            <CardTitle className="text-sm">赚钱效应仪表盘</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{
              background: levelColor + '20', color: levelColor
            }}>
              {data.level}
            </span>
            <button onClick={fetchData} className="p-1 rounded hover:bg-muted transition-colors">
              <RefreshCw className="w-3 h-3 text-muted-foreground" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 综合分 */}
        <div className="flex items-center gap-4">
          <div className="relative w-20 h-20">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="40" fill="none" stroke="hsl(var(--muted))" strokeWidth="8" />
              <circle
                cx="50" cy="50" r="40" fill="none"
                stroke={levelColor}
                strokeWidth="8"
                strokeDasharray={`${data.composite * 2.51} 251`}
                strokeLinecap="round"
                className="transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold font-mono" style={{ color: levelColor }}>
                {data.composite}
              </span>
            </div>
          </div>
          <div className="flex-1 space-y-1.5">
            <ScoreBar label="溢价率" score={data.premium_score} color="#22c55e" />
            <ScoreBar label="连板存活" score={data.survival_score} color="#3b82f6" />
            <ScoreBar label="龙头溢价" score={data.dragon_premium_score} color="#f97316" />
            <ScoreBar label="跌停扩散" score={data.loss_spread_score} color="#ef4444" />
            <ScoreBar label="回封率" score={data.zhaban_reflow_score} color="#8b5cf6" />
          </div>
        </div>

        {/* 核心指标 */}
        <div className="grid grid-cols-3 gap-2">
          <MetricCard
            label="涨停溢价"
            value={`${data.avg_premium_pct >= 0 ? '+' : ''}${data.avg_premium_pct.toFixed(1)}%`}
            icon={data.avg_premium_pct >= 0 ? TrendingUp : TrendingDown}
            color={data.avg_premium_pct >= 0 ? '#22c55e' : '#ef4444'}
          />
          <MetricCard
            label="连板存活率"
            value={`${(data.survival_rate * 100).toFixed(0)}%`}
            icon={Shield}
            color={data.survival_rate > 0.5 ? '#22c55e' : '#f97316'}
          />
          <MetricCard
            label="炸板回封率"
            value={`${(data.zhaban_reflow_rate * 100).toFixed(0)}%`}
            icon={TrendingUp}
            color={data.zhaban_reflow_rate > 0.5 ? '#22c55e' : '#f97316'}
          />
        </div>

        {/* 信号 */}
        {data.signals.length > 0 && (
          <div className="space-y-1">
            {data.signals.slice(0, 4).map((s, i) => (
              <div key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                <span className="mt-1 w-1 h-1 rounded-full shrink-0" style={{ background: levelColor }} />
                {s}
              </div>
            ))}
          </div>
        )}

        {/* 操作建议 */}
        {data.suggestion && (
          <div className="text-xs p-2 rounded border border-border bg-muted/30 text-muted-foreground">
            💡 {data.suggestion}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
