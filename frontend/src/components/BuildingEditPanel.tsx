/**
 * 建筑物编辑/详情面板组件
 * 
 * 功能：
 * - 显示建筑物详情
 * - 编辑建筑物属性
 * - 删除建筑物
 */

import { useState, useEffect } from 'react'
import { 
  X, 
  Building2, 
  MapPin, 
  Users, 
  Clock, 
  Activity, 
  FileText,
  Edit3,
  Trash2,
  Save,
  XCircle,
  Move
} from 'lucide-react'
import { useLocationStore } from '../store/locationStore'
import type { UpdateLocationParams } from '../services/api'

interface BuildingEditPanelProps {
  /** 是否显示 */
  isOpen: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 删除成功回调 */
  onDeleted?: () => void
  /** 开始拖拽回调 */
  onStartDrag?: () => void
}

/**
 * 建筑类型中文映射
 */
const LOCATION_TYPE_LABELS: Record<string, string> = {
  apartment: '公寓',
  house: '住宅',
  cafe: '咖啡馆',
  restaurant: '餐厅',
  supermarket: '超市',
  mall: '商场',
  office: '办公楼',
  factory: '工厂',
  school: '学校',
  hospital: '医院',
  park: '公园',
  plaza: '广场',
  library: '图书馆',
  bank: '银行',
  gym: '健身房',
  barbershop: '理发店',
}

/**
 * 活动类型中文映射
 */
const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  sleep: '睡觉',
  eat: '吃饭',
  work: '工作',
  shop: '购物',
  exercise: '运动',
  relax: '休闲',
  study: '学习',
  socialize: '社交',
  healthcare: '医疗',
  finance: '金融',
}

