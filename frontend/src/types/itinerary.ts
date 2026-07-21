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
  metrics?: {
    day_count: number
    highlight_count: number
    available_poi_count: number
    data_provider: string
    estimated_data: boolean
    stale_data: boolean
  }
  validation?: {
    valid: boolean
    warnings: string[]
  }
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
  start_date: string | null
  party_size: number
  budget_limit: number | null
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

/** 对话 (来自 PG conversations 表) */
export interface Conversation {
  id: string          // = thread_id
  user_id: string
  title: string
  status: 'active' | 'completed' | 'interrupted'
  created_at: string
  updated_at: string
}

/** DB 消息 (来自 PG chat_messages 表, 含完整 metadata) */
export interface ChatMessageDB {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  thinking_content: string | null
  metadata: {
    interrupt_type?: string
    interrupt_value?: Record<string, unknown>
    plans?: Plan[]
    itinerary?: Record<string, unknown>
    budget?: Record<string, unknown>
    daily_plans?: Record<string, unknown>[]
  } | null
  created_at: string
}
