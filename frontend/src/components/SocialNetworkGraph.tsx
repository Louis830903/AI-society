/**
 * 社交网络图组件
 * 
 * 使用Canvas绘制力导向图展示智能体之间的关系网络
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { X, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
import { useAgentStore } from '../store/agentStore'
import { agentApi } from '../services/api'

interface Node {
  id: string
  name: string
  occupation: string
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}

interface Link {
  source: string
  target: string
  closeness: number
}

interface SocialNetworkGraphProps {
  onClose: () => void
}

// 职业颜色映射
const OCCUPATION_COLORS: Record<string, string> = {
  programmer: '#3b82f6',
  designer: '#8b5cf6',
  teacher: '#10b981',
  student: '#f59e0b',
  waiter: '#ef4444',
  artist: '#ec4899',
  retired: '#6b7280',
  default: '#94a3b8',
}

export default function SocialNetworkGraph({ onClose }: SocialNetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | null>(null)
  
  const { agents } = useAgentStore()
  
  // 图数据
  const [nodes, setNodes] = useState<Node[]>([])
  const [links, setLinks] = useState<Link[]>([])
  const [loading, setLoading] = useState(true)
  
  // 视图状态
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  
  // 选中的节点
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null)
  
  // 加载关系数据
  useEffect(() => {
    const loadRelationships = async () => {
      setLoading(true)
      
      try {
        // 为每个智能体获取详情（包含关系）
        const agentDetails = await Promise.all(
          agents.slice(0, 30).map(a => agentApi.get(a.id).catch(() => null))
        )
        
        // 构建节点
        const nodeMap = new Map<string, Node>()
        const linkList: Link[] = []
        
        // 初始化节点位置（圆形分布）
        const centerX = 300
        const centerY = 300
        const radius = 200
        
        agents.slice(0, 30).forEach((agent, index) => {
          const angle = (index / Math.min(agents.length, 30)) * Math.PI * 2
          nodeMap.set(agent.id, {
            id: agent.id,
            name: agent.name,
            occupation: agent.occupation,
            x: centerX + Math.cos(angle) * radius + (Math.random() - 0.5) * 50,
            y: centerY + Math.sin(angle) * radius + (Math.random() - 0.5) * 50,
            vx: 0,
            vy: 0,
            radius: 20,
          })
        })
        
        // 构建连接
        agentDetails.forEach(detail => {
          if (!detail || !detail.relationships) return
          
          Object.values(detail.relationships).forEach(rel => {
            // 只添加一次连接（避免重复）
            const existingLink = linkList.find(
              l => (l.source === detail.id && l.target === rel.target_id) ||
                   (l.source === rel.target_id && l.target === detail.id)
            )
            
            if (!existingLink && nodeMap.has(rel.target_id)) {
              linkList.push({
                source: detail.id,
                target: rel.target_id,
                closeness: rel.closeness,
              })
            }
          })
        })
        
        setNodes(Array.from(nodeMap.values()))
        setLinks(linkList)
      } catch (err) {
        console.error('加载关系数据失败:', err)
      } finally {
        setLoading(false)
      }
    }
    
    if (agents.length > 0) {
      loadRelationships()
    }
  }, [agents])
  
  // 力导向模拟
  const simulate = useCallback(() => {
    if (nodes.length === 0) return
    
    const newNodes = [...nodes]
    
    // 力参数
    const repulsion = 5000     // 斥力
    const attraction = 0.01   // 引力
    const damping = 0.9       // 阻尼
    const centerForce = 0.01  // 中心力
    const centerX = 300
    const centerY = 300
    
    // 计算斥力（节点间互斥）
    for (let i = 0; i < newNodes.length; i++) {
      for (let j = i + 1; j < newNodes.length; j++) {
        const dx = newNodes[j].x - newNodes[i].x
        const dy = newNodes[j].y - newNodes[i].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = repulsion / (dist * dist)
        
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        
        newNodes[i].vx -= fx
        newNodes[i].vy -= fy
        newNodes[j].vx += fx
        newNodes[j].vy += fy
      }
    }
    
    // 计算引力（连接的节点互相吸引）
    links.forEach(link => {
      const source = newNodes.find(n => n.id === link.source)
      const target = newNodes.find(n => n.id === link.target)
      if (!source || !target) return
      
      const dx = target.x - source.x
      const dy = target.y - source.y
      
      // 亲密度越高，引力越大
      const strength = attraction * (link.closeness / 50)
      const fx = dx * strength
      const fy = dy * strength
      
      source.vx += fx
      source.vy += fy
      target.vx -= fx
      target.vy -= fy
    })
    
    // 中心力（防止飘走）
    newNodes.forEach(node => {
      node.vx += (centerX - node.x) * centerForce
      node.vy += (centerY - node.y) * centerForce
    })
    
    // 应用速度和阻尼
    newNodes.forEach(node => {
      node.vx *= damping
      node.vy *= damping
      node.x += node.vx
      node.y += node.vy
    })
    
    setNodes(newNodes)
  }, [nodes, links])
  
  // 渲染图形
  const render = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return
    
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    // 设置画布尺寸
    const rect = container.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    
    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // 应用变换
    ctx.save()
    ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y)
    ctx.scale(scale, scale)
    ctx.translate(-300, -300)  // 居中
    
    // 绘制连接线
    links.forEach(link => {
      const source = nodes.find(n => n.id === link.source)
      const target = nodes.find(n => n.id === link.target)
      if (!source || !target) return
      
      // 线宽根据亲密度
      const lineWidth = Math.max(1, link.closeness / 20)
      
      // 颜色根据亲密度
      const alpha = Math.min(0.8, link.closeness / 100 + 0.2)
      
      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`
      ctx.lineWidth = lineWidth
      ctx.stroke()
    })
    
    // 绘制节点
    nodes.forEach(node => {
      const isSelected = selectedNode?.id === node.id
      const isHovered = hoveredNode?.id === node.id
      const color = OCCUPATION_COLORS[node.occupation] || OCCUPATION_COLORS.default
      
      // 节点圆形
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
      
      // 高亮边框
      if (isSelected || isHovered) {
        ctx.strokeStyle = '#1e293b'
        ctx.lineWidth = 3
        ctx.stroke()
      }
      
      // 名字
      ctx.fillStyle = '#1e293b'
      ctx.font = '11px system-ui'
      ctx.textAlign = 'center'
      ctx.fillText(node.name, node.x, node.y + node.radius + 14)
    })
    
    ctx.restore()
  }, [nodes, links, scale, offset, selectedNode, hoveredNode])
  
  // 动画循环
  useEffect(() => {
    let frameCount = 0
    const maxFrames = 200  // 限制模拟次数
    
    const animate = () => {
      if (frameCount < maxFrames) {
        simulate()
        frameCount++
      }
      render()
      animationRef.current = requestAnimationFrame(animate)
    }
    
    if (!loading && nodes.length > 0) {
      animate()
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [loading, simulate, render])
  
  // 鼠标事件
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
  }
  
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }
    
    // 检测悬停节点
    const canvas = canvasRef.current
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - canvas.width / 2 - offset.x) / scale + 300
    const y = (e.clientY - rect.top - canvas.height / 2 - offset.y) / scale + 300
    
    const hovered = nodes.find(node => {
      const dist = Math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
      return dist < node.radius
    })
    
    setHoveredNode(hovered || null)
  }
  
  const handleMouseUp = () => {
    setIsDragging(false)
  }
  
  const handleClick = () => {
    if (hoveredNode) {
      setSelectedNode(hoveredNode)
    } else {
      setSelectedNode(null)
    }
  }
  
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setScale(prev => Math.max(0.3, Math.min(2, prev + delta)))
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[800px] h-[600px] flex flex-col overflow-hidden">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 px-6 py-4 flex items-center justify-between">
          <div className="text-white">
            <h2 className="text-lg font-bold">社交网络图</h2>
            <p className="text-sm text-white/80">
              {nodes.length} 个智能体 · {links.length} 条关系
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* 画布区域 */}
        <div
          ref={containerRef}
          className="flex-1 bg-slate-50 relative"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleClick}
          onWheel={handleWheel}
        >
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
                <p className="text-slate-600">加载关系数据...</p>
              </div>
            </div>
          ) : nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500">
              暂无关系数据
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              className="w-full h-full cursor-grab active:cursor-grabbing"
            />
          )}
          
          {/* 控制按钮 */}
          <div className="absolute top-4 right-4 flex flex-col gap-2">
            <button
              onClick={() => setScale(s => Math.min(2, s + 0.2))}
              className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 transition-colors"
              title="放大"
            >
              <ZoomIn className="w-4 h-4 text-slate-600" />
            </button>
            <button
              onClick={() => setScale(s => Math.max(0.3, s - 0.2))}
              className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 transition-colors"
              title="缩小"
            >
              <ZoomOut className="w-4 h-4 text-slate-600" />
            </button>
            <button
              onClick={() => { setScale(1); setOffset({ x: 0, y: 0 }); }}
              className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 transition-colors"
              title="重置"
            >
              <RotateCcw className="w-4 h-4 text-slate-600" />
            </button>
          </div>
          
          {/* 选中节点信息 */}
          {selectedNode && (
            <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 max-w-[200px]">
              <div className="font-medium text-slate-800">{selectedNode.name}</div>
              <div className="text-sm text-slate-500">{selectedNode.occupation}</div>
              <div className="mt-2 text-xs text-slate-400">
                {links.filter(l => l.source === selectedNode.id || l.target === selectedNode.id).length} 个关系
              </div>
            </div>
          )}
        </div>
        
        {/* 图例 */}
        <div className="px-6 py-3 border-t border-slate-200 bg-white">
          <div className="flex items-center gap-4 flex-wrap text-xs">
            {Object.entries(OCCUPATION_COLORS).filter(([k]) => k !== 'default').slice(0, 6).map(([occupation, color]) => (
              <div key={occupation} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-slate-600">{occupation}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
