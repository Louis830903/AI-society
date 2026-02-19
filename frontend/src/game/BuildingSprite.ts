/**
 * 建筑物精灵类
 * 
 * 使用程序生成的像素风格建筑
 * 支持拖拽移动位置
 */

import { Container, Graphics, Text, TextStyle, FederatedPointerEvent } from 'pixi.js'
import { getBuildingConfig, BuildingConfig } from './assets'
import { backendToIsometric, isometricToBackend } from './IsometricUtils'
import type { Location } from '../types'

/**
 * 拖拽结束回调类型
 */
export type DragEndCallback = (locationId: string, newX: number, newY: number) => void

/**
 * 建筑物精灵
 */
export class BuildingSprite extends Container {
  private location: Location
  private config: BuildingConfig
  
  // 组件
  private buildingGraphics: Graphics
  private roofGraphics: Graphics
  private windowGraphics: Graphics
  private nameLabel: Text
  private highlightGraphics: Graphics
  
  // 状态
  private isHighlighted: boolean = false
  private isSelected: boolean = false
  private nightLightIntensity: number = 0
  
  // 拖拽状态
  private isDraggable: boolean = false
  private isDragging: boolean = false
  private dragStartPos: { x: number; y: number } | null = null
  private dragOffset: { x: number; y: number } = { x: 0, y: 0 }
  private onDragEnd: DragEndCallback | null = null
  
  constructor(location: Location) {
    super()
    this.location = location
    this.config = getBuildingConfig(location.type)
    
    // 创建组件
    this.buildingGraphics = new Graphics()
    this.roofGraphics = new Graphics()
    this.windowGraphics = new Graphics()
    this.highlightGraphics = new Graphics()
    this.nameLabel = this.createNameLabel()
    
    // 添加到容器
    this.addChild(this.highlightGraphics)
    this.addChild(this.buildingGraphics)
    this.addChild(this.windowGraphics)
    this.addChild(this.roofGraphics)
    this.addChild(this.nameLabel)
    
    // 绘制建筑
    this.draw()
    
    // 设置位置
    this.updatePosition()
    
    // 设置交互
    this.eventMode = 'static'
    this.cursor = 'pointer'
    
    // 存储自定义深度排序值
    ;(this as any).customZIndex = this.y
    
    // 绑定拖拽事件
    this.on('pointerdown', this.onDragStart, this)
    this.on('pointerup', this.onDragStop, this)
    this.on('pointerupoutside', this.onDragStop, this)
  }
  
  /**
   * 创建名称标签
   */
  private createNameLabel(): Text {
    const style = new TextStyle({
      fontSize: 10,
      fill: '#1e293b',
      fontFamily: 'system-ui, sans-serif',
      fontWeight: 'bold',
    })
    
    const text = new Text({ text: this.location.name, style })
    text.anchor.set(0.5, 0)
    text.y = this.config.height / 2 + 5
    
    return text
  }
  
  /**
   * 更新位置
   */
  private updatePosition(): void {
    if (!this.location.position) return
    
    const { isoX, isoY } = backendToIsometric(
      this.location.position.x,
      this.location.position.y
    )
    
    this.x = isoX
    this.y = isoY
    
    // 更新深度排序值
    ;(this as any).customZIndex = isoY
  }
  
  // ===================
  // 拖拽功能
  // ===================
  
  /**
   * 启用/禁用拖拽模式
   */
  setDraggable(enabled: boolean, onDragEnd?: DragEndCallback): void {
    this.isDraggable = enabled
    this.onDragEnd = onDragEnd || null
    this.cursor = enabled ? 'grab' : 'pointer'
    
    // 拖拽模式下显示特殊样式
    if (enabled) {
      this.drawDragModeIndicator()
    } else {
      this.highlightGraphics.clear()
      if (this.isSelected) {
        this.setSelected(true)
      }
    }
  }
  
