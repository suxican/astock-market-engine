'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, Zap, Users, Building, BarChart3, AlertTriangle } from 'lucide-react'

interface LimitUpAnalysis {
  is_limit_up: boolean
  type: string | null
  confidence: string | null
  description: string
  signals: string[]
  lhb: {
    has_lhb: boolean
    净买入: number
    机构净买入: number
    has_hotel: boolean
    hotel_names: string
    has_institution: boolean
    上榜原因?: string
  } | null
}

interface LimitUpCardProps {
  analysis: LimitUpAnalysis
  symbol: string
  name: string
}

const typeConfig: Record<string, { label: string; icon: any; color: string }> = {
  '政策催化': { label: '政策催化', icon: Building, color: 'text-blue-400' },
  '资金驱动': { label: '资金驱动', icon: Zap, color: 'text-yellow-400' },
  '情绪炒作': { label: '情绪炒作', icon: BarChart3, color: 'text-orange-400' },
  '龙头带动': { label: '龙头带动', icon: Users, color: 'text-purple-400' },
  '基本面驱动': { label: '基本面驱动', icon: TrendingUp, color: 'text-green-400' },
}

const confidenceColor = (c: string | null) => {
  if (c === '高') return 'bg-green-500/15 text-green-400'
  if (c === '中') return 'bg-yellow-500/15 text-yellow-400'
  return 'bg-gray-500/15 text-gray-400'
}

export default function LimitUpCard({ analysis, symbol, name }: LimitUpCardProps) {
  if (!analysis.is_limit_up) return null

  const config = typeConfig[analysis.type || ''] || { label: analysis.type || '未知', icon: AlertTriangle, color: 'text-muted-foreground' }
  const Icon = config.icon

  return (
    <Card className="border-red-500/20 bg-gradient-to-br from-red-500/5 to-card/50 overflow-hidden">
      <CardContent className="p-5">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-red-400" />
            <span className="text-sm font-semibold text-red-400">涨停原因分析</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="up" className="text-xs px-2 py-0.5">
              {name} {symbol}
            </Badge>
          </div>
        </div>

        {/* 类型标签 */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-1.5">
            <Icon className={`w-4 h-4 ${config.color}`} />
            <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full ${confidenceColor(analysis.confidence)}`}>
            {analysis.confidence}置信度
          </span>
        </div>

        {/* 分析文本 */}
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          {analysis.description}
        </p>

        {/* 信号列表 */}
        {analysis.signals.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {analysis.signals.map((s, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 rounded-md bg-red-500/10 text-red-300/80"
              >
                {s}
              </span>
            ))}
          </div>
        )}

        {/* 龙虎榜 */}
        {analysis.lhb?.has_lhb && (
          <div className="text-xs text-muted-foreground space-y-1 pt-3 border-t border-border/50">
            <div className="flex items-center gap-2">
              <span>龙虎榜净买入：</span>
              <span className={analysis.lhb.净买入 >= 0 ? 'text-red-400' : 'text-green-400'}>
                {analysis.lhb.净买入 >= 0 ? '+' : ''}{analysis.lhb.净买入?.toFixed(0)} 万元
              </span>
            </div>
            {analysis.lhb.has_institution && (
              <div>机构净买入：{analysis.lhb.机构净买入?.toFixed(0)} 万元</div>
            )}
            {analysis.lhb.has_hotel && (
              <div>知名游资席位：{analysis.lhb.hotel_names}</div>
            )}
            {analysis.lhb.上榜原因 && (
              <div>上榜原因：{analysis.lhb.上榜原因}</div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
