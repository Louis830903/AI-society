/**
 * 智能体精灵类
 * 
 * 使用程序生成的像素风格人物
 */

import { Container, Graphics, Text, TextStyle } from 'pixi.js'
import { getCharacterPalette, CharacterConfig } from './assets'
import { backendToIsometric } from './IsometricUtils'
import { AnimationController, AnimationState } from './AnimationController'
import { TweenManager, Easing } from './TweenManager'
import type { AgentBrief } from '../types'

/**
 * 智能体精灵
 */
export class AgentSprite extends Container {
  private agentData: AgentBrief
  private palette: CharacterConfig
  
  // 组件
  private characterGraphics: Graphics
  private shadowGraphics: Graphics
  private nameLabel: Text
  private statusIcon: Graphics
  
  // 动画
  private animController: AnimationController
  
  // 状态
  private isSelected: boolean = false
  private isFollowing: boolean = false
  private isChatting: boolean = false
  
  // 移动状态
  private isMoving: boolean = false
  private currentTweenId: string | null = null
  
  constructor(agent: AgentBrief) {
    super()
    this.agentData = agent
    this.palette = getCharacterPalette(agent.id)
    
    // 创建组件
    this.shadowGraphics = new Graphics()
    this.characterGraphics = new Graphics()
    this.statusIcon = new Graphics()
    this.nameLabel = this.createNameLabel()
    
    // 添加到容器
    this.addChild(this.shadowGraphics)
    this.addChild(this.characterGraphics)
    this.addChild(this.statusIcon)
    this.addChild(this.nameLabel)
    
    // 初始化动画控制器
    this.animController = new AnimationController()
    this.animController.setOnFrameChange(() => this.drawCharacter())
    
    // 绘制初始状态
    this.drawShadow()
    this.drawCharacter()
    
    // 隐藏名字标签（悬停时显示）
    this.nameLabel.visible = false
    
    // 设置交互
    this.eventMode = 'static'
    this.cursor = 'pointer'
    
    // 存储深度排序值
    ;(this as any).customZIndex = this.y
  }
  
  /**
   * 创建名称标签
   */
  private createNameLabel(): Text {
    const style = new TextStyle({
      fontSize: 9,
      fill: '#1e293b',
      fontFamily: 'system-ui, sans-serif',
      fontWeight: 'bold',
    })
    
    const text = new Text({ text: this.agentData.name, style })
    text.anchor.set(0.5, 1)
    text.y = -20
    
    return text
  }
  
  /**
   * 绘制阴影
   */
  private drawShadow(): void {
    this.shadowGraphics.clear()
    this.shadowGraphics.ellipse(0, 2, 8, 4)
    this.shadowGraphics.fill({ color: 0x000000, alpha: 0.2 })
  }
  
