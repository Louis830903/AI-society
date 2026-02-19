/**
 * AI Society 主应用组件
 * 
 * 包含主布局结构：
 * - TopBar: 顶部导航栏（时间显示、控制按钮）
 * - Main: 主内容区（地图）
 * - Sidebar: 侧边栏（事件流、智能体列表）
 */

import { useState, useEffect, useCallback } from 'react'
import TopBar from './components/TopBar'
import WorldMap from './components/WorldMap'
import Sidebar from './components/Sidebar'
import AgentDetailPanel from './components/AgentDetailPanel'
import ConversationPanel from './components/ConversationPanel'
import EventNotification from './components/EventNotification'
import BuildingCreateModal from './components/BuildingCreateModal'
import BuildingEditPanel from './components/BuildingEditPanel'
import AgentCreateModal from './components/AgentCreateModal'
import WorldControlPanel from './components/WorldControlPanel'
import { useWorldStore } from './store/worldStore'
import { useAgentStore } from './store/agentStore'
import { useConversationStore } from './store/conversationStore'
import { useLocationStore } from './store/locationStore'
import { useWebSocketEvents, useInitialDataLoad } from './hooks'

function App() {
  // 从全局状态获取世界信息
  const { connect } = useWorldStore()
  const { selectedAgentId, clearSelection: clearAgentSelection } = useAgentStore()
  const { selectedConversationId, clearSelection: clearConversationSelection } = useConversationStore()
  const { selectedLocation, clearSelection: clearBuildingSelection, updateLocationPosition } = useLocationStore()
  
  // 侧边栏展开状态
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
  // 建筑物管理状态
  const [showBuildingCreate, setShowBuildingCreate] = useState(false)
  const [showBuildingEdit, setShowBuildingEdit] = useState(false)
  const [buildingCreatePosition, setBuildingCreatePosition] = useState<{ x: number; y: number } | undefined>()
  const [isSelectingPosition, setIsSelectingPosition] = useState(false)
  
  // 建筑物拖拽状态
  const [isDraggingBuilding, setIsDraggingBuilding] = useState(false)
  const [draggingBuildingId, setDraggingBuildingId] = useState<string | null>(null)
  
  // 智能体管理状态
  const [showAgentCreate, setShowAgentCreate] = useState(false)
  
  // 世界控制面板状态
  const [showWorldControl, setShowWorldControl] = useState(false)
  
  // 组件挂载时连接WebSocket
  useEffect(() => {
    connect()
  }, [connect])
  
  // 使用WebSocket事件处理Hook
  useWebSocketEvents()
  
  // 使用初始数据加载Hook
  useInitialDataLoad()
  
  // 建筑物选中时显示编辑面板
  useEffect(() => {
    if (selectedLocation) {
      setShowBuildingEdit(true)
    }
  }, [selectedLocation])
  
  // 关闭建筑编辑面板
  const handleCloseBuildingEdit = useCallback(() => {
    setShowBuildingEdit(false)
    clearBuildingSelection()
  }, [clearBuildingSelection])
  
  // 建筑创建成功
  const handleBuildingCreated = useCallback(() => {
    setShowBuildingCreate(false)
    setBuildingCreatePosition(undefined)
  }, [])
  
  // 建筑删除成功
  const handleBuildingDeleted = useCallback(() => {
    setShowBuildingEdit(false)
  }, [])
  
  // 开始新建建筑物（启用位置选择模式）
  const handleStartBuildingCreate = useCallback(() => {
    setIsSelectingPosition(true)
  }, [])
  
  // 地图位置选择完成
  const handlePositionSelect = useCallback((x: number, y: number) => {
    setIsSelectingPosition(false)
    setBuildingCreatePosition({ x, y })
    setShowBuildingCreate(true)
  }, [])
  
  // 取消位置选择
  const handleCancelPositionSelect = useCallback(() => {
    setIsSelectingPosition(false)
  }, [])
  
  // 开始建筑物拖拽移动
  const handleStartBuildingDrag = useCallback(() => {
    if (selectedLocation) {
      setIsDraggingBuilding(true)
      setDraggingBuildingId(selectedLocation.id)
      setShowBuildingEdit(false)  // 关闭编辑面板
    }
  }, [selectedLocation])
  
  // 建筑物拖拽结束
  const handleBuildingDragEnd = useCallback(async (locationId: string, newX: number, newY: number) => {
    // 调用 API 更新位置
    await updateLocationPosition(locationId, newX, newY)
    
    // 退出拖拽模式
    setIsDraggingBuilding(false)
    setDraggingBuildingId(null)
  }, [updateLocationPosition])
  
  // 智能体创建成功
  const handleAgentCreated = useCallback(() => {
    setShowAgentCreate(false)
  }, [])

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* 顶部导航栏 */}
      <TopBar 
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onAddBuilding={handleStartBuildingCreate}
        onAddAgent={() => setShowAgentCreate(true)}
        onOpenWorldControl={() => setShowWorldControl(true)}
      />
      
      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 地图区域 */}
        <main className="flex-1 relative">
          <WorldMap 
            isSelectingPosition={isSelectingPosition}
            onPositionSelect={handlePositionSelect}
            isDraggingBuilding={isDraggingBuilding}
            draggingBuildingId={draggingBuildingId}
            onBuildingDragEnd={handleBuildingDragEnd}
          />
          
          {/* 位置选择模式下的取消按钮 */}
          {isSelectingPosition && (
            <button
              onClick={handleCancelPositionSelect}
              className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white rounded-lg shadow-md px-4 py-2 hover:bg-red-600 transition-colors"
            >
              取消选择
            </button>
          )}
        </main>
        
        {/* 侧边栏 */}
        {sidebarOpen && (
          <Sidebar onClose={() => setSidebarOpen(false)} />
        )}
        
        {/* 智能体详情面板 */}
        {selectedAgentId && (
          <AgentDetailPanel onClose={clearAgentSelection} />
        )}
        
        {/* 对话详情面板 */}
        {selectedConversationId && !selectedAgentId && (
          <ConversationPanel onClose={clearConversationSelection} />
        )}
        
        {/* 建筑物编辑面板 */}
        <BuildingEditPanel
          isOpen={showBuildingEdit && !!selectedLocation}
          onClose={handleCloseBuildingEdit}
          onDeleted={handleBuildingDeleted}
          onStartDrag={handleStartBuildingDrag}
        />
      </div>
      
      {/* 事件通知 */}
      <EventNotification />
      
      {/* 建筑物创建弹窗 */}
      <BuildingCreateModal
        isOpen={showBuildingCreate}
        onClose={() => {
          setShowBuildingCreate(false)
          setBuildingCreatePosition(undefined)
        }}
        onCreated={handleBuildingCreated}
        defaultPosition={buildingCreatePosition}
      />
      
      {/* 智能体创建弹窗 */}
      <AgentCreateModal
        isOpen={showAgentCreate}
        onClose={() => setShowAgentCreate(false)}
        onCreated={handleAgentCreated}
      />
      
      {/* 世界控制面板 */}
      <WorldControlPanel
        isOpen={showWorldControl}
        onClose={() => setShowWorldControl(false)}
      />
    </div>
  )
}

export default App
