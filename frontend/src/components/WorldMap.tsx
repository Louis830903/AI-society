/**
 * 世界地图组件（PixiJS 版本）
 * 
 * 使用 PixiJS 渲染等距像素风格地图
 * 显示地点、智能体位置和对话气泡
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useWorldStore } from '../store/worldStore'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { useLocationStore } from '../store/locationStore'
import { MapPin, ZoomIn, ZoomOut, RotateCcw, MessageCircle, Crosshair, X, Sun, Cloud, CloudRain, Move } from 'lucide-react'

// 游戏系统
import { pixiApp } from '../game/PixiApp'
import { TileMap } from '../game/TileMap'
import { BuildingManager } from '../game/BuildingSprite'
import { AgentManager } from '../game/AgentSprite'
import { ChatBubbleManager } from '../game/ChatBubble'
import { backendToIsometric, screenToWorld, isometricToBackend } from '../game/IsometricUtils'
import { WeatherType } from '../game/WeatherSystem'

// 地点类型对应的图标
const LOCATION_ICONS: Record<string, string> = {
  home: '🏠',
  cafe: '☕',
  restaurant: '🍽️',
  office: '🏢',
  shop: '🛒',
  park: '🌳',
  school: '📚',
  hospital: '🏥',
  default: '📍',
}

interface MapState {
  scale: number
  offsetX: number
  offsetY: number
}

interface WorldMapProps {
  /** 地图点击选择位置回调（用于新建建筑物） */
  onPositionSelect?: (x: number, y: number) => void
  /** 是否处于位置选择模式 */
  isSelectingPosition?: boolean
  /** 是否处于建筑物拖拽模式 */
  isDraggingBuilding?: boolean
  /** 正在拖拽的建筑物ID */
  draggingBuildingId?: string | null
  /** 建筑物拖拽结束回调 */
  onBuildingDragEnd?: (locationId: string, newX: number, newY: number) => void
}

