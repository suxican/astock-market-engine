'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Trophy, TrendingUp, BarChart3, Loader2, Shield } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { API_BASE } from '@/lib/api'

interface Ranking {
  symbol: string
  name: string
  strategy: string
  strategy_key: string
  total_return: number
  sharpe_ratio: number
  win_rate: number
  max_drawdown: number
  total_trades: number
}

const SORT_OPTIONS = [
  { key: 'sharpe', label: '夏普比' },
  { key: 'return', label: '收益率' },
  { key: 'win_rate', label: '胜率' },
]

export default function StrategyMarketPage() {
  const router = useRouter()
  const [rankings, setRankings] = useState<Ranking[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('sharpe')

  const fetchRankings = async (sort: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/analysis/strategy-market?sort_by=${sort}`)
      if (res.ok) {
        const data = await res.json()
        setRankings(data.rankings ?? [])
      }
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchRankings(sortBy) }, [sortBy])

  const top3 = rankings.slice(0, 3)

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-sm">策略市场</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {loading ? (
          <div className="flex justify-center py-24">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Top 3 podium */}
            {top3.length > 0 && (
              <div className="grid grid-cols-3 gap-4">
                {top3.map((r, i) => {
                  const medals = ['#FFD700', '#C0C0C0', '#CD7F32']
                  const icons = [Trophy, Trophy, Trophy]
                  const Icon = icons[i]
                  return (
                    <Card key={`${r.symbol}-${r.strategy_key}`} className="border-border/50 overflow-hidden">
                      <CardContent className="p-4 text-center">
                        <div className="w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center"
                          style={{ background: medals[i] + '22' }}>
                          <Icon className="w-4 h-4" style={{ color: medals[i] }} />
                        </div>
                        <div className="text-sm font-semibold">{r.name}</div>
                        <div className="text-xs text-muted-foreground">{r.symbol} · {r.strategy}</div>
                        <div className="mt-2 flex items-center justify-center gap-3 text-xs">
                          <span className="text-[#3FB950] font-mono font-semibold">
                            {(r.total_return >= 0 ? '+' : '')}{(r.total_return * 100).toFixed(1)}%
                          </span>
                          <span className="text-muted-foreground">夏普 {r.sharpe_ratio.toFixed(2)}</span>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}

            {/* Sort controls */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">排序：</span>
              {SORT_OPTIONS.map(opt => (
                <button key={opt.key} onClick={() => setSortBy(opt.key)}
                  className={`px-3 py-1.5 rounded-md text-xs transition-all ${
                    sortBy === opt.key ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
                  }`}>
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Rankings table */}
            <Card className="border-border/50">
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/50 text-muted-foreground text-xs">
                      <th className="text-left px-4 py-3 font-medium w-10">#</th>
                      <th className="text-left px-4 py-3 font-medium">股票</th>
                      <th className="text-left px-4 py-3 font-medium">策略</th>
                      <th className="text-right px-4 py-3 font-medium">收益率</th>
                      <th className="text-right px-4 py-3 font-medium">夏普比</th>
                      <th className="text-right px-4 py-3 font-medium">胜率</th>
                      <th className="text-right px-4 py-3 font-medium">最大回撤</th>
                      <th className="text-right px-4 py-3 font-medium">交易</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankings.map((r, i) => (
                      <tr key={`${r.symbol}-${r.strategy_key}`}
                        className="border-b border-border/30 hover:bg-accent/20 transition-colors cursor-pointer"
                        onClick={() => router.push(`/backtest?symbol=${r.symbol}&strategy=${r.strategy_key}`)}>
                        <td className="px-4 py-3 text-muted-foreground font-mono">
                          {i + 1 <= 3 ? (
                            <span style={{ color: ['#FFD700', '#C0C0C0', '#CD7F32'][i] }}>{i + 1}</span>
                          ) : i + 1}
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium">{r.name}</div>
                          <div className="text-xs text-muted-foreground">{r.symbol}</div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="text-[10px]">{r.strategy}</Badge>
                        </td>
                        <td className={`px-4 py-3 text-right font-mono font-semibold ${r.total_return >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]'}`}>
                          {(r.total_return >= 0 ? '+' : '')}{(r.total_return * 100).toFixed(1)}%
                        </td>
                        <td className={`px-4 py-3 text-right font-mono ${r.sharpe_ratio >= 1 ? 'text-[#3FB950]' : r.sharpe_ratio >= 0.5 ? 'text-[#EAB308]' : 'text-muted-foreground'}`}>
                          {r.sharpe_ratio.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                          {(r.win_rate * 100).toFixed(0)}%
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[#F0883E]">
                          {(r.max_drawdown * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-muted-foreground">{r.total_trades}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            {/* Footer */}
            <div className="text-center text-xs text-muted-foreground pb-8">
              * 基于历史K线的纯规则回测，不构成未来收益保证
            </div>
          </>
        )}
      </main>
    </div>
  )
}