  /**
   * 绘制增强版像素人物
   * 参考 generative_agents 的像素艺术风格
   */
  private drawCharacter(): void {
    this.characterGraphics.clear()
    
    const frameData = this.animController.getFrameData()
    const offsetY = frameData.offsetY
    const scaleX = frameData.scaleX
    const currentFrame = this.animController.getCurrentFrame()
    const state = this.animController.getState()
    
    const { skinColor, hairColor, shirtColor } = this.palette
    
    // 计算高光和阴影色
    const darken = (color: number, factor: number = 0.7) => {
      const r = Math.floor(((color >> 16) & 0xFF) * factor)
      const g = Math.floor(((color >> 8) & 0xFF) * factor)
      const b = Math.floor((color & 0xFF) * factor)
      return (r << 16) | (g << 8) | b
    }
    const lighten = (color: number, factor: number = 1.3) => {
      const r = Math.min(255, Math.floor(((color >> 16) & 0xFF) * factor))
      const g = Math.min(255, Math.floor(((color >> 8) & 0xFF) * factor))
      const b = Math.min(255, Math.floor((color & 0xFF) * factor))
      return (r << 16) | (g << 8) | b
    }
    
    const skinDark = darken(skinColor)
    const skinLight = lighten(skinColor)
    const hairDark = darken(hairColor)
    const shirtDark = darken(shirtColor)
    const shirtLight = lighten(shirtColor)
    const outlineColor = 0x2D2D2D
    
    // 应用方向缩放
    this.characterGraphics.scale.x = scaleX
    
    const p = 2  // pixelSize
    
    // === 头发（带造型） ===
    // 头发主体
    this.drawPixel(hairColor, -3, -18 + offsetY, p)
    this.drawPixel(hairColor, -2, -18 + offsetY, p)
    this.drawPixel(hairColor, -1, -18 + offsetY, p)
    this.drawPixel(hairColor, 0, -18 + offsetY, p)
    this.drawPixel(hairColor, 1, -18 + offsetY, p)
    this.drawPixel(hairColor, 2, -18 + offsetY, p)
    // 头发第二层
    this.drawPixel(hairColor, -3, -16 + offsetY, p)
    this.drawPixel(hairDark, -2, -16 + offsetY, p)
    this.drawPixel(hairColor, -1, -16 + offsetY, p)
    this.drawPixel(hairColor, 0, -16 + offsetY, p)
    this.drawPixel(hairDark, 1, -16 + offsetY, p)
    this.drawPixel(hairColor, 2, -16 + offsetY, p)
    // 头发侧边（刘海效果）
    this.drawPixel(hairColor, -4, -14 + offsetY, p)
    this.drawPixel(hairColor, 3, -14 + offsetY, p)
    
    // === 脸部 ===
    // 脸主体
    this.drawPixel(skinColor, -3, -14 + offsetY, p)
    this.drawPixel(skinColor, -2, -14 + offsetY, p)
    this.drawPixel(skinLight, -1, -14 + offsetY, p)  // 高光
    this.drawPixel(skinColor, 0, -14 + offsetY, p)
    this.drawPixel(skinColor, 1, -14 + offsetY, p)
    this.drawPixel(skinColor, 2, -14 + offsetY, p)
    // 脸第二层（眼睛层）
    this.drawPixel(skinColor, -3, -12 + offsetY, p)
    this.drawPixel(0xFFFFFF, -2, -12 + offsetY, p)   // 左眼白
    this.drawPixel(0x000000, -1, -12 + offsetY, p)   // 左瞳孔
    this.drawPixel(skinColor, 0, -12 + offsetY, p)
    this.drawPixel(0xFFFFFF, 1, -12 + offsetY, p)    // 右眼白
    this.drawPixel(0x000000, 2, -12 + offsetY, p)    // 右瞳孔
    // 脸下半部（嘴巴层）
    this.drawPixel(skinDark, -3, -10 + offsetY, p)   // 阴影
    this.drawPixel(skinColor, -2, -10 + offsetY, p)
    this.drawPixel(skinColor, -1, -10 + offsetY, p)
    this.drawPixel(0x000000, 0, -10 + offsetY, p)    // 嘴巴
    this.drawPixel(skinColor, 1, -10 + offsetY, p)
    this.drawPixel(skinDark, 2, -10 + offsetY, p)    // 阴影
    
    // === 脖子 ===
    this.drawPixel(skinDark, -1, -8 + offsetY, p)
    this.drawPixel(skinColor, 0, -8 + offsetY, p)
    this.drawPixel(skinDark, 1, -8 + offsetY, p)
    
    // === 身体/衣服 ===
    // 肩膀
    this.drawPixel(shirtLight, -4, -6 + offsetY, p)  // 左肩高光
    this.drawPixel(shirtColor, -3, -6 + offsetY, p)
    this.drawPixel(shirtColor, -2, -6 + offsetY, p)
    this.drawPixel(shirtColor, -1, -6 + offsetY, p)
    this.drawPixel(shirtColor, 0, -6 + offsetY, p)
    this.drawPixel(shirtColor, 1, -6 + offsetY, p)
    this.drawPixel(shirtColor, 2, -6 + offsetY, p)
    this.drawPixel(shirtDark, 3, -6 + offsetY, p)    // 右肩阴影
    // 身体主体
    for (let row = 0; row < 3; row++) {
      const y = -4 + row * 2 + offsetY
      this.drawPixel(shirtLight, -4, y, p)          // 高光边
      this.drawPixel(shirtColor, -3, y, p)
      this.drawPixel(shirtColor, -2, y, p)
      this.drawPixel(shirtColor, -1, y, p)
      this.drawPixel(shirtColor, 0, y, p)
      this.drawPixel(shirtColor, 1, y, p)
      this.drawPixel(shirtColor, 2, y, p)
      this.drawPixel(shirtDark, 3, y, p)            // 阴影边
    }
    // 衣服下摆
    this.drawPixel(shirtDark, -3, 2 + offsetY, p)
    this.drawPixel(shirtColor, -2, 2 + offsetY, p)
    this.drawPixel(shirtColor, -1, 2 + offsetY, p)
    this.drawPixel(shirtColor, 0, 2 + offsetY, p)
    this.drawPixel(shirtColor, 1, 2 + offsetY, p)
    this.drawPixel(shirtDark, 2, 2 + offsetY, p)
    
    // === 手臂 ===
    const pantsColor = 0x4A4A4A
    const pantsDark = 0x3A3A3A
    
    if (state === AnimationState.WORKING) {
      // 工作时手臂抬起
      this.drawPixel(skinColor, -5, -6 + offsetY, p)
      this.drawPixel(skinColor, -5, -4 + offsetY, p)
      this.drawPixel(skinColor, 4, -6 + offsetY, p)
      this.drawPixel(skinColor, 4, -4 + offsetY, p)
    } else if (state === AnimationState.WALKING) {
      // 行走时手臂摆动
      const armSwing = [1, 0, -1, 0][currentFrame] || 0
      this.drawPixel(skinColor, -5, -4 + offsetY + armSwing, p)
      this.drawPixel(skinDark, -5, -2 + offsetY + armSwing, p)
      this.drawPixel(skinColor, 4, -4 + offsetY - armSwing, p)
      this.drawPixel(skinDark, 4, -2 + offsetY - armSwing, p)
    } else {
      // 静止时手臂
      this.drawPixel(skinColor, -5, -4 + offsetY, p)
      this.drawPixel(skinDark, -5, -2 + offsetY, p)
      this.drawPixel(skinColor, 4, -4 + offsetY, p)
      this.drawPixel(skinDark, 4, -2 + offsetY, p)
    }
    
    // === 腿部 ===
    if (state === AnimationState.WALKING) {
      // 行走时腿部交替前后移动
      const legOffset = [2, 0, -2, 0][currentFrame] || 0
      // 左腿
      this.drawPixel(pantsColor, -3 + legOffset, 4 + offsetY, p)
      this.drawPixel(pantsColor, -3 + legOffset, 6 + offsetY, p)
      this.drawPixel(pantsDark, -3 + legOffset, 8 + offsetY, p)   // 鞋子
      // 右腿
      this.drawPixel(pantsColor, 2 - legOffset, 4 + offsetY, p)
      this.drawPixel(pantsColor, 2 - legOffset, 6 + offsetY, p)
      this.drawPixel(pantsDark, 2 - legOffset, 8 + offsetY, p)    // 鞋子
    } else {
      // 静止站立
      // 左腿
      this.drawPixel(pantsColor, -3, 4 + offsetY, p)
      this.drawPixel(pantsColor, -3, 6 + offsetY, p)
      this.drawPixel(pantsDark, -3, 8 + offsetY, p)
      // 右腿
      this.drawPixel(pantsColor, 2, 4 + offsetY, p)
      this.drawPixel(pantsColor, 2, 6 + offsetY, p)
      this.drawPixel(pantsDark, 2, 8 + offsetY, p)
    }
  }
  
