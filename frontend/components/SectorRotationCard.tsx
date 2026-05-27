'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { TrendingUp, TrendingDown, RefreshCw, Activity, BarChart3 } from 'lucide-react'

interface SectorRecord {
  name: string
  change: number
  flow: number
  flow_yi?: number
}

interface RotationData {
  industry: {
    加强: SectorRecord[]
    持续: SectorRecord[]
    退潮: SectorRecord[]
    反弹: SectorRecord[]
  }
  concept: {
    加强: SectorRecord[]
    持续: SectorRecord[]
    退潮: SectorRecord[]
    反弹: SectorRecord[]
  }
  board_distribution: {
    name: string
    涨停数: number
    flow: number
    change: number
  }[]
  最强板块: string
  最强板块涨停数: number
}

interface Props {
  data: RotationData
}

function SectorSection({ records, title, icon, color }: {
  records: SectorRecord[]
  title: string
  icon: React.ReactNode
  color: string
}) {
  if (!records?.length) return null
  return (
    <div className="mb-3">
      <div className={`flex items-center gap-1 mb-1.5 text-xs font-medium ${color}`}>
        {icon}
        <span>{title} ({records.length})</span>
      </div>
      <div className="space-y-1">
        {records.slice(0, 5).map((r, i) => (
          <div key={i} className="flex items-center justify-between text-xs px-2 py-1 rounded bg-accent/30">
            <span className="font-medium truncate max-w-[120px]">{r.name}</span>
            <div className="flex items-center gap-2 shrink-0">
              <span className={r.change >= 0 ? 'text-red-400' : 'text-green-400'}>
                {r.change >= 0 ? '+' : ''}{r.change.toFixed(2)}%
              </span>
              <span className={r.flow >= 0 ? 'text-red-400' : 'text-green-400'}>
                {r.flow >= 0 ? '+' : ''}{r.flow_yi?.toFixed(2) ?? (r.flow / 1e8).toFixed(2)}亿
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function SectorRotationCard({ data }: Props) {
  const [tab, setTab] = useState('industry')

  if (!data?.industry) return null

  const current = tab === 'industry' ? data.industry : data.concept
  const hasData = current?.加强?.length > 0 || current?.退潮?.length > 0

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm">板块轮动分析</CardTitle>
          {data.最强板块 && (
            <span className="text-xs text-muted-foreground ml-auto">
              最强板块: <span className="text-red-400">{data.最强板块}</span>
              <span className="text-muted-foreground"> · {data.最强板块涨停数}只涨停</span>
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList className="mb-3">
            <TabsTrigger value="industry">行业板块</TabsTrigger>
            <TabsTrigger value="concept">概念板块</TabsTrigger>
          </TabsList>

          <TabsContent value="industry">
            {hasData ? (
              <>
                <SectorSection
                  records={current.加强}
                  title="加强 (涨幅+资金双正)"
                  icon={<TrendingUp className="w-3 h-3" />}
                  color="text-red-400"
                />
                <SectorSection
                  records={current.反弹}
                  title="反弹 (企稳信号)"
                  icon={<RefreshCw className="w-3 h-3" />}
                  color="text-blue-400"
                />
                <SectorSection
                  records={current.退潮}
                  title="退潮 (跌幅+资金流出)"
                  icon={<TrendingDown className="w-3 h-3" />}
                  color="text-green-400"
                />
              </>
            ) : (
              <div className="text-center text-xs text-muted-foreground py-4">暂无板块轮动数据</div>
            )}
          </TabsContent>

          <TabsContent value="concept">
            {data.concept?.加强?.length > 0 || data.concept?.退潮?.length > 0 ? (
              <>
                <SectorSection
                  records={data.concept.加强}
                  title="加强 (涨幅+资金双正)"
                  icon={<TrendingUp className="w-3 h-3" />}
                  color="text-red-400"
                />
                <SectorSection
                  records={data.concept.反弹}
                  title="反弹 (企稳信号)"
                  icon={<RefreshCw className="w-3 h-3" />}
                  color="text-blue-400"
                />
                <SectorSection
                  records={data.concept.退潮}
                  title="退潮 (跌幅+资金流出)"
                  icon={<TrendingDown className="w-3 h-3" />}
                  color="text-green-400"
                />
              </>
            ) : (
              <div className="text-center text-xs text-muted-foreground py-4">暂无概念板块轮动数据</div>
            )}
          </TabsContent>
        </Tabs>

        {/* 涨停分布 Top 5 */}
        {data.board_distribution?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex items-center gap-1 mb-2">
              <BarChart3 className="w-3 h-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground font-medium">涨停分布</span>
            </div>
            {data.board_distribution.slice(0, 5).map((b, i) => {
              const maxCount = Math.max(...data.board_distribution.map(x => x.涨停数))
              const barWidth = maxCount > 0 ? (b.涨停数 / maxCount) * 100 : 0
              return (
                <div key={i} className="flex items-center gap-2 text-xs mb-1.5">
                  <span className="w-16 truncate text-muted-foreground">{b.name}</span>
                  <div className="flex-1 h-4 rounded bg-accent/30 overflow-hidden">
                    <div
                      className="h-full rounded bg-red-400/40 transition-all"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className="w-6 text-right font-medium">{b.涨停数}</span>
                  <span className={`w-14 text-right ${b.change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {b.change >= 0 ? '+' : ''}{b.change?.toFixed(1)}%
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