  /**
   * 绘制拖拽模式指示器
   */
  private drawDragModeIndicator(): void {
    this.highlightGraphics.clear()
    const { width, height } = this.config
    
    // 虚线边框效果
    this.highlightGraphics.roundRect(-width / 2 - 5, -height / 2 - 5, width + 10, height + 10, 8)
    this.highlightGraphics.stroke({ width: 2, color: 0x10B981, alpha: 0.8 })
    
    // 移动图标提示（简单的箭头）
    this.highlightGraphics.circle(0, -height / 2 - 15, 8)
    this.highlightGraphics.fill({ color: 0x10B981 })
  }
  
  /**
   * 拖拽开始
   */
  private onDragStart(event: FederatedPointerEvent): void {
    if (!this.isDraggable || !this.parent) return
    
    this.isDragging = true
    this.cursor = 'grabbing'
    
    // 记录起始位置
    this.dragStartPos = { x: this.x, y: this.y }
    
    // 计算鼠标与精灵中心的偏移
    const pos = event.getLocalPosition(this.parent)
    this.dragOffset = {
      x: this.x - pos.x,
      y: this.y - pos.y,
    }
    
    // 提升层级
    this.zIndex = 1000
    
    // 绑定移动事件到父容器
    this.parent.on('pointermove', this.onDragMove, this)
  }
  
  /**
   * 拖拽移动
   */
  private onDragMove(event: FederatedPointerEvent): void {
    if (!this.isDragging || !this.parent) return
    
    // 更新位置
    const pos = event.getLocalPosition(this.parent)
    this.x = pos.x + this.dragOffset.x
    this.y = pos.y + this.dragOffset.y
    
    // 更新深度排序值
    ;(this as any).customZIndex = this.y
  }
  
  /**
   * 拖拽结束
   */
  private onDragStop(_event: FederatedPointerEvent): void {
    if (!this.isDragging) return
    
    this.isDragging = false
    this.cursor = this.isDraggable ? 'grab' : 'pointer'
    this.zIndex = 0
    
    // 解绑移动事件
    this.parent?.off('pointermove', this.onDragMove, this)
    
    // 计算新的后端坐标
    const { backendX, backendY } = isometricToBackend(this.x, this.y)
    
    // 触发回调
    if (this.onDragEnd) {
      this.onDragEnd(this.location.id, backendX, backendY)
    }
    
    // 更新本地位置数据
    this.location.position.x = backendX
    this.location.position.y = backendY
    
    this.dragStartPos = null
  }
  
  /**
   * 取消拖拽（恢复原位置）
   */
  cancelDrag(): void {
    if (this.dragStartPos) {
      this.x = this.dragStartPos.x
      this.y = this.dragStartPos.y
      ;(this as any).customZIndex = this.y
    }
    this.isDragging = false
    this.dragStartPos = null
    this.parent?.off('pointermove', this.onDragMove, this)
  }
  
  /**
   * 是否正在拖拽
   */
  getIsDragging(): boolean {
    return this.isDragging
  }
  
  /**
   * 绘制建筑物
   */
  private draw(): void {
    const { width, height, color, roofColor } = this.config
    
    // 清除之前的绘制
    this.buildingGraphics.clear()
    this.roofGraphics.clear()
    this.windowGraphics.clear()
    
    // 绘制主体（等距立方体）
    this.drawIsometricBuilding(width, height, color, roofColor)
    
    // 绘制窗户
    this.drawWindows(width, height)
  }
  
