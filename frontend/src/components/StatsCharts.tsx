/**
 * 统计图表组件
 * 
 * 包含：
 * - 职业分布饼图
 * - 其他统计图表
 */

import { useMemo } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { useAgentStore } from '../store/agentStore'

// 职业颜色映射
const OCCUPATION_COLORS: Record<string, string> = {
  '程序员': '#3b82f6',
  '设计师': '#8b5cf6',
  '教师': '#10b981',
  '学生': '#f59e0b',
  '服务员': '#ef4444',
  '艺术家': '#ec4899',
  '退休人员': '#6b7280',
  '医生': '#06b6d4',
  '厨师': '#f97316',
  '销售': '#84cc16',
  'default': '#94a3b8',
}

// 职业中文名映射
const OCCUPATION_LABELS: Record<string, string> = {
  programmer: '程序员',
  designer: '设计师',
  teacher: '教师',
  student: '学生',
  waiter: '服务员',
  artist: '艺术家',
  retired: '退休人员',
  doctor: '医生',
  chef: '厨师',
  sales: '销售',
}

/**
 * 职业分布饼图
 */
export function OccupationPieChart() {
  const { agents } = useAgentStore()
  
  // 计算职业分布
  const occupationData = useMemo(() => {
    const counts: Record<string, number> = {}
    
    agents.forEach(agent => {
      const occupation = OCCUPATION_LABELS[agent.occupation] || agent.occupation
      counts[occupation] = (counts[occupation] || 0) + 1
    })
    
    return Object.entries(counts)
      .map(([name, value]) => ({
        name,
        value,
        color: OCCUPATION_COLORS[name] || OCCUPATION_COLORS.default,
      }))
      .sort((a, b) => b.value - a.value)
  }, [agents])
  
  if (agents.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        暂无智能体数据
      </div>
    )
  }
  
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={occupationData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {occupationData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string) => [`${value} 人`, name]}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

/**
 * 状态分布饼图
 */
export function StatePieChart() {
  const { agents } = useAgentStore()
  
  // 计算状态分布
  const stateData = useMemo(() => {
    const counts: Record<string, number> = {
      '活跃': 0,
      '睡眠': 0,
      '离开': 0,
      '其他': 0,
    }
    
    agents.forEach(agent => {
      switch (agent.state) {
        case 'active':
          counts['活跃']++
          break
        case 'sleeping':
          counts['睡眠']++
          break
        case 'offline':
        case 'paused':
          counts['离线']++
          break
        default:
          counts['其他']++
      }
    })
    
    return [
      { name: '活跃', value: counts['活跃'], color: '#10b981' },
      { name: '睡眠', value: counts['睡眠'], color: '#8b5cf6' },
      { name: '离线', value: counts['离线'], color: '#f59e0b' },
      { name: '其他', value: counts['其他'], color: '#6b7280' },
    ].filter(item => item.value > 0)
  }, [agents])
  
  if (agents.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-400">
        暂无智能体数据
      </div>
    )
  }
  
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={stateData}
            cx="50%"
            cy="50%"
            innerRadius={30}
            outerRadius={60}
            paddingAngle={2}
            dataKey="value"
          >
            {stateData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span className="text-xs text-slate-600">{value}</span>}
          />
          <Tooltip
            formatter={(value: number, name: string) => [`${value} 人`, name]}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

/**
 * 职业列表（简洁版）
 */
export function OccupationList() {
  const { agents } = useAgentStore()
  
  // 计算职业分布
  const occupationData = useMemo(() => {
    const counts: Record<string, number> = {}
    const agentList = agents || []
    
    agentList.forEach(agent => {
      const occupation = OCCUPATION_LABELS[agent.occupation] || agent.occupation
      counts[occupation] = (counts[occupation] || 0) + 1
    })
    
    return Object.entries(counts)
      .map(([name, count]) => ({
        name,
        count,
        percent: agentList.length > 0 ? (count / agentList.length * 100).toFixed(1) : '0',
        color: OCCUPATION_COLORS[name] || OCCUPATION_COLORS.default,
      }))
      .sort((a, b) => b.count - a.count)
  }, [agents])
  
  if (!agents?.length) {
    return <div className="text-center text-slate-400 py-4">暂无数据</div>
  }
  
  return (
    <div className="space-y-2">
      {occupationData.map(({ name, count, percent, color }) => (
        <div key={name} className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="flex-1 text-sm text-slate-700 truncate">{name}</span>
          <span className="text-sm font-medium text-slate-600">{count}</span>
          <span className="text-xs text-slate-400 w-12 text-right">{percent}%</span>
        </div>
      ))}
    </div>
  )
}
