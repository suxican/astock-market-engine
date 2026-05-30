'use client'

import { Flame, TrendingUp, RefreshCw, Crown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner, ErrorState } from '@/components/ui/states'
import { useThemeScores } from '@/lib/hooks'
import { themeLevelColor } from '@/lib/types'

export default function ThemeScoresCard() {
  const { data, error, isLoading, mutate } = useThemeScores()

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
    return <ErrorState message={`主线识别加载失败: ${error.message}`} onRetry={() => mutate()} />
  }

  if (!data || data.themes.length === 0) return null

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="w-3.5 h-3.5 text-muted-foreground" />
            <CardTitle className="text-sm">主线识别</CardTitle>
          </div>
          {data.main_line && (
            <div className="flex items-center gap-1.5">
              <Crown className="w-3 h-3 text-amber-500" />
              <span className="text-xs font-semibold text-amber-500">{data.main_line}</span>
              <span className="text-[10px] font-mono text-muted-foreground">{data.main_line_score}分</span>
            </div>
          )}
          <button onClick={() => mutate()} className="p-1 rounded hover:bg-muted transition-colors">
            <RefreshCw className="w-3 h-3 text-muted-foreground" />
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Top 板块排名 */}
        <div className="space-y-1.5">
          {data.themes.slice(0, 8).map((theme: { name: string; limit_up_count: number; fund_flow: number; dragon_boards: number; concentration: number; composite: number; level: string }, i: number) => {
            const color = themeLevelColor(theme.level)
            const isMain = theme.level === '主线'
            return (
              <div
                key={theme.name}
                className="flex items-center gap-2 py-1 border-b border-border last:border-0"
                style={isMain ? { background: color + '08' } : undefined}
              >
                <span className="text-[10px] font-mono text-muted-foreground w-4 text-right">{i + 1}</span>
                <div className="flex items-center gap-1 flex-1 min-w-0">
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                    style={{ background: color + '20', color }}
                  >
                    {theme.level}
                  </span>
                  <span className="text-xs font-medium truncate">{theme.name}</span>
                  {isMain && <Crown className="w-3 h-3 text-amber-500 shrink-0" />}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[10px] text-up font-mono">{theme.limit_up_count}涨停</span>
                  {theme.dragon_boards > 0 && (
                    <span className="text-[10px] text-amber-500 font-mono">{theme.dragon_boards}板</span>
                  )}
                  {theme.fund_flow !== 0 && (
                    <span className={`text-[10px] font-mono ${theme.fund_flow > 0 ? 'text-up' : 'text-down'}`}>
                      {theme.fund_flow > 0 ? '+' : ''}{theme.fund_flow.toFixed(1)}亿
                    </span>
                  )}
                  <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${theme.composite}%`, background: color }}
                    />
                  </div>
                  <span className="text-[10px] font-mono w-7 text-right" style={{ color }}>
                    {theme.composite}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {/* 信号 */}
        {data.signals.length > 0 && (
          <div className="border-t border-border pt-2 space-y-1">
            {data.signals.slice(0, 3).map((s: string, i: number) => (
              <div key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                <span className="mt-1 w-1 h-1 rounded-full shrink-0 bg-amber-500" />
                {s}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}


