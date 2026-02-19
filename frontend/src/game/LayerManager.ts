/**
 * 渲染层级管理器
 * 
 * 管理不同类型对象的渲染层级
 * 确保正确的遮挡关系
 */

import { Container } from 'pixi.js'

/**
 * 层级枚举
 */
export enum LayerType {
  GROUND = 0,      // 地面/道路
  BUILDING = 1,    // 建筑物
  AGENT = 2,       // 智能体
  EFFECT = 3,      // 天气/粒子效果
  UI = 4,          // 对话气泡/标签
}

/**
 * 渲染层管理器
 * 
 * 层级结构（从底到顶）：
 * 1. groundLayer - 地面瓦片、道路
 * 2. buildingLayer - 建筑物（按Y轴排序）
 * 3. agentLayer - 智能体（按Y轴排序）
 * 4. effectLayer - 天气粒子、特效
 * 5. uiLayer - UI元素、对话气泡
 */
export class LayerManager {
  // 各层级容器
  private _groundLayer: Container
  private _buildingLayer: Container
  private _agentLayer: Container
  private _effectLayer: Container
  private _uiLayer: Container
  
  // 世界容器（包含可缩放/拖拽的内容）
  private _worldContainer: Container
  
  // 脏标记（用于优化排序）
  private buildingsDirty = false
  private agentsDirty = false
  
  constructor(stage: Container) {
    // 创建世界容器（可缩放/拖拽）
    this._worldContainer = new Container()
    this._worldContainer.label = 'worldContainer'
    stage.addChild(this._worldContainer)
    
    // 创建各层级容器
    this._groundLayer = new Container()
    this._groundLayer.label = 'groundLayer'
    this._worldContainer.addChild(this._groundLayer)
    
    this._buildingLayer = new Container()
    this._buildingLayer.label = 'buildingLayer'
    this._worldContainer.addChild(this._buildingLayer)
    
    this._agentLayer = new Container()
    this._agentLayer.label = 'agentLayer'
    this._worldContainer.addChild(this._agentLayer)
    
    this._effectLayer = new Container()
    this._effectLayer.label = 'effectLayer'
    this._worldContainer.addChild(this._effectLayer)
    
    // UI层不跟随世界移动，直接添加到舞台
    this._uiLayer = new Container()
    this._uiLayer.label = 'uiLayer'
    stage.addChild(this._uiLayer)
  }
  
  // Getters
  get groundLayer(): Container {
    return this._groundLayer
  }
  
  get buildingLayer(): Container {
    return this._buildingLayer
  }
  
  get agentLayer(): Container {
    return this._agentLayer
  }
  
  get effectLayer(): Container {
    return this._effectLayer
  }
  
  get uiLayer(): Container {
    return this._uiLayer
  }
  
  get worldContainer(): Container {
    return this._worldContainer
  }
  
  /**
   * 标记建筑层需要重新排序
   */
  markBuildingsDirty(): void {
    this.buildingsDirty = true
  }
  
  /**
   * 标记智能体层需要重新排序
   */
  markAgentsDirty(): void {
    this.agentsDirty = true
  }
  
  /**
   * 更新排序（在渲染前调用）
   */
  updateSorting(): void {
    if (this.buildingsDirty) {
      this.sortChildren(this._buildingLayer)
      this.buildingsDirty = false
    }
    
    if (this.agentsDirty) {
      this.sortChildren(this._agentLayer)
      this.agentsDirty = false
    }
  }
  
  /**
   * 按Y轴对子元素排序
   */
  private sortChildren(container: Container): void {
    const children = container.children.slice()
    
    // 按 zIndex 或 y 坐标排序
    children.sort((a, b) => {
      // 优先使用自定义 zIndex
      const zA = (a as any).customZIndex ?? a.y
      const zB = (b as any).customZIndex ?? b.y
      return zA - zB
    })
    
    // 重新设置子元素顺序
    children.forEach((child, index) => {
      container.setChildIndex(child, index)
    })
  }
  
  /**
   * 设置世界容器的位置（摄像机）
   */
  setWorldPosition(x: number, y: number): void {
    this._worldContainer.x = x
    this._worldContainer.y = y
  }
  
  /**
   * 设置世界容器的缩放
   */
  setWorldScale(scale: number): void {
    this._worldContainer.scale.set(scale)
  }
  
  /**
   * 获取世界容器的位置
   */
  getWorldPosition(): { x: number; y: number } {
    return { x: this._worldContainer.x, y: this._worldContainer.y }
  }
  
  /**
   * 获取世界容器的缩放
   */
  getWorldScale(): number {
    return this._worldContainer.scale.x
  }
  
  /**
   * 清空指定层
   */
  clearLayer(type: LayerType): void {
    const layer = this.getLayerByType(type)
    if (layer) {
      layer.removeChildren()
    }
  }
  
  /**
   * 清空所有层
   */
  clearAll(): void {
    this._groundLayer.removeChildren()
    this._buildingLayer.removeChildren()
    this._agentLayer.removeChildren()
    this._effectLayer.removeChildren()
    this._uiLayer.removeChildren()
  }
  
  /**
   * 根据类型获取层
   */
  getLayerByType(type: LayerType): Container | null {
    switch (type) {
      case LayerType.GROUND:
        return this._groundLayer
      case LayerType.BUILDING:
        return this._buildingLayer
      case LayerType.AGENT:
        return this._agentLayer
      case LayerType.EFFECT:
        return this._effectLayer
      case LayerType.UI:
        return this._uiLayer
      default:
        return null
    }
  }
  
  /**
   * 添加对象到指定层
   */
  addToLayer(type: LayerType, child: Container): void {
    const layer = this.getLayerByType(type)
    if (layer) {
      layer.addChild(child)
      
      // 标记需要重新排序
      if (type === LayerType.BUILDING) {
        this.buildingsDirty = true
      } else if (type === LayerType.AGENT) {
        this.agentsDirty = true
      }
    }
  }
  
  /**
   * 从指定层移除对象
   */
  removeFromLayer(type: LayerType, child: Container): void {
    const layer = this.getLayerByType(type)
    if (layer && child.parent === layer) {
      layer.removeChild(child)
    }
  }
  
  /**
   * 应用昼夜着色到世界层
   */
  applyTint(tint: number): void {
    // 给地面层和建筑层应用着色
    this._groundLayer.children.forEach(child => {
      if ((child as any).tint !== undefined) {
        (child as any).tint = tint
      }
    })
    
    this._buildingLayer.children.forEach(child => {
      if ((child as any).tint !== undefined) {
        (child as any).tint = tint
      }
    })
    
    this._agentLayer.children.forEach(child => {
      if ((child as any).tint !== undefined) {
        (child as any).tint = tint
      }
    })
  }
}
