/**
 * 补间动画管理器
 * 
 * 提供平滑的位置、缩放、旋转等动画
 */

import { Container } from 'pixi.js'

/**
 * 缓动函数类型
 */
export type EaseFunction = (t: number) => number

/**
 * 预定义缓动函数
 */
export const Easing = {
  linear: (t: number) => t,
  
  easeInQuad: (t: number) => t * t,
  easeOutQuad: (t: number) => t * (2 - t),
  easeInOutQuad: (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  
  easeInCubic: (t: number) => t * t * t,
  easeOutCubic: (t: number) => (--t) * t * t + 1,
  easeInOutCubic: (t: number) => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  
  easeInSine: (t: number) => 1 - Math.cos((t * Math.PI) / 2),
  easeOutSine: (t: number) => Math.sin((t * Math.PI) / 2),
  easeInOutSine: (t: number) => -(Math.cos(Math.PI * t) - 1) / 2,
}

/**
 * 补间动画配置
 */
export interface TweenConfig {
  target: Container | any
  duration: number          // 持续时间（秒）
  ease?: EaseFunction       // 缓动函数
  onUpdate?: (progress: number) => void
  onComplete?: () => void
  
  // 动画属性
  x?: number
  y?: number
  scaleX?: number
  scaleY?: number
  rotation?: number
  alpha?: number
}

/**
 * 活跃的补间动画
 */
interface ActiveTween {
  config: TweenConfig
  startValues: Record<string, number>
  endValues: Record<string, number>
  elapsed: number
  id: string
}

/**
 * 补间动画管理器
 */
export class TweenManager {
  private tweens: Map<string, ActiveTween> = new Map()
  private tweenIdCounter = 0
  
  /**
   * 创建补间动画
   * @returns 动画ID（可用于取消）
   */
  create(config: TweenConfig): string {
    const id = `tween_${++this.tweenIdCounter}`
    
    const target = config.target
    const startValues: Record<string, number> = {}
    const endValues: Record<string, number> = {}
    
    // 记录起始值和目标值
    if (config.x !== undefined) {
      startValues.x = target.x ?? 0
      endValues.x = config.x
    }
    if (config.y !== undefined) {
      startValues.y = target.y ?? 0
      endValues.y = config.y
    }
    if (config.scaleX !== undefined) {
      startValues.scaleX = target.scale?.x ?? 1
      endValues.scaleX = config.scaleX
    }
    if (config.scaleY !== undefined) {
      startValues.scaleY = target.scale?.y ?? 1
      endValues.scaleY = config.scaleY
    }
    if (config.rotation !== undefined) {
      startValues.rotation = target.rotation ?? 0
      endValues.rotation = config.rotation
    }
    if (config.alpha !== undefined) {
      startValues.alpha = target.alpha ?? 1
      endValues.alpha = config.alpha
    }
    
    const tween: ActiveTween = {
      config,
      startValues,
      endValues,
      elapsed: 0,
      id,
    }
    
    this.tweens.set(id, tween)
    return id
  }
  
  /**
   * 移动到目标位置
   */
  moveTo(
    target: Container,
    x: number,
    y: number,
    duration: number,
    ease: EaseFunction = Easing.easeOutQuad,
    onComplete?: () => void
  ): string {
    return this.create({
      target,
      duration,
      x,
      y,
      ease,
      onComplete,
    })
  }
  
  /**
   * 淡入淡出
   */
  fadeTo(
    target: Container,
    alpha: number,
    duration: number,
    ease: EaseFunction = Easing.easeOutQuad,
    onComplete?: () => void
  ): string {
    return this.create({
      target,
      duration,
      alpha,
      ease,
      onComplete,
    })
  }
  
  /**
   * 缩放动画
   */
  scaleTo(
    target: Container,
    scaleX: number,
    scaleY: number,
    duration: number,
    ease: EaseFunction = Easing.easeOutQuad,
    onComplete?: () => void
  ): string {
    return this.create({
      target,
      duration,
      scaleX,
      scaleY,
      ease,
      onComplete,
    })
  }
  
  /**
   * 更新所有动画
   * @param deltaTime 帧时间差（秒）
   */
  update(deltaTime: number): void {
    const completedTweens: string[] = []
    
    this.tweens.forEach((tween, id) => {
      tween.elapsed += deltaTime
      
      const progress = Math.min(tween.elapsed / tween.config.duration, 1)
      const ease = tween.config.ease ?? Easing.linear
      const easedProgress = ease(progress)
      
      const target = tween.config.target
      
      // 更新属性
      for (const key of Object.keys(tween.startValues)) {
        const start = tween.startValues[key]
        const end = tween.endValues[key]
        const current = start + (end - start) * easedProgress
        
        if (key === 'scaleX') {
          target.scale.x = current
        } else if (key === 'scaleY') {
          target.scale.y = current
        } else {
          target[key] = current
        }
      }
      
      // 回调
      tween.config.onUpdate?.(easedProgress)
      
      // 检查是否完成
      if (progress >= 1) {
        completedTweens.push(id)
        tween.config.onComplete?.()
      }
    })
    
    // 移除已完成的动画
    completedTweens.forEach(id => this.tweens.delete(id))
  }
  
  /**
   * 取消指定动画
   */
  cancel(id: string): boolean {
    return this.tweens.delete(id)
  }
  
  /**
   * 取消目标对象的所有动画
   */
  cancelAllFor(target: Container): void {
    const toRemove: string[] = []
    
    this.tweens.forEach((tween, id) => {
      if (tween.config.target === target) {
        toRemove.push(id)
      }
    })
    
    toRemove.forEach(id => this.tweens.delete(id))
  }
  
  /**
   * 清空所有动画
   */
  clear(): void {
    this.tweens.clear()
  }
  
  /**
   * 检查是否有活跃动画
   */
  isAnimating(target?: Container): boolean {
    if (!target) {
      return this.tweens.size > 0
    }
    
    for (const tween of this.tweens.values()) {
      if (tween.config.target === target) {
        return true
      }
    }
    return false
  }
  
  /**
   * 获取活跃动画数量
   */
  getActiveCount(): number {
    return this.tweens.size
  }
}
