/**
 * 对话列表面板组件
 * 
 * 显示当前进行中的对话列表
 * 点击可跳转到对话位置或查看详情
 */

import { useEffect } from 'react'
import { MessageCircle, MapPin, Clock, ChevronRight, Users } from 'lucide-react'
import { useConversationStore } from '../store/conversationStore'
import type { ConversationBrief } from '../types'

interface ConversationListPanelProps {
  /** 点击对话时的回调 */
  onSelectConversation?: (conversationId: string) => void
  /** 点击跳转位置时的回调 */
  onJumpToLocation?: (locationId: string) => void
  /** 面板标题 */
  title?: string
  /** 是否显示历史对话 */
  showHistory?: boolean
  /** 最大显示数量 */
  maxItems?: number
}

/**
 * 单个对话条目组件
 */
function ConversationItem({
  conversation,
  onSelect,
  onJumpTo,
}: {
  conversation: ConversationBrief
  onSelect?: () => void
  onJumpTo?: () => void
}) {
  // 计算对话持续时间
  const getDuration = () => {
    const startTime = new Date(conversation.started_at).getTime()
    const now = Date.now()
    const minutes = Math.floor((now - startTime) / 60000)
    if (minutes < 1) return '刚刚开始'
    if (minutes < 60) return `${minutes}分钟`
    return `${Math.floor(minutes / 60)}小时${minutes % 60}分钟`
  }

  // 状态颜色
  const getStateColor = () => {
    switch (conversation.state) {
      case 'active':
        return 'bg-green-500'
      case 'pending':
        return 'bg-yellow-500'
      case 'ending':
        return 'bg-orange-500'
      default:
        return 'bg-gray-400'
    }
  }

  return (
    <div
      className="group p-3 bg-white rounded-lg border border-slate-200 hover:border-primary-300 hover:shadow-sm transition-all cursor-pointer"
      onClick={onSelect}
    >
      {/* 头部：参与者 + 状态 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${getStateColor()}`} />
          <span className="font-medium text-slate-800 text-sm">
            {conversation.participant_a_name}
          </span>
          <span className="text-slate-400 text-xs">与</span>
          <span className="font-medium text-slate-800 text-sm">
            {conversation.participant_b_name}
          </span>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-primary-500 transition-colors" />
      </div>

      {/* 信息区 */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        {/* 地点 */}
        {conversation.location && (
          <button
            className="flex items-center gap-1 hover:text-primary-600 transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              onJumpTo?.()
            }}
          >
            <MapPin className="w-3 h-3" />
            <span>{conversation.location}</span>
          </button>
        )}

        {/* 消息数 */}
        <div className="flex items-center gap-1">
          <MessageCircle className="w-3 h-3" />
          <span>{conversation.message_count}条</span>
        </div>

        {/* 时长 */}
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{getDuration()}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * 对话列表面板
 */
export function ConversationListPanel({
  onSelectConversation,
  onJumpToLocation,
  title = '进行中的对话',
  showHistory = false,
  maxItems = 10,
}: ConversationListPanelProps) {
  const {
    activeConversations,
    historyConversations,
    isLoading,
    fetchActiveConversations,
    fetchHistory,
    selectConversation,
  } = useConversationStore()

  // 加载数据
  useEffect(() => {
    fetchActiveConversations()
    if (showHistory) {
      fetchHistory()
    }
    
    // 定时刷新活跃对话
    const interval = setInterval(fetchActiveConversations, 5000)
    return () => clearInterval(interval)
  }, [fetchActiveConversations, fetchHistory, showHistory])

  // 选择要显示的对话列表
  const conversations = showHistory
    ? [...activeConversations, ...historyConversations].slice(0, maxItems)
    : activeConversations.slice(0, maxItems)

  return (
    <div className="flex flex-col h-full">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-primary-500" />
          <h2 className="font-semibold text-slate-800">{title}</h2>
          {activeConversations.length > 0 && (
            <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded-full">
              {activeConversations.length}
            </span>
          )}
        </div>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading && conversations.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <span className="text-sm">加载中...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-slate-400">
            <MessageCircle className="w-12 h-12 mb-2 opacity-50" />
            <span className="text-sm">暂无进行中的对话</span>
          </div>
        ) : (
          conversations.map((conv) => (
            <ConversationItem
              key={conv.id}
              conversation={conv}
              onSelect={() => {
                selectConversation(conv.id)
                onSelectConversation?.(conv.id)
              }}
              onJumpTo={() => {
                if (conv.location) {
                  onJumpToLocation?.(conv.location)
                }
              }}
            />
          ))
        )}
      </div>

      {/* 底部统计 */}
      {conversations.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              共 {conversations.reduce((sum, c) => sum + c.message_count, 0)} 条消息
            </span>
            <span>
              {activeConversations.length} 个进行中
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default ConversationListPanel
