/**
 * 世界状态全局存储
 * 
 * 使用 Zustand 管理：
 * - WebSocket 连接
 * - 世界时间
 * - 事件流
 * - 地点信息
 * - 统计数据
 * - 世界控制（广播、规则、事件）
 * 
 * 优化特性：
 * - 事件序号追踪，断线后补发丢失事件
 * - 指数退避重连策略
 * - 连接状态详细追踪
 */

import { create } from 'zustand'
import type { WorldTime, WorldEvent, Location, ClockStatus } from '../types'
import { worldApi, locationApi } from '../services/api'

// ==================
// 类型定义
// ==================

export interface WorldRule {
  id: string
  name: string
  description: string
  enabled: boolean
  parameters: Record<string, unknown>
}

// ==================
// 重连配置
// ==================
const RECONNECT_CONFIG = {
  baseDelay: 1000,      // 初始重连延迟 1秒
  maxDelay: 30000,      // 最大重连延迟 30秒
  maxRetries: 10,       // 最大重试次数
}

interface WorldState {
  // ==================
  // WebSocket 连接状态
  // ==================
  isConnected: boolean
  ws: WebSocket | null
  connectionAttempts: number     // 重连尝试次数
  lastEventSeq: number           // 最后处理的事件序号
  
  // ==================
  // 世界时间
  // ==================
  worldTime: WorldTime | null
  clockStatus: ClockStatus | null
  isPaused: boolean
  timeScale: number
  
  // ==================
  // 事件历史
  // ==================
  events: WorldEvent[]
  
  // ==================
  // 地点信息
  // ==================
  locations: Location[]
  locationsLoaded: boolean
  
  // ==================
  // 成本统计
  // ==================
  todayCost: number
  monthCost: number
  budgetRemaining: number
  
  // ==================
  // 世界控制状态
  // ==================
  worldRules: WorldRule[]
  isLoadingControl: boolean
  controlError: string | null
  
  // ==================
  // Actions
  // ==================
  connect: () => void
  disconnect: () => void
  setWorldTime: (time: WorldTime) => void
  addEvent: (event: WorldEvent) => void
  clearEvents: () => void
  fetchLocations: () => Promise<void>
  fetchStats: () => Promise<void>
  togglePause: () => Promise<void>
  setTimeScale: (scale: number) => Promise<void>
  fetchMissedEvents: (fromSeq: number) => Promise<void>
  
  // ==================
  // 世界控制 Actions
  // ==================
  fetchWorldRules: () => Promise<void>
  toggleWorldRule: (ruleId: string, enabled: boolean) => Promise<boolean>
  broadcastMessage: (message: string, priority?: 'low' | 'normal' | 'high' | 'urgent', affectMemory?: boolean) => Promise<number>
  triggerWorldEvent: (eventName: string, eventType?: string, description?: string) => Promise<boolean>
}

// 重连定时器
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

