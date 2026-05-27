'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Lightbulb, TrendingUp, TrendingDown, AlertTriangle, BarChart3, Zap, DollarSign } from 'lucide-react'

interface ExpectationGapAnalysis {
  has_gap: boolean
  gap_type: string | null
  confidence: string | null
  description: string
  signals: string[]
  data_summary: Record<string, string>
}

interface ExpectationGapCardProps {
  analysis: ExpectationGapAnalysis
  symbol: string
  name: string
}

const gapConfig: Record<string, { label: string; icon: any; color: string; desc: string }> = {
  '利好不涨': { label: '利好不涨', icon: TrendingDown, color: 'text-orange-400', desc: '有利好但股价不涨' },
  '业绩增长反而跌': { label: '业绩增长反而跌', icon: BarChart3, color: 'text-red-400', desc: '业绩好但股价跌' },
  '利空落地反而涨': { label: '利空落地反而涨', icon: TrendingUp, color: 'text-green-400', desc: '利空出尽变利好' },
  '放量涨次日跌': { label: '放量涨次日跌', icon: Zap, color: 'text-yellow-400', desc: '放量拉高后出货' },
  '缩量上涨': { label: '缩量上涨', icon: DollarSign, color: 'text-blue-400', desc: '缩量上行主力控盘' },
  '高位放量滞涨': { label: '高位放量滞涨', icon: AlertTriangle, color: 'text-purple-400', desc: '高位放量出货信号' },
}

const confidenceColor = (c: string | null) => {
  if (c === '高') return 'bg-yellow-500/15 text-yellow-400'
  if (c === '中') return 'bg-blue-500/15 text-blue-400'
  return 'bg-gray-500/15 text-gray-400'
}

export default function ExpectationGapCard({ analysis, symbol, name }: ExpectationGapCardProps) {
  if (!analysis.has_gap) return null

  const config = gapConfig[analysis.gap_type || ''] || {
    label: analysis.gap_type || '预期差',
    icon: Lightbulb,
    color: 'text-muted-foreground',
    desc: '',
  }
  const Icon = config.icon

  return (
    <Card className="border-yellow-500/20 bg-gradient-to-br from-yellow-500/5 to-card/50 overflow-hidden">
      <CardContent className="p-5">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-semibold text-yellow-400">预期差分析</span>
          </div>
          <Badge variant="outline" className="text-xs px-2 py-0.5">
            {name} {symbol}
          </Badge>
        </div>

        {/* 类型标签 */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-yellow-500/10">
            <Icon className={`w-4 h-4 ${config.color}`} />
            <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full ${confidenceColor(analysis.confidence)}`}>
            {analysis.confidence}置信度
          </span>
          {config.desc && (
            <span className="text-xs text-muted-foreground">{config.desc}</span>
          )}
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
                className="text-xs px-2 py-1 rounded-md bg-yellow-500/10 text-yellow-300/80"
              >
                {s}
              </span>
            ))}
          </div>
        )}

        {/* 数据摘要 */}
        {analysis.data_summary && Object.keys(analysis.data_summary).length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-3 border-t border-border/50">
            {Object.entries(analysis.data_summary).map(([key, val]) => (
              <div key={key}>
                <div className="text-muted-foreground mb-0.5">{key}</div>
                <div className="font-medium">{val}</div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
