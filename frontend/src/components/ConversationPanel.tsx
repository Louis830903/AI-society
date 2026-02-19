/**
 * 对话详情面板
 * 
 * 显示对话内容和分析结果：
 * - 参与者信息
 * - 消息列表
 * - 话题标签
 * - 情感分析
 * - 关系影响
 */

import { X, MessageCircle, TrendingUp, TrendingDown, Minus, Tag, Loader2 } from 'lucide-react'
import { useConversationStore } from '../store/conversationStore'
import type { Message } from '../types'

interface ConversationPanelProps {
  onClose: () => void
}

/**
 * 单条消息组件
 */
function MessageBubble({ message, isParticipantA }: { message: Message; isParticipantA: boolean }) {
  return (
    <div className={`flex ${isParticipantA ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[80%] px-4 py-2 rounded-2xl ${
          isParticipantA
            ? 'bg-slate-100 text-slate-800 rounded-bl-none'
            : 'bg-primary-500 text-white rounded-br-none'
        }`}
      >
        <div className="text-sm">{message.content}</div>
        {message.emotion && (
          <div className={`text-xs mt-1 ${isParticipantA ? 'text-slate-500' : 'text-white/70'}`}>
            {message.emotion}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 关系变化指示器
 */
function RelationshipIndicator({ change }: { change: number }) {
  const safeChange = change ?? 0
  if (safeChange > 0) {
    return (
      <div className="flex items-center gap-1 text-green-600">
        <TrendingUp className="w-4 h-4" />
        <span className="font-medium">+{safeChange}</span>
      </div>
    )
  } else if (safeChange < 0) {
    return (
      <div className="flex items-center gap-1 text-red-600">
        <TrendingDown className="w-4 h-4" />
        <span className="font-medium">{safeChange}</span>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-1 text-slate-500">
      <Minus className="w-4 h-4" />
      <span className="font-medium">0</span>
    </div>
  )
}

export default function ConversationPanel({ onClose }: ConversationPanelProps) {
  const { selectedConversation: conversation, isLoading } = useConversationStore()
  
  // 加载中状态
  if (isLoading || !conversation) {
    return (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-2xl w-[520px] p-8 flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="text-slate-600">加载中...</span>
        </div>
      </div>
    )
  }
  
  // 获取参与者A的消息（用于判断消息来源）
  const participantAId = conversation.participant_a_id

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[520px] max-h-[90vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <MessageCircle className="w-6 h-6" />
            <div>
              <h2 className="font-bold">
                {conversation.participant_a_name} & {conversation.participant_b_name}
              </h2>
              <div className="text-sm text-white/80">
                {conversation.location} · {conversation.message_count} 条消息
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* 对话内容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50">
          {!conversation.messages?.length ? (
            <div className="text-center py-8 text-slate-500">
              暂无消息记录
            </div>
          ) : (
            conversation.messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isParticipantA={msg.speaker_id === participantAId}
              />
            ))
          )}
        </div>
        
        {/* 分析结果 */}
        <div className="border-t border-slate-200 p-4 space-y-4">
          {/* 话题标签 */}
          {conversation.topics?.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-600 mb-2">
                <Tag className="w-4 h-4" />
                <span>话题</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {conversation.topics.map((topic, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-slate-100 text-slate-600 rounded-full text-xs"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* 统计信息 */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-xs text-slate-500 mb-1">整体情感</div>
              <div className="font-semibold text-slate-800">
                {conversation.overall_emotion}
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-xs text-slate-500 mb-1">关系影响</div>
              <RelationshipIndicator change={conversation.relationship_change} />
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-xs text-slate-500 mb-1">状态</div>
              <div className={`font-semibold ${
                conversation.state === 'active' ? 'text-green-600' :
                conversation.state === 'ended' ? 'text-slate-600' :
                'text-amber-600'
              }`}>
                {conversation.state === 'active' ? '进行中' :
                 conversation.state === 'ended' ? '已结束' :
                 conversation.state === 'pending' ? '等待中' :
                 conversation.state}
              </div>
            </div>
          </div>
          
          {/* 摘要 */}
          {conversation.summary && (
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="text-xs text-blue-600 mb-1">对话摘要</div>
              <div className="text-sm text-blue-800">{conversation.summary}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
