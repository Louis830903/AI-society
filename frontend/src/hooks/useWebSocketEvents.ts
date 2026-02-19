/**
 * WebSocket事件处理Hook
 * 
 * 统一管理WebSocket事件的分发和处理
 * 将事件路由到对应的store进行状态更新
 * 
 * 优化特性：
 * - 使用类型守卫确保类型安全
 * - 防抖刷新避免频繁更新
 */

import { useEffect, useCallback, useRef } from 'react'
import { useWorldStore } from '../store/worldStore'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { useLocationStore } from '../store/locationStore'
import type { WorldEvent } from '../types'
import { isWorldTime, asString } from '../utils/typeGuards'

/**
 * WebSocket事件类型定义
 */
export enum EventType {
  // 世界事件
  WORLD_TICK = 'world.tick',
  WORLD_STATE_CHANGED = 'world.state_changed',
  
  // 智能体事件
  AGENT_CREATED = 'agent.created',
  AGENT_MOVED = 'agent.moved',
  AGENT_ACTION = 'agent.action',
  AGENT_STATE_CHANGED = 'agent.state_changed',
  AGENT_NEED_CHANGED = 'agent.need_changed',
  
  // 对话事件
  CONVERSATION_STARTED = 'conversation.started',
  CONVERSATION_MESSAGE = 'conversation.message',
  CONVERSATION_ENDED = 'conversation.ended',
  
  // 关系事件
  RELATIONSHIP_CHANGED = 'relationship.changed',
  
  // 系统事件
  ERROR = 'error',
}

/**
 * 事件处理器映射
 */
interface EventHandlers {
  onWorldTick?: (data: WorldEvent['data']) => void
  onAgentCreated?: (data: WorldEvent['data']) => void
  onAgentMoved?: (data: WorldEvent['data']) => void
  onAgentAction?: (data: WorldEvent['data']) => void
  onAgentStateChanged?: (data: WorldEvent['data']) => void
  onConversationStarted?: (data: WorldEvent['data']) => void
  onConversationMessage?: (data: WorldEvent['data']) => void
  onConversationEnded?: (data: WorldEvent['data']) => void
  onError?: (data: WorldEvent['data']) => void
}

/**
 * WebSocket事件处理Hook
 * 
 * 自动监听WebSocket事件并更新相应的store
 */
