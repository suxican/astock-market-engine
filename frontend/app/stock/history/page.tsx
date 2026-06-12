'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Clock, Eye, History, Loader2 } from 'lucide-react'
import AppHeader from '@/components/AppHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { capitalStageColor } from '@/lib/types'

interface HistoryRecord {
  id: number
  symbol: string
  name: string
  stage: string
  analysis_type: string
  created_at: string
  is_mock_data: boolean
  is_degraded: boolean
}

function formatTime(value: string) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function StockHistoryPage() {
  const [records, setRecords] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getStockAnalysisHistory(80)
      .then(data => setRecords(data.records || []))
      .catch((e: Error) => setError(e.message || '历史记录加载失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen">
      <AppHeader
        title="个股分析历史"
        icon={<History className="w-4 h-4 text-primary" />}
        showBack
        backHref="/"
      />

      <main className="max-w-5xl mx-auto px-4 pt-6 pb-10">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">历史记录</h1>
            <p className="mt-1 text-xs text-muted-foreground">按分析时间倒序展示最近的个股分析结果</p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/">
              <ArrowLeft className="w-3.5 h-3.5" />
              返回首页
            </Link>
          </Button>
        </div>

        <Card className="rounded-lg">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-muted-foreground" />
                分析记录
              </CardTitle>
              <span className="text-xs text-muted-foreground">{records.length} 条</span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading && (
              <div className="flex items-center justify-center py-20 text-muted-foreground">
                <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                <span className="text-xs">加载中...</span>
              </div>
            )}

            {!loading && error && (
              <div className="px-4 py-10 text-center text-xs text-destructive">{error}</div>
            )}

            {!loading && !error && records.length === 0 && (
              <div className="px-4 py-16 text-center text-xs text-muted-foreground">
                暂无历史记录，完成一次个股分析后会自动出现在这里
              </div>
            )}

            {!loading && !error && records.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-xs">
                  <thead className="border-y border-border/70 bg-muted/30 text-[11px] text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">股票名称 + 代码</th>
                      <th className="px-4 py-3 font-medium">分析时间</th>
                      <th className="px-4 py-3 font-medium">所处阶段</th>
                      <th className="px-4 py-3 font-medium">状态</th>
                      <th className="px-4 py-3 text-right font-medium">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(record => (
                      <tr key={record.id} className="border-b border-border/50 hover:bg-muted/20">
                        <td className="px-4 py-3">
                          <div className="font-medium text-foreground">{record.name || '--'}</div>
                          <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">{record.symbol}</div>
                        </td>
                        <td className="px-4 py-3 font-mono text-muted-foreground">{formatTime(record.created_at)}</td>
                        <td className="px-4 py-3">
                          {record.stage ? (
                            <Badge
                              variant="outline"
                              className="text-[10px]"
                              style={{
                                borderColor: capitalStageColor(record.stage) + '55',
                                background: capitalStageColor(record.stage) + '18',
                                color: capitalStageColor(record.stage),
                              }}
                            >
                              {record.stage}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">--</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            {record.is_degraded && <Badge variant="outline" className="border-amber-500/40 text-[10px] text-amber-500">降级</Badge>}
                            {record.is_mock_data && <Badge variant="outline" className="border-muted-foreground/30 text-[10px] text-muted-foreground">模拟</Badge>}
                            {!record.is_degraded && !record.is_mock_data && <span className="text-muted-foreground">正常</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button asChild size="sm" variant="outline" className="h-8">
                            <Link href={`/stock/history/${record.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                              查看明细
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
