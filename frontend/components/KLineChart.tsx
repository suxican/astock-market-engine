'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, IChartApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts'

interface KLineRecord {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  [key: string]: any
}

interface KLineChartProps {
  data: KLineRecord[]
  height?: number
}

export default function KLineChart({ data, height = 420 }: KLineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data.length) return

    // 清理旧图表
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    const container = containerRef.current
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#888888',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1a1a2e' },
        horzLines: { color: '#1a1a2e' },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#555555',
          width: 1,
          style: 2,
          labelBackgroundColor: '#333333',
        },
        horzLine: {
          color: '#555555',
          width: 1,
          style: 2,
          labelBackgroundColor: '#333333',
        },
      },
      width: container.clientWidth,
      height,
      timeScale: {
        timeVisible: false,
        borderColor: '#2a2a3e',
        barSpacing: 7,
        minBarSpacing: 3,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      rightPriceScale: {
        borderColor: '#2a2a3e',
        scaleMargins: { top: 0.05, bottom: 0.25 },
      },
    })

    // K线数据
    const candleData = data
      .filter((d) => d.open && d.close && d.high && d.low)
      .map((d) => ({
        time: d.date.slice(0, 10) as any,
        open: d.open,
        close: d.close,
        high: d.high,
        low: d.low,
      }))

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderDownColor: '#22c55e',
      borderUpColor: '#ef4444',
      wickDownColor: '#22c55e',
      wickUpColor: '#ef4444',
    })
    candleSeries.setData(candleData)

    // 成交量
    const volumeData = data
      .filter((d) => d.volume != null)
      .map((d) => ({
        time: d.date.slice(0, 10) as any,
        value: d.volume,
        color:
          d.close >= d.open
            ? 'rgba(239, 68, 68, 0.3)'
            : 'rgba(34, 197, 94, 0.3)',
      }))

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' } as any,
      priceScaleId: 'volume',
    })
    volumeSeries.setData(volumeData)

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.77, bottom: 0 },
    })

    // 自适应宽度
    const handleResize = () => {
      chart.applyOptions({ width: container.clientWidth })
    }
    window.addEventListener('resize', handleResize)

    chartRef.current = chart

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data, height])

  if (!data.length) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-sm text-muted-foreground"
      >
        暂无K线数据
      </div>
    )
  }

  return (
    <div className="w-full">
      <div ref={containerRef} className="w-full" />
    </div>
  )
}
