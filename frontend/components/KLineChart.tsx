'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// ─── Types ────────────────────────────────────────────────────────────────────
interface KLineBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover?: number
}

interface KLineChartProps {
  symbol: string
  name: string
  phase?: 'xichou' | 'xipan' | 'zhupan' | 'chuhuo' | 'unknown'
  apiBase?: string
}

// ─── Constants ────────────────────────────────────────────────────────────────
const PHASE_CONFIG = {
  xichou:  { label: '吸筹阶段', bg: '#2A1E3A', color: '#BC8EF0' },
  xipan:   { label: '洗盘阶段', bg: '#1E2A3A', color: '#58A6FF' },
  zhupan:  { label: '主升阶段', bg: '#1A3A27', color: '#3FB950' },
  chuhuo:  { label: '出货阶段', bg: '#3A1E1E', color: '#F85149' },
  unknown: { label: '阶段未知', bg: '#21262D', color: '#8B949E' },
}

const PERIODS = [
  { label: '5日',  value: '5d',  days: 5  },
  { label: '1月',  value: '1m',  days: 30 },
  { label: '3月',  value: '3m',  days: 90 },
  { label: '1年',  value: '1y',  days: 250 },
]

const MA_CONFIG = [
  { n: 5,  color: '#F0883E', key: 'ma5'  },
  { n: 20, color: '#58A6FF', key: 'ma20' },
  { n: 60, color: '#BC8EF0', key: 'ma60' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────
function calcMA(data: KLineBar[], n: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < n - 1) return null
    const sum = data.slice(i - n + 1, i + 1).reduce((a, b) => a + b.close, 0)
    return +(sum / n).toFixed(2)
  })
}

function fmt(n: number, dec = 2) {
  return n.toFixed(dec)
}

function pctChange(a: number, b: number) {
  return ((b - a) / a) * 100
}