  /**
   * 绘制等距建筑（增强像素风格）
   */
  private drawIsometricBuilding(
    width: number,
    height: number,
    mainColor: number,
    roofColor: number
  ): void {
    const halfW = width / 2
    const buildingHeight = height * 0.7
    const roofHeight = height * 0.3
    
    // 颜色变化工具
    const darken = (c: number, factor: number) => this.darkenColor(c, factor)
    const lighten = (c: number, factor: number = 0.15) => {
      const r = Math.min(255, ((c >> 16) & 0xFF) * (1 + factor))
      const g = Math.min(255, ((c >> 8) & 0xFF) * (1 + factor))
      const b = Math.min(255, (c & 0xFF) * (1 + factor))
      return (Math.floor(r) << 16) | (Math.floor(g) << 8) | Math.floor(b)
    }
    
    const rightFaceColor = darken(mainColor, 0.15)
    const leftFaceColor = darken(mainColor, 0.25)
    const highlightColor = lighten(mainColor)
    const outlineColor = darken(mainColor, 0.4)
    
    // 右侧面（带砖块纹理）
    this.buildingGraphics.moveTo(0, 0)
    this.buildingGraphics.lineTo(halfW, -buildingHeight / 4)
    this.buildingGraphics.lineTo(halfW, buildingHeight * 0.5)
    this.buildingGraphics.lineTo(0, buildingHeight * 0.75)
    this.buildingGraphics.closePath()
    this.buildingGraphics.fill({ color: rightFaceColor })
    
    // 右侧砖块纹理线
    for (let i = 1; i < 5; i++) {
      const y1 = -buildingHeight / 4 + i * buildingHeight * 0.15
      const y2 = buildingHeight * 0.5 - (4 - i) * buildingHeight * 0.15
      this.buildingGraphics.moveTo(halfW * 0.2, y1)
      this.buildingGraphics.lineTo(halfW, y1 - buildingHeight * 0.05)
      this.buildingGraphics.stroke({ width: 1, color: darken(rightFaceColor, 0.1), alpha: 0.5 })
    }
    
    // 左侧面
    this.buildingGraphics.moveTo(0, 0)
    this.buildingGraphics.lineTo(-halfW, -buildingHeight / 4)
    this.buildingGraphics.lineTo(-halfW, buildingHeight * 0.5)
    this.buildingGraphics.lineTo(0, buildingHeight * 0.75)
    this.buildingGraphics.closePath()
    this.buildingGraphics.fill({ color: leftFaceColor })
    
    // 左侧砖块纹理线
    for (let i = 1; i < 5; i++) {
      const y1 = -buildingHeight / 4 + i * buildingHeight * 0.15
      this.buildingGraphics.moveTo(-halfW * 0.2, y1)
      this.buildingGraphics.lineTo(-halfW, y1 - buildingHeight * 0.05)
      this.buildingGraphics.stroke({ width: 1, color: darken(leftFaceColor, 0.1), alpha: 0.5 })
    }
    
    // 边缘高光线
    this.buildingGraphics.moveTo(0, 0)
    this.buildingGraphics.lineTo(0, buildingHeight * 0.75)
    this.buildingGraphics.stroke({ width: 2, color: highlightColor, alpha: 0.4 })
    
    // 轮廓线
    this.buildingGraphics.moveTo(0, 0)
    this.buildingGraphics.lineTo(halfW, -buildingHeight / 4)
    this.buildingGraphics.lineTo(halfW, buildingHeight * 0.5)
    this.buildingGraphics.lineTo(0, buildingHeight * 0.75)
    this.buildingGraphics.lineTo(-halfW, buildingHeight * 0.5)
    this.buildingGraphics.lineTo(-halfW, -buildingHeight / 4)
    this.buildingGraphics.closePath()
    this.buildingGraphics.stroke({ width: 1.5, color: outlineColor })
    
    // 屋顶（带3D效果）
    // 屋顶侧面（右）
    this.roofGraphics.moveTo(0, 0)
    this.roofGraphics.lineTo(halfW, -buildingHeight / 4)
    this.roofGraphics.lineTo(halfW, -buildingHeight / 4 - roofHeight / 4)
    this.roofGraphics.lineTo(0, -roofHeight / 2)
    this.roofGraphics.closePath()
    this.roofGraphics.fill({ color: darken(roofColor, 0.1) })
    
    // 屋顶侧面（左）
    this.roofGraphics.moveTo(0, 0)
    this.roofGraphics.lineTo(-halfW, -buildingHeight / 4)
    this.roofGraphics.lineTo(-halfW, -buildingHeight / 4 - roofHeight / 4)
    this.roofGraphics.lineTo(0, -roofHeight / 2)
    this.roofGraphics.closePath()
    this.roofGraphics.fill({ color: darken(roofColor, 0.2) })
    
    // 屋顶顶面
    this.roofGraphics.moveTo(0, -buildingHeight / 2 - roofHeight / 2)  // 顶部
    this.roofGraphics.lineTo(halfW, -buildingHeight / 4 - roofHeight / 4)  // 右
    this.roofGraphics.lineTo(0, -roofHeight / 2)  // 前
    this.roofGraphics.lineTo(-halfW, -buildingHeight / 4 - roofHeight / 4)  // 左
    this.roofGraphics.closePath()
    this.roofGraphics.fill({ color: roofColor })
    
    // 屋顶高光
    this.roofGraphics.moveTo(0, -buildingHeight / 2 - roofHeight / 2)
    this.roofGraphics.lineTo(-halfW * 0.5, -buildingHeight / 4 - roofHeight / 3)
    this.roofGraphics.stroke({ width: 2, color: lighten(roofColor, 0.2), alpha: 0.5 })
    
    // 屋顶轮廓
    this.roofGraphics.moveTo(0, -buildingHeight / 2 - roofHeight / 2)
    this.roofGraphics.lineTo(halfW, -buildingHeight / 4 - roofHeight / 4)
    this.roofGraphics.lineTo(halfW, -buildingHeight / 4)
    this.roofGraphics.moveTo(0, -buildingHeight / 2 - roofHeight / 2)
    this.roofGraphics.lineTo(-halfW, -buildingHeight / 4 - roofHeight / 4)
    this.roofGraphics.lineTo(-halfW, -buildingHeight / 4)
    this.roofGraphics.stroke({ width: 1.5, color: darken(roofColor, 0.3) })
  }
  
