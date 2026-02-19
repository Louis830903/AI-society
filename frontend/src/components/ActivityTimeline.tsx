/**
 * 智能体活动时间线组件
 * 
 * Phase 7: 观察者功能增强
 * 展示智能体的活动历史记录
 */

import { useState, useEffect } from 'react'
import { 
  Loader2, 
  Brain, 
  MessageSquare, 
  Lightbulb, 
  Zap, 
  Calendar,
  ChevronDown,
  ChevronUp,
  Filter
} from 'lucide-react'
import { agentApi } from '../services/api'
import type { Activity, ActivityType } from '../types'

interface ActivityTimelineProps {
  agentId: string
}

/**
 * 活动类型配置
 */
const ACTIVITY_CONFIG: Record<ActivityType, { 
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
  label: string 
}> = {
  decision: { 
    icon: Brain, 
    color: 'text-blue-600', 
    bgColor: 'bg-blue-50',
    label: '决策' 
  },
  conversation: { 
    icon: MessageSquare, 
    color: 'text-green-600', 
    bgColor: 'bg-green-50',
    label: '对话' 
  },
  reflection: { 
    icon: Lightbulb, 
    color: 'text-purple-600', 
    bgColor: 'bg-purple-50',
    label: '反思' 
  },
  reaction: { 
    icon: Zap, 
    color: 'text-orange-600', 
    bgColor: 'bg-orange-50',
    label: '反应' 
  },
  plan: { 
    icon: Calendar, 
    color: 'text-cyan-600', 
    bgColor: 'bg-cyan-50',
    label: '计划' 
  },
}

/**
 * 动作类型中文映射
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
  reflect: '反思',
  plan: '计划',
  interrupt: '中断',
  note: '记录',
}

/**
 * 单个活动项组件
 */
