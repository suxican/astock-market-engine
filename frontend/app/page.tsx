'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Search, TrendingUp, BarChart3, Brain, Zap, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'

const features = [
  { icon: Brain, title: 'AI 认知分析', desc: '不是指标堆砌，而是告诉你为什么涨、为什么跌' },
  { icon: TrendingUp, title: '主力行为识别', desc: '吸筹、洗盘、主升、出货 — 看清主力在做什么' },
  { icon: Zap, title: '情绪周期判断', desc: '冰点→修复→主升→高潮→分歧→退潮，当前在哪个阶段' },
  { icon: Shield, title: '风险预警', desc: '高位放量滞涨、大单出货，提前发现风险信号' },
]

export default function HomePage() {
  const [symbol, setSymbol] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!symbol.trim()) return
    setLoading(true)
    router.push(`/stock?symbol=${symbol.trim()}`)
  }

  const quickStocks = ['600519', '000858', '300750', '002594', '601012', '000333']

  return (
    <div className="min-h-screen">
      {/* 导航 */}
      <header className="border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-xs font-bold text-black">
              A
            </div>
            <span className="font-semibold text-sm">AStock Copilot</span>
          </div>
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            <a href="/" className="hover:text-foreground transition-colors">首页</a>
            <a href="/market" className="hover:text-foreground transition-colors">大盘</a>
            <a href="/review" className="hover:text-foreground transition-colors">复盘</a>
            <a href="/workbench" className="hover:text-foreground transition-colors flex items-center gap-1">
              <Zap className="w-3 h-3" />
              工作台
            </a>
            <a href="/backtest" className="hover:text-foreground transition-colors">回测</a>
            <a href="/strategies" className="hover:text-foreground transition-colors">策略</a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-4 pt-24 pb-12 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/50 border border-border/50 text-xs text-accent-foreground mb-6">
            <BarChart3 className="w-3 h-3" />
            A股市场认知引擎 V2
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            真正理解A股的
            <span className="text-primary"> AI 认知系统</span>
          </h1>
          <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto leading-relaxed">
            不是自动交易机器人，而是帮你理解市场行为逻辑的 AI 分析助手。
            <br />输入股票代码，输出大白话分析。
          </p>

          {/* 搜索框 */}
          <form onSubmit={handleSubmit} className="max-w-md mx-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="输入股票代码，例如 600519"
                className="pl-10 h-12 text-lg bg-card border-border/50 focus-visible:ring-primary"
              />
              <Button
                type="submit"
                size="lg"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-10"
                disabled={loading}
              >
                分析
              </Button>
            </div>
          </form>

          {/* 快捷入口 */}
          <div className="mt-6 flex items-center justify-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">快捷：</span>
            {quickStocks.map((code) => (
              <button
                key={code}
                onClick={() => router.push(`/stock?symbol=${code}`)}
                className="px-3 py-1 rounded-full bg-muted hover:bg-accent text-xs text-muted-foreground hover:text-foreground transition-all"
              >
                {code}
              </button>
            ))}
          </div>
        </motion.div>
      </section>

      {/* 功能卡片 */}
      <section className="max-w-5xl mx-auto px-4 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 * i }}
            >
              <Card className="h-full bg-card/50 border-border/50 hover:border-primary/30 transition-colors">
                <CardContent className="p-5">
                  <div className="w-9 h-9 rounded-lg bg-accent flex items-center justify-center mb-3">
                    <f.icon className="w-4 h-4 text-primary" />
                  </div>
                  <h3 className="text-sm font-medium mb-1.5">{f.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}