  /**
   * 绘制增强版窗户（像素艺术风格）
   */
  private drawWindows(buildingWidth: number, buildingHeight: number): void {
    const windowWidth = 6
    const windowHeight = 8
    const isNight = this.nightLightIntensity > 0
    
    // 窗户颜色配置
    const windowColor = isNight ? 0xFFDD88 : 0x87CEEB
    const windowLightColor = 0xFFF8E0  // 暖光色
    const frameColor = 0x4A5568  // 窗框颜色
    const frameDarkColor = 0x2D3748  // 窗框阴影
    
    // 在左右两侧绘制窗户
    const rows = Math.floor((buildingHeight * 0.5) / 15)
    const cols = Math.floor(buildingWidth / 20)
    
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        // 右侧窗户
        const rightX = 5 + col * 12
        const rightY = -buildingHeight * 0.1 + row * 12
        this.drawSingleWindow(rightX, rightY, windowWidth, windowHeight, windowColor, windowLightColor, frameColor, frameDarkColor, isNight, true)
        
        // 左侧窗户
        const leftX = -5 - col * 12 - windowWidth
        this.drawSingleWindow(leftX, rightY, windowWidth, windowHeight, windowColor, windowLightColor, frameColor, frameDarkColor, isNight, false)
      }
    }
  }
  
  /**
   * 绘制单个像素风格窗户
   */
  private drawSingleWindow(
    x: number, y: number,
    width: number, height: number,
    glassColor: number, lightColor: number,
    frameColor: number, frameDarkColor: number,
    isNight: boolean, isRightSide: boolean
  ): void {
    // 窗框外边框（深色）
    this.windowGraphics.rect(x - 1, y - 1, width + 2, height + 2)
    this.windowGraphics.fill({ color: frameDarkColor })
    
    // 窗框内边框
    this.windowGraphics.rect(x, y, width, height)
    this.windowGraphics.fill({ color: frameColor })
    
    // 窗户玻璃（内部）
    this.windowGraphics.rect(x + 1, y + 1, width - 2, height - 2)
    this.windowGraphics.fill({ color: glassColor, alpha: isNight ? 0.9 : 0.7 })
    
    // 夜间灯光效果
    if (isNight && this.nightLightIntensity > 0) {
      // 发光效果（外部光晕）
      this.windowGraphics.rect(x - 2, y - 2, width + 4, height + 4)
      this.windowGraphics.fill({ color: lightColor, alpha: 0.15 * this.nightLightIntensity })
      
      // 内部高亮
      this.windowGraphics.rect(x + 2, y + 2, width - 4, height - 4)
      this.windowGraphics.fill({ color: lightColor, alpha: 0.5 * this.nightLightIntensity })
    } else {
      // 白天窗户反光效果
      const reflectColor = 0xFFFFFF
      if (isRightSide) {
        // 右上角反光
        this.windowGraphics.rect(x + 1, y + 1, 2, 2)
        this.windowGraphics.fill({ color: reflectColor, alpha: 0.4 })
      } else {
        // 左上角反光
        this.windowGraphics.rect(x + width - 3, y + 1, 2, 2)
        this.windowGraphics.fill({ color: reflectColor, alpha: 0.4 })
      }
    }
    
    // 窗户十字分隔线
    this.windowGraphics.moveTo(x + width / 2, y + 1)
    this.windowGraphics.lineTo(x + width / 2, y + height - 1)
    this.windowGraphics.stroke({ width: 1, color: frameColor, alpha: 0.8 })
    
    this.windowGraphics.moveTo(x + 1, y + height / 2)
    this.windowGraphics.lineTo(x + width - 1, y + height / 2)
    this.windowGraphics.stroke({ width: 1, color: frameColor, alpha: 0.8 })
  }
  
  /**
   * 使颜色变暗
   */
  private darkenColor(color: number, amount: number): number {
    const r = Math.max(0, ((color >> 16) & 0xFF) * (1 - amount))
    const g = Math.max(0, ((color >> 8) & 0xFF) * (1 - amount))
    const b = Math.max(0, (color & 0xFF) * (1 - amount))
    return (Math.floor(r) << 16) | (Math.floor(g) << 8) | Math.floor(b)
  }
  
  /**
   * 设置高亮
   */
  setHighlighted(highlighted: boolean): void {
    if (this.isHighlighted === highlighted) return
    this.isHighlighted = highlighted
    
    this.highlightGraphics.clear()
    
    if (highlighted) {
      const { width, height } = this.config
      // 绘制高亮框
      this.highlightGraphics.roundRect(-width / 2 - 5, -height / 2 - 5, width + 10, height + 10, 8)
      this.highlightGraphics.stroke({ width: 2, color: 0x3B82F6, alpha: 0.8 })
    }
  }
  
  /**
   * 设置选中状态
   */
  setSelected(selected: boolean): void {
    if (this.isSelected === selected) return
    this.isSelected = selected
    
    this.highlightGraphics.clear()
    
    if (selected) {
      const { width, height } = this.config
      // 绘制选中框
      this.highlightGraphics.roundRect(-width / 2 - 5, -height / 2 - 5, width + 10, height + 10, 8)
      this.highlightGraphics.fill({ color: 0x3B82F6, alpha: 0.2 })
      this.highlightGraphics.stroke({ width: 3, color: 0x1D4ED8 })
    }
  }
  
  /**
   * 设置夜间灯光强度
   */
  setNightLight(intensity: number): void {
    if (Math.abs(this.nightLightIntensity - intensity) < 0.01) return
    this.nightLightIntensity = intensity
    
    // 重绘窗户以更新灯光效果
    this.windowGraphics.clear()
    this.drawWindows(this.config.width, this.config.height)
  }
  
  /**
   * 获取位置数据
   */
  getLocation(): Location {
    return this.location
  }
  
  /**
   * 获取位置ID
   */
  getLocationId(): string {
    return this.location.id
  }
  
  /**
   * 更新位置数据
   */
  updateLocation(location: Location): void {
    this.location = location
    this.config = getBuildingConfig(location.type)
    this.draw()
    this.updatePosition()
    this.nameLabel.text = location.name
  }
}

