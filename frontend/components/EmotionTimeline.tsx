'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Clock, ChevronLeft, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { API_BASE } from '@/lib/api'
import { emotionColor } from '@/lib/types'

interface HistoryRecord {
  date: string
  emotion_stage: string
  ai_review_text: string
}

interface Props {
  limit?: number
}

const STAGE_LABELS: Record<string, string> = {
  '冰点期': '冰点', '修复期': '修复', '主升期': '主升',
  '高潮期': '高潮', '分歧期': '分歧', '退潮期': '退潮',
}

export default function EmotionTimeline({ limit = 30 }: Props) {
  const [records, setRecords] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState<number | null>(null)
  const [scroll, setScroll] = useState(0)

  useEffect(() => {
    fetch(`${API_BASE}/api/analysis/rag/history?limit=${limit}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.records) {
          setRecords(data.records.reverse()) // oldest first
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [limit])

  if (loading) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-8 flex items-center justify-center">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-5 h-5 rounded-full border-2 border-border border-t-primary" />
        </CardContent>
      </Card>
    )
  }

  if (records.length === 0) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          暂无历史情绪数据
        </CardContent>
      </Card>
    )
  }

  const maxScroll = Math.max(0, records.length - 14)

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm">情绪周期时间轴</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setScroll(Math.max(0, scroll - 3))}
              disabled={scroll === 0}
              className="p-1 rounded hover:bg-accent disabled:opacity-30"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setScroll(Math.min(maxScroll, scroll + 3))}
              disabled={scroll >= maxScroll}
              className="p-1 rounded hover:bg-accent disabled:opacity-30"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        {/* Timeline line */}
        <div className="relative" style={{ height: 120 }}>
          {/* Base line */}
          <div className="absolute top-16 left-0 right-0 h-0.5 bg-border" />

          {/* Stage segments */}
          <div className="absolute top-0 left-0 right-0 flex" style={{
            transform: `translateX(${-scroll * 52}px)`,
            transition: 'transform 0.3s ease',
          }}>
            {records.map((r, i) => {
              const color = emotionColor(r.emotion_stage)
              const label = STAGE_LABELS[r.emotion_stage] || r.emotion_stage
              const isHovered = hovered === i
              return (
                <div
                  key={r.date}
                  className="relative flex flex-col items-center"
                  style={{ width: 52, flexShrink: 0 }}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {/* Stage bar */}
                  <motion.div
                    animate={{ height: isHovered ? 64 : 40, y: isHovered ? 0 : 12 }}
                    className="w-2.5 rounded-full cursor-pointer"
                    style={{ background: color, marginTop: 20 }}
                  />
                  {/* Dot on line */}
                  <div className="absolute top-[60px] w-2.5 h-2.5 rounded-full border-2 z-10"
                    style={{ background: '#0D1117', borderColor: color }} />
                  {/* Date label */}
                  <div className="absolute top-[76px] text-[10px] text-muted-foreground whitespace-nowrap"
                    style={{ color: isHovered ? '#E6EDF3' : undefined }}>
                    {r.date.slice(5)}
                  </div>

                  {/* Hover tooltip */}
                  {isHovered && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute -top-2 left-1/2 -translate-x-1/2 z-20 px-3 py-2 rounded-lg text-xs whitespace-nowrap"
                      style={{ background: color + '22', border: `1px solid ${color}44`, color }}
                    >
                      <div className="font-semibold">{r.emotion_stage}</div>
                      <div className="text-muted-foreground">{r.date}</div>
                    </motion.div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 justify-center mt-2 pt-3 border-t border-border/50">
          {Object.entries(STAGE_LABELS).map(([stage, label]) => (
            <div key={stage} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: emotionColor(stage) }} />
              <span className="text-[10px] text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
