'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, BarChart3, Loader2, Target, AlertTriangle, DollarSign } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { API_BASE } from '@/lib/api'

const STRATEGIES = [
  { key: 'ma_cross', name: '均线交叉', desc: '金叉买入，死叉卖出' },
  { key: 'volume_breakout', name: '放量突破', desc: '量价突破后持有固定周期' },
  { key: 'dragon_follow', name: '龙头跟随', desc: '追涨强势股，移动止盈' },
]

interface BacktestResult {
  symbol: string
  strategy: string
  period: string
  metrics: {
    total_trades: number
    win_count: number
    lose_count: number
    win_rate: number
    total_return: number
    annual_return: number
    max_drawdown: number
    sharpe_ratio: number
    avg_pnl: number
    avg_hold_days: number
  }
  trades: Array<{ buy_date: string; sell_date: string; buy_price: number; sell_price: number; pnl_pct: number; hold_days: number; reason: string }>
  equity_curve: Array<{ date: string; value: number }>
}

export default function BacktestPage() {
  const router = useRouter()
  const [symbol, setSymbol] = useState('600519')
  const [strategy, setStrategy] = useState('ma_cross')
  const [capital, setCapital] = useState('100000')
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ symbol, strategy, initial_capital: capital })
      const res = await fetch(`${API_BASE}/api/analysis/backtest?${params}`, { method: 'POST' })
      if (!res.ok) throw new Error((await res.json()).detail || '回测失败')
      setResult(await res.json())
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const fmtPct = (v: number) => `${(v >= 0 ? '+' : '')}${(v * 100).toFixed(2)}%`
  const fmtMoney = (v: number) => {
    if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
    if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(1)}万`
    return v.toFixed(2)
  }

  const m = result?.metrics
  const equity = result?.equity_curve ?? []

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-sm">策略回测</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Form */}
        <Card className="border-border/50">
          <CardContent className="p-6">
            <div className="flex flex-wrap gap-4 items-end">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">股票代码</label>
                <Input value={symbol} onChange={e => setSymbol(e.target.value)} className="w-28 h-9" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">策略</label>
                <div className="flex gap-2">
                  {STRATEGIES.map(s => (
                    <button key={s.key} onClick={() => setStrategy(s.key)}
                      className={`px-3 py-1.5 rounded-md text-xs transition-all ${
                        strategy === s.key
                          ? 'bg-primary/20 text-primary border border-primary/40'
                          : 'bg-muted text-muted-foreground border border-transparent'
                      }`}>
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">初始资金</label>
                <Input value={capital} onChange={e => setCapital(e.target.value)} className="w-28 h-9" />
              </div>
              <Button onClick={run} disabled={loading} size="sm">
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <BarChart3 className="w-3.5 h-3.5 mr-1" />}
                运行回测
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">{error}</div>
        )}

        {/* Results */}
        {m && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Metrics grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { icon: TrendingUp, label: '总收益', value: fmtPct(m.total_return), color: m.total_return >= 0 ? '#3FB950' : '#F85149' },
                { icon: Target, label: '胜率', value: `${(m.win_rate * 100).toFixed(1)}%`, color: '#58A6FF' },
                { icon: AlertTriangle, label: '最大回撤', value: fmtPct(-m.max_drawdown), color: '#F0883E' },
                { icon: BarChart3, label: '夏普比', value: m.sharpe_ratio.toFixed(2), color: m.sharpe_ratio >= 1 ? '#3FB950' : '#EAB308' },
                { icon: DollarSign, label: '年化收益', value: fmtPct(m.annual_return), color: m.annual_return >= 0 ? '#3FB950' : '#F85149' },
              ].map(item => (
                <div key={item.label} className="p-3 rounded-lg bg-card border border-border/50">
                  <div className="flex items-center gap-1.5 mb-1">
                    <item.icon className="w-3 h-3" style={{ color: item.color }} />
                    <span className="text-[10px] text-muted-foreground">{item.label}</span>
                  </div>
                  <div className="text-lg font-bold font-mono" style={{ color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Sub metrics */}
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>交易 {m.total_trades} 次</span>
              <span className="text-[#3FB950]">盈 {m.win_count} 次</span>
              <span className="text-[#F85149]">亏 {m.lose_count} 次</span>
              <span>平均收益 {fmtPct(m.avg_pnl)}</span>
              <span>平均持仓 {m.avg_hold_days} 天</span>
            </div>

            {/* Equity curve (mini) */}
            {equity.length > 1 && (
              <Card className="border-border/50">
                <CardHeader className="pb-2"><CardTitle className="text-sm">收益曲线</CardTitle></CardHeader>
                <CardContent>
                  <div className="relative h-32">
                    <svg width="100%" height="100%" viewBox={`0 0 ${equity.length} 100`} preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#3FB950" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#3FB950" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <path
                        d={(() => {
                          const minV = Math.min(...equity.map(d => d.value))
                          const maxV = Math.max(...equity.map(d => d.value))
                          const range = maxV - minV || 1
                          return equity.map((d, i) =>
                            `${i === 0 ? 'M' : 'L'} ${i / (equity.length - 1) * equity.length} ${100 - ((d.value - minV) / range) * 90 - 5}`
                          ).join(' ')
                        })()}
                        fill="none" stroke="#3FB950" strokeWidth="1.5"
                      />
                      <path
                        d={(() => {
                          const minV = Math.min(...equity.map(d => d.value))
                          const maxV = Math.max(...equity.map(d => d.value))
                          const range = maxV - minV || 1
                          const linePath = equity.map((d, i) =>
                            `${i === 0 ? 'M' : 'L'} ${i / (equity.length - 1) * equity.length} ${100 - ((d.value - minV) / range) * 90 - 5}`
                          ).join(' ')
                          return `${linePath} L ${equity.length} 100 L 0 100 Z`
                        })()}
                        fill="url(#equityFill)"
                      />
                      {/* Baseline */}
                      <line x1="0" y1="95" x2={equity.length} y2="95" stroke="#30363D" strokeWidth="0.5" strokeDasharray="2,4" />
                    </svg>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Trades table */}
            {result.trades.length > 0 && (
              <Card className="border-border/50">
                <CardHeader className="pb-2"><CardTitle className="text-sm">交易记录</CardTitle></CardHeader>
                <CardContent className="p-0">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground">
                        <th className="text-left px-3 py-2 font-medium">买入</th>
                        <th className="text-left px-3 py-2 font-medium">卖出</th>
                        <th className="text-right px-3 py-2 font-medium">买价</th>
                        <th className="text-right px-3 py-2 font-medium">卖价</th>
                        <th className="text-right px-3 py-2 font-medium">收益</th>
                        <th className="text-right px-3 py-2 font-medium">持仓</th>
                        <th className="text-left px-3 py-2 font-medium">原因</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades.slice(-20).map((t, i) => (
                        <tr key={i} className="border-b border-border/30 hover:bg-accent/20">
                          <td className="px-3 py-2 font-mono">{t.buy_date}</td>
                          <td className="px-3 py-2 font-mono">{t.sell_date}</td>
                          <td className="px-3 py-2 text-right font-mono">{t.buy_price.toFixed(2)}</td>
                          <td className="px-3 py-2 text-right font-mono">{t.sell_price.toFixed(2)}</td>
                          <td className={`px-3 py-2 text-right font-mono font-semibold ${t.pnl_pct >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]'}`}>
                            {fmtPct(t.pnl_pct)}
                          </td>
                          <td className="px-3 py-2 text-right text-muted-foreground">{t.hold_days}天</td>
                          <td className="px-3 py-2 text-muted-foreground max-w-[200px] truncate">{t.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </motion.div>
        )}

        {!loading && !result && !error && (
          <div className="text-center py-20 text-muted-foreground text-sm">
            选择股票和策略，点击「运行回测」
          </div>
        )}
      </main>
    </div>
  )
}