/**
 * 建筑物精灵管理器
 */
export class BuildingManager {
  private buildings: Map<string, BuildingSprite> = new Map()
  private container: Container
  
  constructor(buildingLayer: Container) {
    this.container = buildingLayer
  }
  
  /**
   * 添加或更新建筑
   */
  addOrUpdate(location: Location): BuildingSprite {
    let sprite = this.buildings.get(location.id)
    
    if (sprite) {
      sprite.updateLocation(location)
    } else {
      sprite = new BuildingSprite(location)
      this.buildings.set(location.id, sprite)
      this.container.addChild(sprite)
    }
    
    return sprite
  }
  
  /**
   * 移除建筑
   */
  remove(locationId: string): void {
    const sprite = this.buildings.get(locationId)
    if (sprite) {
      this.container.removeChild(sprite)
      sprite.destroy()
      this.buildings.delete(locationId)
    }
  }
  
  /**
   * 同步建筑列表
   */
  sync(locations: Location[]): void {
    const currentIds = new Set(locations.map(l => l.id))
    
    // 添加或更新
    for (const location of locations) {
      if (location.position) {
        this.addOrUpdate(location)
      }
    }
    
    // 移除不存在的
    for (const id of this.buildings.keys()) {
      if (!currentIds.has(id)) {
        this.remove(id)
      }
    }
  }
  
