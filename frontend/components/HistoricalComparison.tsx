'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { History, Loader2 } from 'lucide-react'

interface SimilarDay {
  date: string
  score: number
  emotion_stage?: string
  limit_up_count?: number
  limit_down_count?: number
  board_height?: number
}

interface Props {
  similarDays: SimilarDay[]
  loading?: boolean
}

const emotionColors: Record<string, string> = {
  '冰点期': 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  '修复期': 'text-green-400 bg-green-500/10 border-green-500/30',
  '主升期': 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  '高潮期': 'text-red-400 bg-red-500/10 border-red-500/30',
  '分歧期': 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  '退潮期': 'text-purple-400 bg-purple-500/10 border-purple-500/30',
}

function getEmotionClass(stage?: string): string {
  return emotionColors[stage || ''] || 'text-muted-foreground bg-muted border-border/30'
}

export default function HistoricalComparison({ similarDays, loading }: Props) {
  if (loading) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-6 flex justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (!similarDays || similarDays.length === 0) {
    return null
  }

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm">历史相似日对比</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {similarDays.map((day, i) => (
          <div
            key={day.date}
            className={`rounded-lg border p-3 ${getEmotionClass(day.emotion_stage)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{day.date}</span>
              <span className="text-xs text-muted-foreground">
                相似度 {(day.score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">涨停</span>
                <div className="font-semibold text-red-400">{day.limit_up_count ?? '--'}</div>
              </div>
              <div>
                <span className="text-muted-foreground">跌停</span>
                <div className="font-semibold text-green-400">{day.limit_down_count ?? '--'}</div>
              </div>
              <div>
                <span className="text-muted-foreground">连板</span>
                <div className="font-semibold">{day.board_height ?? '--'}板</div>
              </div>
              <div>
                <span className="text-muted-foreground">情绪</span>
                <div className="font-semibold">{day.emotion_stage ?? '--'}</div>
              </div>
            </div>
          </div>
        ))}
        <div className="text-xs text-muted-foreground text-center pt-1">
          AI 复盘已参考以上 {similarDays.length} 个历史相似日数据
        </div>
      </CardContent>
    </Card>
  )
}