  /**
   * 绘制单个像素
   */
  private drawPixel(color: number, x: number, y: number, pixelSize: number): void {
    this.characterGraphics.rect(x * pixelSize / 2, y * pixelSize / 2, pixelSize, pixelSize)
    this.characterGraphics.fill({ color })
  }
  
  /**
   * 更新动画
   */
  update(deltaTime: number): void {
    this.animController.update(deltaTime)
  }
  
  /**
   * 移动到目标位置
   */
  moveTo(
    targetIsoX: number,
    targetIsoY: number,
    tweenManager: TweenManager,
    duration: number = 0.5
  ): void {
    // 取消之前的移动动画
    if (this.currentTweenId) {
      tweenManager.cancel(this.currentTweenId)
    }
    
    // 设置移动状态
    this.isMoving = true
    this.animController.setState(AnimationState.WALKING)
    this.animController.setDirectionToTarget(this.x, this.y, targetIsoX, targetIsoY)
    
    // 创建补间动画
    this.currentTweenId = tweenManager.moveTo(
      this,
      targetIsoX,
      targetIsoY,
      duration,
      Easing.easeOutQuad,
      () => {
        this.isMoving = false
        this.currentTweenId = null
        
        // 根据状态设置动画
        if (this.isChatting) {
          this.animController.setState(AnimationState.CHATTING)
        } else {
          this.animController.setState(AnimationState.IDLE)
        }
        
        // 更新深度排序值
        ;(this as any).customZIndex = this.y
      }
    )
  }
  
