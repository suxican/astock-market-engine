'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Grid3X3, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { API_BASE } from '@/lib/api'

interface SectorStat {
  sector: string
  limit_up: number
  zhaban: number
  total: number
  zhaban_rate: number
  avg_boards: number
}

// Color scale: green (safe) → yellow → orange → red (dangerous)
function heatColor(rate: number): string {
  if (rate >= 0.5) return '#F85149'
  if (rate >= 0.35) return '#F0883E'
  if (rate >= 0.2) return '#EAB308'
  if (rate > 0) return '#3FB950'
  return '#58A6FF' // 0% zhaban = blue (perfect)
}

function heatBg(rate: number): string {
  if (rate >= 0.5) return '#3A1E1E'
  if (rate >= 0.35) return '#2A1E10'
  if (rate >= 0.2) return '#2A2010'
  if (rate > 0) return '#1A3A27'
  return '#102A3A'
}

export default function ZhabanHeatmap() {
  const [sectors, setSectors] = useState<SectorStat[]>([])
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState<number | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/analysis/sector-stats`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.sectors) setSectors(data.sectors)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

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

  if (sectors.length === 0) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          暂无板块数据（非交易日或数据获取中）
        </CardContent>
      </Card>
    )
  }

  const maxTotal = Math.max(...sectors.map(s => s.total), 1)
  const maxBoards = Math.max(...sectors.map(s => s.avg_boards), 1)

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Grid3X3 className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm">炸板热力图</CardTitle>
          <span className="text-xs text-muted-foreground ml-auto">
            {sectors.length} 个板块
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {/* Column headers */}
        <div className="flex items-center gap-2 mb-2 px-2">
          <div className="w-20 shrink-0" />
          <div className="flex-1 grid grid-cols-4 gap-1.5">
            {['涨停数', '炸板率', '炸板数', '均板'].map(h => (
              <div key={h} className="text-[10px] text-muted-foreground text-center">{h}</div>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          {sectors.map((s, i) => {
            const color = heatColor(s.zhaban_rate)
            const bg = heatBg(s.zhaban_rate)
            const isHovered = hovered === i
            return (
              <motion.div
                key={s.sector}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
                className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-default transition-all"
                style={{
                  background: isHovered ? bg : 'transparent',
                  border: isHovered ? `1px solid ${color}33` : '1px solid transparent',
                }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Sector name */}
                <div className="w-20 shrink-0 text-xs truncate" style={{ color: isHovered ? '#E6EDF3' : '#8B949E' }}>
                  {s.sector}
                </div>

                {/* Metrics grid */}
                <div className="flex-1 grid grid-cols-4 gap-1.5 text-center text-xs">
                  {/* Limit up count → bar */}
                  <div className="flex items-center justify-center">
                    <div className="flex items-center gap-1">
                      <div className="h-3 rounded-sm bg-[#3FB950] opacity-60"
                        style={{ width: `${Math.max(4, (s.limit_up / maxTotal) * 40)}px` }} />
                      <span className="font-mono text-[#3FB950]">{s.limit_up}</span>
                    </div>
                  </div>

                  {/* Zhaban rate → heat color */}
                  <div className="flex items-center justify-center gap-1">
                    <div className="w-8 h-3 rounded-sm" style={{ background: color, opacity: 0.7 }} />
                    <span className="font-mono text-[11px]" style={{ color }}>
                      {(s.zhaban_rate * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* Zhaban count */}
                  <div className="flex items-center justify-center">
                    <span className={`font-mono ${s.zhaban > 0 ? 'text-[#F85149]' : 'text-muted-foreground'}`}>
                      {s.zhaban > 0 ? s.zhaban : '--'}
                    </span>
                  </div>

                  {/* Avg boards */}
                  <div className="flex items-center justify-center">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="w-2.5 h-2.5 text-[#F0883E]" />
                      <span className="font-mono" style={{ color: s.avg_boards >= 3 ? '#F0883E' : '#8B949E' }}>
                        {s.avg_boards}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/50 justify-center">
          {[
            { label: '0%', color: '#58A6FF' },
            { label: '<20%', color: '#3FB950' },
            { label: '20-35%', color: '#EAB308' },
            { label: '35-50%', color: '#F0883E' },
            { label: '>50%', color: '#F85149' },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-1">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ background: item.color }} />
              <span className="text-[10px] text-muted-foreground">{item.label}</span>
            </div>
          ))}
          <span className="text-[10px] text-muted-foreground ml-2">炸板率</span>
        </div>
      </CardContent>
    </Card>
  )
}
