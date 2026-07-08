/** 行程数据类型定义 — 与后端 state.py Pydantic 模型对齐 */

export interface Location {
  lat: number
  lng: number
  address: string
}

export interface Activity {
  name: string
  description: string
  duration_hours: number
  cost: number
  location: Location
}

export interface Plan {
  plan_id: number
  title: string
  style: string
  highlights: string[]
  daily_overview: string[]
  estimated_budget: string
}

export interface DailyPlan {
  day: number
  date: string
  activities: Activity[]
  transport: string
  hotel_name: string
  restaurant_names: string[]
}

export interface ItineraryResult {
  destination: string
  duration: number
  daily_plans: DailyPlan[]
  total_budget: number
  tips: string[]
}

export interface IntentResult {
  destination: string
  duration: number
  travel_style: string
  budget_level: string
  special_requests: string[]
}

export interface BudgetResult {
  total_budget: number
  accommodation_cost: number
  food_cost: number
  transport_cost: number
  activity_cost: number
  budget_breakdown: Record<string, number>
}

/** 用户旅行画像 (Store profile) */
export interface UserProfile {
  preferred_style: string
  budget_level: string
  past_trips: string[]
}

/** 对话摘要 (Store conversation_summary) */
export interface ConversationSummary {
  thread_id: string
  destination?: string
  [key: string]: unknown
}

/** Checkpoint state (timeline) */
export interface CheckpointState {
  checkpoint_id: string
  next_node: string[]
  timestamp: string
  metadata: Record<string, unknown>
}