  /**
   * 立即设置位置
   */
  setPosition(isoX: number, isoY: number): void {
    this.x = isoX
    this.y = isoY
    ;(this as any).customZIndex = isoY
  }
  
  /**
   * 根据后端坐标设置位置
   */
  setPositionFromBackend(backendX: number, backendY: number): void {
    const { isoX, isoY } = backendToIsometric(backendX, backendY)
    this.setPosition(isoX, isoY)
  }
  
  /**
   * 设置选中状态
   */
  setSelected(selected: boolean): void {
    this.isSelected = selected
    this.nameLabel.visible = selected || this.isFollowing || this.isChatting
    this.drawStatusIndicator()
  }
  
  /**
   * 设置跟随状态
   */
  setFollowing(following: boolean): void {
    this.isFollowing = following
    this.nameLabel.visible = this.isSelected || following || this.isChatting
    this.drawStatusIndicator()
  }
  
  /**
   * 设置聊天状态
   */
  setChatting(chatting: boolean): void {
    this.isChatting = chatting
    this.nameLabel.visible = this.isSelected || this.isFollowing || chatting
    
    if (chatting) {
      this.animController.setState(AnimationState.CHATTING)
    } else if (!this.isMoving) {
      this.animController.setState(AnimationState.IDLE)
    }
    
    this.drawStatusIndicator()
  }
  
  /**
   * 绘制状态指示器
   */
  private drawStatusIndicator(): void {
    this.statusIcon.clear()
    
    if (this.isFollowing) {
      // 跟随状态：绿色圆圈
      this.statusIcon.circle(0, 0, 12)
      this.statusIcon.fill({ color: 0x22C55E, alpha: 0.2 })
      this.statusIcon.stroke({ width: 2, color: 0x22C55E })
    } else if (this.isChatting) {
      // 聊天状态：蓝色圆圈
      this.statusIcon.circle(0, 0, 10)
      this.statusIcon.fill({ color: 0x3B82F6, alpha: 0.2 })
      this.statusIcon.stroke({ width: 1.5, color: 0x3B82F6 })
    } else if (this.isSelected) {
      // 选中状态：蓝色圆圈
      this.statusIcon.circle(0, 0, 10)
      this.statusIcon.stroke({ width: 2, color: 0x3B82F6 })
    }
  }
  
  /**
   * 获取智能体数据
   */
  getAgentData(): AgentBrief {
    return this.agentData
  }
  
  /**
   * 获取智能体ID
   */
  getAgentId(): string {
    return this.agentData.id
  }
  
  /**
   * 更新智能体数据
   */
  updateAgentData(agent: AgentBrief): void {
    this.agentData = agent
    this.nameLabel.text = agent.name
  }
  
  /**
   * 是否正在移动
   */
  getIsMoving(): boolean {
    return this.isMoving
  }
}

/**
 * 智能体精灵管理器
 */
export class AgentManager {
  private agents: Map<string, AgentSprite> = new Map()
  private container: Container
  private tweenManager: TweenManager | null = null
  
  // 位置缓存（用于在同一地点的智能体分散）
  private locationPositions: Map<string, { agents: Set<string>; positions: Map<string, { x: number; y: number }> }> = new Map()
  
  constructor(agentLayer: Container) {
    this.container = agentLayer
  }
  
  /**
   * 设置补间管理器
   */
  setTweenManager(tweenManager: TweenManager): void {
    this.tweenManager = tweenManager
  }
  
