/**
 * 聊天气泡精灵类
 * 
 * 在地图上智能体头顶显示的对话气泡
 * 像漫画气泡一样展示最新对话内容
 */

import { Container, Graphics, Text, TextStyle } from 'pixi.js'

/**
 * 聊天气泡配置
 */
export interface ChatBubbleConfig {
  /** 最大文字长度 */
  maxLength?: number
  /** 气泡最大宽度 */
  maxWidth?: number
  /** 显示时长（毫秒） */
  displayDuration?: number
  /** 淡出时长（毫秒） */
  fadeOutDuration?: number
  /** 背景色 */
  backgroundColor?: number
  /** 文字颜色 */
  textColor?: number
  /** 气泡圆角半径 */
  cornerRadius?: number
  /** 气泡内边距 */
  padding?: number
}

const DEFAULT_CONFIG: Required<ChatBubbleConfig> = {
  maxLength: 30,
  maxWidth: 150,
  displayDuration: 4000,
  fadeOutDuration: 500,
  backgroundColor: 0xFFFFFF,
  textColor: 0x1e293b,
  cornerRadius: 8,
  padding: 8,
}

/**
 * 聊天气泡精灵
 */
export class ChatBubble extends Container {
  private config: Required<ChatBubbleConfig>
  
  // 组件
  private bubbleGraphics: Graphics
  private tailGraphics: Graphics
  private textLabel: Text
  
  // 状态
  private content: string = ''
  private displayTimer: number | null = null
  private fadeOutTimer: number | null = null
  private isFadingOut: boolean = false
  
  // 关联的智能体ID
  private agentId: string
  
  constructor(agentId: string, config: ChatBubbleConfig = {}) {
    super()
    this.agentId = agentId
    this.config = { ...DEFAULT_CONFIG, ...config }
    
    // 创建组件
    this.bubbleGraphics = new Graphics()
    this.tailGraphics = new Graphics()
    this.textLabel = this.createTextLabel()
    
    // 添加到容器（注意顺序：先尾巴再气泡再文字）
    this.addChild(this.tailGraphics)
    this.addChild(this.bubbleGraphics)
    this.addChild(this.textLabel)
    
    // 初始隐藏
    this.visible = false
    this.alpha = 0
  }
  
  /**
   * 创建文字标签
   */
  private createTextLabel(): Text {
    const style = new TextStyle({
      fontSize: 11,
      fill: this.config.textColor,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      wordWrap: true,
      wordWrapWidth: this.config.maxWidth - this.config.padding * 2,
      lineHeight: 14,
    })
    
    const text = new Text({ text: '', style })
    text.anchor.set(0.5, 1)
    
    return text
  }
  
  /**
   * 截断文字
   */
  private truncateText(text: string): string {
    if (text.length <= this.config.maxLength) {
      return text
    }
    return text.substring(0, this.config.maxLength - 3) + '...'
  }
  
