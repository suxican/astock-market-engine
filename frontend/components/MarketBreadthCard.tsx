'use client'

import { useState, useEffect } from 'react'
import { BarChart3, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner, ErrorState } from '@/components/ui/states'
import { useMarketBreadth } from '@/lib/hooks'
import { breadthColor } from '@/lib/types'

export default function MarketBreadthCard() {
  const { data, error, isLoading, mutate } = useMarketBreadth()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-8 flex items-center justify-center">
          <Spinner size="sm" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return <ErrorState message={`市场宽度加载失败: ${error.message}`} onRetry={() => mutate()} />
  }

  if (!data) return null

  const color = breadthColor(data.breadth_level)
  const total = data.up_count + data.down_count + data.flat_count

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-3.5 h-3.5 text-muted-foreground" />
            <CardTitle className="text-sm">市场宽度</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{
              background: color + '20', color
            }}>
              {data.breadth_level}
            </span>
            <span className="text-[10px] font-mono text-muted-foreground">{data.breadth_score}分</span>
            <button onClick={() => mutate()} className="p-1 rounded hover:bg-muted transition-colors">
              <RefreshCw className="w-3 h-3 text-muted-foreground" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 涨跌家数 — 可视化条 */}
        <div>
          <div className="flex items-center justify-between text-[11px] mb-1">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-up" />
              <span className="text-up font-semibold">{data.up_count}</span>
              <span className="text-muted-foreground">上涨</span>
            </span>
            <span className="text-muted-foreground">涨跌比 {data.up_ratio.toFixed(1)}</span>
            <span className="flex items-center gap-1">
              <span className="text-muted-foreground">下跌</span>
              <span className="text-down font-semibold">{data.down_count}</span>
              <TrendingDown className="w-3 h-3 text-down" />
            </span>
          </div>
          <div className="flex h-2.5 rounded-full overflow-hidden bg-muted">
            <div
              className="bg-up transition-all duration-500"
              style={{ width: `${(data.up_count / Math.max(total, 1)) * 100}%` }}
            />
            <div
              className="bg-muted-foreground/30 transition-all duration-500"
              style={{ width: `${(data.flat_count / Math.max(total, 1)) * 100}%` }}
            />
            <div
              className="bg-down transition-all duration-500"
              style={{ width: `${(data.down_count / Math.max(total, 1)) * 100}%` }}
            />
          </div>
        </div>

        {/* 涨跌停 + 强弱 */}
        <div className="grid grid-cols-4 gap-2">
          <div className="text-center p-1.5 rounded border border-border">
            <div className="text-[10px] text-muted-foreground">涨停</div>
            <div className="text-sm font-bold font-mono text-up">{data.limit_up_count}</div>
          </div>
          <div className="text-center p-1.5 rounded border border-border">
            <div className="text-[10px] text-muted-foreground">跌停</div>
            <div className="text-sm font-bold font-mono text-down">{data.limit_down_count}</div>
          </div>
          <div className="text-center p-1.5 rounded border border-border">
            <div className="text-[10px] text-muted-foreground">强势&gt;5%</div>
            <div className="text-sm font-bold font-mono text-up">{data.strong_up_count}</div>
          </div>
          <div className="text-center p-1.5 rounded border border-border">
            <div className="text-[10px] text-muted-foreground">弱势&lt;-5%</div>
            <div className="text-sm font-bold font-mono text-down">{data.strong_down_count}</div>
          </div>
        </div>

        {/* 信号 */}
        {data.signals.length > 0 && (
          <div className="space-y-1">
            {data.signals.slice(0, 3).map((s: string, i: number) => (
              <div key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                <span className="mt-1 w-1 h-1 rounded-full shrink-0" style={{ background: color }} />
                {s}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