  /**
   * 添加或更新智能体
   */
  addOrUpdate(agent: AgentBrief, locationIsoX: number, locationIsoY: number): AgentSprite {
    let sprite = this.agents.get(agent.id)
    
    if (sprite) {
      sprite.updateAgentData(agent)
      
      // 如果位置变化，移动到新位置
      const targetPos = this.getAgentPosition(agent.id, agent.current_location, locationIsoX, locationIsoY)
      
      if (this.tweenManager && !sprite.getIsMoving()) {
        // 使用补间动画移动
        sprite.moveTo(targetPos.x, targetPos.y, this.tweenManager, 0.8)
      }
    } else {
      sprite = new AgentSprite(agent)
      
      // 计算初始位置
      const pos = this.getAgentPosition(agent.id, agent.current_location, locationIsoX, locationIsoY)
      sprite.setPosition(pos.x, pos.y)
      
      this.agents.set(agent.id, sprite)
      this.container.addChild(sprite)
    }
    
    return sprite
  }
  
  /**
   * 计算智能体在地点内的位置（分散显示）
   */
  private getAgentPosition(
    agentId: string,
    locationName: string,
    locationIsoX: number,
    locationIsoY: number
  ): { x: number; y: number } {
    // 获取或创建地点位置缓存
    let locData = this.locationPositions.get(locationName)
    if (!locData) {
      locData = { agents: new Set(), positions: new Map() }
      this.locationPositions.set(locationName, locData)
    }
    
    // 检查是否已有缓存位置
    const cached = locData.positions.get(agentId)
    if (cached && locData.agents.has(agentId)) {
      return cached
    }
    
    // 计算新位置（在地点周围随机分散）
    const offsetRange = 20
    const offsetX = (Math.random() - 0.5) * offsetRange
    const offsetY = (Math.random() - 0.5) * offsetRange
    
    const pos = {
      x: locationIsoX + offsetX,
      y: locationIsoY + offsetY,
    }
    
    // 缓存位置
    locData.agents.add(agentId)
    locData.positions.set(agentId, pos)
    
    return pos
  }
  
  /**
   * 移除智能体
   */
  remove(agentId: string): void {
    const sprite = this.agents.get(agentId)
    if (sprite) {
      this.container.removeChild(sprite)
      sprite.destroy()
      this.agents.delete(agentId)
    }
    
    // 清理位置缓存
    this.locationPositions.forEach(locData => {
      locData.agents.delete(agentId)
      locData.positions.delete(agentId)
    })
  }
  
  /**
   * 获取智能体精灵
   */
  get(agentId: string): AgentSprite | undefined {
    return this.agents.get(agentId)
  }
  
  /**
   * 更新所有智能体动画
   */
  update(deltaTime: number): void {
    this.agents.forEach(sprite => {
      sprite.update(deltaTime)
    })
  }
  
  /**
   * 设置选中的智能体
   */
  setSelected(agentId: string | null): void {
    this.agents.forEach((sprite, id) => {
      sprite.setSelected(id === agentId)
    })
  }
  
  /**
   * 设置跟随的智能体
   */
  setFollowing(agentId: string | null): void {
    this.agents.forEach((sprite, id) => {
      sprite.setFollowing(id === agentId)
    })
  }
  
  /**
   * 设置聊天状态
   */
  setChattingAgents(chattingIds: Set<string>): void {
    this.agents.forEach((sprite, id) => {
      sprite.setChatting(chattingIds.has(id))
    })
  }
  
  /**
   * 清除所有
   */
  clear(): void {
    this.agents.forEach(sprite => {
      this.container.removeChild(sprite)
      sprite.destroy()
    })
    this.agents.clear()
    this.locationPositions.clear()
  }
  
  /**
   * 获取所有智能体
   */
  getAll(): AgentSprite[] {
    return Array.from(this.agents.values())
  }
  
  /**
   * 检查点是否命中某个智能体
   */
  hitTest(worldX: number, worldY: number, hitRadius: number = 15): AgentSprite | null {
    for (const sprite of this.agents.values()) {
      const dx = sprite.x - worldX
      const dy = sprite.y - worldY
      const dist = Math.sqrt(dx * dx + dy * dy)
      
      if (dist < hitRadius) {
        return sprite
      }
    }
    return null
  }
}
