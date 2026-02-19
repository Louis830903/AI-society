/**
 * 侧边栏组件
 * 
 * 包含：
 * - 事件流面板
 * - 智能体列表
 * - 统计信息
 */

import { X, MessageCircle, Users, BarChart2, RefreshCw, Plus, MapPin, MessagesSquare } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useWorldStore } from '../store/worldStore'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { OccupationList } from './StatsCharts'
import { ConversationListPanel } from './ConversationListPanel'
import type { WorldEvent } from '../types'

interface SidebarProps {
  onClose: () => void
}

type TabType = 'events' | 'conversations' | 'agents' | 'stats'

export default function Sidebar({ onClose }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<TabType>('events')
  
  return (
    <aside className="w-80 bg-white border-l border-slate-200 flex flex-col shadow-lg">
      {/* 标签页头部 */}
      <div className="flex items-center border-b border-slate-200">
        <button
          onClick={() => setActiveTab('events')}
          className={`flex-1 px-3 py-3 text-xs font-medium flex items-center justify-center gap-1 transition-colors ${
            activeTab === 'events' 
              ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50' 
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          <MessageCircle className="w-4 h-4" />
          事件
        </button>
        <button
          onClick={() => setActiveTab('conversations')}
          className={`flex-1 px-3 py-3 text-xs font-medium flex items-center justify-center gap-1 transition-colors ${
            activeTab === 'conversations' 
              ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50' 
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          <MessagesSquare className="w-4 h-4" />
          对话
        </button>
        <button
          onClick={() => setActiveTab('agents')}
          className={`flex-1 px-3 py-3 text-xs font-medium flex items-center justify-center gap-1 transition-colors ${
            activeTab === 'agents' 
              ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50' 
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          <Users className="w-4 h-4" />
          智能体
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`flex-1 px-3 py-3 text-xs font-medium flex items-center justify-center gap-1 transition-colors ${
            activeTab === 'stats' 
              ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50' 
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          统计
        </button>
        <button 
          onClick={onClose}
          className="p-3 hover:bg-slate-100 transition-colors"
        >
          <X className="w-4 h-4 text-slate-500" />
        </button>
      </div>
      
      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'events' && <EventsPanel />}
        {activeTab === 'conversations' && <ConversationListPanel />}
        {activeTab === 'agents' && <AgentsPanel />}
        {activeTab === 'stats' && <StatsPanel />}
      </div>
    </aside>
  )
}

/**
 * 事件类型对应的图标和颜色
 */
const EVENT_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  'world.tick': { icon: '⏰', color: 'bg-slate-100 text-slate-600', label: '时间流逝' },
  'agent.created': { icon: '👤', color: 'bg-green-100 text-green-700', label: '智能体创建' },
  'agent.moved': { icon: '🚶', color: 'bg-blue-100 text-blue-700', label: '移动' },
  'agent.action': { icon: '⚡', color: 'bg-amber-100 text-amber-700', label: '行动' },
  'agent.state_changed': { icon: '🔄', color: 'bg-purple-100 text-purple-700', label: '状态变更' },
  'conversation.started': { icon: '💬', color: 'bg-cyan-100 text-cyan-700', label: '对话开始' },
  'conversation.message': { icon: '💭', color: 'bg-indigo-100 text-indigo-700', label: '新消息' },
  'conversation.ended': { icon: '✅', color: 'bg-teal-100 text-teal-700', label: '对话结束' },
  'relationship.changed': { icon: '❤️', color: 'bg-pink-100 text-pink-700', label: '关系变化' },
  'error': { icon: '❌', color: 'bg-red-100 text-red-700', label: '错误' },
}

/**
 * 事件流面板
 */
function EventsPanel() {
  const { events, isConnected, clearEvents } = useWorldStore()
  const { selectConversation } = useConversationStore()
  
  // 过滤掉world.tick事件（太多了）
  const filteredEvents = (events || []).filter(e => e.event_type !== 'world.tick').slice(-50)
  
  if (!isConnected) {
    return (
      <div className="p-4">
        <div className="text-center py-8 text-slate-500">
          <div className="text-3xl mb-2">🔌</div>
          <p>等待连接到服务器...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="p-4">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500">
          最近 {filteredEvents.length} 条事件
        </span>
        <button
          onClick={clearEvents}
          className="text-xs text-slate-500 hover:text-primary-600 transition-colors"
        >
          清空
        </button>
      </div>
      
      {/* 事件列表 */}
      {filteredEvents.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <div className="text-3xl mb-2">📭</div>
          <p>暂无事件</p>
        </div>
      ) : (
        <div className="space-y-2">
          {[...filteredEvents].reverse().map((event, idx) => (
            <EventCard
              key={`${event.event_type}-${idx}`}
              event={event}
              onClick={() => {
                if (event.event_type?.startsWith('conversation.') && event.data?.conversation_id) {
                  selectConversation(event.data.conversation_id as string)
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * 事件卡片
 */
function EventCard({ event, onClick }: { event: WorldEvent; onClick?: () => void }) {
  const eventType = event?.event_type || ''
  
  const config = EVENT_CONFIG[eventType] || { 
    icon: '📋', 
    color: 'bg-slate-100 text-slate-600', 
    label: eventType || '未知事件'
  }
  
  const isClickable = eventType.startsWith('conversation.')
  
  return (
    <div
      onClick={isClickable ? onClick : undefined}
      className={`p-3 rounded-lg border border-slate-100 ${config.color} ${
        isClickable ? 'cursor-pointer hover:border-slate-300 hover:shadow-md' : ''
      } transition-all card-hover animate-slide-in-left`}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium">{config.label}</div>
          <div className="text-xs opacity-75 mt-0.5 truncate">
            {formatEventData(event)}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * 格式化事件数据
 */
function formatEventData(event: WorldEvent): string {
  const { event_type, data } = event
  
  switch (event_type) {
    case 'agent.created':
      return `${data.agent_name || '新智能体'}创建成功`
    case 'agent.moved':
      return `${data.agent_name || '智能体'} → ${data.to_location || '未知地点'}`
    case 'agent.action':
      return `${data.agent_name || '智能体'}: ${data.action_type || '行动'}`
    case 'conversation.started':
      return `${data.agent_a_name || '?'} 与 ${data.agent_b_name || '?'} 开始对话`
    case 'conversation.message':
      return `${data.speaker_name || '?'}: ${(data.content as string)?.slice(0, 20) || '...'}`
    case 'conversation.ended':
      return `对话结束`
    case 'relationship.changed':
      const change = data.change as number || 0
      return `亲密度 ${change > 0 ? '+' : ''}${change}`
    default:
      return JSON.stringify(data).slice(0, 50)
  }
}

/**
 * 智能体列表面板
 */
function AgentsPanel() {
  const { agents, totalAgents, maxAgents, isLoading, fetchAgents, generateAgents, selectAgent } = useAgentStore()
  const [generating, setGenerating] = useState(false)
  
  // 首次加载
  useEffect(() => {
    if (!agents?.length) {
      fetchAgents()
    }
  }, [agents?.length, fetchAgents])
  
  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await generateAgents(10) // 每次生成10个
    } finally {
      setGenerating(false)
    }
  }
  
  return (
    <div className="p-4">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500">
          {totalAgents} / {maxAgents} 智能体
        </span>
        <div className="flex items-center gap-2">
          {totalAgents < maxAgents && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-primary-100 text-primary-700 rounded hover:bg-primary-200 transition-colors disabled:opacity-50"
            >
              {generating ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : (
                <Plus className="w-3 h-3" />
              )}
              生成
            </button>
          )}
          <button
            onClick={() => fetchAgents()}
            disabled={isLoading}
            className="p-1 text-slate-500 hover:text-primary-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
      
      {/* 智能体列表 */}
      {!agents?.length ? (
        <div className="text-center py-8 text-slate-500">
          <div className="text-3xl mb-2">👥</div>
          <p>暂无智能体</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="mt-3 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {generating ? '生成中...' : '生成智能体'}
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {(agents || []).map((agent, index) => (
            <div
              key={agent.id}
              onClick={() => selectAgent(agent.id)}
              className="p-3 bg-slate-50 rounded-lg border border-slate-100 hover:border-primary-300 hover:shadow-md cursor-pointer transition-all card-hover stagger-item"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-lg">
                    {agent.gender === '男' ? '👨' : '👩'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-700 truncate">{agent.name}</div>
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    <span>{agent.occupation}</span>
                    <span>·</span>
                    <MapPin className="w-3 h-3" />
                    <span className="truncate">{agent.current_location}</span>
                  </div>
                </div>
                <div className={`px-2 py-0.5 text-xs rounded-full ${
                  agent.state === 'active' ? 'bg-green-100 text-green-700' :
                  agent.state === 'sleeping' ? 'bg-purple-100 text-purple-700' :
                  agent.state === 'in_conversation' ? 'bg-blue-100 text-blue-700' :
                  agent.state === 'busy' ? 'bg-orange-100 text-orange-700' :
                  agent.state === 'paused' ? 'bg-gray-100 text-gray-700' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {agent.state === 'active' ? '活跃' :
                   agent.state === 'sleeping' ? '睡眠' :
                   agent.state === 'in_conversation' ? '对话中' :
                   agent.state === 'busy' ? '忙碌' :
                   agent.state === 'paused' ? '暂停' :
                   agent.state === 'offline' ? '离线' :
                   agent.state || '未知'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * 统计面板
 */
function StatsPanel() {
  const { todayCost, monthCost, budgetRemaining, isConnected } = useWorldStore()
  const { totalAgents, maxAgents } = useAgentStore()
  const { stats, fetchStats } = useConversationStore()
  
  // 首次加载
  useEffect(() => {
    fetchStats()
  }, [fetchStats])
  
  return (
    <div className="p-4 space-y-4">
      {/* 智能体统计 */}
      <div className="p-4 bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg border border-primary-200">
        <div className="text-sm font-medium text-primary-700 mb-2">智能体总数</div>
        <div className="text-3xl font-bold text-primary-600">
          {totalAgents} <span className="text-lg text-primary-400">/ {maxAgents}</span>
        </div>
        <div className="mt-2 h-2 bg-primary-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-500 rounded-full transition-all"
            style={{ width: `${(totalAgents / maxAgents) * 100}%` }}
          />
        </div>
      </div>
      
      {/* 职业分布 */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="text-sm font-medium text-slate-700 mb-3">职业分布</div>
        <OccupationList />
      </div>
      
      {/* 对话统计 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
          <div className="text-sm font-medium text-slate-600 mb-1">今日对话</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.history_count || 0}
          </div>
        </div>
        <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
          <div className="text-sm font-medium text-slate-600 mb-1">活跃对话</div>
          <div className="text-2xl font-bold text-blue-600">
            {stats?.active_conversations || 0}
          </div>
        </div>
      </div>
      
      {/* 成本统计 */}
      <div className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
        <div className="text-sm font-medium text-amber-700 mb-2">API 成本</div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-amber-600">今日</div>
            <div className="text-xl font-bold text-amber-700">${(todayCost ?? 0).toFixed(2)}</div>
          </div>
          <div>
            <div className="text-xs text-amber-600">本月</div>
            <div className="text-xl font-bold text-amber-700">${(monthCost ?? 0).toFixed(2)}</div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-amber-200">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-600">剩余预算</span>
            <span className="font-bold text-amber-700">${(budgetRemaining ?? 0).toFixed(0)}</span>
          </div>
          <div className="mt-1 h-2 bg-amber-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full transition-all"
              style={{ width: `${Math.max(0, ((budgetRemaining ?? 0) / 200) * 100)}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* 连接状态 */}
      <div className={`p-3 rounded-lg text-center ${
        isConnected 
          ? 'bg-green-50 border border-green-200 text-green-700' 
          : 'bg-red-50 border border-red-200 text-red-700'
      }`}>
        <div className="text-sm font-medium">
          {isConnected ? '✅ 服务器已连接' : '❌ 服务器断开'}
        </div>
      </div>
    </div>
  )
}
