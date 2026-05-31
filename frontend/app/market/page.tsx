'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { TrendingUp, TrendingDown, Activity, BarChart3, Loader2, Building, Flame } from 'lucide-react'
import AppHeader from '@/components/AppHeader'
import SystemStatusBar from '@/components/SystemStatusBar'
import { ErrorState } from '@/components/ui/states'
import { useMarketOverview, useMarketReview, useSectorFlow, useMarketScores, useThemeScores, useMarketBreadth, useEarningEffect, useMarketHealth } from '@/lib/hooks'
import { useSystemStatus } from '@/components/SystemStatusProvider'

export default function MarketPage() {
  const router = useRouter()
  const [scrolled, setScrolled] = useState(false)
  const { isMock } = useSystemStatus()

  const { data: overview, error: ovErr } = useMarketOverview()
  const { data: review } = useMarketReview()
  const { data: sectorData } = useSectorFlow()
  const { data: scores } = useMarketScores()
  const { data: themes } = useThemeScores()
  const { data: breadth } = useMarketBreadth()
  const { data: earning } = useEarningEffect()
  const { data: health } = useMarketHealth()

  const loading = !overview && !review && !ovErr

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
    </div>
  )

  if (ovErr && !overview) return <ErrorState message={`加载失败: ${ovErr?.message}`} />

  const indices = [
    { label: '上证指数', key: '上证指数' },
    { label: '深证成指', key: '深证成指' },
    { label: '创业板指', key: '创业板指' },
    { label: '科创50', key: '科创50' },
  ]

  const emotion = scores?.emotion
  const risk = scores?.risk
  const topBoards = review?.top_boards || []
  const sectorFlow = sectorData?.sectors || []
  const mainThemes = themes?.themes?.slice(0, 4) || []

  return (
    <div className="min-h-screen bg-background">
      <AppHeader title="市场概况" variant="sticky" scrolled={scrolled}
        statusBar={<SystemStatusBar />}
        navItems={[
          { href: '/', label: '首页' },
          { href: '/review', label: '复盘' },
          { href: '/workbench', label: '工作台' },
        ]} />

      <main className="max-w-6xl mx-auto px-4 pt-14 pb-8">
        {/* ── Bento Grid ── */}
        <div className="grid grid-cols-12 gap-3">

          {/* ═══ 行指数 (4格横排) ═══ */}
          {indices.map((idx, i) => {
            const v = overview?.[idx.key]
            if (!v) return null
            const close = parseFloat(v['最新价'] || 0)
            const pct = parseFloat(v['涨跌幅'] || 0)
            const isUp = pct >= 0
            return (
              <div key={idx.key} className="col-span-3 rounded-xl border border-border bg-card p-3.5">
                <div className="text-[10px] text-muted-foreground mb-1">{idx.label}</div>
                <div className="text-lg font-bold font-mono tracking-tight">{close.toFixed(2)}</div>
                <div className={`text-xs font-mono font-medium ${isUp ? 'text-up' : 'text-down'}`}>
                  {isUp ? '+' : ''}{pct.toFixed(2)}%
                </div>
              </div>
            )
          })}

          {/* ═══ 情绪周期指示器 ═══ */}
          <div className="col-span-12 md:col-span-8 rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">情绪周期</div>
              {emotion && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  style={{
                    background: emotion.score >= 60 ? 'hsl(var(--up) / 0.1)' : 'hsl(var(--muted))',
                    color: emotion.score >= 60 ? 'hsl(var(--up))' : 'hsl(var(--muted-foreground))'
                  }}>
                  {emotion.stage}
                </span>
              )}
            </div>
            {/* 阶段进度条 */}
            {emotion && (
              <div className="space-y-2">
                <div className="flex gap-1">
                  {['冰点', '修复', '主升', '高潮', '分歧', '退潮'].map((s, i) => {
                    const isActive = emotion.stage?.includes(s)
                    return (
                      <div key={s} className="flex-1 text-center">
                        <div className={`h-1.5 rounded-full mb-1 transition-all ${isActive ? 'bg-primary' : 'bg-muted'}`} />
                        <span className={`text-[9px] ${isActive ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>{s}</span>
                      </div>
                    )
                  })}
                </div>
                {emotion.signals?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {emotion.signals.map((s: string, i: number) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground">{s}</span>
                    ))}
                  </div>
                )}
                <div className="text-[11px] text-muted-foreground mt-1">{emotion.suggestion}</div>
              </div>
            )}
          </div>

          {/* ═══ 市场健康分 ═══ */}
          <div className="col-span-12 md:col-span-4 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">综合健康分</div>
            {health ? (
              <div className="text-center">
                <div className="text-4xl font-bold font-mono" style={{
                  color: health.composite >= 70 ? 'hsl(var(--down))' : health.composite >= 40 ? 'hsl(var(--warn))' : 'hsl(var(--up))'
                }}>{health.composite}</div>
                <div className="text-xs text-muted-foreground mt-1">{health.level}</div>
                <div className="grid grid-cols-2 gap-2 mt-3 text-[10px]">
                  <div className="flex justify-between"><span className="text-muted-foreground">情绪</span><span className="font-mono">{health.emotion?.score}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">龙头</span><span className="font-mono">{health.dragon_intensity?.score}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">赚钱</span><span className="font-mono">{health.earning_effect?.composite}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">风险</span><span className="font-mono">{health.risk?.score}</span></div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground animate-pulse">加载中...</div>
            )}
          </div>

          {/* ═══ 主线识别 ═══ */}
          <div className="col-span-12 md:col-span-6 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">主线识别</div>
            {mainThemes.length > 0 ? (
              <div className="space-y-2">
                {mainThemes.map((t: any, i: number) => (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium">{t.name}</span>
                      {t.is_main_line && <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">主线</span>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-muted-foreground">{t.limit_up_count}涨停</span>
                      <span className="text-xs font-mono font-medium">{t.score}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">暂无主线数据</div>
            )}
          </div>

          {/* ═══ 龙头榜 ═══ */}
          <div className="col-span-12 md:col-span-6 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">龙头高标</div>
            {topBoards.length > 0 ? (
              <div className="space-y-1.5">
                {topBoards.slice(0, 5).map((s: any) => (
                  <button key={s.symbol} onClick={() => router.push(`/stock?code=${s.symbol}`)}
                    className="w-full flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/50 transition-colors">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono">{s.symbol}</span>
                      <span className="text-xs font-medium">{s.name}</span>
                      <span className="text-[10px] text-muted-foreground">{s.industry}</span>
                    </div>
                    <div className="text-sm font-bold font-mono text-up">{s.boards}板</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">暂无龙头数据</div>
            )}
          </div>

          {/* ═══ 涨跌停 ═══ */}
          <div className="col-span-6 md:col-span-3 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">涨停</div>
            <div className="text-2xl font-bold font-mono text-up">{review?.limit_up_count ?? '--'}</div>
          </div>
          <div className="col-span-6 md:col-span-3 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">跌停</div>
            <div className="text-2xl font-bold font-mono text-down">{review?.limit_down_count ?? '--'}</div>
          </div>
          <div className="col-span-6 md:col-span-3 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">炸板率</div>
            <div className="text-2xl font-bold font-mono">{review?.zhaban_rate != null ? (review.zhaban_rate * 100).toFixed(0) + '%' : '--'}</div>
          </div>
          <div className="col-span-6 md:col-span-3 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">最高板</div>
            <div className="text-2xl font-bold font-mono">{topBoards[0]?.boards ?? '--'}</div>
          </div>

          {/* ═══ 板块资金流向（热图风格） ═══ */}
          <div className="col-span-12 rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">板块资金流向</div>
            {sectorFlow.length > 0 ? (
              <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-1.5">
                {sectorFlow.slice(0, 20).map((s: any, i: number) => {
                  const pct = parseFloat(s['今日涨跌幅'] || 0)
                  const flow = parseFloat(s['主力净流入-净额'] || 0)
                  const intensity = Math.min(Math.abs(pct) / 3, 1)
                  return (
                    <div key={i} className="rounded-lg p-2 text-center transition-all hover:scale-105"
                      style={{
                        background: pct >= 0
                          ? `hsl(var(--up) / ${0.05 + intensity * 0.15})`
                          : `hsl(var(--down) / ${0.05 + intensity * 0.15})`,
                      }}>
                      <div className="text-[10px] font-medium truncate">{s['名称'] || '--'}</div>
                      <div className={`text-xs font-mono font-bold ${pct >= 0 ? 'text-up' : 'text-down'}`}>
                        {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">暂无板块数据</div>
            )}
          </div>

        </div>
      </main>
    </div>
  )
}