export default function WorldMap({ 
  onPositionSelect, 
  isSelectingPosition = false,
  isDraggingBuilding = false,
  draggingBuildingId = null,
  onBuildingDragEnd,
}: WorldMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const pixiContainerRef = useRef<HTMLDivElement>(null)
  
  // 从全局状态获取数据（使用 locationStore 的 locations，确保与 CRUD 操作同步）
  const { worldTime } = useWorldStore()
  const { locations, locationsLoaded, selectLocation } = useLocationStore()
  const { agents, selectedAgentId, selectAgent, fetchAgents, agentsLoaded, followingAgentId, stopFollowing } = useAgentStore()
  const { activeConversations, fetchActiveConversations, latestMessages } = useConversationStore()
  
  // 游戏系统引用
  const tileMapRef = useRef<TileMap | null>(null)
  const buildingManagerRef = useRef<BuildingManager | null>(null)
  const agentManagerRef = useRef<AgentManager | null>(null)
  const chatBubbleManagerRef = useRef<ChatBubbleManager | null>(null)
  
  // 地图状态
  const [mapState, setMapState] = useState<MapState>({
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  })
  
  // 天气状态
  const [currentWeather, setCurrentWeather] = useState<WeatherType>('sunny')
  
  // 拖拽状态
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  
  // PixiJS 初始化标记
  const [isPixiReady, setIsPixiReady] = useState(false)
  
  // 初始化 PixiJS
  useEffect(() => {
    const container = pixiContainerRef.current
    if (!container) return
    
    let mounted = true
    
    const initPixi = async () => {
      try {
        const rect = container.getBoundingClientRect()
        
        await pixiApp.init({
          width: rect.width,
          height: rect.height,
          backgroundColor: 0x87CEEB,  // 默认天空蓝
        })
        
        // 组件已卸载，不继续初始化
        if (!mounted) return
        
        const canvas = pixiApp.getCanvas()
        if (canvas && mounted) {
          container.appendChild(canvas)
          
          // 初始化游戏系统
          const layerManager = pixiApp.layerManager
          if (layerManager) {
            // 创建瓦片地图
            tileMapRef.current = new TileMap(layerManager.groundLayer, 50, 50)
            tileMapRef.current.generate()
            
            // 创建建筑管理器
            buildingManagerRef.current = new BuildingManager(layerManager.buildingLayer)
            
            // 创建智能体管理器
            agentManagerRef.current = new AgentManager(layerManager.agentLayer)
            
            // 创建聊天气泡管理器（添加到 UI 层）
            chatBubbleManagerRef.current = new ChatBubbleManager(layerManager.uiLayer)
            
            // 设置补间管理器
            if (pixiApp.tweenManager) {
              agentManagerRef.current.setTweenManager(pixiApp.tweenManager)
            }
            
            // 设置昼夜系统回调
            pixiApp.daylightSystem?.setCallbacks({
              onBackgroundChange: (color: number) => {
                pixiApp.setBackgroundColor(color)
              },
              onTintChange: (tint: number) => {
                layerManager.applyTint(tint)
                tileMapRef.current?.applyTint(tint)
              },
              onNightStart: () => {
                buildingManagerRef.current?.setAllNightLight(1)
              },
              onDayStart: () => {
                buildingManagerRef.current?.setAllNightLight(0)
              },
            })
            
            // 设置初始天气
            pixiApp.weatherSystem?.setWeather('sunny')
            
            // 注册智能体动画更新回调
            pixiApp.addUpdateCallback((deltaTime: number) => {
              agentManagerRef.current?.update(deltaTime)
            })
          }
          
          setIsPixiReady(true)
        }
      } catch (error) {
        // 如果是初始化被中止（组件卸载导致），这是正常情况，不记录错误
        if (error instanceof Error && error.message === 'PixiJS 初始化被中止') {
          console.debug('[WorldMap] PixiJS init aborted (component unmounted)')
          return
        }
        console.error('Failed to init PixiJS:', error)
      }
    }
    
    initPixi()
    
    return () => {
      mounted = false
      tileMapRef.current?.destroy()
      buildingManagerRef.current?.clear()
      agentManagerRef.current?.clear()
      chatBubbleManagerRef.current?.destroy()
      pixiApp.destroy()
      setIsPixiReady(false)
    }
  }, [])
  
  // 窗口大小变化处理
  useEffect(() => {
    if (!isPixiReady) return
    
    const handleResize = () => {
      const container = pixiContainerRef.current
      if (!container) return
      
      const rect = container.getBoundingClientRect()
      pixiApp.resize(rect.width, rect.height)
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [isPixiReady])
  
  // 首次加载数据
  useEffect(() => {
    if (!agentsLoaded) {
      fetchAgents()
    }
    fetchActiveConversations()
    
    const interval = setInterval(() => {
      fetchActiveConversations()
    }, 5000)
    
    return () => clearInterval(interval)
  }, [agentsLoaded, fetchAgents, fetchActiveConversations])
  
  // 同步建筑物
  useEffect(() => {
    if (!isPixiReady || !buildingManagerRef.current || !locations) return
    buildingManagerRef.current.sync(locations)
    
    // 标记需要重新排序
    pixiApp.layerManager?.markBuildingsDirty()
  }, [isPixiReady, locations])
  
  // 处理建筑物拖拽模式
  useEffect(() => {
    if (!isPixiReady || !buildingManagerRef.current) return
    
    if (isDraggingBuilding && draggingBuildingId) {
      // 创建拖拽结束回调
      const handleDragEnd = (locationId: string, newIsoX: number, newIsoY: number) => {
        // 转换等距坐标到后端坐标
        const { backendX, backendY } = isometricToBackend(newIsoX, newIsoY)
        onBuildingDragEnd?.(locationId, Math.round(backendX), Math.round(backendY))
      }
      
      // 启用指定建筑物的拖拽
      buildingManagerRef.current.setDraggable(draggingBuildingId, true, handleDragEnd)
    } else {
      // 禁用所有建筑物的拖拽
      buildingManagerRef.current.disableAllDragging()
    }
  }, [isPixiReady, isDraggingBuilding, draggingBuildingId, onBuildingDragEnd])
  
  // 同步智能体
  useEffect(() => {
    if (!isPixiReady || !agentManagerRef.current || !agents || !locations) return
    
    // 更新每个智能体
    agents.forEach(agent => {
      const location = locations.find(l => l.name === agent.current_location)
      if (location?.position) {
        const { isoX, isoY } = backendToIsometric(location.position.x, location.position.y)
        agentManagerRef.current?.addOrUpdate(agent, isoX, isoY)
      }
    })
    
    // 标记需要重新排序
    pixiApp.layerManager?.markAgentsDirty()
  }, [isPixiReady, agents, locations])
  
  // 同步选中状态
  useEffect(() => {
    if (!isPixiReady || !agentManagerRef.current) return
    agentManagerRef.current.setSelected(selectedAgentId)
  }, [isPixiReady, selectedAgentId])
  
  // 同步跟随状态
  useEffect(() => {
    if (!isPixiReady || !agentManagerRef.current) return
    agentManagerRef.current.setFollowing(followingAgentId)
  }, [isPixiReady, followingAgentId])
  
  // 同步对话状态
  useEffect(() => {
    if (!isPixiReady || !agentManagerRef.current || !agents) return
    
    const chattingIds = new Set<string>()
    activeConversations.forEach(conv => {
      const agentA = agents.find(a => a.name === conv.participant_a_name)
      const agentB = agents.find(a => a.name === conv.participant_b_name)
      if (agentA) chattingIds.add(agentA.id)
      if (agentB) chattingIds.add(agentB.id)
    })
    
    agentManagerRef.current.setChattingAgents(chattingIds)
  }, [isPixiReady, activeConversations, agents])
  
  // 同步聊天气泡（根据最新消息显示）
  useEffect(() => {
    if (!isPixiReady || !chatBubbleManagerRef.current || !agents || !locations) return
    
    // 遍历最新消息，为说话者显示气泡
    latestMessages.forEach((message, agentId) => {
      // 找到说话者
      const agent = agents.find(a => a.id === agentId)
      if (!agent) return
      
      // 找到智能体位置
      const agentLocation = locations.find(l => l.name === agent.current_location)
      if (!agentLocation?.position) return
      
      const { isoX, isoY } = backendToIsometric(agentLocation.position.x, agentLocation.position.y)
      
      // 显示气泡并更新位置
      chatBubbleManagerRef.current?.showBubble(agentId, message.content)
      chatBubbleManagerRef.current?.updateBubblePosition(agentId, isoX, isoY - 30)
    })
  }, [isPixiReady, latestMessages, agents, locations])
  
  // 更新昼夜系统
  useEffect(() => {
    if (!isPixiReady || !worldTime) return
    
    // 从 worldTime 提取小时
    const timeParts = worldTime.formatted_time.match(/(\d+):(\d+)/)
    if (timeParts) {
      const hour = parseInt(timeParts[1], 10)
      const minute = parseInt(timeParts[2], 10)
      const hourDecimal = hour + minute / 60
      
      pixiApp.daylightSystem?.updateTime(hourDecimal)
      
      // 更新建筑灯光
      const lightIntensity = pixiApp.daylightSystem?.getBuildingLightIntensity() ?? 0
      buildingManagerRef.current?.setAllNightLight(lightIntensity)
    }
  }, [isPixiReady, worldTime])
  
  // 跟随智能体逻辑
  useEffect(() => {
    if (!isPixiReady || !followingAgentId || !agents?.length || !locations) return
    
    const followingAgent = agents.find(a => a.id === followingAgentId)
    if (!followingAgent) return
    
    const agentLocation = locations.find(l => l.name === followingAgent.current_location)
    if (!agentLocation?.position) return
    
    const { isoX, isoY } = backendToIsometric(agentLocation.position.x, agentLocation.position.y)
    
    setMapState(prev => ({
      ...prev,
      offsetX: -isoX * prev.scale,
      offsetY: -isoY * prev.scale,
    }))
  }, [isPixiReady, followingAgentId, agents, locations])
  
  // 更新摄像机位置
  useEffect(() => {
    if (!isPixiReady) return
    
    const layerManager = pixiApp.layerManager
    if (!layerManager) return
    
    const container = pixiContainerRef.current
    if (!container) return
    
    const rect = container.getBoundingClientRect()
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    
    layerManager.setWorldPosition(centerX + mapState.offsetX, centerY + mapState.offsetY)
    layerManager.setWorldScale(mapState.scale)
    
    // 更新层排序
    layerManager.updateSorting()
  }, [isPixiReady, mapState])
  
  // 鼠标事件处理（建筑物拖拽模式下禁用地图拖拽）
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // 建筑物拖拽模式下不处理地图拖拽
    if (isDraggingBuilding) return
    
    setIsDragging(true)
    setDragStart({ x: e.clientX - mapState.offsetX, y: e.clientY - mapState.offsetY })
  }, [mapState.offsetX, mapState.offsetY, isDraggingBuilding])
  
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    // 建筑物拖拽模式下不处理地图拖拽
    if (isDraggingBuilding) return
    
    if (isDragging) {
      setMapState(prev => ({
        ...prev,
        offsetX: e.clientX - dragStart.x,
        offsetY: e.clientY - dragStart.y,
      }))
    }
  }, [isDragging, dragStart, isDraggingBuilding])
  
  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])
  
  // 点击选择智能体或建筑物，或选择位置
  const handleClick = useCallback((e: React.MouseEvent) => {
    if (isDragging) return
    if (!isPixiReady) return
    
    const container = pixiContainerRef.current
    if (!container) return
    
    const rect = container.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const clickY = e.clientY - rect.top
    
    // 转换为世界坐标
    const { worldX, worldY } = screenToWorld(
      clickX,
      clickY,
      mapState.offsetX,
      mapState.offsetY,
      mapState.scale,
      rect.width,
      rect.height
    )
    
    // 如果是位置选择模式，转换为后端坐标并回调
    if (isSelectingPosition && onPositionSelect) {
      const { backendX, backendY } = isometricToBackend(worldX, worldY)
      onPositionSelect(Math.round(backendX), Math.round(backendY))
      return
    }
    
    // 优先检测点击的智能体
    if (agentManagerRef.current) {
      const hitAgent = agentManagerRef.current.hitTest(worldX, worldY, 20)
      if (hitAgent) {
        selectAgent(hitAgent.getAgentId())
        return
      }
    }
    
    // 其次检测点击的建筑物
    if (buildingManagerRef.current) {
      const hitBuilding = buildingManagerRef.current.hitTest(worldX, worldY, 40)
      if (hitBuilding) {
        selectLocation(hitBuilding.getLocationId())
        return
      }
    }
  }, [isDragging, isPixiReady, mapState, selectAgent, selectLocation, isSelectingPosition, onPositionSelect])
  
  // 缩放
  const handleZoom = useCallback((delta: number) => {
    setMapState(prev => ({
      ...prev,
      scale: Math.max(0.5, Math.min(3, prev.scale + delta)),
    }))
  }, [])
  
  // 重置视图
  const handleReset = useCallback(() => {
    setMapState({ scale: 1, offsetX: 0, offsetY: 0 })
  }, [])
  
  // 滚轮缩放（使用原生事件监听器避免 passive 问题）
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      setMapState(prev => ({
        ...prev,
        scale: Math.max(0.5, Math.min(3, prev.scale + delta)),
      }))
    }
    
    // 使用 passive: false 允许 preventDefault
    container.addEventListener('wheel', handleWheel, { passive: false })
    
    return () => {
      container.removeEventListener('wheel', handleWheel)
    }
  }, [])
  
  // 切换天气
  const handleWeatherChange = useCallback((weather: WeatherType) => {
    setCurrentWeather(weather)
    pixiApp.weatherSystem?.setWeather(weather)
  }, [])
  
  // 天气图标
  const getWeatherIcon = (weather: WeatherType) => {
    switch (weather) {
      case 'sunny': return <Sun className="w-4 h-4" />
      case 'cloudy': return <Cloud className="w-4 h-4" />
      case 'rainy': return <CloudRain className="w-4 h-4" />
    }
  }

  return (
    <div 
      ref={containerRef}
      className="w-full h-full relative overflow-hidden"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
    >
      {/* PixiJS 画布容器 */}
      <div 
        ref={pixiContainerRef}
        className={`w-full h-full ${
          isSelectingPosition 
            ? 'cursor-crosshair' 
            : isDraggingBuilding 
              ? 'cursor-move' 
              : 'cursor-grab active:cursor-grabbing'
        }`}
      />
      
      {/* 位置选择模式提示 */}
      {isSelectingPosition && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-emerald-500 text-white rounded-lg shadow-md px-4 py-2 flex items-center gap-2 animate-pulse">
          <MapPin className="w-4 h-4" />
          <span className="text-sm font-medium">点击地图选择建筑物位置</span>
        </div>
      )}
      
      {/* 建筑物拖拽模式提示 */}
      {isDraggingBuilding && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-emerald-500 text-white rounded-lg shadow-md px-4 py-2 flex items-center gap-2 animate-pulse">
          <Move className="w-4 h-4" />
          <span className="text-sm font-medium">拖动建筑物到新位置，松开鼠标确认</span>
        </div>
      )}
      
      {/* 控制按钮 */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 animate-slide-in-right">
        <button
          onClick={() => handleZoom(0.2)}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 hover:shadow-lg transition-all btn-press"
          title="放大"
        >
          <ZoomIn className="w-5 h-5 text-slate-600" />
        </button>
        <button
          onClick={() => handleZoom(-0.2)}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 hover:shadow-lg transition-all btn-press"
          title="缩小"
        >
          <ZoomOut className="w-5 h-5 text-slate-600" />
        </button>
        <button
          onClick={handleReset}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 hover:shadow-lg transition-all btn-press"
          title="重置"
        >
          <RotateCcw className="w-5 h-5 text-slate-600" />
        </button>
      </div>
      
      {/* 天气控制 */}
      <div className="absolute top-4 right-20 flex gap-1 bg-white rounded-lg shadow-md p-1">
        {(['sunny', 'cloudy', 'rainy'] as WeatherType[]).map(weather => (
          <button
            key={weather}
            onClick={() => handleWeatherChange(weather)}
            className={`p-2 rounded transition-all ${
              currentWeather === weather 
                ? 'bg-blue-100 text-blue-600' 
                : 'hover:bg-slate-50 text-slate-500'
            }`}
            title={weather === 'sunny' ? '晴天' : weather === 'cloudy' ? '多云' : '雨天'}
          >
            {getWeatherIcon(weather)}
          </button>
        ))}
      </div>
      
      {/* 对话统计 */}
      {activeConversations.length > 0 && (
        <div className="absolute top-4 left-4 bg-blue-500 text-white rounded-lg shadow-md px-3 py-2 flex items-center gap-2 animate-slide-in-left animate-pulse-glow">
          <MessageCircle className="w-4 h-4" />
          <span className="text-sm font-medium">{activeConversations.length} 场对话进行中</span>
        </div>
      )}
      
      {/* 跟随状态指示器 */}
      {followingAgentId && (
        <div className="absolute top-4 left-4 mt-12 bg-green-500 text-white rounded-lg shadow-md px-3 py-2 flex items-center gap-2">
          <Crosshair className="w-4 h-4" />
          <span className="text-sm font-medium">
            正在跟随: {agents?.find(a => a.id === followingAgentId)?.name || '未知'}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              stopFollowing()
            }}
            className="ml-1 p-0.5 hover:bg-white/20 rounded transition-colors"
            title="停止跟随"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      
      
      {/* 地点图例 */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-md p-3">
        <div className="text-xs font-medium text-slate-600 mb-2">地点类型</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {Object.entries(LOCATION_ICONS).filter(([k]) => k !== 'default').map(([type, icon]) => (
            <div key={type} className="flex items-center gap-1">
              <span>{icon}</span>
              <span className="text-slate-500">{type}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* 统计信息 */}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-md px-3 py-2">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <MapPin className="w-4 h-4 text-slate-500" />
            <span className="text-slate-600">{locations?.length || 0} 个地点</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span className="text-slate-600">{agents?.length || 0} 个智能体</span>
          </div>
        </div>
      </div>
      
      {/* 加载状态 */}
      {(!locationsLoaded || !isPixiReady) && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-slate-600">
              {!isPixiReady ? '初始化渲染引擎...' : '加载地图中...'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
