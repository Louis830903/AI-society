/**
 * 智能体状态全局存储
 * 
 * 使用 Zustand 管理：
 * - 智能体列表
 * - 选中的智能体
 * - 智能体详情
 * - 跟随功能
 * - CRUD 操作
 * 
 * 优化特性：
 * - AbortController 防止竞态条件
 * - 请求ID追踪确保数据一致性
 */

import { create } from 'zustand'
import type { Agent, AgentBrief } from '../types'
import { agentApi, type CreateAgentParams, type UpdateAgentParams, type AgentCommandParams } from '../services/api'

// ==================
// 请求控制器（防止竞态条件）
// ==================
let detailAbortController: AbortController | null = null
let currentDetailRequestId = 0  // 请求ID追踪

interface AgentState {
  // ==================
  // 智能体数据
  // ==================
  agents: AgentBrief[]
  totalAgents: number
  maxAgents: number
  agentsLoaded: boolean
  
  // ==================
  // 选中的智能体
  // ==================
  selectedAgentId: string | null
  selectedAgent: Agent | null
  
  // ==================
  // 跟随状态
  // ==================
  followingAgentId: string | null
  
  // ==================
  // 加载状态
  // ==================
  isLoading: boolean
  error: string | null
  
  // ==================
  // Actions
  // ==================
  fetchAgents: () => Promise<void>
  fetchAgentDetail: (id: string) => Promise<void>
  selectAgent: (id: string | null) => void
  generateAgents: (count?: number) => Promise<void>
  clearSelection: () => void
  toggleFollow: (id: string | null) => void
  stopFollowing: () => void
  cancelPendingRequests: () => void
  
  // ==================
  // CRUD Actions
  // ==================
  createAgent: (params: CreateAgentParams) => Promise<Agent | null>
  updateAgent: (id: string, params: UpdateAgentParams) => Promise<Agent | null>
  deleteAgent: (id: string) => Promise<boolean>
  commandAgent: (id: string, params: AgentCommandParams) => Promise<boolean>
}

export const useAgentStore = create<AgentState>((set, get) => ({
  // ==================
  // 初始状态
  // ==================
  agents: [],
  totalAgents: 0,
  maxAgents: 50,
  agentsLoaded: false,
  selectedAgentId: null,
  selectedAgent: null,
  followingAgentId: null,
  isLoading: false,
  error: null,
  
  // ==================
  // 获取智能体列表
  // ==================
  fetchAgents: async () => {
    set({ isLoading: true, error: null })
    
    try {
      const [listResult, countResult] = await Promise.all([
        agentApi.list({ limit: 100 }),
        agentApi.getCount(),
      ])
      
      set({
        agents: listResult.agents,
        totalAgents: countResult.total,
        maxAgents: countResult.max,
        agentsLoaded: true,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '获取智能体失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 获取智能体详情（带竞态控制）
  // ==================
  fetchAgentDetail: async (id: string) => {
    // 取消之前的请求
    if (detailAbortController) {
      detailAbortController.abort()
    }
    
    // 创建新的控制器和请求ID
    detailAbortController = new AbortController()
    const requestId = ++currentDetailRequestId
    
    set({ isLoading: true, error: null })
    
    try {
      const agent = await agentApi.get(id)
      
      // 检查是否是最新请求（防止旧数据覆盖新数据）
      if (requestId !== currentDetailRequestId) {
        console.log(`[AgentStore] 忽略过时的请求 #${requestId}，当前为 #${currentDetailRequestId}`)
        return
      }
      
      set({
        selectedAgent: agent,
        selectedAgentId: id,
        isLoading: false,
      })
    } catch (err) {
      // 忽略取消的请求错误
      if (err instanceof Error && err.name === 'AbortError') {
        console.log(`[AgentStore] 请求 #${requestId} 已取消`)
        return
      }
      
      // 检查是否是最新请求
      if (requestId !== currentDetailRequestId) {
        return
      }
      
      set({
        error: err instanceof Error ? err.message : '获取智能体详情失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 选择智能体
  // ==================
  selectAgent: (id: string | null) => {
    if (id) {
      set({ selectedAgentId: id })
      get().fetchAgentDetail(id)
    } else {
      // 取消进行中的请求
      get().cancelPendingRequests()
      set({ selectedAgentId: null, selectedAgent: null })
    }
  },
  
  // ==================
  // 生成智能体
  // ==================
  generateAgents: async (count?: number) => {
    set({ isLoading: true, error: null })
    
    try {
      await agentApi.generate(count)
      // 重新获取列表
      await get().fetchAgents()
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '生成智能体失败',
        isLoading: false,
      })
    }
  },
  
  // ==================
  // 清除选择
  // ==================
  clearSelection: () => {
    get().cancelPendingRequests()
    set({ selectedAgentId: null, selectedAgent: null })
  },
  
  // ==================
  // 切换跟随
  // ==================
  toggleFollow: (id: string | null) => {
    const { followingAgentId } = get()
    if (followingAgentId === id) {
      set({ followingAgentId: null })
    } else {
      set({ followingAgentId: id })
    }
  },
  
  // ==================
  // 停止跟随
  // ==================
  stopFollowing: () => {
    set({ followingAgentId: null })
  },
  
  // ==================
  // 取消待处理的请求
  // ==================
  cancelPendingRequests: () => {
    if (detailAbortController) {
      detailAbortController.abort()
      detailAbortController = null
    }
  },
  
  // ==================
  // 创建智能体
  // ==================
  createAgent: async (params: CreateAgentParams) => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await agentApi.create(params)
      // 重新获取列表
      await get().fetchAgents()
      return result.agent
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '创建智能体失败',
        isLoading: false,
      })
      return null
    }
  },
  
  // ==================
  // 更新智能体
  // ==================
  updateAgent: async (id: string, params: UpdateAgentParams) => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await agentApi.update(id, params)
      // 更新本地状态
      if (get().selectedAgentId === id) {
        set({ selectedAgent: result.agent })
      }
      // 重新获取列表
      await get().fetchAgents()
      return result.agent
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '更新智能体失败',
        isLoading: false,
      })
      return null
    }
  },
  
  // ==================
  // 删除智能体
  // ==================
  deleteAgent: async (id: string) => {
    set({ isLoading: true, error: null })
    
    try {
      await agentApi.delete(id)
      // 如果删除的是当前选中的，清除选择
      if (get().selectedAgentId === id) {
        set({ selectedAgentId: null, selectedAgent: null })
      }
      // 重新获取列表
      await get().fetchAgents()
      return true
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '删除智能体失败',
        isLoading: false,
      })
      return false
    }
  },
  
  // ==================
  // 发送指令给智能体
  // ==================
  commandAgent: async (id: string, params: AgentCommandParams) => {
    set({ isLoading: true, error: null })
    
    try {
      await agentApi.command(id, params)
      // 刷新详情
      if (get().selectedAgentId === id) {
        await get().fetchAgentDetail(id)
      }
      return true
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '发送指令失败',
        isLoading: false,
      })
      return false
    }
  },
}))
