'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Search, TrendingUp, TrendingDown, Activity, BarChart3, BookOpen, LineChart, Layers, Flame, Loader2, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { API_BASE } from '@/lib/api'
import { useSystemStatus } from '@/components/SystemStatusProvider'

const DEFAULT_RECENT_CODES = ['600519', '000858', '300750', '002594', '601012']
const RECENT_CODES_KEY = 'astock.recentStockCodes'

const NAV = [
  { href: '/market', label: '大盘', icon: LineChart },
  { href: '/review', label: '复盘', icon: BookOpen },
  { href: '/workbench', label: '工作台', icon: Activity },
  { href: '/backtest', label: '回测', icon: BarChart3 },
]

export default function HomePage() {
  const [symbol, setSymbol] = useState('')
  const [recentCodes, setRecentCodes] = useState<string[]>(DEFAULT_RECENT_CODES)
  const router = useRouter()
  const { isMock } = useSystemStatus()

  const [snap, setSnap] = useState<any>(null)
  useEffect(() => {
    fetch(`${API_BASE}/api/analysis/market-scores`).then(r => r.json()).then(setSnap).catch(() => {})
  }, [])

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(RECENT_CODES_KEY)
      if (!stored) return
      const codes = JSON.parse(stored)
      if (Array.isArray(codes)) {
        setRecentCodes(codes.filter(code => typeof code === 'string' && /^\d{6}$/.test(code)).slice(0, 5))
      }
    } catch {}
  }, [])

  const rememberCode = (value: string) => {
    const code = value.trim()
    if (!/^\d{6}$/.test(code)) return
    const next = [code, ...recentCodes.filter(item => item !== code)].slice(0, 5)
    setRecentCodes(next)
    try {
      window.localStorage.setItem(RECENT_CODES_KEY, JSON.stringify(next))
    } catch {}
  }

  const openStock = (value: string) => {
    const code = value.trim()
    if (!code) return
    rememberCode(code)
    router.push(`/stock?code=${code}`)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    openStock(symbol)
  }

  const emotion = snap?.emotion
  const dragon = snap?.dragon_intensity
  const risk = snap?.risk

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部导航 */}
      <header className="border-b border-border/50 sticky top-0 z-50 glass">
        <div className="max-w-5xl mx-auto px-6 h-11 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-primary flex items-center justify-center">
              <Flame className="w-3 h-3 text-primary-foreground" />
            </div>
            <span className="text-xs font-semibold tracking-tight">AStock</span>
            <span className="text-[10px] text-muted-foreground tracking-wider ml-1 hidden sm:inline">市场认知引擎 v4</span>
          </div>
          <nav className="flex items-center gap-1">
            {NAV.map(link => (
              <a key={link.href} href={link.href}
                className="px-2.5 py-1 rounded text-[11px] text-muted-foreground hover:text-foreground hover:bg-secondary transition-all">
                {link.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 pt-20 pb-16">
        {/* 品牌标识 */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight mb-1.5">市场认知引擎</h1>
          <p className="text-[11px] text-muted-foreground tracking-widest uppercase">A-Stock Market Cognition Engine</p>
        </div>

        {/* 搜索框 */}
        <div className="mx-auto mb-10 flex max-w-3xl flex-col gap-3 md:flex-row md:items-start">
        <form onSubmit={handleSubmit} className="flex-1">
          <div className="flex items-center rounded-lg border border-border bg-card overflow-hidden
            focus-within:ring-2 focus-within:ring-primary/30 transition-all">
            <Search className="ml-4 w-4 h-4 text-muted-foreground shrink-0" />
            <Input
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              placeholder="输入股票代码，例如 600519"
              className="flex-1 h-10 border-0 bg-transparent focus-visible:ring-0 shadow-none text-sm"
            />
            <Button type="submit" size="sm" className="mr-1.5 h-7 px-4 text-xs rounded-md">
              分析
            </Button>
          </div>
          <div className="mt-3 flex items-center justify-center gap-2 flex-wrap">
            {recentCodes.map(code => (
              <button type="button" key={code} onClick={() => openStock(code)}
                className="px-2 py-0.5 rounded text-[10px] text-muted-foreground font-mono
                  hover:text-foreground hover:bg-secondary transition-all">
                {code}
              </button>
            ))}
          </div>
        </form>
          <Button
            type="button"
            variant="outline"
            className="h-10 min-w-32 justify-center border-primary/35 text-primary hover:bg-primary/10"
            onClick={() => router.push('/stock/history')}
          >
            <History className="w-4 h-4" />
            历史记录
          </Button>
        </div>

        {/* 市场快照 — 三栏数据卡 */}
        <div className="grid grid-cols-3 gap-3 mb-10">
          {/* 情绪 */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">市场情绪</div>
            {emotion ? (
              <>
                <div className="text-2xl font-bold font-mono mb-1" style={{
                  color: emotion.score >= 60 ? 'hsl(var(--up))' : emotion.score >= 30 ? 'hsl(var(--warn))' : 'hsl(var(--muted-foreground))'
                }}>{emotion.stage}</div>
                <div className="text-xs text-muted-foreground">{emotion.score}/100 · {emotion.confidence}置信</div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground animate-pulse">加载中...</div>
            )}
          </div>

          {/* 龙头 */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">龙头强度</div>
            {dragon ? (
              <>
                <div className="text-2xl font-bold font-mono mb-1">{dragon.score}</div>
                <div className="text-xs text-muted-foreground">{dragon.high_board_count} 只高标</div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground animate-pulse">加载中...</div>
            )}
          </div>

          {/* 风险 */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">风险等级</div>
            {risk ? (
              <>
                <div className="text-2xl font-bold font-mono mb-1" style={{
                  color: risk.score >= 70 ? 'hsl(var(--up))' : risk.score >= 40 ? 'hsl(var(--warn))' : 'hsl(var(--down))'
                }}>{risk.level}</div>
                <div className="text-xs text-muted-foreground">{risk.score}/100</div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground animate-pulse">加载中...</div>
            )}
          </div>
        </div>

        {/* 功能入口 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {NAV.map(link => (
            <a key={link.href} href={link.href}
              className="group flex items-center gap-2.5 p-3 rounded-lg border border-border bg-card
                hover:border-primary/20 hover:bg-card/80 transition-all">
              <link.icon className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
              <span className="text-xs font-medium">{link.label}</span>
            </a>
          ))}
        </div>
      </main>

      {/* 底部 */}
      <footer className="text-center text-[10px] text-muted-foreground/50 pb-6">
        {isMock ? '* 模拟数据模式' : '* 数据基于 akshare，不构成投资建议'}
      </footer>
    </div>
  )
}
