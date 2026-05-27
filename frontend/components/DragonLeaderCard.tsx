'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Crown, TrendingUp, Zap, Clock, Building, BarChart3 } from 'lucide-react'

interface Leader {
  symbol: string
  name: string
  boards: number
  fengdan: number
  turnover: number
  industry: string
  first_time: string
  score: number
  score_details?: Record<string, number>
  main_flow?: number
}

interface DragonLeaderData {
  leaders: Leader[]
  top_leader: Leader | null
  sector_leaders: Leader[]
  日内龙头: Leader | null
  连板高标: Leader[]
  market_summary: {
    涨停数: number
    连板股数: number
    最高板: number
  }
}

interface Props {
  data: DragonLeaderData
}

export default function DragonLeaderCard({ data }: Props) {
  const router = useRouter()

  if (!data?.leaders?.length) return null

  const { top_leader, 日内龙头, 连板高标, sector_leaders, market_summary } = data

  return (
    <Card className="border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-card/50 overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Crown className="w-4 h-4 text-amber-400" />
          <CardTitle className="text-sm">龙头股识别</CardTitle>
          <span className="text-xs text-muted-foreground ml-auto">
            涨停{market_summary.涨停数}只 · 连板{market_summary.连板股数}只
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 总龙头 */}
        {top_leader && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-center gap-2 mb-1">
              <Crown className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs font-medium text-amber-400">总龙头</span>
            </div>
            <button
              onClick={() => router.push(`/stock?symbol=${top_leader.symbol}`)}
              className="text-left w-full"
            >
              <div className="text-lg font-bold text-amber-300">{top_leader.name}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {top_leader.symbol} · {top_leader.industry} · {top_leader.boards}板
                {top_leader.fengdan > 0 && ` · 封单${top_leader.fengdan.toFixed(2)}亿`}
              </div>
            </button>
          </div>
        )}

        {/* 快照信息 */}
        <div className="grid grid-cols-3 gap-3 text-xs">
          {日内龙头 && (
            <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-1 mb-1">
                <Clock className="w-3 h-3 text-blue-400" />
                <span className="text-blue-400 font-medium">日内龙头</span>
              </div>
              <button
                onClick={() => router.push(`/stock?symbol=${日内龙头.symbol}`)}
                className="text-left hover:text-primary transition-colors"
              >
                <div className="font-medium">{日内龙头.name}</div>
                <div className="text-muted-foreground">{日内龙头.first_time}封板</div>
              </button>
            </div>
          )}

          {连板高标.length > 0 && (
            <div className="p-2 rounded-md bg-purple-500/10 border border-purple-500/20">
              <div className="flex items-center gap-1 mb-1">
                <Zap className="w-3 h-3 text-purple-400" />
                <span className="text-purple-400 font-medium">连板高标</span>
              </div>
              <div className="space-y-0.5">
                {连板高标.slice(0, 3).map((s) => (
                  <button
                    key={s.symbol}
                    onClick={() => router.push(`/stock?symbol=${s.symbol}`)}
                    className="block hover:text-primary transition-colors"
                  >
                    {s.name}{' '}
                    <span className="text-purple-400">{s.boards}板</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="p-2 rounded-md bg-green-500/10 border border-green-500/20">
            <div className="flex items-center gap-1 mb-1">
              <BarChart3 className="w-3 h-3 text-green-400" />
              <span className="text-green-400 font-medium">市场概况</span>
            </div>
            <div className="text-muted-foreground space-y-0.5">
              <div>涨停 {market_summary.涨停数} 只</div>
              <div>最高 {market_summary.最高板} 板</div>
            </div>
          </div>
        </div>

        {/* 板块龙头 */}
        {sector_leaders.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-2">
              <Building className="w-3 h-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground font-medium">板块龙头</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {sector_leaders.slice(0, 8).map((s) => (
                <button
                  key={s.symbol}
                  onClick={() => router.push(`/stock?symbol=${s.symbol}`)}
                  className="text-left p-2 rounded-md bg-accent/30 hover:bg-accent/50 transition-colors"
                >
                  <div className="text-xs font-medium">{s.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {s.industry}
                    <span className="text-red-400 ml-1">{s.boards}板</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 全体排名列表 */}
        <div>
          <div className="flex items-center gap-1 mb-2">
            <TrendingUp className="w-3 h-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground font-medium">龙头排名 Top 10</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50 text-muted-foreground">
                  <th className="text-left px-2 py-1.5 font-medium">#</th>
                  <th className="text-left px-2 py-1.5 font-medium">名称</th>
                  <th className="text-center px-2 py-1.5 font-medium">连板</th>
                  <th className="text-center px-2 py-1.5 font-medium">综合分</th>
                  <th className="text-left px-2 py-1.5 font-medium">行业</th>
                </tr>
              </thead>
              <tbody>
                {data.leaders.slice(0, 10).map((s, i) => (
                  <tr
                    key={s.symbol}
                    className="border-b border-border/30 hover:bg-accent/30 transition-colors"
                  >
                    <td className="px-2 py-2 text-muted-foreground">{i + 1}</td>
                    <td className="px-2 py-2">
                      <button
                        onClick={() => router.push(`/stock?symbol=${s.symbol}`)}
                        className="hover:text-primary transition-colors"
                      >
                        {s.name}
                      </button>
                    </td>
                    <td className="px-2 py-2 text-center text-red-400 font-medium">{s.boards}板</td>
                    <td className="px-2 py-2 text-center">{s.score?.toFixed(2) ?? '--'}</td>
                    <td className="px-2 py-2 text-muted-foreground">{s.industry || '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
