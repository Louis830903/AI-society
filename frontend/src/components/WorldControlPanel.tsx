/**
 * 世界控制面板组件
 * 
 * 功能：
 * - 发送世界广播
 * - 管理世界规则
 * - 触发世界事件
 */

import { useState, useEffect } from 'react'
import { X, Radio, BookOpen, Zap, Settings, Send, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react'
import { useWorldStore, type WorldRule } from '../store/worldStore'

interface WorldControlPanelProps {
  /** 是否显示 */
  isOpen: boolean
  /** 关闭回调 */
  onClose: () => void
}

/**
 * 规则图标映射
 */
const RULE_ICONS: Record<string, string> = {
  curfew: '🌙',
  festival: '🎉',
  economic_crisis: '📉',
  free_day: '🏖️',
}

/**
 * 事件类型选项
 */
const EVENT_TYPES = [
  { value: 'announcement', label: '公告', icon: '📢' },
  { value: 'celebration', label: '庆典', icon: '🎊' },
  { value: 'disaster', label: '灾难', icon: '⚠️' },
  { value: 'economic', label: '经济', icon: '💰' },
]

/**
 * 广播优先级选项
 */
const PRIORITY_OPTIONS = [
  { value: 'low', label: '低', color: 'bg-slate-100 text-slate-600' },
  { value: 'normal', label: '普通', color: 'bg-blue-100 text-blue-600' },
  { value: 'high', label: '高', color: 'bg-amber-100 text-amber-600' },
  { value: 'urgent', label: '紧急', color: 'bg-red-100 text-red-600' },
]

export default function WorldControlPanel({
  isOpen,
  onClose,
}: WorldControlPanelProps) {
  const {
    worldRules,
    isLoadingControl,
    controlError,
    fetchWorldRules,
    toggleWorldRule,
    broadcastMessage,
    triggerWorldEvent,
  } = useWorldStore()
  
  // 当前标签页
  const [activeTab, setActiveTab] = useState<'broadcast' | 'rules' | 'events'>('broadcast')
  
  // 广播表单
  const [broadcastText, setBroadcastText] = useState('')
  const [broadcastPriority, setBroadcastPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal')
  const [affectMemory, setAffectMemory] = useState(true)
  const [broadcastResult, setBroadcastResult] = useState<string | null>(null)
  
  // 事件表单
  const [eventName, setEventName] = useState('')
  const [eventType, setEventType] = useState('announcement')
  const [eventDescription, setEventDescription] = useState('')
  const [eventResult, setEventResult] = useState<string | null>(null)
  
  // 加载规则
  useEffect(() => {
    if (isOpen && worldRules.length === 0) {
      fetchWorldRules()
    }
  }, [isOpen, worldRules.length, fetchWorldRules])
  
  // 发送广播
  const handleBroadcast = async () => {
    if (!broadcastText.trim()) return
    
    const affected = await broadcastMessage(broadcastText, broadcastPriority, affectMemory)
    
    if (affected > 0) {
      setBroadcastResult(`广播已发送，影响 ${affected} 个智能体`)
      setBroadcastText('')
      setTimeout(() => setBroadcastResult(null), 3000)
    }
  }
  
  // 触发事件
  const handleTriggerEvent = async () => {
    if (!eventName.trim()) return
    
    const success = await triggerWorldEvent(eventName, eventType, eventDescription)
    
    if (success) {
      setEventResult(`事件 "${eventName}" 已触发`)
      setEventName('')
      setEventDescription('')
      setTimeout(() => setEventResult(null), 3000)
    }
  }
  
  // 切换规则
  const handleToggleRule = async (rule: WorldRule) => {
    await toggleWorldRule(rule.id, !rule.enabled)
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[520px] max-h-[85vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <Settings className="w-6 h-6" />
            <h2 className="font-bold text-lg">世界控制中心</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* 标签页 */}
        <div className="flex border-b border-slate-200">
          <button
            onClick={() => setActiveTab('broadcast')}
            className={`flex-1 px-4 py-3 flex items-center justify-center gap-2 text-sm font-medium transition-colors ${
              activeTab === 'broadcast'
                ? 'text-indigo-600 border-b-2 border-indigo-500 bg-indigo-50'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Radio className="w-4 h-4" />
            广播
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            className={`flex-1 px-4 py-3 flex items-center justify-center gap-2 text-sm font-medium transition-colors ${
              activeTab === 'rules'
                ? 'text-indigo-600 border-b-2 border-indigo-500 bg-indigo-50'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            规则
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`flex-1 px-4 py-3 flex items-center justify-center gap-2 text-sm font-medium transition-colors ${
              activeTab === 'events'
                ? 'text-indigo-600 border-b-2 border-indigo-500 bg-indigo-50'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Zap className="w-4 h-4" />
            事件
          </button>
        </div>
        
        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* 错误提示 */}
          {controlError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {controlError}
            </div>
          )}
          
          {/* 广播标签页 */}
          {activeTab === 'broadcast' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  广播消息
                </label>
                <textarea
                  value={broadcastText}
                  onChange={(e) => setBroadcastText(e.target.value)}
                  placeholder="输入要向所有智能体发送的消息..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
                  rows={3}
                  maxLength={500}
                />
                <div className="text-xs text-slate-400 mt-1 text-right">
                  {broadcastText.length}/500
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  优先级
                </label>
                <div className="flex gap-2">
                  {PRIORITY_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setBroadcastPriority(opt.value as typeof broadcastPriority)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        broadcastPriority === opt.value
                          ? opt.color + ' ring-2 ring-offset-1 ring-indigo-500'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="affectMemory"
                  checked={affectMemory}
                  onChange={(e) => setAffectMemory(e.target.checked)}
                  className="w-4 h-4 text-indigo-500 rounded focus:ring-indigo-500"
                />
                <label htmlFor="affectMemory" className="text-sm text-slate-600">
                  写入智能体记忆（让智能体记住这条消息）
                </label>
              </div>
              
              {broadcastResult && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                  {broadcastResult}
                </div>
              )}
              
              <button
                onClick={handleBroadcast}
                disabled={isLoadingControl || !broadcastText.trim()}
                className="w-full py-2.5 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoadingControl ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    发送中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    发送广播
                  </>
                )}
              </button>
            </div>
          )}
          
          {/* 规则标签页 */}
          {activeTab === 'rules' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500 mb-4">
                启用或禁用世界规则，影响所有智能体的行为决策。
              </p>
              
              {worldRules.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  {isLoadingControl ? (
                    <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                  ) : (
                    '暂无可用规则'
                  )}
                </div>
              ) : (
                worldRules.map(rule => (
                  <div
                    key={rule.id}
                    className={`p-4 rounded-lg border transition-colors ${
                      rule.enabled
                        ? 'bg-indigo-50 border-indigo-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">{RULE_ICONS[rule.id] || '📋'}</span>
                        <div>
                          <h4 className="font-medium text-slate-800">{rule.name}</h4>
                          <p className="text-sm text-slate-500 mt-0.5">{rule.description}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleToggleRule(rule)}
                        disabled={isLoadingControl}
                        className="p-1 hover:bg-white/50 rounded transition-colors"
                      >
                        {rule.enabled ? (
                          <ToggleRight className="w-8 h-8 text-indigo-500" />
                        ) : (
                          <ToggleLeft className="w-8 h-8 text-slate-400" />
                        )}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
          
          {/* 事件标签页 */}
          {activeTab === 'events' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  事件名称
                </label>
                <input
                  type="text"
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                  placeholder="例如：新年庆典、突发暴雨"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  maxLength={100}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  事件类型
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {EVENT_TYPES.map(type => (
                    <button
                      key={type.value}
                      onClick={() => setEventType(type.value)}
                      className={`px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
                        eventType === type.value
                          ? 'bg-indigo-500 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      <span>{type.icon}</span>
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  事件描述（可选）
                </label>
                <textarea
                  value={eventDescription}
                  onChange={(e) => setEventDescription(e.target.value)}
                  placeholder="描述事件的具体内容..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
                  rows={2}
                  maxLength={500}
                />
              </div>
              
              {eventResult && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                  {eventResult}
                </div>
              )}
              
              <button
                onClick={handleTriggerEvent}
                disabled={isLoadingControl || !eventName.trim()}
                className="w-full py-2.5 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoadingControl ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    触发中...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    触发事件
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
