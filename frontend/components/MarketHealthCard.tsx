'use client'

import { useState, useEffect } from 'react'
import { Activity, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner, ErrorState } from '@/components/ui/states'
import { api } from '@/lib/api'
import { marketHealthColor, emotionColor, earningEffectColor } from '@/lib/types'
import type { MarketHealthScore } from '@/lib/types'

function DimensionBar({ label, score, color, weight }: {
  label: string; score: number; color: string; weight?: number
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-muted-foreground w-16 shrink-0 text-right">{label}</span>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{
          width: `${score}%`, background: color
        }} />
      </div>
      <span className="text-[10px] font-mono w-7 text-right" style={{ color }}>{score}</span>
      {weight !== undefined && (
        <span className="text-[9px] text-muted-foreground w-8">×{(weight * 100).toFixed(0)}%</span>
      )}
    </div>
  )
}

export default function MarketHealthCard() {
  const [data, setData] = useState<MarketHealthScore | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = () => {
    setLoading(true)
    setError('')
    api.getMarketHealth(false)
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
    return <ErrorState message={`健康分加载失败: ${error}`} onRetry={fetchData} />
  }

  if (!data) return null

  const levelColor = marketHealthColor(data.level)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-muted-foreground" />
            <CardTitle className="text-sm">市场综合健康分</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">{data.confidence}置信</span>
            <button onClick={fetchData} className="p-1 rounded hover:bg-muted transition-colors">
              <RefreshCw className="w-3 h-3 text-muted-foreground" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 主分数 */}
        <div className="flex items-center gap-4">
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="40" fill="none" stroke="hsl(var(--muted))" strokeWidth="10" />
              <circle
                cx="50" cy="50" r="40" fill="none"
                stroke={levelColor}
                strokeWidth="10"
                strokeDasharray={`${data.composite * 2.51} 251`}
                strokeLinecap="round"
                className="transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold font-mono" style={{ color: levelColor }}>
                {data.composite}
              </span>
            </div>
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold" style={{ color: levelColor }}>
              {data.level}
            </div>
            <div className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
              {data.explain_summary}
            </div>
          </div>
        </div>

        {/* 维度分 */}
        <div className="space-y-1.5">
          <DimensionBar
            label="情绪"
            score={data.emotion.score}
            color={emotionColor(data.emotion.stage)}
            weight={data.weights?.emotion}
          />
          <DimensionBar
            label="龙头"
            score={data.dragon_intensity.score}
            color="#f97316"
            weight={data.weights?.dragon}
          />
          <DimensionBar
            label="风险"
            score={100 - data.risk.score}
            color={data.risk.score > 60 ? '#ef4444' : '#22c55e'}
            weight={data.weights?.risk_inv}
          />
          <DimensionBar
            label="赚钱效应"
            score={data.earning_effect.composite}
            color={earningEffectColor(data.earning_effect.level)}
            weight={data.weights?.earning}
          />
        </div>

        {/* 关键信号 */}
        {data.signals.length > 0 && (
          <div className="border-t border-border pt-2 space-y-1">
            {data.signals.slice(0, 3).map((s, i) => (
              <div key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                <span className="mt-1 w-1 h-1 rounded-full shrink-0" style={{ background: levelColor }} />
                {s}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
