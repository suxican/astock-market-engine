'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, History, Loader2, TrendingDown, TrendingUp } from 'lucide-react'
import AnalysisView from '@/components/AnalysisView'
import AppHeader from '@/components/AppHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { api } from '@/lib/api'
import { capitalStageColor } from '@/lib/types'

interface HistoryDetail {
  id: number
  symbol: string
  name: string
  stage: string
  created_at: string
  summary: Record<string, any>
  scores: any
  analysis: string | Record<string, any>
  is_mock_data: boolean
  is_degraded: boolean
}

function formatTime(value: string) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatNumber(value: any, digits = 2) {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(digits) : '--'
}

function analysisText(value: string | Record<string, any>) {
  if (typeof value === 'string') return value
  return String(value?.analysis || value?.text || value?.content || '')
}

export default function StockHistoryDetailPage() {
  const params = useParams<{ id: string }>()
  const [detail, setDetail] = useState<HistoryDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!params.id) return
    api.getStockAnalysisHistoryDetail(params.id)
      .then(data => setDetail(data as HistoryDetail))
      .catch((e: Error) => setError(e.message || '历史明细加载失败'))
      .finally(() => setLoading(false))
  }, [params.id])

  const summary = detail?.summary || {}
  const pct = Number(summary.pct_change)

  return (
    <div className="min-h-screen">
      <AppHeader
        title="分析详情"
        icon={<History className="w-4 h-4 text-primary" />}
        showBack
        backHref="/stock/history"
      />

      <main className="max-w-4xl mx-auto px-4 pt-6 pb-10">
        {loading && (
          <div className="flex items-center justify-center py-32 text-muted-foreground">
            <Loader2 className="mr-2 w-5 h-5 animate-spin" />
            <span className="text-xs">加载中...</span>
          </div>
        )}

        {!loading && error && (
          <Card className="rounded-lg border-destructive/30">
            <CardContent className="py-10 text-center text-xs text-destructive">{error}</CardContent>
          </Card>
        )}

        {!loading && detail && (
          <div className="space-y-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-lg font-semibold tracking-tight">{detail.name || summary.name || '--'}</h1>
                  <span className="font-mono text-xs text-muted-foreground">{detail.symbol}</span>
                  {detail.stage && (
                    <Badge
                      variant="outline"
                      className="text-[10px]"
                      style={{
                        borderColor: capitalStageColor(detail.stage) + '55',
                        background: capitalStageColor(detail.stage) + '18',
                        color: capitalStageColor(detail.stage),
                      }}
                    >
                      {detail.stage}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">分析时间：{formatTime(detail.created_at)}</p>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href="/stock/history">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  返回列表
                </Link>
              </Button>
            </div>

            <Card className="rounded-lg">
              <CardContent className="p-5">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground">收盘/最新价</div>
                    <div className="mt-1 flex items-baseline gap-3">
                      <span className="font-mono text-2xl font-bold">{formatNumber(summary.close)}</span>
                      <span className={`font-mono text-sm font-medium ${pct >= 0 ? 'text-up' : 'text-down'}`}>
                        {Number.isFinite(pct) ? `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%` : '--'}
                      </span>
                      {Number.isFinite(pct) && (
                        <Badge variant={pct >= 0 ? 'up' : 'down'} className="text-[10px]">
                          {pct >= 0 ? <TrendingUp className="w-3 h-3 mr-0.5" /> : <TrendingDown className="w-3 h-3 mr-0.5" />}
                          {pct >= 0 ? '上涨' : '下跌'}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-5 text-xs">
                    <Metric label="最高" value={formatNumber(summary.high)} />
                    <Metric label="最低" value={formatNumber(summary.low)} />
                    <Metric label="换手率" value={Number.isFinite(Number(summary.turnover)) ? `${formatNumber(summary.turnover)}%` : '--'} />
                  </div>
                </div>
              </CardContent>
            </Card>

            {detail.is_degraded && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-400">
                该记录生成时处于数据降级状态，详情仅保留当时可用信息。
              </div>
            )}

            <AnalysisView text={analysisText(detail.analysis)} />
          </div>
        )}
      </main>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-xs text-foreground">{value}</div>
    </div>
  )
}
