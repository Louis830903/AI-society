/**
 * 智能体创建弹窗组件
 * 
 * 功能：
 * - 表单填写智能体属性
 * - 支持大五人格参数配置
 * - 支持选择初始位置
 */

import { useState, useEffect } from 'react'
import { X, User, Brain, Wallet, MapPin, Plus, Tag, BookOpen } from 'lucide-react'
import { useAgentStore } from '../store/agentStore'
import { useLocationStore } from '../store/locationStore'
import type { CreateAgentParams } from '../services/api'

interface AgentCreateModalProps {
  /** 是否显示 */
  isOpen: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 创建成功回调 */
  onCreated?: (agentId: string) => void
}

/**
 * 性格标签选项
 */
const TRAIT_OPTIONS = [
  '外向', '内向', '乐观', '悲观', '友善', '冷漠',
  '勤奋', '懒惰', '谨慎', '冲动', '创造力', '务实',
  '幽默', '严肃', '善良', '自私', '勇敢', '胆小',
]

/**
 * 性别选项
 */
const GENDER_OPTIONS = ['男', '女']

/**
 * 职业选项
 */
const OCCUPATION_OPTIONS = [
  '程序员', '设计师', '教师', '医生', '工程师',
  '销售', '厨师', '作家', '艺术家', '学生',
  '自由职业', '企业家', '会计', '律师', '护士',
]

