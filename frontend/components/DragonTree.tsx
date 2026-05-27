'use client'

import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Crown, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Leader {
  symbol: string
  name: string
  boards: number
  fengdan: number
  industry: string
  score: number
}

interface DragonData {
  leaders: Leader[]
  top_leader: Leader | null
  sector_leaders: Leader[]
  日内龙头: Leader | null
  连板高标: Leader[]
  market_summary: { 涨停数: number; 连板股数: number; 最高板: number }
}

interface Props {
  data: DragonData
}

// Board height → color gradient (higher = hotter)
function boardColor(boards: number): string {
  if (boards >= 8) return '#FF6B6B'
  if (boards >= 5) return '#F0883E'
  if (boards >= 3) return '#EAB308'
  return '#58A6FF'
}

function boardBg(boards: number): string {
  if (boards >= 8) return '#3A1E1E'
  if (boards >= 5) return '#2A1E10'
  if (boards >= 3) return '#2A2010'
  return '#102A3A'
}

export default function DragonTree({ data }: Props) {
  const router = useRouter()

  if (!data?.leaders?.length) return null

  const { top_leader, 日内龙头, 连板高标, sector_leaders, market_summary } = data

  // Group leaders by board count for the tree
  const byBoards: Record<number, Leader[]> = {}
  data.leaders.forEach(l => {
    if (!byBoards[l.boards]) byBoards[l.boards] = []
    byBoards[l.boards].push(l)
  })
  const boardLevels = Object.keys(byBoards).map(Number).sort((a, b) => b - a)

  const maxCount = Math.max(...boardLevels.map(b => byBoards[b].length), 1)

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Crown className="w-4 h-4 text-amber-400" />
          <CardTitle className="text-sm">龙头晋级树</CardTitle>
          <span className="text-xs text-muted-foreground ml-auto">
            {market_summary.涨停数}涨停 · 最高{market_summary.最高板}板
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {/* Tree visualization */}
        <div className="space-y-1">
          {boardLevels.map((boards, levelIdx) => {
            const leaders = byBoards[boards]
            const isTop = levelIdx === 0
            return (
              <div key={boards}>
                {/* Level header */}
                <div className="flex items-center gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold"
                    style={{ background: boardBg(boards), color: boardColor(boards) }}>
                    <TrendingUp className="w-3 h-3" />
                    {boards}板
                  </div>
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-[10px] text-muted-foreground">{leaders.length}只</span>
                </div>

                {/* Level items */}
                <div className="grid gap-1.5 mb-2" style={{
                  gridTemplateColumns: `repeat(${Math.min(leaders.length, 6)}, minmax(0, 1fr))`
                }}>
                  {leaders.slice(0, 8).map((l, i) => (
                    <motion.button
                      key={l.symbol}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: levelIdx * 0.05 + i * 0.03 }}
                      onClick={() => router.push(`/stock?symbol=${l.symbol}`)}
                      className="text-left p-2 rounded-lg border transition-all hover:scale-[1.02]"
                      style={{
                        background: boardBg(boards),
                        borderColor: boardColor(boards) + '33',
                        ...(isTop && i === 0 ? {
                          borderColor: boardColor(boards),
                          boxShadow: `0 0 12px ${boardColor(boards)}22`,
                        } : {}),
                      }}
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-xs font-semibold truncate" style={{ color: '#E6EDF3' }}>
                          {l.name}
                        </span>
                        {isTop && i === 0 && (
                          <Crown className="w-3 h-3 text-amber-400 shrink-0" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground">{l.symbol}</span>
                        {l.fengdan > 0 && (
                          <span className="text-[10px]" style={{ color: boardColor(boards) }}>
                            封{l.fengdan.toFixed(1)}亿
                          </span>
                        )}
                      </div>
                      {l.industry && (
                        <div className="text-[10px] text-muted-foreground mt-0.5">{l.industry}</div>
                      )}
                    </motion.button>
                  ))}
                </div>

                {/* Connector to next level */}
                {levelIdx < boardLevels.length - 1 && (
                  <div className="flex justify-center py-0.5">
                    <svg width="20" height="12" className="text-border">
                      <line x1="10" y1="0" x2="10" y2="8" stroke="currentColor" strokeWidth="1" />
                      <line x1="0" y1="8" x2="20" y2="8" stroke="currentColor" strokeWidth="1" />
                      <line x1="0" y1="8" x2="4" y2="12" stroke="currentColor" strokeWidth="1" />
                      <line x1="20" y1="8" x2="16" y2="12" stroke="currentColor" strokeWidth="1" />
                    </svg>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