export function useWebSocketEvents(handlers?: EventHandlers) {
  // 获取store actions
  const worldStore = useWorldStore()
  const agentStore = useAgentStore()
  const conversationStore = useConversationStore()
  
  // 使用ref保存handlers以避免重复订阅
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers
  
  // 防抖标志：防止短时间内多次刷新
  const refreshTimersRef = useRef<{
    agents: ReturnType<typeof setTimeout> | null
    conversations: ReturnType<typeof setTimeout> | null
  }>({ agents: null, conversations: null })
  
  /**
   * 防抖刷新智能体列表
   */
  const debouncedRefreshAgents = useCallback(() => {
    if (refreshTimersRef.current.agents) {
      clearTimeout(refreshTimersRef.current.agents)
    }
    refreshTimersRef.current.agents = setTimeout(() => {
      agentStore.fetchAgents()
    }, 500) // 500ms防抖
  }, [agentStore])
  
  /**
   * 防抖刷新对话列表
   */
  const debouncedRefreshConversations = useCallback(() => {
    if (refreshTimersRef.current.conversations) {
      clearTimeout(refreshTimersRef.current.conversations)
    }
    refreshTimersRef.current.conversations = setTimeout(() => {
      conversationStore.fetchActiveConversations()
      conversationStore.fetchStats()
    }, 500) // 500ms防抖
  }, [conversationStore])
  
  /**
   * 处理WebSocket事件
   */
  const handleEvent = useCallback((event: WorldEvent) => {
    const { event_type, data } = event
    
    switch (event_type) {
      // ====================
      // 世界事件
      // ====================
      case EventType.WORLD_TICK:
        // 使用类型守卫验证数据
        if (data.world_time && isWorldTime(data.world_time)) {
          worldStore.setWorldTime(data.world_time)
        }
        handlersRef.current?.onWorldTick?.(data)
        break
        
      case EventType.WORLD_STATE_CHANGED:
        worldStore.fetchStats()
        break
        
      // ====================
      // 智能体事件
      // ====================
      case EventType.AGENT_CREATED:
        debouncedRefreshAgents()
        handlersRef.current?.onAgentCreated?.(data)
        break
        
      case EventType.AGENT_MOVED:
        // 如果当前选中了该智能体，刷新详情
        if (agentStore.selectedAgentId === data.agent_id) {
          const agentId = asString(data.agent_id)
          if (agentId) agentStore.fetchAgentDetail(agentId)
        }
        handlersRef.current?.onAgentMoved?.(data)
        break
        
      case EventType.AGENT_ACTION:
        handlersRef.current?.onAgentAction?.(data)
        break
        
      case EventType.AGENT_STATE_CHANGED:
        // 刷新智能体列表
        debouncedRefreshAgents()
        // 如果当前选中了该智能体，刷新详情
        if (agentStore.selectedAgentId === data.agent_id) {
          const agentId = asString(data.agent_id)
          if (agentId) agentStore.fetchAgentDetail(agentId)
        }
        handlersRef.current?.onAgentStateChanged?.(data)
        break
        
      case EventType.AGENT_NEED_CHANGED:
        // 如果当前选中了该智能体，刷新详情
        if (agentStore.selectedAgentId === data.agent_id) {
          const agentId = asString(data.agent_id)
          if (agentId) agentStore.fetchAgentDetail(agentId)
        }
        break
        
      // ====================
      // 对话事件
      // ====================
      case EventType.CONVERSATION_STARTED:
        debouncedRefreshConversations()
        handlersRef.current?.onConversationStarted?.(data)
        break
        
      case EventType.CONVERSATION_MESSAGE:
        // 追踪最新消息用于显示气泡
        conversationStore.handleNewMessage({
          conversation_id: asString(data.conversation_id) || '',
          message_id: asString(data.message_id) || '',
          speaker_id: asString(data.speaker_id) || '',
          speaker_name: asString(data.speaker_name) || '',
          content: asString(data.content) || '',
          emotion: asString(data.emotion),
          location: asString(data.location),
          participant_a_id: asString(data.participant_a_id),
          participant_b_id: asString(data.participant_b_id),
        })
        // 如果当前选中了该对话，刷新详情
        if (conversationStore.selectedConversationId === data.conversation_id) {
          const convId = asString(data.conversation_id)
          if (convId) conversationStore.fetchConversationDetail(convId)
        }
        handlersRef.current?.onConversationMessage?.(data)
        break
        
      case EventType.CONVERSATION_ENDED:
        debouncedRefreshConversations()
        // 如果当前选中的对话结束了，刷新详情
        if (conversationStore.selectedConversationId === data.conversation_id) {
          const convId = asString(data.conversation_id)
          if (convId) conversationStore.fetchConversationDetail(convId)
        }
        handlersRef.current?.onConversationEnded?.(data)
        break
        
      // ====================
      // 关系事件
      // ====================
      case EventType.RELATIONSHIP_CHANGED:
        // 如果当前选中了相关智能体，刷新详情
        if (
          agentStore.selectedAgentId === data.agent_a_id ||
          agentStore.selectedAgentId === data.agent_b_id
        ) {
          if (agentStore.selectedAgentId) {
            agentStore.fetchAgentDetail(agentStore.selectedAgentId)
          }
        }
        break
        
      // ====================
      // 错误事件
      // ====================
      case EventType.ERROR:
        console.error('WebSocket错误事件:', data)
        handlersRef.current?.onError?.(data)
        break
    }
  }, [worldStore, agentStore, conversationStore, debouncedRefreshAgents, debouncedRefreshConversations])
  
  /**
   * 订阅事件
   */
  useEffect(() => {
    // 获取事件流
    const events = worldStore.events
    if (events.length === 0) return
    
    // 处理最新事件
    const latestEvent = events[events.length - 1]
    handleEvent(latestEvent)
  }, [worldStore.events, handleEvent])
  
  // 清理定时器
  useEffect(() => {
    return () => {
      if (refreshTimersRef.current.agents) {
        clearTimeout(refreshTimersRef.current.agents)
      }
      if (refreshTimersRef.current.conversations) {
        clearTimeout(refreshTimersRef.current.conversations)
      }
    }
  }, [])
  
  return {
    isConnected: worldStore.isConnected,
    events: worldStore.events,
  }
}

/**
 * 初始化数据加载Hook
 * 
 * 在WebSocket连接后加载所有初始数据
 */
export function useInitialDataLoad() {
  const { isConnected } = useWorldStore()
  const { fetchAgents, agentsLoaded } = useAgentStore()
  const { fetchActiveConversations, fetchStats } = useConversationStore()
  const { fetchLocations, fetchLocationTypes, fetchActivityTypes } = useLocationStore()
  
  useEffect(() => {
    if (isConnected && !agentsLoaded) {
      // 连接成功后加载初始数据
      fetchAgents()
      fetchActiveConversations()
      fetchStats()
      
      // 加载建筑物相关数据
      fetchLocations()
      fetchLocationTypes()
      fetchActivityTypes()
    }
  }, [isConnected, agentsLoaded, fetchAgents, fetchActiveConversations, fetchStats, fetchLocations, fetchLocationTypes, fetchActivityTypes])
}
