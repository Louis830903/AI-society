/**
 * 智能体详情面板
 * 
 * 显示选中智能体的详细信息：
 * - 基本信息
 * - 人格特征
 * - 需求状态
 * - 当前行动
 * - 关系网络
 * - 记忆列表
 * - 编辑/删除/指令功能
 */

import { useState, useEffect } from 'react'
import { X, Brain, Heart, MapPin, Briefcase, Clock, Users, Loader2, Crosshair, BookOpen, ChevronDown, ChevronUp, Edit2, Trash2, Send, Navigation, MessageSquare, Activity, Zap, History } from 'lucide-react'
import { useAgentStore } from '../store/agentStore'
import { useLocationStore } from '../store/locationStore'
import { agentApi } from '../services/api'
import type { Memory } from '../types'
import type { UpdateAgentParams, AgentCommandParams } from '../services/api'
import { ActivityTimeline } from './ActivityTimeline'

interface AgentDetailPanelProps {
  onClose: () => void
}

/**
 * 需求条形图
 */
function NeedBar({ label, value, color }: { label: string; value: number; color: string }) {
  const safeValue = value ?? 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-12">{label}</span>
      <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
      <span className="text-xs text-slate-600 w-8 text-right">{safeValue.toFixed(0)}</span>
    </div>
  )
}

/**
 * 人格特征条形图
 */
function PersonalityBar({ label, value }: { label: string; value: number }) {
  const safeValue = value ?? 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-16">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all"
          style={{ width: `${safeValue}%` }}
        />
      </div>
      <span className="text-xs text-slate-600 w-6 text-right">{safeValue}</span>
    </div>
  )
}

/**
 * 行动类型对应的图标
 */
const ACTION_ICONS: Record<string, string> = {
  idle: '💤',
  move: '🚶',
  work: '💼',
  eat: '🍽️',
  sleep: '😴',
  rest: '🛋️',
  chat: '💬',
  shop: '🛒',
}

/**
 * 行动类型对应的中文
 */
const ACTION_LABELS: Record<string, string> = {
  idle: '闲逛',
  move: '移动',
  work: '工作',
  eat: '吃饭',
  sleep: '睡觉',
  rest: '休息',
  chat: '聊天',
  shop: '购物',
}

/**
 * 记忆类型对应的图标和颜色
 */
const MEMORY_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  event: { icon: '📅', color: 'bg-blue-100 text-blue-700', label: '事件' },
  conversation: { icon: '💬', color: 'bg-green-100 text-green-700', label: '对话' },
  observation: { icon: '👁️', color: 'bg-amber-100 text-amber-700', label: '观察' },
  reflection: { icon: '💭', color: 'bg-purple-100 text-purple-700', label: '反思' },
  plan: { icon: '📋', color: 'bg-cyan-100 text-cyan-700', label: '计划' },
}

/**
 * 记忆列表组件
 */