// ─── Mock data generator (replaced by real API in production) ─────────────────
function generateMockData(days: number): KLineBar[] {
  let seed = 42
  const rand = () => { seed = Math.sin(seed) * 10000; return seed - Math.floor(seed) }
  const bars: KLineBar[] = []
  let c = 1660
  const base = new Date('2025-01-01')
  for (let i = 0; i < days; i++) {
    const chg = (rand() - 0.48) * 14
    const o = c
    c = Math.max(c * 0.85, Math.min(c * 1.15, c + chg))
    const h = Math.max(o, c) + rand() * 6
    const l = Math.min(o, c) - rand() * 6
    const v = Math.floor(150000 + rand() * 300000)
    const d = new Date(base); d.setDate(d.getDate() + i)
    bars.push({
      date: d.toISOString().slice(0, 10),
      open: +o.toFixed(2), high: +h.toFixed(2),
      low: +l.toFixed(2), close: +c.toFixed(2),
      volume: v, turnover: +(rand() * 4 + 0.5).toFixed(2),
    })
  }
  return bars
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ padding: '10px 14px', borderRight: '1px solid #21262D' }}>
      <div style={{ fontSize: 11, color: '#6E7681', marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: color ?? '#E6EDF3',
        fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function KLineChart({ symbol, name, phase = 'unknown', apiBase = '' }: KLineChartProps) {
  const mainRef = useRef<HTMLCanvasElement>(null)
  const volRef  = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  const [period, setPeriod]   = useState('3m')
  const [data, setData]       = useState<KLineBar[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [hovered, setHovered] = useState(-1)
  const [hoveredBar, setHoveredBar] = useState<KLineBar | null>(null)
  const [showMA,  setShowMA]  = useState(true)
  const [showVol, setShowVol] = useState(true)

  const phaseConf = PHASE_CONFIG[phase]

  // ── Fetch data ──────────────────────────────────────────────────────────────
  const fetchData = useCallback(async (p: string) => {
    setLoading(true); setError('')
    try {
      const days = PERIODS.find(x => x.value === p)?.days ?? 90
      // Try real API first, fall back to mock
      if (apiBase) {
        const res = await fetch(`${apiBase}/api/analysis/kline/${symbol}?period=${p}`, {
          signal: AbortSignal.timeout(5000)
        })
        if (res.ok) {
          const json = await res.json()
          setData(json.data ?? json)
          setLoading(false)
          return
        }
      }
      // Mock fallback
      await new Promise(r => setTimeout(r, 300))
      setData(generateMockData(days))
    } catch {
      setError('数据加载失败，显示模拟数据')
      setData(generateMockData(90))
    } finally {
      setLoading(false)
    }
  }, [symbol, apiBase])

  useEffect(() => { fetchData(period) }, [period, fetchData])

  // ── Draw ────────────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const mc = mainRef.current; const vc = volRef.current
    if (!mc || !vc || data.length === 0) return
    const mctx = mc.getContext('2d'); const vctx = vc.getContext('2d')
    if (!mctx || !vctx) return

    const W = mc.width, H = mc.height
    const VW = vc.width, VH = vc.height
    const n = data.length
    const PAD = { l: 8, r: 72, t: 20, b: 30 }
    const cw = (W - PAD.l - PAD.r) / n
    const bw = Math.max(2, cw * 0.55)

    mctx.clearRect(0, 0, W, H)
    vctx.clearRect(0, 0, VW, VH)

    // Price range
    const pMin = Math.min(...data.map(d => d.low))  * 0.9985
    const pMax = Math.max(...data.map(d => d.high)) * 1.0015
    const py = (p: number) => PAD.t + (pMax - p) / (pMax - pMin) * (H - PAD.t - PAD.b)

    // Grid lines + price labels
    mctx.strokeStyle = '#21262D'; mctx.lineWidth = 1
    for (let i = 0; i <= 4; i++) {
      const y = PAD.t + i * (H - PAD.t - PAD.b) / 4
      mctx.beginPath(); mctx.moveTo(PAD.l, y); mctx.lineTo(W - PAD.r, y); mctx.stroke()
      const p = pMax - (pMax - pMin) * i / 4
      const isUp = p >= data[0].close
      mctx.fillStyle = isUp ? '#3FB950' : '#F85149'
      mctx.font = '20px JetBrains Mono, monospace'
      mctx.textAlign = 'left'
      mctx.fillText(p.toFixed(1), W - PAD.r + 10, y + 7)
    }

    // Candlesticks
    data.forEach((d, i) => {
      const x = PAD.l + i * cw + cw / 2
      const up = d.close >= d.open
      const col = up ? '#3FB950' : '#F85149'

      if (i === hovered) {
        mctx.fillStyle = 'rgba(255,255,255,0.05)'
        mctx.fillRect(PAD.l + i * cw, PAD.t, cw, H - PAD.t - PAD.b)
      }
      // Wick
      mctx.strokeStyle = col; mctx.lineWidth = i === hovered ? 3 : 2
      mctx.beginPath(); mctx.moveTo(x, py(d.high)); mctx.lineTo(x, py(d.low)); mctx.stroke()
      // Body
      const oy = py(d.open), cy = py(d.close)
      const by2 = Math.min(oy, cy), bh = Math.max(2, Math.abs(oy - cy))
      mctx.fillStyle = col
      mctx.fillRect(x - bw / 2, by2, bw, bh)
    })

    // MA lines
    if (showMA) {
      MA_CONFIG.forEach(({ n: mn, color }) => {
        const ma = calcMA(data, mn)
        mctx.strokeStyle = color; mctx.lineWidth = 2; mctx.beginPath()
        let started = false
        ma.forEach((v, i) => {
          if (v === null) return
          const x = PAD.l + i * cw + cw / 2
          if (!started) { mctx.moveTo(x, py(v)); started = true }
          else mctx.lineTo(x, py(v))
        })
        mctx.stroke()
      })
    }

    // Crosshair
    if (hovered >= 0) {
      const x = PAD.l + hovered * cw + cw / 2
      mctx.strokeStyle = 'rgba(255,255,255,0.18)'; mctx.lineWidth = 1
      mctx.setLineDash([5, 5])
      mctx.beginPath(); mctx.moveTo(x, PAD.t); mctx.lineTo(x, H - PAD.b); mctx.stroke()
      mctx.setLineDash([])
      // Date label
      mctx.fillStyle = '#30363D'; mctx.fillRect(x - 40, H - PAD.b + 2, 80, 22)
      mctx.fillStyle = '#8B949E'; mctx.font = '18px JetBrains Mono, monospace'
      mctx.textAlign = 'center'
      mctx.fillText(data[hovered].date.slice(5), x, H - PAD.b + 16)
    }

    // Volume
    if (showVol) {
      const vols = data.map(d => d.volume)
      const vMax = Math.max(...vols)
      const VP = { l: 8, r: 72, t: 6, b: 18 }
      vctx.strokeStyle = '#21262D'; vctx.lineWidth = 1
      vctx.beginPath(); vctx.moveTo(VP.l, VP.t); vctx.lineTo(VW - VP.r, VP.t); vctx.stroke()
      data.forEach((d, i) => {
        const x = VP.l + i * cw + cw / 2
        const h = (VH - VP.t - VP.b) * (d.volume / vMax)
        vctx.fillStyle = d.close >= d.open ? 'rgba(63,185,80,0.65)' : 'rgba(248,81,73,0.65)'
        vctx.fillRect(x - bw / 2, VH - VP.b - h, bw, h)
      })
      // Vol label
      vctx.fillStyle = '#6E7681'; vctx.font = '18px JetBrains Mono, monospace'; vctx.textAlign = 'left'
      vctx.fillText((vMax / 10000).toFixed(0) + '万', VW - VP.r + 10, VP.t + 14)
    }
  }, [data, hovered, showMA, showVol])

  // ── Resize observer ─────────────────────────────────────────────────────────
  useEffect(() => {
    const resize = () => {
      const mc = mainRef.current; const vc = volRef.current
      const wrap = wrapRef.current
      if (!mc || !vc || !wrap) return
      const w = wrap.offsetWidth
      mc.width = w * 2; mc.height = 280 * 2
      mc.style.width = w + 'px'; mc.style.height = '280px'
      vc.width = w * 2; vc.height = 72 * 2
      vc.style.width = w + 'px'; vc.style.height = '72px'
      draw()
    }
    resize()
    const ro = new ResizeObserver(resize)
    if (wrapRef.current) ro.observe(wrapRef.current)
    return () => ro.disconnect()
  }, [draw])

  useEffect(() => { draw() }, [draw])

  // ── Mouse interaction ───────────────────────────────────────────────────────
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const mc = mainRef.current; if (!mc || data.length === 0) return
    const rect = mc.getBoundingClientRect()
    const x = e.clientX - rect.left
    const PAD = { l: 8, r: 72 }
    const cw = (mc.offsetWidth - PAD.l - PAD.r) / data.length
    const idx = Math.floor((x - PAD.l) / cw)
    if (idx >= 0 && idx < data.length) {
      setHovered(idx); setHoveredBar(data[idx])
    }
  }, [data])

  const handleMouseLeave = useCallback(() => {
    setHovered(-1); setHoveredBar(null)
  }, [])

  // ── Derived stats ───────────────────────────────────────────────────────────
  const last = data[data.length - 1]
  const prev = data[data.length - 2]
  const dayPct = last && prev ? pctChange(prev.close, last.close) : 0
  const mas = MA_CONFIG.map(({ n: mn }) => {
    const ma = calcMA(data, mn)
    return ma[data.length - 1]
  })

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      style={{
        background: '#0D1117',
        borderRadius: 12,
        border: '1px solid #21262D',
        overflow: 'hidden',
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      }}
    >
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 18px 12px', borderBottom: '1px solid #21262D' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: '#E6EDF3' }}>{name}</span>
            <span style={{ fontSize: 12, color: '#8B949E' }}>{symbol}</span>
            <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
              background: phaseConf.bg, color: phaseConf.color }}>
              {phaseConf.label}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: 24, fontWeight: 700,
              color: dayPct >= 0 ? '#3FB950' : '#F85149' }}>
              {last ? fmt(last.close) : '---'}
            </span>
            {last && (
              <span style={{ fontSize: 13, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                background: dayPct >= 0 ? '#1A3A27' : '#3A1E1E',
                color: dayPct >= 0 ? '#3FB950' : '#F85149' }}>
                {dayPct >= 0 ? '+' : ''}{fmt(dayPct)}%
              </span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
          {/* Period tabs */}
          <div style={{ display: 'flex', gap: 2, background: '#161B22',
            borderRadius: 6, padding: 3 }}>
            {PERIODS.map(p => (
              <button key={p.value} onClick={() => setPeriod(p.value)}
                style={{ padding: '4px 10px', fontSize: 12, borderRadius: 4, border: 'none',
                  cursor: 'pointer', transition: 'all 0.15s',
                  background: period === p.value ? '#21262D' : 'transparent',
                  color: period === p.value ? '#E6EDF3' : '#8B949E' }}>
                {p.label}
              </button>
            ))}
          </div>
          {/* Indicator toggles */}
          <div style={{ display: 'flex', gap: 6 }}>
            {[['MA', showMA, () => setShowMA(v => !v)],
              ['VOL', showVol, () => setShowVol(v => !v)]].map(([label, active, toggle]) => (
              <button key={label as string} onClick={toggle as () => void}
                style={{ padding: '3px 9px', fontSize: 11, borderRadius: 4, border: 'none',
                  cursor: 'pointer', background: active ? '#21262D' : 'transparent',
                  color: active ? '#E6EDF3' : '#6E7681' }}>
                {label as string}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── MA Indicator bar ── */}
      <div style={{ display: 'flex', gap: 16, padding: '8px 18px',
        borderBottom: '1px solid #21262D', alignItems: 'center' }}>
        {MA_CONFIG.map(({ n: mn, color, key }, i) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 10, height: 2, borderRadius: 1, background: color }} />
            <span style={{ fontSize: 11, color }}>MA{mn}</span>
            <span style={{ fontSize: 11, color: '#8B949E' }}>
              {mas[i] ? fmt(mas[i]!) : '--'}
            </span>
          </div>
        ))}

        {/* Hovered bar info */}
        <AnimatePresence>
          {hoveredBar && (
            <motion.div key="hbar" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              exit={{ opacity: 0 }} transition={{ duration: 0.12 }}
              style={{ marginLeft: 'auto', display: 'flex', gap: 14, fontSize: 11 }}>
              {[
                ['开', hoveredBar.open],
                ['高', hoveredBar.high],
                ['低', hoveredBar.low],
                ['收', hoveredBar.close],
              ].map(([l, v]) => (
                <span key={l as string} style={{ color: '#8B949E' }}>
                  {l as string}<span style={{
                    marginLeft: 3, fontWeight: 600,
                    color: (v as number) >= hoveredBar.open ? '#3FB950' : '#F85149'
                  }}>{fmt(v as number)}</span>
                </span>
              ))}
              <span style={{ color: '#8B949E' }}>
                量<span style={{ marginLeft: 3, color: '#E6EDF3' }}>
                  {(hoveredBar.volume / 10000).toFixed(1)}万
                </span>
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Chart canvas ── */}
      <div ref={wrapRef} style={{ position: 'relative', background: '#0D1117' }}>
        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 10,
            background: 'rgba(13,17,23,0.85)' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              style={{ width: 24, height: 24, borderRadius: '50%',
                border: '2px solid #21262D', borderTop: '2px solid #3FB950' }} />
          </div>
        )}
        {error && (
          <div style={{ position: 'absolute', top: 8, right: 18, zIndex: 10,
            fontSize: 11, color: '#F0883E', background: '#2A1E10',
            padding: '3px 8px', borderRadius: 4 }}>
            {error}
          </div>
        )}
        <canvas ref={mainRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ display: 'block', cursor: 'crosshair' }} />
        {showVol && (
          <canvas ref={volRef}
            style={{ display: 'block', borderTop: '1px solid #21262D' }} />
        )}
      </div>

      {/* ── Stats row ── */}
      {last && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
          borderTop: '1px solid #21262D' }}>
          <StatCard label="今开" value={fmt(last.open)} />
          <StatCard label="最高" value={fmt(last.high)} color="#3FB950" />
          <StatCard label="最低" value={fmt(last.low)}  color="#F85149" />
          <StatCard label="成交量" value={(last.volume / 10000).toFixed(1) + '万手'} />
          <StatCard label="换手率" value={last.turnover ? fmt(last.turnover) + '%' : '--'} />
        </div>
      )}
    </motion.div>
  )
}