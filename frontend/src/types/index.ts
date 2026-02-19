/**
 * 类型定义
 * 
 * 前端与后端共享的数据类型定义
 */

// ==================
// 世界相关类型
// ==================

export interface WorldTime {
  datetime: string
  day: number
  time_of_day: string
  is_daytime: boolean
  formatted_time: string
  formatted_date: string
}

export interface WorldEvent {
  event_id: string
  event_type: string
  data: Record<string, unknown>
  timestamp: string
  source: string | null
}

export interface ClockStatus {
  time_scale: number
  is_running: boolean
  is_paused: boolean
  start_time: string
  elapsed_real_seconds: number
  elapsed_game_seconds: number
  current_game_time: string
}

// ==================
// 地点相关类型
// ==================

export interface Location {
  id: string
  name: string
  type: string
  description: string
  position: { x: number; y: number }
  size: { width: number; height: number }
  capacity: number
  current_occupants: number
  activities: string[]
  open_hours: { open: number; close: number } | null
  is_open_now: boolean
}

// ==================
// 智能体相关类型
// ==================

export interface Personality {
  openness: number
  conscientiousness: number
  extraversion: number
  agreeableness: number
  neuroticism: number
}

export interface Needs {
  hunger: number
  fatigue: number
  social: number
  entertainment: number
  hygiene: number
  comfort: number
}

export interface Position {
  x: number
  y: number
  location_id: string | null
  location_name: string
}

export type AgentState = 'active' | 'sleeping' | 'busy' | 'in_conversation' | 'paused' | 'offline'

export type ActionType = 'idle' | 'move' | 'work' | 'eat' | 'sleep' | 'rest' | 'chat' | 'shop'

export interface CurrentAction {
  type: ActionType
  target: string | null
  started_at: string
  duration: number | null
}

export interface Relationship {
  target_id: string
  target_name: string
  closeness: number
  trust: number
  description: string
}

export interface Agent {
  id: string
  name: string
  age: number
  gender: string
  occupation: string
  personality: Personality
  needs: Needs
  position: Position
  state: AgentState
  current_action: CurrentAction
  balance: number
  relationships: Record<string, Relationship>
  model_name: string
  created_at: string
}

export interface AgentBrief {
  id: string
  name: string
  occupation: string
  gender: string
  state: AgentState
  current_location: string
  current_action: ActionType
}

// ==================
// 对话相关类型
// ==================

export type ConversationState = 'pending' | 'active' | 'ending' | 'ended' | 'interrupted'

export interface Message {
  id: string
  speaker_id: string
  speaker_name: string
  content: string
  emotion: string | null
  is_end_signal: boolean
  timestamp: string
}

export interface Conversation {
  id: string
  participant_a_id: string
  participant_a_name: string
  participant_b_id: string
  participant_b_name: string
  state: ConversationState
  location: string
  message_count: number
  messages: Message[]
  started_at: string
  ended_at: string | null
  topics: string[]
  overall_emotion: string
  relationship_change: number
  summary: string
}

export interface ConversationBrief {
  id: string
  participant_a_name: string
  participant_b_name: string
  state: ConversationState
  location: string
  message_count: number
  started_at: string
}

// ==================
// 统计相关类型
// ==================

export interface WorldStats {
  clock: ClockStatus
  cost: {
    today: number
    this_month: number
    total: number
    budget_remaining: number
  }
  config: {
    time_scale: number
    monthly_budget: number
    max_agents: number
  }
}

export interface ConversationStats {
  active_conversations: number
  agents_in_conversation: number
  pending_requests: number
  history_count: number
  total_messages_active: number
  total_messages_history: number
  // 额外添加的计算字段
  today_count?: number
  active_count?: number
}

// ==================
// 记忆相关类型
// ==================

export type MemoryType = 
  | 'event'        // 事件记忆
  | 'conversation' // 对话记忆
  | 'observation'  // 观察记忆
  | 'reflection'   // 反思记忆
  | 'plan'         // 计划记忆

export interface Memory {
  id: string
  content: string
  type: MemoryType
  importance: number
  created_at: string
  accessed_at: string | null
  access_count: number
  keywords: string[]
  related_agents: string[]
  embedding_score?: number
}

// ==================
// 活动日志相关类型 (Phase 7)
// ==================

export type ActivityType = 
  | 'decision'      // 决策
  | 'conversation'  // 对话
  | 'reflection'    // 反思
  | 'reaction'      // 反应
  | 'plan'          // 计划

export interface Activity {
  id: number
  agent_id: string
  agent_name: string
  activity_type: ActivityType
  action: string
  target: string | null
  location: string | null
  thinking: string | null
  conversation_id: string | null
  conversation_partner: string | null
  message_content: string | null
  reflection_content: string | null
  game_time: string
  created_at: string
}

export interface DailySummary {
  date: string
  agent_id: string
  total_activities: number
  by_type: Record<string, number>
  by_action: Record<string, number>
  conversation_partners: Record<string, number>
}