  /**
   * 绘制像素风格气泡
   */
  private drawBubble(): void {
    this.bubbleGraphics.clear()
    this.tailGraphics.clear()
    
    // 计算气泡尺寸
    const textBounds = this.textLabel.getBounds()
    const bubbleWidth = Math.min(
      this.config.maxWidth,
      Math.max(60, textBounds.width + this.config.padding * 2)
    )
    const bubbleHeight = textBounds.height + this.config.padding * 2
    
    // 气泡位置（居中，在人物头顶上方）
    const bubbleX = -bubbleWidth / 2
    const bubbleY = -bubbleHeight - 12  // 12是尾巴高度
    
    // 像素风格配色
    const bgColor = this.config.backgroundColor
    const borderColor = 0x374151  // 深灰边框
    const shadowColor = 0x1f2937  // 更深的阴影
    const highlightColor = 0xf9fafb  // 高光色
    
    // 绘制像素风格气泡主体
    // 1. 外部阴影（向右下偏移2像素）
    this.bubbleGraphics.rect(bubbleX + 2, bubbleY + 2, bubbleWidth, bubbleHeight)
    this.bubbleGraphics.fill({ color: shadowColor, alpha: 0.3 })
    
    // 2. 主边框（深色）
    this.bubbleGraphics.rect(bubbleX - 1, bubbleY - 1, bubbleWidth + 2, bubbleHeight + 2)
    this.bubbleGraphics.fill({ color: borderColor })
    
    // 3. 气泡主体背景
    this.bubbleGraphics.rect(bubbleX, bubbleY, bubbleWidth, bubbleHeight)
    this.bubbleGraphics.fill({ color: bgColor })
    
    // 4. 顶部高光线（像素风格）
    this.bubbleGraphics.rect(bubbleX + 2, bubbleY + 1, bubbleWidth - 4, 2)
    this.bubbleGraphics.fill({ color: highlightColor, alpha: 0.5 })
    
    // 5. 左侧高光线
    this.bubbleGraphics.rect(bubbleX + 1, bubbleY + 2, 2, bubbleHeight - 4)
    this.bubbleGraphics.fill({ color: highlightColor, alpha: 0.3 })
    
    // 6. 底部阴影线
    this.bubbleGraphics.rect(bubbleX + 2, bubbleY + bubbleHeight - 3, bubbleWidth - 4, 2)
    this.bubbleGraphics.fill({ color: borderColor, alpha: 0.2 })
    
    // 7. 右侧阴影线
    this.bubbleGraphics.rect(bubbleX + bubbleWidth - 3, bubbleY + 2, 2, bubbleHeight - 4)
    this.bubbleGraphics.fill({ color: borderColor, alpha: 0.2 })
    
    // 8. 角落像素处理（圆角效果）
    // 左上角
    this.bubbleGraphics.rect(bubbleX, bubbleY, 2, 2)
    this.bubbleGraphics.fill({ color: borderColor })
    this.bubbleGraphics.rect(bubbleX + 1, bubbleY + 1, 1, 1)
    this.bubbleGraphics.fill({ color: bgColor })
    
    // 右上角
    this.bubbleGraphics.rect(bubbleX + bubbleWidth - 2, bubbleY, 2, 2)
    this.bubbleGraphics.fill({ color: borderColor })
    this.bubbleGraphics.rect(bubbleX + bubbleWidth - 2, bubbleY + 1, 1, 1)
    this.bubbleGraphics.fill({ color: bgColor })
    
    // 左下角
    this.bubbleGraphics.rect(bubbleX, bubbleY + bubbleHeight - 2, 2, 2)
    this.bubbleGraphics.fill({ color: borderColor })
    this.bubbleGraphics.rect(bubbleX + 1, bubbleY + bubbleHeight - 2, 1, 1)
    this.bubbleGraphics.fill({ color: bgColor })
    
    // 右下角
    this.bubbleGraphics.rect(bubbleX + bubbleWidth - 2, bubbleY + bubbleHeight - 2, 2, 2)
    this.bubbleGraphics.fill({ color: borderColor })
    this.bubbleGraphics.rect(bubbleX + bubbleWidth - 2, bubbleY + bubbleHeight - 2, 1, 1)
    this.bubbleGraphics.fill({ color: bgColor })
    
    // 绘制像素风格尾巴（指向人物的三角形）
    const tailCenterX = 0
    const tailTopY = bubbleY + bubbleHeight
    const tailHeight = 8
    const tailWidth = 8
    
    // 尾巴阴影
    this.tailGraphics.moveTo(tailCenterX + 1, tailTopY)
    this.tailGraphics.lineTo(tailCenterX + tailWidth / 2 + 2, tailTopY + tailHeight + 1)
    this.tailGraphics.lineTo(tailCenterX + tailWidth / 2 + 1, tailTopY)
    this.tailGraphics.closePath()
    this.tailGraphics.fill({ color: shadowColor, alpha: 0.3 })
    
    // 尾巴边框
    this.tailGraphics.moveTo(tailCenterX - tailWidth / 2 - 1, tailTopY - 1)
    this.tailGraphics.lineTo(tailCenterX, tailTopY + tailHeight + 1)
    this.tailGraphics.lineTo(tailCenterX + tailWidth / 2 + 1, tailTopY - 1)
    this.tailGraphics.closePath()
    this.tailGraphics.fill({ color: borderColor })
    
    // 尾巴主体
    this.tailGraphics.moveTo(tailCenterX - tailWidth / 2, tailTopY)
    this.tailGraphics.lineTo(tailCenterX, tailTopY + tailHeight)
    this.tailGraphics.lineTo(tailCenterX + tailWidth / 2, tailTopY)
    this.tailGraphics.closePath()
    this.tailGraphics.fill({ color: bgColor })
    
    // 尾巴左侧高光
    this.tailGraphics.moveTo(tailCenterX - tailWidth / 2 + 1, tailTopY)
    this.tailGraphics.lineTo(tailCenterX - 1, tailTopY + tailHeight - 2)
    this.tailGraphics.stroke({ width: 1, color: highlightColor, alpha: 0.4 })
    
    // 文字位置
    this.textLabel.x = 0
    this.textLabel.y = bubbleY + bubbleHeight - this.config.padding
  }
  
