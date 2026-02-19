/**
 * API 服务层
 * 
 * 封装与后端的所有HTTP通信
 */

import type {
  WorldTime,
  WorldStats,
  ClockStatus,
  Location,
  Agent,
  AgentBrief,
  Conversation,
  ConversationBrief,
  ConversationStats,
  Memory,
  Activity,
  DailySummary,
} from '../types'

// API基础URL（开发环境由Vite代理）
const API_BASE = '/api'

/**
 * 通用请求封装
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API请求失败: ${response.status} - ${error}`)
  }
  
  return response.json()
}

// ==================
// 世界 API
// ==================

export const worldApi = {
  /**
   * 获取世界状态
   */
  getStatus: () => request<WorldStats>('/world/status'),
  
  /**
   * 获取世界时间
   */
  getTime: () => request<WorldTime>('/world/time'),
  
  /**
   * 获取时钟状态
   */
  getClock: () => request<ClockStatus>('/world/clock'),
  
  /**
   * 暂停世界
   */
  pause: () => request<{ status: string }>('/world/pause', { method: 'POST' }),
  
  /**
   * 恢复世界
   */
  resume: () => request<{ status: string }>('/world/resume', { method: 'POST' }),
  
  /**
   * 设置时间缩放
   */
  setTimeScale: (scale: number) => 
    request<{ status: string; time_scale: number }>(`/world/time-scale/${scale}`, { method: 'POST' }),
  
  // ==================
  // 世界控制 API
  // ==================
  
  /**
   * 发送世界广播
   */
  broadcast: (params: {
    message: string
    priority?: 'low' | 'normal' | 'high' | 'urgent'
    affect_memory?: boolean
  }) => request<{
    success: boolean
    message: string
    affected_agents: number
    priority: string
    content: string
  }>('/world/broadcast', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  
  /**
   * 获取世界规则
   */
  getRules: () => request<{
    rules: Array<{
      id: string
      name: string
      description: string
      enabled: boolean
      parameters: Record<string, unknown>
    }>
    total: number
    enabled_count: number
  }>('/world/rules'),
  
  /**
   * 更新世界规则
   */
  updateRule: (ruleId: string, enabled: boolean) =>
    request<{
      success: boolean
      message: string
      rule: {
        id: string
        name: string
        description: string
        enabled: boolean
        parameters: Record<string, unknown>
      }
    }>(`/world/rules/${ruleId}?enabled=${enabled}`, {
      method: 'PUT',
    }),
  
  /**
   * 触发世界事件
   */
  triggerEvent: (params: {
    event_name: string
    event_type?: 'announcement' | 'disaster' | 'celebration' | 'economic'
    description?: string
    duration_hours?: number
    affect_all_agents?: boolean
    parameters?: Record<string, unknown>
  }) => request<{
    success: boolean
    message: string
    event_name: string
    event_type: string
    affected_agents: number
    duration_hours: number
  }>('/world/event', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  
  /**
   * 获取世界控制状态
   */
  getControlStatus: () => request<{
    agents_count: number
    active_rules: Array<{
      id: string
      name: string
      description: string
      enabled: boolean
      parameters: Record<string, unknown>
    }>
    active_rules_count: number
    clock_status: ClockStatus
    is_paused: boolean
  }>('/world/control/status'),
}

// ==================
// 地点 API
// ==================

/**
 * 创建建筑物请求参数
 */
export interface CreateLocationParams {
  name: string
  type: string
  x: number
  y: number
  width?: number
  height?: number
  capacity?: number
  activities?: string[]
  description?: string
  open_hour?: number
  close_hour?: number
}

/**
 * 更新建筑物请求参数
 */
export interface UpdateLocationParams {
  name?: string
  description?: string
  capacity?: number
  activities?: string[]
  open_hour?: number
  close_hour?: number
}

export const locationApi = {
  /**
   * 获取所有地点
   */
  list: (params?: { location_type?: string }) => {
    const query = params?.location_type ? `?location_type=${params.location_type}` : ''
    return request<{ locations: Location[]; total: number }>(`/locations${query}`)
  },
  
  /**
   * 获取单个地点
   */
  get: (id: string) => request<Location>(`/locations/${id}`),
  
  /**
   * 获取地点统计
   */
  getStats: () => request<{
    total_locations: number
    total_capacity: number
    by_type: Record<string, number>
  }>('/locations/stats'),
  
  /**
   * 获取地点类型列表
   */
  getTypes: () => request<{
    types: Array<{ value: string; name: string }>
  }>('/locations/types'),
  
  /**
   * 获取活动类型列表
   */
  getActivities: () => request<{
    activities: Array<{ value: string; name: string }>
  }>('/locations/activities'),
  
  /**
   * 创建新建筑物
   */
  create: (params: CreateLocationParams) => 
    request<{
      success: boolean
      message: string
      location: Location
    }>('/locations', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  
  /**
   * 更新建筑物属性
   */
  update: (id: string, params: UpdateLocationParams) =>
    request<{
      success: boolean
      message: string
      location: Location
    }>(`/locations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(params),
    }),
  
  /**
   * 更新建筑物位置（拖拽）
   */
  updatePosition: (id: string, x: number, y: number) =>
    request<{
      success: boolean
      message: string
      location: Location
    }>(`/locations/${id}/position`, {
      method: 'PATCH',
      body: JSON.stringify({ x, y }),
    }),
  
  /**
   * 删除建筑物
   */
  delete: (id: string, relocateAgents: boolean = true) =>
    request<{
      success: boolean
      message: string
      location_id: string
      relocated_agents: number
    }>(`/locations/${id}?relocate_agents=${relocateAgents}`, {
      method: 'DELETE',
    }),
}

// ==================
// 智能体 API
// ==================

/**
 * 创建智能体请求参数
 */
export interface CreateAgentParams {
  name: string
  age?: number
  gender?: string
  occupation?: string
  backstory?: string
  traits?: string[]
  balance?: number
  // 大五人格参数
  openness?: number
  conscientiousness?: number
  extraversion?: number
  agreeableness?: number
  neuroticism?: number
  location_id?: string
}

/**
 * 更新智能体请求参数
 */
export interface UpdateAgentParams {
  name?: string
  occupation?: string
  backstory?: string
  traits?: string[]
  balance?: number
  openness?: number
  conscientiousness?: number
  extraversion?: number
  agreeableness?: number
  neuroticism?: number
  location_id?: string
}

/**
 * 智能体指令参数
 */
export interface AgentCommandParams {
  command_type: 'move' | 'talk' | 'activity' | 'custom'
  target?: string
  custom_text?: string
}

export const agentApi = {
  /**
   * 获取智能体列表
   */
  list: (params?: { state?: string; location_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.state) searchParams.set('state', params.state)
    if (params?.location_id) searchParams.set('location_id', params.location_id)
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    const query = searchParams.toString() ? `?${searchParams}` : ''
    return request<{ agents: AgentBrief[]; total: number }>(`/agents${query}`)
  },
  
  /**
   * 获取单个智能体详情
   */
  get: (id: string) => request<Agent>(`/agents/${id}`),
  
  /**
   * 获取智能体数量
   */
  getCount: () => request<{ total: number; max: number; by_state: Record<string, number> }>('/agents/count'),
  
  /**
   * 批量生成智能体
   */
  generate: (count: number = 10) => 
    request<{ status: string; message: string; count: number }>(
      `/agents/generate/batch`,
      { 
        method: 'POST',
        body: JSON.stringify({ count, use_llm_ratio: 0.2 }),
      }
    ),
  
  /**
   * 获取智能体记忆
   */
  getMemories: (id: string, limit?: number) => 
    request<Memory[]>(`/agents/${id}/memories${limit ? `?limit=${limit}` : ''}`),
  
  /**
   * 创建新智能体
   */
  create: (params: CreateAgentParams) =>
    request<{
      success: boolean
      message: string
      agent: Agent
    }>('/agents', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  
  /**
   * 更新智能体
   */
  update: (id: string, params: UpdateAgentParams) =>
    request<{
      success: boolean
      message: string
      agent: Agent
    }>(`/agents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(params),
    }),
  
  /**
   * 删除智能体
   */
  delete: (id: string) =>
    request<{
      success: boolean
      message: string
      agent_id: string
    }>(`/agents/${id}`, {
      method: 'DELETE',
    }),
  
  /**
   * 发送指令给智能体
   */
  command: (id: string, params: AgentCommandParams) =>
    request<{
      success: boolean
      message: string
      command_type: string
      agent_id: string
    }>(`/agents/${id}/command`, {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  
  // ==================
  // 活动日志 API (Phase 7)
  // ==================
  
  /**
   * 获取智能体活动历史
   */
  getActivities: (id: string, params?: {
    start_time?: string
    end_time?: string
    activity_type?: string
    limit?: number
    offset?: number
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.start_time) searchParams.set('start_time', params.start_time)
    if (params?.end_time) searchParams.set('end_time', params.end_time)
    if (params?.activity_type) searchParams.set('activity_type', params.activity_type)
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())
    const query = searchParams.toString() ? `?${searchParams}` : ''
    return request<{ activities: Activity[]; total: number }>(`/agents/${id}/activities${query}`)
  },
  
  /**
   * 获取智能体每日活动汇总
   */
  getDailySummary: (id: string, date?: string) => {
    const query = date ? `?date=${date}` : ''
    return request<DailySummary>(`/agents/${id}/activities/daily${query}`)
  },
}

// ==================
// 对话 API
// ==================

export const conversationApi = {
  /**
   * 获取活跃对话列表
   */
  listActive: () => request<ConversationBrief[]>('/conversations'),
  
  /**
   * 获取对话历史
   */
  getHistory: (params?: { agent_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.agent_id) searchParams.set('agent_id', params.agent_id)
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    const query = searchParams.toString() ? `?${searchParams}` : ''
    return request<ConversationBrief[]>(`/conversations/history${query}`)
  },
  
  /**
   * 获取对话详情
   */
  get: (id: string) => request<Conversation>(`/conversations/${id}`),
  
  /**
   * 获取统计信息
   */
  getStats: () => request<ConversationStats>('/conversations/stats'),
  
  /**
   * 获取智能体当前对话
   */
  getAgentConversation: (agentId: string) => 
    request<{
      in_conversation: boolean
      conversation_id?: string
      other_participant?: string
      message_count?: number
    }>(`/conversations/agent/${agentId}/current`),
}

// ==================
// LLM API
// ==================

export const llmApi = {
  /**
   * 获取成本统计
   */
  getCosts: () => request<{
    today: { total_cost: number; total_tokens: number; call_count: number }
    this_month: { total_cost: number; total_tokens: number; call_count: number }
    budget: { monthly_limit: number; remaining: number; usage_percent: number }
  }>('/llm/costs'),
  
  /**
   * 获取可用模型列表
   */
  getModels: () => request<{ models: string[]; default: string }>('/llm/models'),
}

// 导出所有API
export const api = {
  world: worldApi,
  location: locationApi,
  agent: agentApi,
  conversation: conversationApi,
  llm: llmApi,
}

export default api
