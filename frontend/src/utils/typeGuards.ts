/**
 * 运行时类型守卫工具
 * ===================
 * 
 * 提供类型安全的数据验证函数，替代 `as` 类型断言
 * 确保从 API/WebSocket 接收的数据符合预期类型
 * 
 * 使用场景：
 * - API 响应数据验证
 * - WebSocket 消息解析
 * - 外部数据处理
 */

import type {
  Agent,
  AgentBrief,
  WorldTime,
  WorldEvent,
  Location,
  Message,
  Memory,
} from '../types'

// ==================
// 基础类型守卫
// ==================

/**
 * 检查值是否为非空字符串
 */
export function isString(value: unknown): value is string {
  return typeof value === 'string'
}

/**
 * 检查值是否为数字
 */
export function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value)
}

/**
 * 检查值是否为布尔值
 */
export function isBoolean(value: unknown): value is boolean {
  return typeof value === 'boolean'
}

/**
 * 检查值是否为对象（非null）
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * 检查值是否为数组
 */
export function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value)
}

// ==================
// 安全类型转换
// ==================

/**
 * 安全获取字符串值，如果不是字符串返回默认值
 */
export function asString(value: unknown, defaultValue = ''): string {
  return isString(value) ? value : defaultValue
}

/**
 * 安全获取数字值，如果不是数字返回默认值
 */
export function asNumber(value: unknown, defaultValue = 0): number {
  return isNumber(value) ? value : defaultValue
}

/**
 * 安全获取布尔值，如果不是布尔值返回默认值
 */
export function asBoolean(value: unknown, defaultValue = false): boolean {
  return isBoolean(value) ? value : defaultValue
}

/**
 * 安全获取数组，如果不是数组返回空数组
 */
export function asArray<T>(value: unknown, itemGuard?: (item: unknown) => item is T): T[] {
  if (!isArray(value)) return []
  if (!itemGuard) return value as T[]
  return value.filter(itemGuard)
}

// ==================
// 业务类型守卫
// ==================

/**
 * 检查是否为有效的 WorldTime
 */
export function isWorldTime(value: unknown): value is WorldTime {
  if (!isObject(value)) return false
  
  return (
    isNumber(value.day) &&
    isNumber(value.hour) &&
    isNumber(value.minute) &&
    isString(value.period)
  )
}

/**
 * 检查是否为有效的 WorldEvent
 */
export function isWorldEvent(value: unknown): value is WorldEvent {
  if (!isObject(value)) return false
  
  return (
    isString(value.event_type) &&
    isObject(value.data)
  )
}

/**
 * 检查是否为有效的 AgentBrief
 */
export function isAgentBrief(value: unknown): value is AgentBrief {
  if (!isObject(value)) return false
  
  return (
    isString(value.id) &&
    isString(value.name) &&
    isString(value.occupation)
  )
}

/**
 * 检查是否为有效的 Agent
 */
export function isAgent(value: unknown): value is Agent {
  if (!isObject(value)) return false
  
  return (
    isString(value.id) &&
    isString(value.name) &&
    isNumber(value.age) &&
    isString(value.gender) &&
    isString(value.occupation) &&
    isObject(value.personality) &&
    isObject(value.needs)
  )
}

/**
 * 检查是否为有效的 Location
 */
export function isLocation(value: unknown): value is Location {
  if (!isObject(value)) return false
  
  return (
    isString(value.id) &&
    isString(value.name) &&
    isString(value.type) &&
    isObject(value.position)
  )
}

/**
 * 检查是否为有效的 Message
 */
export function isMessage(value: unknown): value is Message {
  if (!isObject(value)) return false
  
  return (
    isString(value.id) &&
    isString(value.speaker_id) &&
    isString(value.content)
  )
}

/**
 * 检查是否为有效的 Memory
 */
export function isMemory(value: unknown): value is Memory {
  if (!isObject(value)) return false
  
  return (
    isString(value.id) &&
    isString(value.type) &&
    isString(value.content) &&
    isNumber(value.importance)
  )
}

// ==================
// 安全解析函数
// ==================

/**
 * 安全解析 JSON，失败返回 null
 */
export function safeJsonParse<T>(
  json: string,
  guard?: (value: unknown) => value is T
): T | null {
  try {
    const parsed = JSON.parse(json)
    if (guard && !guard(parsed)) {
      console.warn('[TypeGuard] JSON 解析成功但类型不匹配')
      return null
    }
    return parsed as T
  } catch (err) {
    console.error('[TypeGuard] JSON 解析失败:', err)
    return null
  }
}

/**
 * 安全从对象获取嵌套属性
 */
export function safeGet<T>(
  obj: unknown,
  path: string,
  defaultValue: T
): T {
  if (!isObject(obj)) return defaultValue
  
  const keys = path.split('.')
  let current: unknown = obj
  
  for (const key of keys) {
    if (!isObject(current)) return defaultValue
    current = (current as Record<string, unknown>)[key]
  }
  
  return current as T ?? defaultValue
}

// ==================
// 数据验证与转换
// ==================

/**
 * 验证并转换 WebSocket 事件数据
 */
export function parseWebSocketEvent(data: unknown): WorldEvent | null {
  if (isWorldEvent(data)) {
    return data
  }
  
  // 尝试从字符串解析
  if (isString(data)) {
    return safeJsonParse(data, isWorldEvent)
  }
  
  console.warn('[TypeGuard] 无效的 WebSocket 事件:', data)
  return null
}

/**
 * 验证智能体列表数据
 */
export function validateAgentList(data: unknown): AgentBrief[] {
  if (!isArray(data)) return []
  return data.filter(isAgentBrief)
}

/**
 * 验证地点列表数据
 */
export function validateLocationList(data: unknown): Location[] {
  if (!isArray(data)) return []
  return data.filter(isLocation)
}

// ==================
// 调试工具
// ==================

/**
 * 类型断言并记录警告（开发环境使用）
 */
export function assertType<T>(
  value: unknown,
  guard: (v: unknown) => v is T,
  context: string
): T | undefined {
  if (guard(value)) {
    return value
  }
  
  // 开发环境警告
  console.warn(`[TypeGuard] 类型断言失败 @ ${context}:`, value)
  
  return undefined
}
