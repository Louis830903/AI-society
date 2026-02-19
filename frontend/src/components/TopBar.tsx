/**
 * 顶部导航栏组件
 * 
 * 显示：
 * - Logo和标题
 * - 世界时间
 * - 时间控制（暂停/恢复/缩放）
 * - 连接状态
 * - 成本统计
 */

import { useState } from 'react'
import { 
  Play, 
  Pause, 
  Clock, 
  Wifi, 
  WifiOff, 
  Menu, 
  DollarSign,
  FastForward,
  ChevronDown,
  Building2,
  Plus,
  User,
  Settings,
} from 'lucide-react'
import { useWorldStore } from '../store/worldStore'
import { SocialHealthIndicator } from './EventNotification'

interface TopBarProps {
  onToggleSidebar: () => void
  onAddBuilding?: () => void
  onAddAgent?: () => void
  onOpenWorldControl?: () => void
}

// 时间缩放选项
const TIME_SCALE_OPTIONS = [1, 5, 10, 20, 50]

export default function TopBar({ onToggleSidebar, onAddBuilding, onAddAgent, onOpenWorldControl }: TopBarProps) {
  // 从全局状态获取数据
  const { 
    worldTime, 
    isConnected, 
    isPaused, 
    timeScale, 
    togglePause, 
    setTimeScale,
    todayCost,
    budgetRemaining,
  } = useWorldStore()
  
  // 时间缩放下拉菜单状态
  const [showScaleMenu, setShowScaleMenu] = useState(false)
  
  return (
    <header className="h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between shadow-sm">
      {/* 左侧：Logo和标题 */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onToggleSidebar}
          className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          title="切换侧边栏"
        >
          <Menu className="w-5 h-5 text-slate-600" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800 leading-tight">AI Society</h1>
            <p className="text-xs text-slate-400 -mt-0.5">自治智能体社会</p>
          </div>
        </div>
      </div>
      
      {/* 中间：世界时间 */}
      <div className="flex items-center gap-6">
        {worldTime ? (
          <>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-500" />
              <span className="text-lg font-mono font-medium text-slate-700">
                {worldTime.formatted_time}
              </span>
              <span className="text-sm text-slate-500">
                {worldTime.formatted_date}
              </span>
            </div>
            <div className={`px-2 py-1 rounded text-xs font-medium ${
              worldTime.is_daytime 
                ? 'bg-amber-100 text-amber-700' 
                : 'bg-indigo-100 text-indigo-700'
            }`}>
              {worldTime.is_daytime ? '☀️ 白天' : '🌙 夜晚'}
            </div>
          </>
        ) : (
          <span className="text-slate-400">加载中...</span>
        )}
      </div>
      
      {/* 右侧：控制按钮和状态 */}
      <div className="flex items-center gap-4">
        {/* 新建建筑按钮 */}
        {onAddBuilding && (
          <button
            onClick={onAddBuilding}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
            title="新建建筑物"
          >
            <Building2 className="w-4 h-4" />
            <Plus className="w-3 h-3" />
          </button>
        )}
        
        {/* 新建智能体按钮 */}
        {onAddAgent && (
          <button
            onClick={onAddAgent}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-500 hover:bg-violet-600 text-white rounded-lg transition-colors"
            title="新建智能体"
          >
            <User className="w-4 h-4" />
            <Plus className="w-3 h-3" />
          </button>
        )}
        
        {/* 世界控制按钮 */}
        {onOpenWorldControl && (
          <button
            onClick={onOpenWorldControl}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
            title="世界控制中心"
          >
            <Settings className="w-4 h-4" />
          </button>
        )}
        
        {/* 时间控制 */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {/* 暂停/恢复按钮 */}
          <button 
            onClick={() => togglePause()}
            className={`p-2 rounded-lg transition-colors ${
              isPaused 
                ? 'bg-green-500 text-white hover:bg-green-600' 
                : 'hover:bg-slate-200'
            }`}
            title={isPaused ? '恢复' : '暂停'}
          >
            {isPaused ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4 text-slate-600" />
            )}
          </button>
          
          {/* 时间缩放选择器 */}
          <div className="relative">
            <button
              onClick={() => setShowScaleMenu(!showScaleMenu)}
              className="flex items-center gap-1 px-2 py-2 hover:bg-slate-200 rounded-lg transition-colors"
              title="时间缩放"
            >
              <FastForward className="w-4 h-4 text-slate-600" />
              <span className="text-sm font-medium text-slate-700">{timeScale}x</span>
              <ChevronDown className="w-3 h-3 text-slate-500" />
            </button>
            
            {/* 下拉菜单 */}
            {showScaleMenu && (
              <div className="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
                {TIME_SCALE_OPTIONS.map((scale) => (
                  <button
                    key={scale}
                    onClick={() => {
                      setTimeScale(scale)
                      setShowScaleMenu(false)
                    }}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-100 transition-colors ${
                      timeScale === scale ? 'text-primary-600 font-medium' : 'text-slate-700'
                    }`}
                  >
                    {scale}x
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* 社会健康指示器 */}
        <div className="px-3 py-1.5 bg-slate-100 rounded-lg">
          <SocialHealthIndicator />
        </div>
        
        {/* 成本统计 */}
        <div className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 rounded-lg">
          <DollarSign className="w-4 h-4 text-slate-500" />
          <div className="text-sm">
            <span className="font-medium text-slate-700">${(todayCost ?? 0).toFixed(2)}</span>
            <span className="text-slate-400 mx-1">/</span>
            <span className="text-slate-500">${(budgetRemaining ?? 0).toFixed(0)}</span>
          </div>
        </div>
        
        {/* 连接状态 */}
        <div className={`flex items-center gap-1 px-2 py-1.5 rounded-lg ${
          isConnected 
            ? 'bg-green-100 text-green-700' 
            : 'bg-red-100 text-red-700'
        }`}>
          {isConnected ? (
            <Wifi className="w-4 h-4" />
          ) : (
            <WifiOff className="w-4 h-4" />
          )}
          <span className="text-xs font-medium">
            {isConnected ? '已连接' : '断开'}
          </span>
        </div>
      </div>
    </header>
  )
}