export default function BuildingEditPanel({
  isOpen,
  onClose,
  onDeleted,
  onStartDrag,
}: BuildingEditPanelProps) {
  const { 
    selectedLocation,
    activityTypes,
    updateLocation,
    deleteLocation,
    fetchActivityTypes,
    isLoading,
    error,
    clearError,
    setEditMode,
    isEditMode,
  } = useLocationStore()
  
  // 编辑状态
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editCapacity, setEditCapacity] = useState(10)
  const [editActivities, setEditActivities] = useState<string[]>([])
  const [editOpenHour, setEditOpenHour] = useState(0)
  const [editCloseHour, setEditCloseHour] = useState(24)
  const [is24Hours, setIs24Hours] = useState(true)
  
  // 删除确认
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  // 加载活动类型
  useEffect(() => {
    if (isOpen && activityTypes.length === 0) {
      fetchActivityTypes()
    }
  }, [isOpen, activityTypes.length, fetchActivityTypes])
  
  // 同步编辑数据
  useEffect(() => {
    if (selectedLocation) {
      setEditName(selectedLocation.name)
      setEditDescription(selectedLocation.description || '')
      setEditCapacity(selectedLocation.capacity)
      setEditActivities(selectedLocation.activities || [])
      
      if (selectedLocation.open_hours) {
        const is24 = selectedLocation.open_hours.open === 0 && selectedLocation.open_hours.close === 24
        setIs24Hours(is24)
        setEditOpenHour(selectedLocation.open_hours.open)
        setEditCloseHour(selectedLocation.open_hours.close)
      } else {
        setIs24Hours(true)
        setEditOpenHour(0)
        setEditCloseHour(24)
      }
    }
  }, [selectedLocation])
  
  // 切换活动类型
  const toggleActivity = (activity: string) => {
    setEditActivities(prev => 
      prev.includes(activity)
        ? prev.filter(a => a !== activity)
        : [...prev, activity]
    )
  }
  
  // 保存更改
  const handleSave = async () => {
    if (!selectedLocation) return
    
    const params: UpdateLocationParams = {
      name: editName.trim(),
      description: editDescription.trim(),
      capacity: editCapacity,
      activities: editActivities,
      open_hour: is24Hours ? 0 : editOpenHour,
      close_hour: is24Hours ? 24 : editCloseHour,
    }
    
    const result = await updateLocation(selectedLocation.id, params)
    
    if (result) {
      setEditMode(false)
    }
  }
  
  // 取消编辑
  const handleCancelEdit = () => {
    if (selectedLocation) {
      setEditName(selectedLocation.name)
      setEditDescription(selectedLocation.description || '')
      setEditCapacity(selectedLocation.capacity)
      setEditActivities(selectedLocation.activities || [])
    }
    setEditMode(false)
    clearError()
  }
  
  // 删除建筑物
  const handleDelete = async () => {
    if (!selectedLocation) return
    
    const success = await deleteLocation(selectedLocation.id)
    
    if (success) {
      setShowDeleteConfirm(false)
      onDeleted?.()
      onClose()
    }
  }
  
  // 开始拖拽
  const handleStartDrag = () => {
    onStartDrag?.()
    onClose()
  }
  
  if (!isOpen || !selectedLocation) return null
  
  const location = selectedLocation
  
  return (
    <div className="fixed right-4 top-20 w-80 bg-white rounded-xl shadow-2xl z-40 flex flex-col max-h-[calc(100vh-6rem)] overflow-hidden">
      {/* 头部 */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white">
          <Building2 className="w-5 h-5" />
          <h3 className="font-bold truncate">
            {isEditMode ? '编辑建筑物' : location.name}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          {!isEditMode && (
            <>
              <button
                onClick={() => setEditMode(true)}
                className="p-1.5 hover:bg-white/20 rounded transition-colors"
                title="编辑"
              >
                <Edit3 className="w-4 h-4 text-white" />
              </button>
              <button
                onClick={handleStartDrag}
                className="p-1.5 hover:bg-white/20 rounded transition-colors"
                title="拖动位置"
              >
                <Move className="w-4 h-4 text-white" />
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-1.5 hover:bg-white/20 rounded transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4 text-white" />
              </button>
            </>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
      
      {/* 内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
            {error}
          </div>
        )}
        
        {/* 删除确认 */}
        {showDeleteConfirm && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-3">
            <p className="text-sm text-red-700">
              确定要删除 <strong>{location.name}</strong> 吗？
              {location.current_occupants > 0 && (
                <span className="block mt-1">
                  内部的 {location.current_occupants} 个智能体将被转移到最近的公共区域。
                </span>
              )}
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleDelete}
                disabled={isLoading}
                className="flex-1 px-3 py-1.5 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:opacity-50"
              >
                {isLoading ? '删除中...' : '确认删除'}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-3 py-1.5 bg-slate-100 text-slate-600 rounded text-sm hover:bg-slate-200"
              >
                取消
              </button>
            </div>
          </div>
        )}
        
        {/* 基本信息 */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-slate-500 uppercase flex items-center gap-1">
            <FileText className="w-3 h-3" />
            基本信息
          </h4>
          
          {isEditMode ? (
            <>
              <div>
                <label className="block text-xs text-slate-500 mb-1">名称</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  maxLength={50}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">描述</label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                  rows={2}
                  maxLength={200}
                />
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                  {LOCATION_TYPE_LABELS[location.type] || location.type}
                </span>
              </div>
              {location.description && (
                <p className="text-sm text-slate-600">{location.description}</p>
              )}
            </>
          )}
        </div>
        
        {/* 位置信息 */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-500 uppercase flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            位置
          </h4>
          <div className="text-sm text-slate-600">
            坐标: ({location.position.x}, {location.position.y})
            <span className="mx-2">·</span>
            尺寸: {location.size.width} × {location.size.height}
          </div>
        </div>
        
        {/* 容量 */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-500 uppercase flex items-center gap-1">
            <Users className="w-3 h-3" />
            容量
          </h4>
          {isEditMode ? (
            <input
              type="number"
              value={editCapacity}
              onChange={(e) => setEditCapacity(Math.max(1, Math.min(100, Number(e.target.value))))}
              min={1}
              max={100}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${(location.current_occupants / location.capacity) * 100}%` }}
                />
              </div>
              <span className="text-sm text-slate-600">
                {location.current_occupants}/{location.capacity}
              </span>
            </div>
          )}
        </div>
        
        {/* 支持的活动 */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-500 uppercase flex items-center gap-1">
            <Activity className="w-3 h-3" />
            支持的活动
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {isEditMode ? (
              activityTypes.map(act => (
                <button
                  key={act.value}
                  type="button"
                  onClick={() => toggleActivity(act.value)}
                  className={`px-2 py-1 rounded text-xs transition-colors ${
                    editActivities.includes(act.value)
                      ? 'bg-blue-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {ACTIVITY_TYPE_LABELS[act.value] || act.name}
                </button>
              ))
            ) : (
              location.activities.length > 0 ? (
                location.activities.map(act => (
                  <span
                    key={act}
                    className="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded"
                  >
                    {ACTIVITY_TYPE_LABELS[act] || act}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-400">无</span>
              )
            )}
          </div>
        </div>
        
        {/* 营业时间 */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-500 uppercase flex items-center gap-1">
            <Clock className="w-3 h-3" />
            营业时间
          </h4>
          {isEditMode ? (
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={is24Hours}
                  onChange={(e) => setIs24Hours(e.target.checked)}
                  className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-slate-600">24小时营业</span>
              </label>
              {!is24Hours && (
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={editOpenHour}
                    onChange={(e) => setEditOpenHour(Number(e.target.value))}
                    className="px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                    ))}
                  </select>
                  <select
                    value={editCloseHour}
                    onChange={(e) => setEditCloseHour(Number(e.target.value))}
                    className="px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {Array.from({ length: 25 }, (_, i) => (
                      <option key={i} value={i}>{i === 24 ? '24:00' : i.toString().padStart(2, '0') + ':00'}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-600">
              {location.open_hours ? (
                location.open_hours.open === 0 && location.open_hours.close === 24 
                  ? '24小时营业'
                  : `${location.open_hours.open.toString().padStart(2, '0')}:00 - ${location.open_hours.close.toString().padStart(2, '0')}:00`
              ) : (
                '24小时营业'
              )}
              <span className="mx-2">·</span>
              <span className={location.is_open_now ? 'text-green-600' : 'text-red-600'}>
                {location.is_open_now ? '营业中' : '已关闭'}
              </span>
            </div>
          )}
        </div>
      </div>
      
      {/* 底部按钮（编辑模式） */}
      {isEditMode && (
        <div className="border-t border-slate-200 px-4 py-3 flex gap-2">
          <button
            onClick={handleCancelEdit}
            className="flex-1 px-3 py-2 text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors flex items-center justify-center gap-1 text-sm"
          >
            <XCircle className="w-4 h-4" />
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading || !editName.trim()}
            className="flex-1 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-1 text-sm"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            保存
          </button>
        </div>
      )}
    </div>
  )
}