function MemoryList({ agentId }: { agentId: string }) {
  const [memories, setMemories] = useState<Memory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isExpanded, setIsExpanded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    const fetchMemories = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await agentApi.getMemories(agentId, 20)
        setMemories(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取记忆失败')
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchMemories()
  }, [agentId])
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="text-center py-4 text-sm text-slate-500">
        {error}
      </div>
    )
  }
  
  if (memories.length === 0) {
    return (
      <div className="text-center py-4 text-sm text-slate-500">
        暂无记忆
      </div>
    )
  }
  
  const displayMemories = isExpanded ? memories : memories.slice(0, 3)
  
  return (
    <div className="space-y-2">
      {displayMemories.map((memory, index) => {
        const config = MEMORY_CONFIG[memory.type] || { 
          icon: '📝', 
          color: 'bg-slate-100 text-slate-600', 
          label: memory.type 
        }
        
        return (
          <div
            key={memory.id}
            className={`p-3 rounded-lg border border-slate-100 ${config.color} stagger-item`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex items-start gap-2">
              <span className="text-base">{config.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium flex items-center gap-2">
                  <span>{config.label}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-400">重要度 {(memory.importance ?? 0).toFixed(1)}</span>
                </div>
                <div className="text-xs mt-1 line-clamp-2">
                  {memory.content}
                </div>
                {memory.keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {memory.keywords.slice(0, 3).map((kw, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-white/50 rounded text-xs">
                        {kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
      
      {memories.length > 3 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full py-2 text-xs text-slate-500 hover:text-primary-600 flex items-center justify-center gap-1 transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              展开更多 ({memories.length - 3})
            </>
          )}
        </button>
      )}
    </div>
  )
}

export default function AgentDetailPanel({ onClose }: AgentDetailPanelProps) {
  const { selectedAgent: agent, isLoading, followingAgentId, toggleFollow, updateAgent, deleteAgent, commandAgent } = useAgentStore()
  const { locations, fetchLocations } = useLocationStore()
  
  const isFollowing = followingAgentId === agent?.id
  
  // 编辑状态
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<UpdateAgentParams>({})
  
  // 指令面板状态
  const [showCommandPanel, setShowCommandPanel] = useState(false)
  const [commandType, setCommandType] = useState<'move' | 'talk' | 'activity' | 'custom'>('move')
  const [commandTarget, setCommandTarget] = useState('')
  const [customCommand, setCustomCommand] = useState('')
  const [commandLoading, setCommandLoading] = useState(false)
  
  // 删除确认
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  // 加载位置列表
  useEffect(() => {
    if (showCommandPanel && locations.length === 0) {
      fetchLocations()
    }
  }, [showCommandPanel, locations.length, fetchLocations])
  
  // 初始化编辑表单
  useEffect(() => {
    if (agent && isEditing) {
      setEditForm({
        name: agent.name,
        occupation: agent.occupation,
        balance: agent.balance,
      })
    }
  }, [agent, isEditing])
  
  // 保存编辑
  const handleSaveEdit = async () => {
    if (!agent) return
    const result = await updateAgent(agent.id, editForm)
    if (result) {
      setIsEditing(false)
    }
  }
  
  // 删除智能体
  const handleDelete = async () => {
    if (!agent) return
    const success = await deleteAgent(agent.id)
    if (success) {
      onClose()
    }
  }
  
  // 发送指令
  const handleSendCommand = async () => {
    if (!agent) return
    
    setCommandLoading(true)
    const params: AgentCommandParams = {
      command_type: commandType,
      target: commandTarget || undefined,
      custom_text: commandType === 'custom' ? customCommand : undefined,
    }
    
    await commandAgent(agent.id, params)
    setCommandLoading(false)
    setShowCommandPanel(false)
    setCommandTarget('')
    setCustomCommand('')
  }
  
  // 加载中状态
  if (isLoading || !agent) {
    return (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-2xl w-[480px] p-8 flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          <span className="text-slate-600">加载中...</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl w-[480px] max-h-[90vh] overflow-hidden animate-scale-in">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                <span className="text-3xl">
                  {agent.gender === '男' ? '👨' : '👩'}
                </span>
              </div>
              <div className="text-white">
                <h2 className="text-xl font-bold">{agent.name}</h2>
                <div className="flex items-center gap-2 text-white/80 text-sm">
                  <span>{agent.age}岁</span>
                  <span>·</span>
                  <span>{agent.gender}</span>
                  <span>·</span>
                  <span>{agent.occupation}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {/* 指令按钮 */}
              <button
                onClick={() => setShowCommandPanel(!showCommandPanel)}
                className={`p-1.5 rounded transition-colors ${
                  showCommandPanel 
                    ? 'bg-amber-500 hover:bg-amber-600' 
                    : 'hover:bg-white/20'
                }`}
                title="发送指令"
              >
                <Send className="w-5 h-5 text-white" />
              </button>
              {/* 编辑按钮 */}
              <button
                onClick={() => setIsEditing(!isEditing)}
                className={`p-1.5 rounded transition-colors ${
                  isEditing 
                    ? 'bg-blue-500 hover:bg-blue-600' 
                    : 'hover:bg-white/20'
                }`}
                title="编辑智能体"
              >
                <Edit2 className="w-5 h-5 text-white" />
              </button>
              {/* 删除按钮 */}
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-1.5 rounded hover:bg-red-500 transition-colors"
                title="删除智能体"
              >
                <Trash2 className="w-5 h-5 text-white" />
              </button>
              {/* 跟随按钮 */}
              <button
                onClick={() => toggleFollow(agent.id)}
                className={`p-1.5 rounded transition-colors ${
                  isFollowing 
                    ? 'bg-green-500 hover:bg-green-600' 
                    : 'hover:bg-white/20'
                }`}
                title={isFollowing ? '停止跟随' : '跟随此智能体'}
              >
                <Crosshair className="w-5 h-5 text-white" />
              </button>
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded transition-colors"
              >
                <X className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>
        </div>
        
        {/* 删除确认对话框 */}
        {showDeleteConfirm && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-10 rounded-xl">
            <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm mx-4">
              <h3 className="text-lg font-semibold text-slate-800 mb-2">确认删除</h3>
              <p className="text-slate-600 mb-4">
                确定要删除智能体 <span className="font-medium">{agent.name}</span> 吗？此操作不可撤销。
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* 指令面板 */}
        {showCommandPanel && (
          <div className="bg-amber-50 border-b border-amber-100 px-6 py-4">
            <h4 className="text-sm font-medium text-amber-800 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              发送指令
            </h4>
            
            {/* 指令类型选择 */}
            <div className="flex gap-2 mb-3">
              <button
                onClick={() => setCommandType('move')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  commandType === 'move'
                    ? 'bg-amber-500 text-white'
                    : 'bg-white text-amber-700 hover:bg-amber-100'
                }`}
              >
                <Navigation className="w-4 h-4" />
                移动
              </button>
              <button
                onClick={() => setCommandType('talk')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  commandType === 'talk'
                    ? 'bg-amber-500 text-white'
                    : 'bg-white text-amber-700 hover:bg-amber-100'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                对话
              </button>
              <button
                onClick={() => setCommandType('activity')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  commandType === 'activity'
                    ? 'bg-amber-500 text-white'
                    : 'bg-white text-amber-700 hover:bg-amber-100'
                }`}
              >
                <Activity className="w-4 h-4" />
                活动
              </button>
              <button
                onClick={() => setCommandType('custom')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  commandType === 'custom'
                    ? 'bg-amber-500 text-white'
                    : 'bg-white text-amber-700 hover:bg-amber-100'
                }`}
              >
                <Send className="w-4 h-4" />
                自定义
              </button>
            </div>
            
            {/* 指令目标输入 */}
            {commandType === 'move' && (
              <select
                value={commandTarget}
                onChange={(e) => setCommandTarget(e.target.value)}
                className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none mb-3"
              >
                <option value="">选择目的地...</option>
                {locations.map(loc => (
                  <option key={loc.id} value={loc.id}>{loc.name}</option>
                ))}
              </select>
            )}
            
            {commandType === 'talk' && (
              <input
                type="text"
                value={commandTarget}
                onChange={(e) => setCommandTarget(e.target.value)}
                placeholder="输入对话对象名称..."
                className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none mb-3"
              />
            )}
            
            {commandType === 'activity' && (
              <select
                value={commandTarget}
                onChange={(e) => setCommandTarget(e.target.value)}
                className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none mb-3"
              >
                <option value="">选择活动...</option>
                <option value="eat">吃饭</option>
                <option value="work">工作</option>
                <option value="rest">休息</option>
                <option value="exercise">运动</option>
                <option value="shop">购物</option>
                <option value="socialize">社交</option>
              </select>
            )}
            
            {commandType === 'custom' && (
              <textarea
                value={customCommand}
                onChange={(e) => setCustomCommand(e.target.value)}
                placeholder="输入自定义指令..."
                className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none mb-3 resize-none"
                rows={2}
                maxLength={200}
              />
            )}
            
            <button
              onClick={handleSendCommand}
              disabled={commandLoading || (commandType !== 'custom' && !commandTarget) || (commandType === 'custom' && !customCommand)}
              className="w-full py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {commandLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  发送中...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  发送指令
                </>
              )}
            </button>
          </div>
        )}
        
        {/* 编辑面板 */}
        {isEditing && (
          <div className="bg-blue-50 border-b border-blue-100 px-6 py-4">
            <h4 className="text-sm font-medium text-blue-800 mb-3 flex items-center gap-2">
              <Edit2 className="w-4 h-4" />
              编辑智能体
            </h4>
            
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-blue-700 mb-1">姓名</label>
                <input
                  type="text"
                  value={editForm.name || ''}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-blue-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              
              <div>
                <label className="block text-xs text-blue-700 mb-1">职业</label>
                <input
                  type="text"
                  value={editForm.occupation || ''}
                  onChange={(e) => setEditForm({ ...editForm, occupation: e.target.value })}
                  className="w-full px-3 py-2 border border-blue-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              
              <div>
                <label className="block text-xs text-blue-700 mb-1">余额</label>
                <input
                  type="number"
                  value={editForm.balance || 0}
                  onChange={(e) => setEditForm({ ...editForm, balance: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-blue-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => setIsEditing(false)}
                  className="flex-1 py-2 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={isLoading}
                  className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                >
                  {isLoading ? '保存中...' : '保存'}
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* 内容 */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* 当前状态 */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <Clock className="w-4 h-4" />
              当前状态
            </h3>
            <div className="bg-slate-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {ACTION_ICONS[agent.current_action?.type] || '❓'}
                </span>
                <div>
                  <div className="font-medium text-slate-800">
                    {ACTION_LABELS[agent.current_action?.type] || agent.current_action?.type || '未知'}
                  </div>
                  {agent.current_action?.target && (
                    <div className="text-sm text-slate-500">
                      目标: {agent.current_action.target}
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
                <MapPin className="w-4 h-4" />
                <span>{agent.position?.location_name || '未知位置'}</span>
              </div>
            </div>
          </section>
          
          {/* 需求状态 */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <Heart className="w-4 h-4" />
              需求状态
            </h3>
            <div className="space-y-2">
              <NeedBar label="饥饿" value={agent.needs?.hunger} color="bg-orange-500" />
              <NeedBar label="疲劳" value={agent.needs?.fatigue} color="bg-purple-500" />
              <NeedBar label="社交" value={agent.needs?.social} color="bg-blue-500" />
              <NeedBar label="娱乐" value={agent.needs?.entertainment} color="bg-pink-500" />
              <NeedBar label="卫生" value={agent.needs?.hygiene} color="bg-cyan-500" />
              <NeedBar label="舒适" value={agent.needs?.comfort} color="bg-green-500" />
            </div>
          </section>
          
          {/* 人格特征 */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <Brain className="w-4 h-4" />
              人格特征 (OCEAN)
            </h3>
            <div className="space-y-1.5">
              <PersonalityBar label="开放性" value={agent.personality?.openness} />
              <PersonalityBar label="尽责性" value={agent.personality?.conscientiousness} />
              <PersonalityBar label="外向性" value={agent.personality?.extraversion} />
              <PersonalityBar label="宜人性" value={agent.personality?.agreeableness} />
              <PersonalityBar label="神经质" value={agent.personality?.neuroticism} />
            </div>
          </section>
          
          {/* 基本信息 */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <Briefcase className="w-4 h-4" />
              基本信息
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-slate-500 text-xs">账户余额</div>
                <div className="font-semibold text-slate-800">¥{(agent.balance ?? 0).toFixed(2)}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-slate-500 text-xs">使用模型</div>
                <div className="font-semibold text-slate-800 text-xs truncate">
                  {agent.model_name}
                </div>
              </div>
            </div>
          </section>
          
          {/* 关系网络 */}
          {agent.relationships && Object.keys(agent.relationships).length > 0 && (
            <section>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
                <Users className="w-4 h-4" />
                关系网络
              </h3>
              <div className="space-y-2">
                {Object.values(agent.relationships).map((rel) => (
                  <div
                    key={rel.target_id}
                    className="flex items-center justify-between bg-slate-50 rounded-lg p-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-lg">👤</span>
                      <div>
                        <div className="font-medium text-slate-700">{rel.target_name}</div>
                        <div className="text-xs text-slate-500">{rel.description}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-slate-500">亲密度</div>
                      <div className="font-semibold text-primary-600">{rel.closeness}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
          
          {/* 记忆列表 */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <BookOpen className="w-4 h-4" />
              近期记忆
            </h3>
            <MemoryList agentId={agent.id} />
          </section>
          
          {/* 活动历史 (Phase 7) */}
          <section>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
              <History className="w-4 h-4" />
              活动历史
            </h3>
            <ActivityTimeline agentId={agent.id} />
          </section>
        </div>
      </div>
    </div>
  )
}