export const useWorldStore = create<WorldState>((set, get) => ({
  // ==================
  // 初始状态
  // ==================
  isConnected: false,
  ws: null,
  connectionAttempts: 0,
  lastEventSeq: 0,
  worldTime: null,
  clockStatus: null,
  isPaused: false,
  timeScale: 10,
  events: [],
  locations: [],
  locationsLoaded: false,
  todayCost: 0,
  monthCost: 0,
  budgetRemaining: 200,
  
  // ==================
  // 连接 WebSocket（带重连机制）
  // ==================
  connect: () => {
    const { ws, connectionAttempts } = get()
    if (ws && ws.readyState === WebSocket.OPEN) return
    
    // 清理之前的重连定时器
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/api/world/ws`
      
      console.log(`[WebSocket] 尝试连接... (第 ${connectionAttempts + 1} 次)`)
      const socket = new WebSocket(wsUrl)
      
      socket.onopen = () => {
        console.log('🔗 WebSocket 已连接')
        const { lastEventSeq } = get()
        
        set({ 
          isConnected: true, 
          ws: socket,
          connectionAttempts: 0,  // 重置重连计数
        })
        
        // 连接后获取初始数据
        get().fetchStats()
        get().fetchLocations()
        
        // 如果有丢失的事件，尝试补发
        if (lastEventSeq > 0) {
          console.log(`[WebSocket] 检查是否有丢失事件，上次序号: ${lastEventSeq}`)
          get().fetchMissedEvents(lastEventSeq)
        }
      }
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WorldEvent & { seq?: number }
          
          // 更新事件序号（如果服务端返回）
          if (data.seq && data.seq > get().lastEventSeq) {
            set({ lastEventSeq: data.seq })
          }
          
          // 处理不同类型的事件
          switch (data.event_type) {
            case 'world.tick':
              if (data.data.world_time) {
                set({ worldTime: data.data.world_time as WorldTime })
              }
              break
              
            case 'agent.moved':
            case 'agent.action':
            case 'agent.state_changed':
              break
              
            case 'conversation.started':
            case 'conversation.message':
            case 'conversation.ended':
              break
          }
          
          // 添加到事件历史
          get().addEvent(data)
        } catch (err) {
          console.error('解析 WebSocket 消息失败:', err)
        }
      }
      
      socket.onclose = (event) => {
        console.log(`🔌 WebSocket 已断开 (code: ${event.code}, reason: ${event.reason})`)
        set({ isConnected: false, ws: null })
        
        // 非正常关闭时自动重连
        if (event.code !== 1000) {
          const { connectionAttempts } = get()
          
          if (connectionAttempts < RECONNECT_CONFIG.maxRetries) {
            // 指数退避计算延迟
            const delay = Math.min(
              RECONNECT_CONFIG.baseDelay * Math.pow(2, connectionAttempts),
              RECONNECT_CONFIG.maxDelay
            )
            
            console.log(`[WebSocket] 将在 ${delay}ms 后重连...`)
            set({ connectionAttempts: connectionAttempts + 1 })
            
            reconnectTimer = setTimeout(() => {
              get().connect()
            }, delay)
          } else {
            console.error('[WebSocket] 达到最大重连次数，停止重连')
          }
        }
      }
      
      socket.onerror = (error) => {
        console.error('WebSocket 错误:', error)
      }
    } catch (err) {
      console.error('创建 WebSocket 失败:', err)
    }
  },
  
  // ==================
  // 断开连接
  // ==================
  disconnect: () => {
    // 清理重连定时器
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    const { ws } = get()
    if (ws) {
      ws.close(1000, '用户主动断开')  // 正常关闭码
      set({ isConnected: false, ws: null, connectionAttempts: 0 })
    }
  },
  
  // ==================
  // 设置世界时间
  // ==================
  setWorldTime: (time) => {
    set({ worldTime: time })
  },
  
  // ==================
  // 添加事件
  // ==================
  addEvent: (event) => {
    set((state) => ({
      events: [...state.events.slice(-99), event],
    }))
  },
  
  // ==================
  // 清空事件
  // ==================
  clearEvents: () => {
    set({ events: [] })
  },
  
  // ==================
  // 获取地点数据
  // ==================
  fetchLocations: async () => {
    try {
      const { locations } = await locationApi.list()
      set({ locations, locationsLoaded: true })
    } catch (err) {
      console.error('获取地点失败:', err)
    }
  },
  
  // ==================
  // 获取统计数据
  // ==================
  fetchStats: async () => {
    try {
      const status = await worldApi.getStatus()
      set({
        clockStatus: status.clock,
        isPaused: status.clock.is_paused,
        timeScale: status.clock.time_scale,
        // 修复字段映射：后端使用 current_month_cost, remaining_budget
        todayCost: (status.cost as any).current_month_cost ?? 0,
        monthCost: (status.cost as any).current_month_cost ?? 0,
        budgetRemaining: (status.cost as any).remaining_budget ?? 200,
      })
      
      const time = await worldApi.getTime()
      set({ worldTime: time })
    } catch (err) {
      console.error('获取统计失败:', err)
    }
  },
  
  // ==================
  // 切换暂停状态
  // ==================
  togglePause: async () => {
    try {
      const { isPaused } = get()
      if (isPaused) {
        await worldApi.resume()
        set({ isPaused: false })
      } else {
        await worldApi.pause()
        set({ isPaused: true })
      }
    } catch (err) {
      console.error('切换暂停失败:', err)
    }
  },
  
  // ==================
  // 设置时间缩放
  // ==================
  setTimeScale: async (scale: number) => {
    try {
      const result = await worldApi.setTimeScale(scale)
      if (result.status === 'ok') {
        set({ timeScale: result.time_scale })
      }
    } catch (err) {
      console.error('设置时间缩放失败:', err)
    }
  },
  
  // ==================
  // 获取丢失的事件（重连后补发）
  // ==================
  fetchMissedEvents: async (fromSeq: number) => {
    try {
      // 注意：这需要后端支持 /api/world/events?from_seq=xxx 接口
      // 如果后端未实现，此方法静默失败
      const response = await fetch(`/api/world/events?from_seq=${fromSeq}`)
      if (response.ok) {
        const missedEvents = await response.json() as WorldEvent[]
        console.log(`[WebSocket] 补发 ${missedEvents.length} 个丢失事件`)
        
        missedEvents.forEach(event => {
          get().addEvent(event)
        })
      }
    } catch (err) {
      // 静默失败，不影响正常使用
      console.log('[WebSocket] 无法获取丢失事件（接口可能未实现）')
    }
  },
  
  // ==================
  // 世界控制状态初始值
  // ==================
  worldRules: [],
  isLoadingControl: false,
  controlError: null,
  
  // ==================
  // 获取世界规则
  // ==================
  fetchWorldRules: async () => {
    set({ isLoadingControl: true, controlError: null })
    
    try {
      const result = await worldApi.getRules()
      set({
        worldRules: result.rules,
        isLoadingControl: false,
      })
    } catch (err) {
      set({
        controlError: err instanceof Error ? err.message : '获取规则失败',
        isLoadingControl: false,
      })
    }
  },
  
  // ==================
  // 切换世界规则
  // ==================
  toggleWorldRule: async (ruleId: string, enabled: boolean) => {
    set({ isLoadingControl: true, controlError: null })
    
    try {
      const result = await worldApi.updateRule(ruleId, enabled)
      
      if (result.success) {
        // 更新本地状态
        set(state => ({
          worldRules: state.worldRules.map(r =>
            r.id === ruleId ? { ...r, enabled } : r
          ),
          isLoadingControl: false,
        }))
        return true
      } else {
        set({
          controlError: result.message || '更新失败',
          isLoadingControl: false,
        })
        return false
      }
    } catch (err) {
      set({
        controlError: err instanceof Error ? err.message : '更新规则失败',
        isLoadingControl: false,
      })
      return false
    }
  },
  
  // ==================
  // 发送世界广播
  // ==================
  broadcastMessage: async (message: string, priority: 'low' | 'normal' | 'high' | 'urgent' = 'normal', affectMemory: boolean = true) => {
    set({ isLoadingControl: true, controlError: null })
    
    try {
      const result = await worldApi.broadcast({
        message,
        priority,
        affect_memory: affectMemory,
      })
      
      set({ isLoadingControl: false })
      return result.affected_agents
    } catch (err) {
      set({
        controlError: err instanceof Error ? err.message : '广播失败',
        isLoadingControl: false,
      })
      return 0
    }
  },
  
  // ==================
  // 触发世界事件
  // ==================
  triggerWorldEvent: async (eventName: string, eventType: string = 'announcement', description: string = '') => {
    set({ isLoadingControl: true, controlError: null })
    
    try {
      const result = await worldApi.triggerEvent({
        event_name: eventName,
        event_type: eventType as 'announcement' | 'disaster' | 'celebration' | 'economic',
        description,
        affect_all_agents: true,
      })
      
      set({ isLoadingControl: false })
      return result.success
    } catch (err) {
      set({
        controlError: err instanceof Error ? err.message : '触发事件失败',
        isLoadingControl: false,
      })
      return false
    }
  },
}))
