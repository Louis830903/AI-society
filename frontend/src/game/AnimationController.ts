/**
 * 动画控制器
 * 
 * 管理精灵动画状态机
 */

import { ANIMATION_CONFIG } from './assets'

/**
 * 动画状态
 */
export enum AnimationState {
  IDLE = 'idle',
  WALKING = 'walking',
  WORKING = 'working',
  CHATTING = 'chatting',
}

/**
 * 动画方向
 */
export type AnimationDirection = 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW'

/**
 * 动画帧数据
 */
interface AnimationFrameData {
  offsetX: number
  offsetY: number
  scaleX: number
}

/**
 * 动画控制器
 * 
 * 使用程序生成的帧动画
 */
export class AnimationController {
  private state: AnimationState = AnimationState.IDLE
  private direction: AnimationDirection = 'S'
  private currentFrame: number = 0
  private frameTime: number = 0
  private frameDuration: number = 1 / ANIMATION_CONFIG.fps
  
  // 动画回调
  private onFrameChange?: (frame: number, state: AnimationState) => void
  
  constructor() {}
  
  /**
   * 设置帧变化回调
   */
  setOnFrameChange(callback: (frame: number, state: AnimationState) => void): void {
    this.onFrameChange = callback
  }
  
  /**
   * 更新动画
   * @param deltaTime 帧时间差（秒）
   */
  update(deltaTime: number): void {
    this.frameTime += deltaTime
    
    if (this.frameTime >= this.frameDuration) {
      this.frameTime -= this.frameDuration
      this.advanceFrame()
    }
  }
  
  /**
   * 推进帧
   */
  private advanceFrame(): void {
    const maxFrames = this.getFrameCount()
    this.currentFrame = (this.currentFrame + 1) % maxFrames
    this.onFrameChange?.(this.currentFrame, this.state)
  }
  
  /**
   * 获取当前状态的帧数
   */
  private getFrameCount(): number {
    switch (this.state) {
      case AnimationState.IDLE:
        return ANIMATION_CONFIG.idleFrames
      case AnimationState.WALKING:
        return ANIMATION_CONFIG.walkFrames
      case AnimationState.WORKING:
        return ANIMATION_CONFIG.workFrames
      case AnimationState.CHATTING:
        return ANIMATION_CONFIG.idleFrames
      default:
        return 2
    }
  }
  
  /**
   * 设置动画状态
   */
  setState(state: AnimationState): void {
    if (this.state !== state) {
      this.state = state
      this.currentFrame = 0
      this.frameTime = 0
    }
  }
  
  /**
   * 设置方向
   */
  setDirection(direction: AnimationDirection): void {
    this.direction = direction
  }
  
  /**
   * 根据目标位置设置方向
   */
  setDirectionToTarget(fromX: number, fromY: number, toX: number, toY: number): void {
    const angle = Math.atan2(toY - fromY, toX - fromX)
    const deg = (angle * 180 / Math.PI + 360) % 360
    
    if (deg >= 337.5 || deg < 22.5) this.direction = 'E'
    else if (deg >= 22.5 && deg < 67.5) this.direction = 'SE'
    else if (deg >= 67.5 && deg < 112.5) this.direction = 'S'
    else if (deg >= 112.5 && deg < 157.5) this.direction = 'SW'
    else if (deg >= 157.5 && deg < 202.5) this.direction = 'W'
    else if (deg >= 202.5 && deg < 247.5) this.direction = 'NW'
    else if (deg >= 247.5 && deg < 292.5) this.direction = 'N'
    else this.direction = 'NE'
  }
  
  /**
   * 获取当前状态
   */
  getState(): AnimationState {
    return this.state
  }
  
  /**
   * 获取当前方向
   */
  getDirection(): AnimationDirection {
    return this.direction
  }
  
  /**
   * 获取当前帧
   */
  getCurrentFrame(): number {
    return this.currentFrame
  }
  
  /**
   * 获取帧数据（用于程序生成动画）
   */
  getFrameData(): AnimationFrameData {
    switch (this.state) {
      case AnimationState.IDLE:
        // 呼吸动画：轻微上下移动
        return {
          offsetX: 0,
          offsetY: this.currentFrame === 0 ? 0 : -1,
          scaleX: this.getDirectionScaleX(),
        }
        
      case AnimationState.WALKING:
        // 行走动画：上下弹跳
        const bounce = [0, -2, 0, -2][this.currentFrame] || 0
        return {
          offsetX: 0,
          offsetY: bounce,
          scaleX: this.getDirectionScaleX(),
        }
        
      case AnimationState.WORKING:
        // 工作动画：轻微晃动
        const workOffset = [0, 1, 0, -1][this.currentFrame] || 0
        return {
          offsetX: workOffset,
          offsetY: 0,
          scaleX: this.getDirectionScaleX(),
        }
        
      case AnimationState.CHATTING:
        // 聊天动画：轻微点头
        return {
          offsetX: 0,
          offsetY: this.currentFrame === 0 ? 0 : -1,
          scaleX: this.getDirectionScaleX(),
        }
        
      default:
        return { offsetX: 0, offsetY: 0, scaleX: 1 }
    }
  }
  
  /**
   * 根据方向获取X缩放（用于水平翻转）
   */
  private getDirectionScaleX(): number {
    // 面向左侧的方向需要翻转
    if (this.direction === 'W' || this.direction === 'NW' || this.direction === 'SW') {
      return -1
    }
    return 1
  }
}
