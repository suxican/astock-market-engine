/** 前后端契约 — 与 backend/schemas/*.py 同步
 *
 * 变更时记得同步更新后端 Pydantic 模型。
 * 也可通过 openapi-typescript 从 /openapi.json 自动生成。
 */

// ── 市场评分 ──

export interface EmotionScores {
  score: number               // 0-100，主升期最高
  stage: string               // 冰点期|修复期|主升期|高潮期|分歧期|退潮期
  confidence: "高" | "中" | "低"
  all_stage_scores: Record<string, number>
  signals: string[]
  suggestion: string
}

export interface DragonIntensity {
  score: number               // 0-100
  top_leader_score: number
  high_board_count: number
  top_leaders: Array<{
    name: string
    boards: number
    industry: string
  }>
}

export interface RiskScores {
  score: number               // 0-100，越高越危险
  level: "低" | "中" | "高" | "极高"
  factors: string[]
}

export interface MarketScores {
  emotion: EmotionScores
  dragon_intensity: DragonIntensity
  risk: RiskScores
  computed_at: string
}

// ── 个股评分 ──

export interface MainCapitalScores {
  score: number               // 0-100，主升=90，出货=15
  stage: string               // 吸筹|洗盘|主升|出货
  confidence: "高" | "中" | "低"
  all_stage_scores: Record<string, number>
  factors: string[]
  advice: string
  risk_flags?: string[]
  evidence?: Record<string, unknown>
}

export interface TechnicalScores {
  score: number               // 0-100
  trend_score: number         // 0-40
  volume_score: number        // 0-30
  position_score: number      // 0-30
  factors: string[]
}

export interface StockScores {
  symbol: string
  name: string
  main_capital: MainCapitalScores
  technical: TechnicalScores
  composite: number           // 0-100
}

// ── 请求 ──

export interface StockScoresQuery {
  symbol: string
}

// ── 评分颜色映射（前端可视化用）──

export function emotionColor(stage: string): string {
  const map: Record<string, string> = {
    "冰点期": "#3b82f6", "修复期": "#22c55e", "主升期": "#ef4444",
    "高潮期": "#f97316", "分歧期": "#eab308", "退潮期": "#6b7280",
  }
  return map[stage] ?? "#6b7280"
}

export function riskColor(level: string): string {
  const map: Record<string, string> = {
    "低": "#22c55e", "中": "#eab308", "高": "#f97316", "极高": "#ef4444",
  }
  return map[level] ?? "#6b7280"
}

export function confidenceColor(conf: string): string {
  const map: Record<string, string> = {
    "高": "#22c55e", "中": "#eab308", "低": "#6b7280",
  }
  return map[conf] ?? "#6b7280"
}

export function capitalStageColor(stage: string): string {
  const map: Record<string, string> = {
    "主升": "#ef4444", "吸筹": "#22c55e", "洗盘": "#3b82f6", "出货": "#6b7280",
  }
  return map[stage] ?? "#6b7280"
}

// ── 数据质量类型 ──

export interface QualityInfo {
  source: string
  confidence: number
  realtime: boolean
  fallback_used: boolean
}

export type SystemStatusType = "realtime" | "cache" | "stale" | "mock" | "unknown"

export interface SystemStatusResponse {
  status: SystemStatusType
  sources: Array<{
    name: string
    source: string
    confidence: number
    realtime: boolean
    fallback_used: boolean
  }>
  updated_at: string
}

// ══════════════════════════════════════════
// V3 新增类型
// ══════════════════════════════════════════

// ── 赚钱效应 ──

export interface EarningEffectScores {
  premium_score: number         // 涨停次日溢价率得分
  survival_score: number        // 连板存活率得分
  dragon_premium_score: number  // 龙头溢价得分
  loss_spread_score: number     // 跌停扩散得分
  zhaban_reflow_score: number   // 炸板回封率得分
  avg_premium_pct: number       // 涨停股次日平均涨幅 %
  survival_rate: number         // 连板存活率 0-1
  dragon_premium_pct: number    // 龙头次日涨幅 %
  loss_spread_ratio: number     // 跌停扩散比
  zhaban_reflow_rate: number    // 炸板回封率 0-1
  composite: number             // 综合分 0-100
  signals: string[]
  suggestion: string
  level: string                 // 强/中/弱/极弱
  computed_at: string
}

