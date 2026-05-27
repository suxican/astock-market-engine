'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, BarChart3, Loader2, Brain, TrendingUp, TrendingDown, CandlestickChart, Activity, MessageSquareText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import DragonLeaderCard from '@/components/DragonLeaderCard'
import SectorRotationCard from '@/components/SectorRotationCard'
import HistoricalComparison from '@/components/HistoricalComparison'
import { API_BASE, api } from '@/lib/api'
import type { MarketScores } from '@/lib/types'
import { emotionColor, riskColor } from '@/lib/types'

export default function ReviewPage() {
  const router = useRouter()
  const [marketReview, setMarketReview] = useState<any>(null)
  const [overview, setOverview] = useState<any>(null)
  const [dragonLeaders, setDragonLeaders] = useState<any>(null)
  const [sectorRotation, setSectorRotation] = useState<any>(null)
  const [similarDays, setSimilarDays] = useState<any>(null)
  const [marketScores, setMarketScores] = useState<MarketScores | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/analysis/market-review`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/stock/market-overview`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/analysis/dragon-leaders`, { method: 'POST' }).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/analysis/sector-rotation`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/analysis/rag/similar-today`).then(r => r.ok ? r.json() : null),
    ])
      .then(async ([review, ov, leaders, rotation, similarToday]) => {
        setMarketReview(review)
        setOverview(ov)
        setDragonLeaders(leaders)
        setSectorRotation(rotation)
        setSimilarDays(similarToday?.similar_days || null)

        // V8 结构化评分
        try {
          const sc = await api.getMarketScores()
          setMarketScores(sc)
        } catch {}
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

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

  const renderMarkdown = (text: string) => {
    const html = text
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>')
    return (
      <div
        className="review-content leading-relaxed text-sm"
        dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
      />
    )
  }

  const emotion = marketReview?.emotion
  const topBoards = marketReview?.top_boards || []
  const zhabanRate = marketReview?.zhaban_rate
  const limitUpCount = marketReview?.limit_up_count ?? 0
  const limitDownCount = marketReview?.limit_down_count ?? 0
  const aiReview = marketReview?.ai_review

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/50">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-sm">AI 市场复盘</span>
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
            {/* 大盘概览 */}
            {overview && (
              <Card className="bg-gradient-to-br from-card to-card/50 border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity className="w-5 h-5 text-primary" />
                    <span className="text-sm font-medium">大盘概览</span>
                  </div>
                  <div className="text-3xl font-bold mb-1">
                    {overview['最新价']?.toFixed(2) ?? '--'}
                  </div>
                  <div className={`text-sm font-medium ${overview['涨跌幅'] >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {overview['指数'] || '上证指数'} {overview['涨跌幅'] >= 0 ? '+' : ''}{overview['涨跌幅']?.toFixed(2)}%
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 情绪周期 */}
            {emotion ? (
              <Card className={`${getEmotionStyle(emotion.stage).bg} border-0`}>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Brain className="w-5 h-5" />
                    <span className="text-sm font-medium">情绪周期</span>
                  </div>
                  <div className={`text-2xl font-bold mb-2 ${getEmotionStyle(emotion.stage).color}`}>
                    {emotion.stage}
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">{emotion.description}</p>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm pt-3 border-t border-border/30">
                    <div>
                      <div className="text-muted-foreground text-xs">涨停</div>
                      <div className="font-semibold text-lg text-red-400">{limitUpCount}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">跌停</div>
                      <div className="font-semibold text-lg text-green-400">{limitDownCount}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">炸板率</div>
                      <div className="font-semibold text-lg">{zhabanRate >= 0 ? `${(zhabanRate * 100).toFixed(1)}%` : '--'}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">连板高度</div>
                      <div className="font-semibold text-lg">{topBoards.length > 0 ? `${topBoards[0].boards} 板` : '--'}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-border/50">
                <CardContent className="p-6 text-center text-muted-foreground text-sm">
                  今日非交易日或数据获取中
                </CardContent>
              </Card>
            )}

            {/* V8 结构化市场评分 */}
            {marketScores && (
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm">V8 结构化评分</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-3 rounded-lg bg-accent/10">
                      <div className="text-xs text-muted-foreground mb-1">情绪</div>
                      <div className="text-xl font-bold" style={{ color: emotionColor(marketScores.emotion.stage) }}>
                        {marketScores.emotion.score}
                      </div>
                      <Badge style={{
                        background: emotionColor(marketScores.emotion.stage) + '22',
                        color: emotionColor(marketScores.emotion.stage),
                        border: 'none'
                      }} className="text-[10px]">{marketScores.emotion.stage}</Badge>
                    </div>
                    <div className="p-3 rounded-lg bg-accent/10">
                      <div className="text-xs text-muted-foreground mb-1">龙头</div>
                      <div className="text-xl font-bold text-[#F0883E]">
                        {marketScores.dragon_intensity.score}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {marketScores.dragon_intensity.high_board_count} 只高标
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-accent/10">
                      <div className="text-xs text-muted-foreground mb-1">风险</div>
                      <div className="text-xl font-bold" style={{ color: riskColor(marketScores.risk.level) }}>
                        {marketScores.risk.score}
                      </div>
                      <Badge style={{
                        background: riskColor(marketScores.risk.level) + '22',
                        color: riskColor(marketScores.risk.level),
                        border: 'none'
                      }} className="text-[10px]">{marketScores.risk.level}风险</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 历史相似日对比 */}
            {similarDays && similarDays.length > 0 && (
              <HistoricalComparison similarDays={similarDays} />
            )}

            {/* 操作建议 */}
            {emotion?.suggestion && (
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">今日策略建议</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{emotion.suggestion}</p>
                </CardContent>
              </Card>
            )}

            {/* AI 复盘分析 */}
            {aiReview && (
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <MessageSquareText className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm">AI 复盘分析</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {renderMarkdown(aiReview)}
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
                          <th className="text-left px-4 py-2 text-muted-foreground font-medium">所属行业</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topBoards.slice(0, 8).map((s: any, i: number) => (
                          <tr
                            key={s.symbol}
                            className="border-b border-border/30 hover:bg-accent/30 transition-colors"
                          >
                            <td className="px-4 py-2.5 text-muted-foreground">{i + 1}</td>
                            <td className="px-4 py-2.5">{s.symbol}</td>
                            <td className="px-4 py-2.5">
                              <button
                                onClick={() => router.push(`/stock?symbol=${s.symbol}`)}
                                className="hover:text-primary transition-colors"
                              >
                                {s.name}
                              </button>
                            </td>
                            <td className="px-4 py-2.5 text-right font-semibold text-red-400">
                              {s.boards}板
                            </td>
                            <td className="px-4 py-2.5 text-muted-foreground">{s.industry || '--'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 说明 */}
            <div className="text-center text-xs text-muted-foreground pb-8">
              * 数据基于 akshare 实时数据，仅供参考，不构成投资建议
            </div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
