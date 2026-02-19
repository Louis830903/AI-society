/**
 * 对话状态全局存储
 * 
 * 使用 Zustand 管理：
 * - 活跃对话列表
 * - 选中的对话
 * - 对话详情
 * - 最新消息追踪（用于聊天气泡）
 */

import { create } from 'zustand'
import type { Conversation, ConversationBrief, ConversationStats } from '../types'
import { conversationApi } from '../services/api'

/**
 * 最新消息数据（用于聊天气泡显示）
 */
export interface LatestMessage {
  conversationId: string
  messageId: string
  speakerId: string
  speakerName: string
  content: string
  emotion?: string
  location?: string
  participantAId?: string
  participantBId?: string
  timestamp: number
}

interface ConversationState {
  // ==================
  // 对话数据
  // ==================
  activeConversations: ConversationBrief[]
  historyConversations: ConversationBrief[]
  stats: ConversationStats | null
  
  // ==================
  // 选中的对话
  // ==================
  selectedConversationId: string | null
  selectedConversation: Conversation | null
  
  // ==================
  // 最新消息（用于聊天气泡）
  // ==================
  latestMessages: Map<string, LatestMessage>  // agentId -> LatestMessage
  
  // ==================
  // 加载状态
  // ==================
  isLoading: boolean
  error: string | null
  
  // ==================
  // Actions
  // ==================
  fetchActiveConversations: () => Promise<void>
  fetchHistory: (agentId?: string) => Promise<void>
  fetchConversationDetail: (id: string) => Promise<void>
  fetchStats: () => Promise<void>
  selectConversation: (id: string | null) => void
  clearSelection: () => void
  
  // 消息追踪
  handleNewMessage: (data: {
    conversation_id: string
    message_id: string
    speaker_id: string
    speaker_name: string
    content: string
    emotion?: string
    location?: string
    participant_a_id?: string
    participant_b_id?: string
  }) => void
  getLatestMessage: (agentId: string) => LatestMessage | undefined
  clearLatestMessage: (agentId: string) => void
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  // ==================
  // 初始状态
  // ==================
  activeConversations: [],
  historyConversations: [],
  stats: null,
  selectedConversationId: null,
  selectedConversation: null,
  latestMessages: new Map(),
  isLoading: false,
  error: null,
  
  // ==================
  // 获取活跃对话
  // ==================
  fetchActiveConversations: async () => {
    set({ isLoading: true, error: null })
    
    try {
      const conversations = await conversationApi.listActive()
      set({
        activeConversations: conversations,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '获取活跃对话失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 获取对话历史
  // ==================
  fetchHistory: async (agentId?: string) => {
    set({ isLoading: true, error: null })
    
    try {
      const conversations = await conversationApi.getHistory({
        agent_id: agentId,
        limit: 50,
      })
      set({
        historyConversations: conversations,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '获取对话历史失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 获取对话详情
  // ==================
  fetchConversationDetail: async (id: string) => {
    set({ isLoading: true, error: null })
    
    try {
      const conversation = await conversationApi.get(id)
      set({
        selectedConversation: conversation,
        selectedConversationId: id,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '获取对话详情失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 获取统计信息
  // ==================
  fetchStats: async () => {
    try {
      const stats = await conversationApi.getStats()
      set({ stats })
    } catch (err) {
      console.error('获取对话统计失败:', err)
    }
  },
  
  // ==================
  // 选择对话
  // ==================
  selectConversation: (id: string | null) => {
    if (id) {
      set({ selectedConversationId: id })
      get().fetchConversationDetail(id)
    } else {
      set({ selectedConversationId: null, selectedConversation: null })
    }
  },
  
  // ==================
  // 清除选择
  // ==================
  clearSelection: () => {
    set({ selectedConversationId: null, selectedConversation: null })
  },
  
  // ==================
  // 处理新消息（用于聊天气泡）
  // ==================
  handleNewMessage: (data) => {
    const message: LatestMessage = {
      conversationId: data.conversation_id,
      messageId: data.message_id,
      speakerId: data.speaker_id,
      speakerName: data.speaker_name,
      content: data.content,
      emotion: data.emotion,
      location: data.location,
      participantAId: data.participant_a_id,
      participantBId: data.participant_b_id,
      timestamp: Date.now(),
    }
    
    // 更新说话者的最新消息
    const newMap = new Map(get().latestMessages)
    newMap.set(data.speaker_id, message)
    set({ latestMessages: newMap })
  },
  
  // ==================
  // 获取智能体的最新消息
  // ==================
  getLatestMessage: (agentId: string) => {
    return get().latestMessages.get(agentId)
  },
  
  // ==================
  // 清除智能体的最新消息
  // ==================
  clearLatestMessage: (agentId: string) => {
    const newMap = new Map(get().latestMessages)
    newMap.delete(agentId)
    set({ latestMessages: newMap })
  },
}))
