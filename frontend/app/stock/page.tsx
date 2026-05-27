'use client'

import { Suspense, useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Search, TrendingUp, TrendingDown,
  AlertTriangle, Loader2, BarChart3, CandlestickChart,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import KLineChart from '@/components/KLineChart'
import LimitUpCard from '@/components/LimitUpCard'
import LimitDownCard from '@/components/LimitDownCard'
import ExpectationGapCard from '@/components/ExpectationGapCard'
import { API_BASE } from '@/lib/api'

export default function StockPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    }>
      <StockPageContent />
    </Suspense>
  )
}

interface StockSummary {
  symbol: string
  name: string
  close: number
  pct_change: number
  volume: number
  turnover: number
  high: number
  low: number
  market_cap?: number
  pe?: number
}

interface KLineRecord {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  [key: string]: any
}

interface AnalysisResult {
  summary: StockSummary
  analysis: string
  data_points: number
  kline_data?: KLineRecord[]
}

function StockPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const symbol = searchParams.get('symbol') || ''

  const [inputSymbol, setInputSymbol] = useState(symbol)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [limitUpResult, setLimitUpResult] = useState<any>(null)
  const [limitDownResult, setLimitDownResult] = useState<any>(null)
  const [gapResult, setGapResult] = useState<any>(null)

  useEffect(() => {
    if (symbol) {
      fetchAnalysis(symbol)
    }
  }, [symbol])

  const fetchAnalysis = async (code: string) => {
    setLoading(true)
    setError('')
    setResult(null)
    setLimitUpResult(null)
    setLimitDownResult(null)
    setGapResult(null)
    try {
      // 优先尝试 AI 综合分析；失败时（无 key / 网络问题）自动降级到本地规则引擎
      const aiRes = await fetch(`${API_BASE}/api/analysis/stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: code, analysis_type: 'comprehensive' }),
      })
      let data: AnalysisResult
      if (aiRes.ok) {
        data = await aiRes.json()
      } else {
        const fallback = await fetch(`${API_BASE}/api/analysis/local-analysis`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: code, analysis_type: 'comprehensive' }),
        })
        if (!fallback.ok) {
          const err = await fallback.json()
          throw new Error(err.detail || '分析失败')
        }
        data = await fallback.json()
      }
      setResult(data)

      // 并发获取涨停/跌停分析
      const [upRes, downRes, gapRes] = await Promise.all([
        fetch(`${API_BASE}/api/analysis/limit-up`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: code }),
        }),
        fetch(`${API_BASE}/api/analysis/limit-down`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: code }),
        }),
        fetch(`${API_BASE}/api/analysis/expectation-gap`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: code }),
        }),
      ])
      if (upRes.ok) setLimitUpResult(await upRes.json())
      if (downRes.ok) setLimitDownResult(await downRes.json())
      if (gapRes.ok) setGapResult(await gapRes.json())
    } catch (e: any) {
      setError(e.message || '请求失败，请确认后端服务已启动')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputSymbol.trim()) return
    router.push(`/stock?symbol=${inputSymbol.trim()}`)
  }

  const formatPrice = (v: number) => v?.toFixed(2) ?? '--'
  const formatVol = (v: number) => {
    if (!v) return '--'
    if (v > 1e8) return (v / 1e8).toFixed(2) + '亿'
    if (v > 1e4) return (v / 1e4).toFixed(2) + '万'
    return v.toFixed(0)
  }

  const renderAnalysis = (text: string) => {
    const html = text
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>')
    return (
      <div
        className="analysis-content leading-relaxed"
        dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
      />
    )
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/50 sticky top-0 bg-background/80 backdrop-blur-lg z-10">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <form onSubmit={handleSubmit} className="flex-1 flex gap-2 max-w-md">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={inputSymbol}
                onChange={(e) => setInputSymbol(e.target.value)}
                placeholder="输入股票代码"
                className="pl-9 h-9 bg-muted border-0"
              />
            </div>
            <Button type="submit" size="sm">分析</Button>
          </form>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading && (
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
            <p className="text-sm text-muted-foreground">正在分析数据...</p>
          </div>
        )}

        {error && (
          <Card className="bg-destructive/5 border-destructive/20">
            <CardContent className="p-6 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-sm mb-1">分析出错</p>
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <Card className="bg-gradient-to-br from-card to-card/50 border-border/50">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h1 className="text-xl font-bold">{result.summary.name}</h1>
                      <span className="text-sm text-muted-foreground">{result.summary.symbol}</span>
                    </div>
                    <div className="flex items-baseline gap-3">
                      <span className="text-3xl font-bold tracking-tight">
                        {formatPrice(result.summary.close)}
                      </span>
                      <span className={`text-lg font-medium ${result.summary.pct_change >= 0 ? 'up' : 'down'}`}>
                        {result.summary.pct_change >= 0 ? '+' : ''}{result.summary.pct_change.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                  <Badge variant={result.summary.pct_change >= 0 ? 'up' : 'down'} className="text-sm px-3 py-1">
                    {result.summary.pct_change >= 0 ? <TrendingUp className="w-3.5 h-3.5 mr-1" /> : <TrendingDown className="w-3.5 h-3.5 mr-1" />}
                    {result.summary.pct_change >= 0 ? '上涨' : '下跌'}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs mb-0.5">最高</div>
                    <div className="font-medium">{formatPrice(result.summary.high)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-0.5">最低</div>
                    <div className="font-medium">{formatPrice(result.summary.low)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-0.5">成交量</div>
                    <div className="font-medium">{formatVol(result.summary.volume)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-0.5">换手率</div>
                    <div className="font-medium">{result.summary.turnover?.toFixed(2)}%</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 涨停/跌停分析 */}
            {limitUpResult?.analysis?.is_limit_up && (
              <LimitUpCard
                analysis={limitUpResult.analysis}
                symbol={limitUpResult.symbol}
                name={limitUpResult.name}
              />
            )}
            {limitDownResult?.analysis?.is_limit_down && (
              <LimitDownCard
                analysis={limitDownResult.analysis}
                symbol={limitDownResult.symbol}
                name={limitDownResult.name}
              />
            )}

            {/* 预期差分析 */}
            {gapResult?.analysis?.has_gap && (
              <ExpectationGapCard
                analysis={gapResult.analysis}
                symbol={gapResult.symbol}
                name={gapResult.name}
              />
            )}

            {/* K线图 */}
            {result.kline_data && result.kline_data.length > 0 && (
              <Card className="border-border/50 overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <CandlestickChart className="w-4 h-4 text-primary" />
                    <CardTitle className="text-base">日K线走势</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-0 pb-3">
                  <KLineChart data={result.kline_data} />
                </CardContent>
              </Card>
            )}

            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <BrainIcon className="w-4 h-4 text-primary" />
                  <CardTitle className="text-base">AI 认知分析</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {renderAnalysis(result.analysis)}
              </CardContent>
            </Card>

            <div className="text-center text-xs text-muted-foreground pb-8">
              基于 {result.data_points} 个交易日数据 · 不构成投资建议
            </div>
          </motion.div>
        )}

        {!symbol && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <BarChart3 className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm">输入股票代码开始分析</p>
          </div>
        )}
      </main>
    </div>
  )
}

function BrainIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 4a4 4 0 0 1 3.5 2.1 6 6 0 0 1 3.5 0 4 4 0 0 1 0 7.8 6 6 0 0 1-3.5 0A4 4 0 0 1 12 20a4 4 0 0 1-3.5-2.1 6 6 0 0 1-3.5 0 4 4 0 0 1 0-7.8 6 6 0 0 1 3.5 0A4 4 0 0 1 12 4Z" />
      <path d="M12 4v16" />
      <path d="M8 8v8" />
      <path d="M16 8v8" />
    </svg>
  )
}
