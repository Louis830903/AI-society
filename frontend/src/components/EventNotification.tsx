/**
 * 事件通知组件
 * =============
 * 显示智能体新增/离开等系统事件
 */

import { useState, useEffect, useCallback } from 'react'

interface ExpansionEvent {
  event_type: 'agent_joined' | 'agent_left'
  agent_id: string
  agent_name: string
  reason: string
  timestamp: string
  details: {
    occupation?: string
    location?: string
    lonely_agent_name?: string
    [key: string]: unknown
  }
}

interface EventNotificationProps {
  maxNotifications?: number
  autoHideDuration?: number
}

export default function EventNotification({
  maxNotifications = 5,
  autoHideDuration = 10000,
}: EventNotificationProps) {
  const [notifications, setNotifications] = useState<ExpansionEvent[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  // 获取最新事件
  const fetchEvents = useCallback(async () => {
    try {
      const response = await fetch('/api/expansion/events?limit=10')
      if (!response.ok) return

      const events: ExpansionEvent[] = await response.json()
      
      // 只保留新事件
      const now = new Date()
      const newEvents = events.filter(event => {
        const eventTime = new Date(event.timestamp)
        if (!lastFetch) return true
        return eventTime > lastFetch
      })

      if (newEvents.length > 0) {
        setNotifications(prev => {
          const combined = [...newEvents, ...prev]
          return combined.slice(0, maxNotifications)
        })
      }

      setLastFetch(now)
    } catch (error) {
      console.error('Failed to fetch events:', error)
    }
  }, [lastFetch, maxNotifications])

  // 定时获取事件
  useEffect(() => {
    fetchEvents()
    const interval = setInterval(fetchEvents, 30000) // 每30秒获取一次
    return () => clearInterval(interval)
  }, [fetchEvents])

  // 自动隐藏旧通知
  useEffect(() => {
    if (autoHideDuration <= 0) return

    const timer = setTimeout(() => {
      setNotifications(prev => {
        if (prev.length === 0) return prev
        const now = new Date()
        return prev.filter(event => {
          const eventTime = new Date(event.timestamp)
          return now.getTime() - eventTime.getTime() < autoHideDuration
        })
      })
    }, autoHideDuration)

    return () => clearTimeout(timer)
  }, [notifications, autoHideDuration])

  // 移除通知
  const dismissNotification = (index: number) => {
    setNotifications(prev => prev.filter((_, i) => i !== index))
  }

  // 清空所有通知
  const clearAll = () => {
    setNotifications([])
  }

  if (notifications.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      {/* 通知列表 */}
      <div className={`space-y-2 ${isExpanded ? '' : 'max-h-64 overflow-hidden'}`}>
        {notifications.map((event, index) => (
          <div
            key={`${event.agent_id}-${event.timestamp}`}
            className={`
              p-3 rounded-lg shadow-lg backdrop-blur-sm animate-slide-in-right
              ${event.event_type === 'agent_joined'
                ? 'bg-green-500/90 text-white'
                : 'bg-orange-500/90 text-white'
              }
            `}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                {/* 事件图标 */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">
                    {event.event_type === 'agent_joined' ? '👋' : '🚶'}
                  </span>
                  <span className="font-medium truncate">
                    {event.agent_name}
                  </span>
                </div>
                
                {/* 事件类型 */}
                <div className="text-sm opacity-90 mb-1">
                  {event.event_type === 'agent_joined' ? '加入了小镇' : '离开了小镇'}
                </div>
                
                {/* 原因 */}
                <div className="text-xs opacity-75 truncate">
                  {event.reason}
                </div>
                
                {/* 详情 */}
                {event.details.occupation && (
                  <div className="text-xs opacity-75 mt-1">
                    职业: {event.details.occupation}
                  </div>
                )}
              </div>
              
              {/* 关闭按钮 */}
              <button
                onClick={() => dismissNotification(index)}
                className="p-1 hover:bg-white/20 rounded transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 底部工具栏 */}
      {notifications.length > 1 && (
        <div className="flex items-center justify-between mt-2 px-2 text-xs text-gray-400">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="hover:text-white transition-colors"
          >
            {isExpanded ? '收起' : `展开 (${notifications.length})`}
          </button>
          <button
            onClick={clearAll}
            className="hover:text-white transition-colors"
          >
            清空
          </button>
        </div>
      )}
    </div>
  )
}


/**
 * 社会健康状态指示器
 */
interface HealthIndicatorProps {
  className?: string
}

export function SocialHealthIndicator({ className = '' }: HealthIndicatorProps) {
  const [healthScore, setHealthScore] = useState<number | null>(null)
  const [urgentNeeds, setUrgentNeeds] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const fetchHealth = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/expansion/balance/report')
      if (!response.ok) return

      const report = await response.json()
      setHealthScore(report.overall_health_score)
      setUrgentNeeds(report.urgent_needs || [])
    } catch (error) {
      console.error('Failed to fetch health:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 60000) // 每分钟更新
    return () => clearInterval(interval)
  }, [])

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-red-400'
  }

  const getHealthLabel = (score: number) => {
    if (score >= 80) return '健康'
    if (score >= 60) return '良好'
    if (score >= 40) return '一般'
    return '需关注'
  }

  if (healthScore === null) return null

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`flex items-center gap-1 ${getHealthColor(healthScore)}`}>
        <span className="text-sm">社会健康:</span>
        <span className="font-medium">{healthScore.toFixed(0)}</span>
        <span className="text-xs opacity-75">({getHealthLabel(healthScore)})</span>
      </div>
      
      {urgentNeeds.length > 0 && (
        <div className="relative group">
          <span className="text-orange-400 text-sm cursor-help">
            ⚠️ {urgentNeeds.length}个问题
          </span>
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 p-2 bg-gray-800 rounded shadow-lg 
                          invisible group-hover:visible opacity-0 group-hover:opacity-100 
                          transition-all duration-200 w-48 text-xs z-[100]">
            <div className="font-medium mb-1 text-white">紧急需求:</div>
            {urgentNeeds.map((need, i) => (
              <div key={i} className="text-gray-300">{need}</div>
            ))}
          </div>
        </div>
      )}
      
      {isLoading && (
        <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      )}
    </div>
  )
}
