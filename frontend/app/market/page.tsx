'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, TrendingDown, Activity, BarChart3, Loader2, CandlestickChart, Building } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import DragonLeaderCard from '@/components/DragonLeaderCard'
import SectorRotationCard from '@/components/SectorRotationCard'
import { API_BASE } from '@/lib/api'

export default function MarketPage() {
  const router = useRouter()
  const [overview, setOverview] = useState<any>(null)
  const [marketReview, setMarketReview] = useState<any>(null)
  const [sectorFlow, setSectorFlow] = useState<any[]>([])
  const [dragonLeaders, setDragonLeaders] = useState<any>(null)
  const [sectorRotation, setSectorRotation] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [overviewRes, reviewRes, sectorRes, leaderRes, rotationRes] = await Promise.all([
        fetch(`${API_BASE}/api/stock/market-overview`),
        fetch(`${API_BASE}/api/analysis/market-review`),
        fetch(`${API_BASE}/api/stock/sector-flow`),
        fetch(`${API_BASE}/api/analysis/dragon-leaders`, { method: 'POST' }),
        fetch(`${API_BASE}/api/analysis/sector-rotation`),
      ])
      if (overviewRes.ok) setOverview(await overviewRes.json())
      if (reviewRes.ok) setMarketReview(await reviewRes.json())
      if (sectorRes.ok) {
        const data = await sectorRes.json()
        setSectorFlow(data.sectors || [])
      }
      if (leaderRes.ok) setDragonLeaders(await leaderRes.json())
      if (rotationRes.ok) setSectorRotation(await rotationRes.json())
    } catch (e) {
      console.error('获取数据失败', e)
    } finally {
      setLoading(false)
    }
  }

  const getEmotionStyle = (stage: string) => {
    const map: Record<string, { color: string; bg: string }> = {
      '冰点期': { color: 'text-blue-400', bg: 'bg-blue-500/10' },
      '修复期': { color: 'text-green-400', bg: 'bg-green-500/10' },
      '主升期': { color: 'text-orange-400', bg: 'bg-orange-500/10' },
      '高潮期': { color: 'text-red-400', bg: 'bg-red-500/10' },
      '分歧期': { color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
      '退潮期': { color: 'text-purple-400', bg: 'bg-purple-500/10' },
    }
    return map[stage] || { color: 'text-muted-foreground', bg: 'bg-muted' }
  }

  const emotion = marketReview?.emotion
  const topBoards = marketReview?.top_boards || []
  const zhabanRate = marketReview?.zhaban_rate
  const limitUpCount = marketReview?.limit_up_count ?? 0
  const limitDownCount = marketReview?.limit_down_count ?? 0

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/50">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-sm">大盘概况</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex justify-center py-24">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* 大盘指数 */}
            {overview && (
              <Card className="bg-gradient-to-br from-card to-card/50 border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-primary" />
                      <h2 className="text-base font-semibold">{overview['指数'] || '上证指数'}</h2>
                    </div>
                    <Badge variant={overview['涨跌幅'] >= 0 ? 'up' : 'down'}>
                      {overview['涨跌幅'] >= 0 ? '+' : ''}{overview['涨跌幅']?.toFixed(2)}%
                    </Badge>
                  </div>
                  <div className="text-3xl font-bold mb-4">
                    {overview['最新价']?.toFixed(2) ?? '--'}
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground text-xs">最高</span>
                      <div className="font-medium">{overview['最高']?.toFixed(2) ?? '--'}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs">最低</span>
                      <div className="font-medium">{overview['最低']?.toFixed(2) ?? '--'}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 情绪周期 + 涨停/跌停统计 */}
            {emotion && (
              <Card className={`${getEmotionStyle(emotion.stage).bg} border-0`}>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="w-5 h-5" />
                    <span className="text-sm font-medium">市场情绪</span>
                  </div>
                  <div className={`text-2xl font-bold mb-3 ${getEmotionStyle(emotion.stage).color}`}>
                    {emotion.stage}
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">{emotion.description}</p>
                  {emotion.suggestion && (
                    <div className="text-sm text-muted-foreground mb-4">
                      💡 {emotion.suggestion}
                    </div>
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground text-xs mb-0.5">涨停</div>
                      <div className="font-semibold text-red-400">{limitUpCount} 只</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs mb-0.5">跌停</div>
                      <div className="font-semibold text-green-400">{limitDownCount} 只</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs mb-0.5">炸板率</div>
                      <div className="font-semibold">
                        {zhabanRate >= 0 ? `${(zhabanRate * 100).toFixed(1)}%` : '--'}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs mb-0.5">连板高度</div>
                      <div className="font-semibold">
                        {topBoards.length > 0 ? `${topBoards[0].boards} 板` : '--'}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 龙头股识别 */}
            {dragonLeaders && (
              <DragonLeaderCard data={dragonLeaders} />
            )}

            {/* 板块轮动分析 */}
            {sectorRotation && (
              <SectorRotationCard data={sectorRotation} />
            )}

            {/* 连板高度排名 */}
            {topBoards.length > 0 && (
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <CandlestickChart className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm">连板高度排名</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/50">
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">#</th>
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">代码</th>
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">名称</th>
                          <th className="text-right px-4 py-2 text-muted-foreground font-medium">连板</th>
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">行业</th>
                          <th className="text-right px-4 py-2 text-muted-foreground font-medium">封单(亿)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topBoards.map((stock: any, i: number) => (
                          <tr
                            key={stock.symbol}
                            className="border-b border-border/30 hover:bg-accent/30 transition-colors"
                          >
                            <td className="px-4 py-2.5 text-muted-foreground">{i + 1}</td>
                            <td className="px-4 py-2.5">{stock.symbol}</td>
                            <td className="px-4 py-2.5">
                              <button
                                onClick={() => router.push(`/stock?symbol=${stock.symbol}`)}
                                className="hover:text-primary transition-colors"
                              >
                                {stock.name}
                              </button>
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              <span className="text-red-400 font-semibold">{stock.boards}板</span>
                            </td>
                            <td className="px-4 py-2.5 text-muted-foreground">{stock.industry || '--'}</td>
                            <td className="px-4 py-2.5 text-right">{stock.fengdan?.toFixed(2) || '--'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 板块资金流向 Top 10 */}
            {sectorFlow.length > 0 && (
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm">板块资金流向</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/50">
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">#</th>
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">板块</th>
                          <th className="text-right px-4 py-2 text-muted-foreground font-medium">涨跌幅</th>
                          <th className="text-right px-4 py-2 text-muted-foreground font-medium">主力净流入</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sectorFlow.slice(0, 10).map((s: any, i: number) => (
                          <tr
                            key={i}
                            className="border-b border-border/30 hover:bg-accent/30 transition-colors"
                          >
                            <td className="px-4 py-2.5 text-muted-foreground">{i + 1}</td>
                            <td className="px-4 py-2.5">{s['名称'] || '--'}</td>
                            <td className={`px-4 py-2.5 text-right ${parseFloat(s['今日涨跌幅'] || 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                              {s['今日涨跌幅'] ? `${parseFloat(s['今日涨跌幅']).toFixed(2)}%` : '--'}
                            </td>
                            <td className={`px-4 py-2.5 text-right ${parseFloat(s['主力净流入-净额'] || 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                              {s['主力净流入-净额'] ? `${(parseFloat(s['主力净流入-净额']) / 1e8).toFixed(2)}亿` : '--'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        )}
      </main>
    </div>
  )
}