function ActivityItem({ 
  activity, 
  isExpanded,
  onToggle 
}: { 
  activity: Activity
  isExpanded: boolean
  onToggle: () => void
}) {
  const config = ACTIVITY_CONFIG[activity.activity_type] || ACTIVITY_CONFIG.decision
  const Icon = config.icon
  const actionLabel = ACTION_LABELS[activity.action] || activity.action
  
  // 格式化时间
  const gameTime = activity.game_time ? new Date(activity.game_time).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  }) : ''
  
  // 构建主要描述文本
  const getMainDescription = () => {
    if (activity.activity_type === 'conversation' && activity.conversation_partner) {
      return `与 ${activity.conversation_partner} 聊天`
    }
    if (activity.target) {
      return `${actionLabel} - ${activity.target}`
    }
    return actionLabel
  }
  
  // 判断是否有可展开的详情
  const hasDetails = !!(activity.thinking || activity.message_content || activity.reflection_content)
  
  return (
    <div className={`${config.bgColor} rounded-lg border border-slate-100 overflow-hidden`}>
      {/* 主要信息行 */}
      <div 
        className={`p-3 flex items-start gap-3 ${hasDetails ? 'cursor-pointer hover:bg-white/50' : ''}`}
        onClick={hasDetails ? onToggle : undefined}
      >
        {/* 图标 */}
        <div className={`p-1.5 rounded-full bg-white ${config.color}`}>
          <Icon className="w-4 h-4" />
        </div>
        
        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${config.color}`}>
              {config.label}
            </span>
            <span className="text-xs text-slate-400">·</span>
            <span className="text-xs text-slate-500">{gameTime}</span>
            {activity.location && (
              <>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-xs text-slate-400">{activity.location}</span>
              </>
            )}
          </div>
          <div className="text-sm text-slate-700 mt-0.5">
            {getMainDescription()}
          </div>
          
          {/* 对话消息预览 */}
          {activity.message_content && !isExpanded && (
            <div className="text-xs text-slate-500 mt-1 line-clamp-1">
              "{activity.message_content}"
            </div>
          )}
        </div>
        
        {/* 展开/收起按钮 */}
        {hasDetails && (
          <button className="p-1 text-slate-400 hover:text-slate-600">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>
      
      {/* 展开的详情 */}
      {isExpanded && hasDetails && (
        <div className="px-3 pb-3 pt-0 border-t border-slate-100/50">
          {/* 思考过程 */}
          {activity.thinking && (
            <div className="mt-2">
              <div className="text-xs font-medium text-slate-500 mb-1">思考过程</div>
              <div className="text-xs text-slate-600 bg-white/70 rounded p-2 whitespace-pre-wrap">
                {activity.thinking}
              </div>
            </div>
          )}
          
          {/* 对话内容 */}
          {activity.message_content && (
            <div className="mt-2">
              <div className="text-xs font-medium text-slate-500 mb-1">对话内容</div>
              <div className="text-xs text-slate-600 bg-white/70 rounded p-2">
                "{activity.message_content}"
              </div>
            </div>
          )}
          
          {/* 反思内容 */}
          {activity.reflection_content && (
            <div className="mt-2">
              <div className="text-xs font-medium text-slate-500 mb-1">反思洞察</div>
              <div className="text-xs text-slate-600 bg-white/70 rounded p-2">
                {activity.reflection_content}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * 活动时间线组件
 */
export function ActivityTimeline({ agentId }: ActivityTimelineProps) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [filter, setFilter] = useState<ActivityType | 'all'>('all')
  const [showMore, setShowMore] = useState(false)
  
  // 加载活动数据
  useEffect(() => {
    const fetchActivities = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const params: { activity_type?: string; limit: number } = { limit: 50 }
        if (filter !== 'all') {
          params.activity_type = filter
        }
        const data = await agentApi.getActivities(agentId, params)
        setActivities(data.activities)
        setTotal(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取活动历史失败')
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchActivities()
  }, [agentId, filter])
  
  // 切换展开状态
  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id)
  }
  
  // 渲染筛选按钮
  const renderFilterButtons = () => (
    <div className="flex items-center gap-1 mb-3 flex-wrap">
      <button
        onClick={() => setFilter('all')}
        className={`px-2 py-1 text-xs rounded-full transition-colors ${
          filter === 'all' 
            ? 'bg-primary-100 text-primary-700' 
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        }`}
      >
        全部
      </button>
      {(Object.entries(ACTIVITY_CONFIG) as [ActivityType, typeof ACTIVITY_CONFIG[ActivityType]][]).map(([type, config]) => (
        <button
          key={type}
          onClick={() => setFilter(type)}
          className={`px-2 py-1 text-xs rounded-full transition-colors flex items-center gap-1 ${
            filter === type 
              ? `${config.bgColor} ${config.color}` 
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <config.icon className="w-3 h-3" />
          {config.label}
        </button>
      ))}
    </div>
  )
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-sm text-red-500">{error}</div>
        <button 
          onClick={() => setFilter(filter)}
          className="mt-2 text-xs text-primary-600 hover:underline"
        >
          重试
        </button>
      </div>
    )
  }
  
  if (activities.length === 0) {
    return (
      <div className="text-center py-8">
        {renderFilterButtons()}
        <div className="text-sm text-slate-500 mt-4">
          {filter === 'all' ? '暂无活动记录' : `暂无${ACTIVITY_CONFIG[filter]?.label || ''}活动`}
        </div>
      </div>
    )
  }
  
  const displayActivities = showMore ? activities : activities.slice(0, 10)
  
  return (
    <div className="space-y-3">
      {/* 筛选器 */}
      {renderFilterButtons()}
      
      {/* 统计信息 */}
      <div className="text-xs text-slate-500 mb-2">
        共 {total} 条活动记录
      </div>
      
      {/* 活动列表 */}
      <div className="space-y-2">
        {displayActivities.map((activity, index) => (
          <div
            key={activity.id}
            className="stagger-item"
            style={{ animationDelay: `${index * 30}ms` }}
          >
            <ActivityItem
              activity={activity}
              isExpanded={expandedId === activity.id}
              onToggle={() => toggleExpand(activity.id)}
            />
          </div>
        ))}
      </div>
      
      {/* 加载更多 */}
      {activities.length > 10 && (
        <button
          onClick={() => setShowMore(!showMore)}
          className="w-full py-2 text-xs text-slate-500 hover:text-primary-600 flex items-center justify-center gap-1 transition-colors"
        >
          {showMore ? (
            <>
              <ChevronUp className="w-4 h-4" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              查看更多 ({activities.length - 10} 条)
            </>
          )}
        </button>
      )}
    </div>
  )
}

export default ActivityTimeline
