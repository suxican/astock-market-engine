'use client'

import { useState, useRef, useCallback, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Loader2 } from 'lucide-react'

interface Props {
  children: ReactNode
  symbol: string
  query?: string
  side?: 'top' | 'bottom' | 'left' | 'right'
}

// Simple in-memory cache per symbol+query
const _cache = new Map<string, string>()

export default function AITooltip({ children, symbol, query, side = 'top' }: Props) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const cacheKey = `${symbol}::${query ?? 'comprehensive'}`

  const fetchExplanation = useCallback(async () => {
    if (_cache.has(cacheKey)) {
      setText(_cache.get(cacheKey)!)
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/analysis/stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          analysis_type: query ?? 'comprehensive',
        }),
      })
      if (res.ok) {
        const data = await res.json()
        const raw = typeof data.analysis === 'string'
          ? data.analysis
          : data.analysis?.raw ?? data.analysis?.text ?? ''
        // Extract first meaningful paragraph (skip markdown headers)
        const lines = raw.split('\n').filter((l: string) =>
          l.trim() && !l.startsWith('#') && l.length > 10
        )
        const snippet = lines.slice(0, 3).join('\n').slice(0, 300)
        _cache.set(cacheKey, snippet)
        setText(snippet)
      }
    } catch {
      setText('AI 解释暂时不可用')
    } finally {
      setLoading(false)
    }
  }, [symbol, query, cacheKey])

  const handleEnter = () => {
    timerRef.current = setTimeout(() => {
      setOpen(true)
      fetchExplanation()
    }, 400)
  }

  const handleLeave = () => {
    clearTimeout(timerRef.current)
    setOpen(false)
  }

  const sideStyles: Record<string, React.CSSProperties> = {
    top:    { bottom: 'calc(100% + 8px)', left: '50%', transform: 'translateX(-50%)' },
    bottom: { top: 'calc(100% + 8px)', left: '50%', transform: 'translateX(-50%)' },
    left:   { right: 'calc(100% + 8px)', top: '50%', transform: 'translateY(-50%)' },
    right:  { left: 'calc(100% + 8px)', top: '50%', transform: 'translateY(-50%)' },
  }

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      {children}

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-72"
            style={sideStyles[side]}
          >
            <div
              className="p-4 rounded-xl border shadow-xl backdrop-blur-xl"
              style={{
                background: 'rgba(13,17,23,0.97)',
                borderColor: '#30363D',
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-3.5 h-3.5 text-primary" />
                <span className="text-xs font-semibold text-primary">AI 解读</span>
              </div>

              {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  分析中...
                </div>
              ) : (
                <p className="text-xs leading-relaxed text-[#C9D1D9]">{text}</p>
              )}

              <div className="mt-2 text-[10px] text-muted-foreground">
                {symbol} · 不构成投资建议
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
