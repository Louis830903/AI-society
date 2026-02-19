/**
 * 建筑物创建弹窗组件
 * 
 * 功能：
 * - 表单填写建筑物属性
 * - 支持选择建筑类型
 * - 支持配置容量、活动类型、营业时间
 */

import { useState, useEffect } from 'react'
import { X, Building2, MapPin, Users, Clock, Activity, FileText, Plus } from 'lucide-react'
import { useLocationStore } from '../store/locationStore'
import type { CreateLocationParams } from '../services/api'

interface BuildingCreateModalProps {
  /** 是否显示 */
  isOpen: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 创建成功回调 */
  onCreated?: (locationId: string) => void
  /** 预设位置（从地图点击传入） */
  defaultPosition?: { x: number; y: number }
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

export default function BuildingCreateModal({
  isOpen,
  onClose,
  onCreated,
  defaultPosition,
}: BuildingCreateModalProps) {
  const { 
    locationTypes, 
    activityTypes, 
    createLocation, 
    fetchLocationTypes,
    fetchActivityTypes,
    isLoading,
    error,
    clearError,
  } = useLocationStore()
  
  // 表单状态
  const [name, setName] = useState('')
  const [type, setType] = useState('')
  const [x, setX] = useState(defaultPosition?.x ?? 0)
  const [y, setY] = useState(defaultPosition?.y ?? 0)
  const [width, setWidth] = useState(2)
  const [height, setHeight] = useState(2)
  const [capacity, setCapacity] = useState(10)
  const [selectedActivities, setSelectedActivities] = useState<string[]>([])
  const [description, setDescription] = useState('')
  const [openHour, setOpenHour] = useState(0)
  const [closeHour, setCloseHour] = useState(24)
  const [is24Hours, setIs24Hours] = useState(true)
  
  // 加载类型列表
  useEffect(() => {
    if (isOpen) {
      if (locationTypes.length === 0) {
        fetchLocationTypes()
      }
      if (activityTypes.length === 0) {
        fetchActivityTypes()
      }
    }
  }, [isOpen, locationTypes.length, activityTypes.length, fetchLocationTypes, fetchActivityTypes])
  
  // 更新默认位置
  useEffect(() => {
    if (defaultPosition) {
      setX(defaultPosition.x)
      setY(defaultPosition.y)
    }
  }, [defaultPosition])
  
  // 重置表单
  const resetForm = () => {
    setName('')
    setType('')
    setX(defaultPosition?.x ?? 0)
    setY(defaultPosition?.y ?? 0)
    setWidth(2)
    setHeight(2)
    setCapacity(10)
    setSelectedActivities([])
    setDescription('')
    setOpenHour(0)
    setCloseHour(24)
    setIs24Hours(true)
    clearError()
  }
  
  // 关闭弹窗
  const handleClose = () => {
    resetForm()
    onClose()
  }
  
  // 切换活动类型
  const toggleActivity = (activity: string) => {
    setSelectedActivities(prev => 
      prev.includes(activity)
        ? prev.filter(a => a !== activity)
        : [...prev, activity]
    )
  }
  
  // 提交创建
  const handleSubmit = async () => {
    // 验证必填字段
    if (!name.trim()) {
      return
    }
    if (!type) {
      return
    }
    
    const params: CreateLocationParams = {
      name: name.trim(),
      type,
      x,
      y,
      width,
      height,
      capacity,
      activities: selectedActivities,
      description: description.trim(),
      open_hour: is24Hours ? 0 : openHour,
      close_hour: is24Hours ? 24 : closeHour,
    }
    
    const location = await createLocation(params)
    
    if (location) {
      onCreated?.(location.id)
      handleClose()
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[520px] max-h-[90vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <Building2 className="w-6 h-6" />
            <h2 className="font-bold text-lg">新建建筑物</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* 表单内容 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* 错误提示 */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          {/* 基本信息 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              基本信息
            </h3>
            
            {/* 名称 */}
            <div>
              <label className="block text-sm text-slate-600 mb-1">建筑名称 *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：时光咖啡馆"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                maxLength={50}
              />
            </div>
            
            {/* 类型 */}
            <div>
              <label className="block text-sm text-slate-600 mb-1">建筑类型 *</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
              >
                <option value="">选择类型...</option>
                {locationTypes.map(t => (
                  <option key={t.value} value={t.value}>
                    {LOCATION_TYPE_LABELS[t.value] || t.name}
                  </option>
                ))}
              </select>
            </div>
            
            {/* 描述 */}
            <div>
              <label className="block text-sm text-slate-600 mb-1">描述</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简单描述这个建筑..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none resize-none"
                rows={2}
                maxLength={200}
              />
            </div>
          </div>
          
          {/* 位置和尺寸 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              位置和尺寸
              {defaultPosition && (
                <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  已从地图选择
                </span>
              )}
            </h3>
            
            {defaultPosition && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-sm text-emerald-700">
                坐标已从地图选择：({x}, {y})
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-600 mb-1">X 坐标</label>
                <input
                  type="number"
                  value={x}
                  onChange={(e) => setX(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                  readOnly={!!defaultPosition}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Y 坐标</label>
                <input
                  type="number"
                  value={y}
                  onChange={(e) => setY(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                  readOnly={!!defaultPosition}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">宽度</label>
                <input
                  type="number"
                  value={width}
                  onChange={(e) => setWidth(Math.max(1, Math.min(10, Number(e.target.value))))}
                  min={1}
                  max={10}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">高度</label>
                <input
                  type="number"
                  value={height}
                  onChange={(e) => setHeight(Math.max(1, Math.min(10, Number(e.target.value))))}
                  min={1}
                  max={10}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                />
              </div>
            </div>
          </div>
          
          {/* 容量 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Users className="w-4 h-4" />
              容量
            </h3>
            
            <div>
              <label className="block text-sm text-slate-600 mb-1">最大容纳人数</label>
              <input
                type="number"
                value={capacity}
                onChange={(e) => setCapacity(Math.max(1, Math.min(100, Number(e.target.value))))}
                min={1}
                max={100}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
              />
            </div>
          </div>
          
          {/* 支持的活动 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              支持的活动
            </h3>
            
            <div className="flex flex-wrap gap-2">
              {activityTypes.map(act => (
                <button
                  key={act.value}
                  type="button"
                  onClick={() => toggleActivity(act.value)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    selectedActivities.includes(act.value)
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {ACTIVITY_TYPE_LABELS[act.value] || act.name}
                </button>
              ))}
            </div>
          </div>
          
          {/* 营业时间 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              营业时间
            </h3>
            
            <div className="space-y-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={is24Hours}
                  onChange={(e) => setIs24Hours(e.target.checked)}
                  className="w-4 h-4 text-emerald-500 rounded focus:ring-emerald-500"
                />
                <span className="text-sm text-slate-600">24小时营业</span>
              </label>
              
              {!is24Hours && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-600 mb-1">开门时间</label>
                    <select
                      value={openHour}
                      onChange={(e) => setOpenHour(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                    >
                      {Array.from({ length: 24 }, (_, i) => (
                        <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-600 mb-1">关门时间</label>
                    <select
                      value={closeHour}
                      onChange={(e) => setCloseHour(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                    >
                      {Array.from({ length: 25 }, (_, i) => (
                        <option key={i} value={i}>{i === 24 ? '24:00' : i.toString().padStart(2, '0') + ':00'}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* 底部按钮 */}
        <div className="border-t border-slate-200 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !name.trim() || !type}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                创建建筑物
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