  /**
   * 获取建筑精灵
   */
  get(locationId: string): BuildingSprite | undefined {
    return this.buildings.get(locationId)
  }
  
  /**
   * 设置所有建筑夜间灯光
   */
  setAllNightLight(intensity: number): void {
    this.buildings.forEach(building => {
      building.setNightLight(intensity)
    })
  }
  
  /**
   * 清除所有
   */
  clear(): void {
    this.buildings.forEach(sprite => {
      this.container.removeChild(sprite)
      sprite.destroy()
    })
    this.buildings.clear()
  }
  
  /**
   * 获取所有建筑
   */
  getAll(): BuildingSprite[] {
    return Array.from(this.buildings.values())
  }
  
  /**
   * 点击检测 - 检测指定坐标是否点击了建筑物
   * @param worldX 世界坐标 X
   * @param worldY 世界坐标 Y
   * @param threshold 检测阈值（像素）
   * @returns 被点击的建筑精灵，或 undefined
   */
  hitTest(worldX: number, worldY: number, threshold: number = 30): BuildingSprite | undefined {
    let closestSprite: BuildingSprite | undefined
    let closestDistance = Infinity
    
    this.buildings.forEach(sprite => {
      const dx = worldX - sprite.x
      const dy = worldY - sprite.y
      const distance = Math.sqrt(dx * dx + dy * dy)
      
      if (distance < threshold && distance < closestDistance) {
        closestDistance = distance
        closestSprite = sprite
      }
    })
    
    return closestSprite
  }
  
  /**
   * 为指定建筑物启用/禁用拖拽
   * @param locationId 建筑物ID
   * @param enabled 是否启用拖拽
   * @param onDragEnd 拖拽结束回调（接收等距坐标）
   */
  setDraggable(
    locationId: string, 
    enabled: boolean, 
    onDragEnd?: (locationId: string, newIsoX: number, newIsoY: number) => void
  ): void {
    const sprite = this.buildings.get(locationId)
    if (sprite) {
      // 包装回调：将精灵的 x,y（等距坐标）传递出去
      const wrappedCallback: DragEndCallback | undefined = onDragEnd
        ? (id: string, _backendX: number, _backendY: number) => {
            // BuildingSprite 的 onDragEnd 已经转换为后端坐标了
            // 但我们这里需要传递精灵的当前位置（等距坐标）
            onDragEnd(id, sprite.x, sprite.y)
          }
        : undefined
      
      sprite.setDraggable(enabled, wrappedCallback)
    }
  }
  
  /**
   * 禁用所有建筑物的拖拽
   */
  disableAllDragging(): void {
    this.buildings.forEach(sprite => {
      sprite.setDraggable(false)
    })
  }
}