// ── 事件引擎 V2 ──

export interface EventCluster {
  cluster_id: string
  title: string
  event_type: string
  count: number
  affected_sectors: string[]
  sentiment: "positive" | "negative" | "neutral"
  raw_impact: number
  decayed_impact: number
  latest_time: string
}

export interface TrendingTopic {
  keyword: string
  count: number
  trend: "rising" | "falling" | "stable"
  related_sectors: string[]
}

export interface EventV2Result {
  clusters: EventCluster[]
  trending_topics: TrendingTopic[]
  market_drivers: Array<{
    time: string
    event: string
    type: string
    importance: string
    affected: string[]
  }>
  event_score: number
  sentiment_score: number
  policy_score: number
  signals: string[]
  timeline_count: number
  computed_at: string
}

// ── 市场健康分 ──

export interface MarketHealthScore {
  composite: number             // 0-100 综合分
  level: string                 // 极强/偏强/中性/偏弱/极弱
  confidence: string
  emotion: EmotionScores
  dragon_intensity: {
    score: number
    top_leader_score: number
    high_board_count: number
  }
  risk: RiskScores
  earning_effect: EarningEffectScores
  event: {
    event_score: number
    sentiment_score: number
    policy_score: number
  }
  weights: Record<string, number>
  explain_summary: string
  signals: string[]
  computed_at: string
}

// ── 数据质量仪表盘 ──

export interface SourceHealth {
  source: string
  total_requests: number
  success_rate: number
  health_status: "healthy" | "degraded" | "unhealthy" | "unknown"
  avg_latency_ms: number
  last_success_at: string
  last_failure_at: string
}

export interface QualityDashboard {
  overall_status: SystemStatusType
  overall_confidence: number
  source_health: Record<string, SourceHealth>
  recent_snapshots: Array<{
    timestamp: string
    endpoint: string
    sources_used: string[]
    overall_confidence: number
    is_valid: boolean
    fallback_used: boolean
    system_status: string
  }>
  alerts: string[]
  computed_at: string
}

// ── V3 统一仪表盘 ──

export interface V3MarketDashboard {
  features: Record<string, unknown>
  scores: MarketScores
  earning_effect: EarningEffectScores
  market_breath: MarketBreadth
  theme_scores: ThemeScoresResult
  health: MarketHealthScore
  computed_at: string
}


// ── 市场宽度 ──

export interface MarketBreadth {
  up_count: number
  down_count: number
  flat_count: number
  total_count: number
  up_ratio: number
  limit_up_count: number
  limit_down_count: number
  strong_up_count: number
  strong_down_count: number
  breadth_score: number
  breadth_level: string
  signals: string[]
  computed_at: string
}

// ── 主线识别 ──

export interface ThemeScore {
  name: string
  limit_up_count: number
  fund_flow: number
  dragon_boards: number
  concentration: number
  composite: number
  level: string
}

export interface ThemeScoresResult {
  themes: ThemeScore[]
  main_line: string
  main_line_score: number
  signals: string[]
  computed_at: string
}

// ── V3 颜色映射 ──

export function earningEffectColor(level: string): string {
  const map: Record<string, string> = {
    "强": "#22c55e", "中": "#eab308", "弱": "#f97316", "极弱": "#ef4444",
  }
  return map[level] ?? "#6b7280"
}

export function marketHealthColor(level: string): string {
  const map: Record<string, string> = {
    "极强": "#22c55e", "偏强": "#86efac", "中性": "#eab308",
    "偏弱": "#f97316", "极弱": "#ef4444",
  }
  return map[level] ?? "#6b7280"
}

export function breadthColor(level: string): string {
  const map: Record<string, string> = {
    "极强": "#22c55e", "偏强": "#86efac", "中性": "#eab308",
    "偏弱": "#f97316", "极弱": "#ef4444",
  }
  return map[level] ?? "#6b7280"
}

export function themeLevelColor(level: string): string {
  const map: Record<string, string> = {
    "主线": "#ef4444", "支线": "#f97316", "活跃": "#eab308", "弱势": "#6b7280",
  }
  return map[level] ?? "#6b7280"
}

export function sentimentColor(score: number): string {
  if (score >= 65) return "#22c55e"
  if (score >= 45) return "#eab308"
  return "#ef4444"
}