  /**
   * 显示消息
   */
  showMessage(content: string, speakerName?: string): void {
    // 清除之前的定时器
    this.clearTimers()
    
    // 设置内容
    const displayContent = speakerName 
      ? `${speakerName}: ${this.truncateText(content)}`
      : this.truncateText(content)
    
    this.content = displayContent
    this.textLabel.text = displayContent
    
    // 绘制气泡
    this.drawBubble()
    
    // 显示并淡入
    this.visible = true
    this.isFadingOut = false
    this.alpha = 0
    
    // 简单的淡入动画
    this.fadeIn()
    
    // 设置自动隐藏定时器
    this.displayTimer = window.setTimeout(() => {
      this.fadeOut()
    }, this.config.displayDuration)
  }
  
  /**
   * 淡入动画
   */
  private fadeIn(): void {
    const startTime = Date.now()
    const duration = 200  // 淡入持续时间
    
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      
      this.alpha = progress
      
      if (progress < 1 && !this.isFadingOut) {
        requestAnimationFrame(animate)
      }
    }
    
    requestAnimationFrame(animate)
  }
  
  /**
   * 淡出动画
   */
  private fadeOut(): void {
    if (this.isFadingOut) return
    
    this.isFadingOut = true
    const startTime = Date.now()
    const startAlpha = this.alpha
    
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / this.config.fadeOutDuration, 1)
      
      this.alpha = startAlpha * (1 - progress)
      
      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        this.visible = false
        this.isFadingOut = false
      }
    }
    
    requestAnimationFrame(animate)
  }
  
  /**
   * 立即隐藏
   */
  hide(): void {
    this.clearTimers()
    this.visible = false
    this.alpha = 0
    this.isFadingOut = false
  }
  
  /**
   * 清除定时器
   */
  private clearTimers(): void {
    if (this.displayTimer) {
      clearTimeout(this.displayTimer)
      this.displayTimer = null
    }
    if (this.fadeOutTimer) {
      clearTimeout(this.fadeOutTimer)
      this.fadeOutTimer = null
    }
  }
  
  /**
   * 获取关联的智能体ID
   */
  getAgentId(): string {
    return this.agentId
  }
  
  /**
   * 获取当前内容
   */
  getContent(): string {
    return this.content
  }
  
  /**
   * 是否正在显示
   */
  isShowing(): boolean {
    return this.visible && !this.isFadingOut
  }
  
  /**
   * 更新位置（跟随智能体）
   */
  updatePosition(x: number, y: number): void {
    this.x = x
    this.y = y - 25  // 在智能体头顶上方
  }
  
  /**
   * 销毁
   */
  destroy(): void {
    this.clearTimers()
    super.destroy({ children: true })
  }
}

/**
 * 聊天气泡管理器
 * 
 * 管理地图上所有的聊天气泡
 */
export class ChatBubbleManager {
  private bubbles: Map<string, ChatBubble> = new Map()
  private container: Container
  private config: ChatBubbleConfig
  
  constructor(container: Container, config: ChatBubbleConfig = {}) {
    this.container = container
    this.config = config
  }
  
  /**
   * 显示智能体的聊天气泡
   */
  showBubble(agentId: string, content: string, speakerName?: string): ChatBubble {
    let bubble = this.bubbles.get(agentId)
    
    if (!bubble) {
      // 创建新气泡
      bubble = new ChatBubble(agentId, this.config)
      this.bubbles.set(agentId, bubble)
      this.container.addChild(bubble)
    }
    
    bubble.showMessage(content, speakerName)
    return bubble
  }
  
  /**
   * 隐藏智能体的聊天气泡
   */
  hideBubble(agentId: string): void {
    const bubble = this.bubbles.get(agentId)
    if (bubble) {
      bubble.hide()
    }
  }
  
  /**
   * 更新气泡位置（跟随智能体）
   */
  updateBubblePosition(agentId: string, x: number, y: number): void {
    const bubble = this.bubbles.get(agentId)
    if (bubble) {
      bubble.updatePosition(x, y)
    }
  }
  
  /**
   * 获取智能体的气泡
   */
  getBubble(agentId: string): ChatBubble | undefined {
    return this.bubbles.get(agentId)
  }
  
  /**
   * 移除智能体的气泡
   */
  removeBubble(agentId: string): void {
    const bubble = this.bubbles.get(agentId)
    if (bubble) {
      bubble.destroy()
      this.bubbles.delete(agentId)
    }
  }
  
  /**
   * 清除所有气泡
   */
  clearAll(): void {
    for (const bubble of this.bubbles.values()) {
      bubble.destroy()
    }
    this.bubbles.clear()
  }
  
  /**
   * 获取所有活跃气泡数量
   */
  getActiveCount(): number {
    let count = 0
    for (const bubble of this.bubbles.values()) {
      if (bubble.isShowing()) {
        count++
      }
    }
    return count
  }
  
  /**
   * 销毁管理器
   */
  destroy(): void {
    this.clearAll()
  }
}