export default function AgentCreateModal({
  isOpen,
  onClose,
  onCreated,
}: AgentCreateModalProps) {
  const { createAgent, isLoading, error } = useAgentStore()
  const { locations, fetchLocations } = useLocationStore()
  
  // 基本信息
  const [name, setName] = useState('')
  const [age, setAge] = useState(25)
  const [gender, setGender] = useState('男')
  const [occupation, setOccupation] = useState('自由职业')
  const [backstory, setBackstory] = useState('')
  const [selectedTraits, setSelectedTraits] = useState<string[]>([])
  const [balance, setBalance] = useState(1000)
  const [locationId, setLocationId] = useState('')
  
  // 大五人格参数
  const [openness, setOpenness] = useState(50)
  const [conscientiousness, setConscientiousness] = useState(50)
  const [extraversion, setExtraversion] = useState(50)
  const [agreeableness, setAgreeableness] = useState(50)
  const [neuroticism, setNeuroticism] = useState(50)
  
  // 加载位置列表
  useEffect(() => {
    if (isOpen && locations.length === 0) {
      fetchLocations()
    }
  }, [isOpen, locations.length, fetchLocations])
  
  // 重置表单
  const resetForm = () => {
    setName('')
    setAge(25)
    setGender('男')
    setOccupation('自由职业')
    setBackstory('')
    setSelectedTraits([])
    setBalance(1000)
    setLocationId('')
    setOpenness(50)
    setConscientiousness(50)
    setExtraversion(50)
    setAgreeableness(50)
    setNeuroticism(50)
  }
  
  // 关闭弹窗
  const handleClose = () => {
    resetForm()
    onClose()
  }
  
  // 切换性格标签
  const toggleTrait = (trait: string) => {
    setSelectedTraits(prev => 
      prev.includes(trait)
        ? prev.filter(t => t !== trait)
        : prev.length < 5 ? [...prev, trait] : prev
    )
  }
  
  // 提交创建
  const handleSubmit = async () => {
    if (!name.trim()) return
    
    const params: CreateAgentParams = {
      name: name.trim(),
      age,
      gender,
      occupation,
      backstory: backstory.trim(),
      traits: selectedTraits,
      balance,
      openness,
      conscientiousness,
      extraversion,
      agreeableness,
      neuroticism,
      location_id: locationId || undefined,
    }
    
    const agent = await createAgent(params)
    
    if (agent) {
      onCreated?.(agent.id)
      handleClose()
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[560px] max-h-[90vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-violet-500 to-violet-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <User className="w-6 h-6" />
            <h2 className="font-bold text-lg">创建智能体</h2>
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
              <User className="w-4 h-4" />
              基本信息
            </h3>
            
            {/* 姓名 */}
            <div>
              <label className="block text-sm text-slate-600 mb-1">姓名 *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：张三"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
                maxLength={20}
              />
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              {/* 年龄 */}
              <div>
                <label className="block text-sm text-slate-600 mb-1">年龄</label>
                <input
                  type="number"
                  value={age}
                  onChange={(e) => setAge(Math.max(18, Math.min(80, Number(e.target.value))))}
                  min={18}
                  max={80}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
                />
              </div>
              
              {/* 性别 */}
              <div>
                <label className="block text-sm text-slate-600 mb-1">性别</label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
                >
                  {GENDER_OPTIONS.map(g => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
              
              {/* 职业 */}
              <div>
                <label className="block text-sm text-slate-600 mb-1">职业</label>
                <select
                  value={occupation}
                  onChange={(e) => setOccupation(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
                >
                  {OCCUPATION_OPTIONS.map(o => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          
          {/* 背景故事 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              背景故事
            </h3>
            
            <textarea
              value={backstory}
              onChange={(e) => setBackstory(e.target.value)}
              placeholder="描述这个智能体的背景故事..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none resize-none"
              rows={3}
              maxLength={500}
            />
          </div>
          
          {/* 性格标签 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Tag className="w-4 h-4" />
              性格标签 (最多5个)
            </h3>
            
            <div className="flex flex-wrap gap-2">
              {TRAIT_OPTIONS.map(trait => (
                <button
                  key={trait}
                  type="button"
                  onClick={() => toggleTrait(trait)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    selectedTraits.includes(trait)
                      ? 'bg-violet-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {trait}
                </button>
              ))}
            </div>
          </div>
          
          {/* 初始资金 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Wallet className="w-4 h-4" />
              初始资金
            </h3>
            
            <div>
              <input
                type="number"
                value={balance}
                onChange={(e) => setBalance(Math.max(0, Number(e.target.value)))}
                min={0}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
              />
              <p className="text-xs text-slate-500 mt-1">智能体的初始金币数量</p>
            </div>
          </div>
          
          {/* 初始位置 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              初始位置
            </h3>
            
            <select
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
            >
              <option value="">随机分配</option>
              {locations.map(loc => (
                <option key={loc.id} value={loc.id}>{loc.name}</option>
              ))}
            </select>
          </div>
          
          {/* 大五人格参数 */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <Brain className="w-4 h-4" />
              人格特质 (大五人格模型)
            </h3>
            
            <div className="space-y-3">
              {/* 开放性 */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">开放性</span>
                  <span className="text-violet-600 font-medium">{openness}</span>
                </div>
                <input
                  type="range"
                  value={openness}
                  onChange={(e) => setOpenness(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                  <span>保守</span>
                  <span>创新</span>
                </div>
              </div>
              
              {/* 尽责性 */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">尽责性</span>
                  <span className="text-violet-600 font-medium">{conscientiousness}</span>
                </div>
                <input
                  type="range"
                  value={conscientiousness}
                  onChange={(e) => setConscientiousness(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                  <span>随性</span>
                  <span>自律</span>
                </div>
              </div>
              
              {/* 外向性 */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">外向性</span>
                  <span className="text-violet-600 font-medium">{extraversion}</span>
                </div>
                <input
                  type="range"
                  value={extraversion}
                  onChange={(e) => setExtraversion(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                  <span>内向</span>
                  <span>外向</span>
                </div>
              </div>
              
              {/* 宜人性 */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">宜人性</span>
                  <span className="text-violet-600 font-medium">{agreeableness}</span>
                </div>
                <input
                  type="range"
                  value={agreeableness}
                  onChange={(e) => setAgreeableness(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                  <span>独立</span>
                  <span>合作</span>
                </div>
              </div>
              
              {/* 神经质 */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">情绪稳定性</span>
                  <span className="text-violet-600 font-medium">{100 - neuroticism}</span>
                </div>
                <input
                  type="range"
                  value={neuroticism}
                  onChange={(e) => setNeuroticism(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                  <span>敏感</span>
                  <span>稳定</span>
                </div>
              </div>
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
            disabled={isLoading || !name.trim()}
            className="px-4 py-2 bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                创建智能体
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
