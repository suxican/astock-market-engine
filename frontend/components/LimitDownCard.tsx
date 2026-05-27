'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingDown, Skull, DollarSign, Users, AlertTriangle, Droplet, BarChart3 } from 'lucide-react'

interface LimitDownAnalysis {
  is_limit_down: boolean
  type: string | null
  confidence: string | null
  description: string
  signals: string[]
}

interface LimitDownCardProps {
  analysis: LimitDownAnalysis
  symbol: string
  name: string
}

const typeConfig: Record<string, { label: string; icon: any; color: string }> = {
  '公司暴雷': { label: '公司暴雷', icon: Skull, color: 'text-red-400' },
  '主力出货': { label: '主力出货', icon: DollarSign, color: 'text-orange-400' },
  '板块退潮': { label: '板块退潮', icon: Users, color: 'text-yellow-400' },
  '情绪崩塌': { label: '情绪崩塌', icon: BarChart3, color: 'text-purple-400' },
  '高位补跌': { label: '高位补跌', icon: TrendingDown, color: 'text-blue-400' },
  '流动性危机': { label: '流动性危机', icon: Droplet, color: 'text-cyan-400' },
}

const confidenceColor = (c: string | null) => {
  if (c === '高') return 'bg-green-500/15 text-green-400'
  if (c === '中') return 'bg-yellow-500/15 text-yellow-400'
  return 'bg-gray-500/15 text-gray-400'
}

export default function LimitDownCard({ analysis, symbol, name }: LimitDownCardProps) {
  if (!analysis.is_limit_down) return null

  const config = typeConfig[analysis.type || ''] || { label: analysis.type || '未知', icon: AlertTriangle, color: 'text-muted-foreground' }
  const Icon = config.icon

  return (
    <Card className="border-green-500/20 bg-gradient-to-br from-green-500/5 to-card/50 overflow-hidden">
      <CardContent className="p-5">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-green-400" />
            <span className="text-sm font-semibold text-green-400">跌停原因分析</span>
          </div>
          <Badge variant="down" className="text-xs px-2 py-0.5">
            {name} {symbol}
          </Badge>
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
          <div className="flex flex-wrap gap-2">
            {analysis.signals.map((s, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 rounded-md bg-green-500/10 text-green-300/80"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
