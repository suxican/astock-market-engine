'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, RefreshCw, Zap } from 'lucide-react'
import EmotionTimeline from '@/components/EmotionTimeline'
import DragonTree from '@/components/DragonTree'
import ZhabanHeatmap from '@/components/ZhabanHeatmap'
import { API_BASE } from '@/lib/api'

export default function WorkbenchPage() {
  const router = useRouter()
  const [dragonData, setDragonData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState('')

  const fetchAll = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/analysis/dragon-leaders`)
      if (res.ok) setDragonData(await res.json())
      setLastRefresh(new Date().toLocaleTimeString('zh-CN'))
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchAll() }, [])

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <header className="border-b border-border/50 sticky top-0 bg-background/80 backdrop-blur-lg z-10">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/')} className="text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-primary" />
              <span className="font-semibold text-sm">AI 市场认知工作台</span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {lastRefresh && (
              <span className="text-xs">更新于 {lastRefresh}</span>
            )}
            <button onClick={fetchAll} disabled={loading}
              className="flex items-center gap-1 text-xs hover:text-foreground transition-colors">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
            <a href="/" className="hover:text-foreground">首页</a>
            <a href="/market" className="hover:text-foreground">大盘</a>
            <a href="/review" className="hover:text-foreground">复盘</a>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {loading && !dragonData ? (
          <div className="flex items-center justify-center py-24">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-8 h-8 rounded-full border-2 border-border border-t-primary" />
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Row 1: Emotion Timeline (full width) */}
            <EmotionTimeline limit={30} />

            {/* Row 2: Dragon Tree + Zhaban Heatmap */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {dragonData && <DragonTree data={dragonData} />}
              <ZhabanHeatmap />
            </div>

            {/* Footer */}
            <div className="text-center text-xs text-muted-foreground pb-8">
              * 数据基于 akshare 实时数据 · 不构成投资建议
            </div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
