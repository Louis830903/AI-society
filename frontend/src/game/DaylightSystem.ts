/**
 * 昼夜系统
 * 
 * 根据游戏时间调整:
 * - 背景色（天空颜色）
 * - 环境光强度
 * - 精灵着色
 */

import { getDaylightConfig, DaylightConfig } from './assets'

/**
 * 昼夜系统事件类型
 */
export type DaylightEventType = 'dawn' | 'sunrise' | 'noon' | 'sunset' | 'dusk' | 'night'

/**
 * 昼夜系统回调
 */
export interface DaylightCallbacks {
  onBackgroundChange?: (color: number) => void
  onTintChange?: (tint: number) => void
  onTimeOfDayChange?: (event: DaylightEventType) => void
  onNightStart?: () => void
  onDayStart?: () => void
}

/**
 * 昼夜系统
 */
export class DaylightSystem {
  private currentHour: number = 12
  private currentConfig: DaylightConfig
  private callbacks: DaylightCallbacks = {}
  private isNight: boolean = false
  
  constructor() {
    this.currentConfig = getDaylightConfig(12)
  }
  
  /**
   * 设置回调
   */
  setCallbacks(callbacks: DaylightCallbacks): void {
    this.callbacks = callbacks
  }
  
  /**
   * 更新时间
   * @param hour 小时（0-23，支持小数）
   */
  updateTime(hour: number): void {
    const prevHour = this.currentHour
    this.currentHour = hour
    
    // 获取新的光照配置
    this.currentConfig = getDaylightConfig(hour)
    
    // 触发回调
    this.callbacks.onBackgroundChange?.(this.currentConfig.sky)
    this.callbacks.onTintChange?.(this.currentConfig.tint)
    
    // 检查昼夜变化
    const wasNight = this.isNight
    this.isNight = hour >= 19 || hour < 6
    
    if (!wasNight && this.isNight) {
      this.callbacks.onNightStart?.()
    } else if (wasNight && !this.isNight) {
      this.callbacks.onDayStart?.()
    }
    
    // 检查时间段变化
    this.checkTimeOfDayEvent(prevHour, hour)
  }
  
  /**
   * 检查时间段事件
   */
  private checkTimeOfDayEvent(prevHour: number, newHour: number): void {
    const events: { hour: number; event: DaylightEventType }[] = [
      { hour: 5, event: 'dawn' },
      { hour: 7, event: 'sunrise' },
      { hour: 12, event: 'noon' },
      { hour: 17, event: 'sunset' },
      { hour: 19, event: 'dusk' },
      { hour: 21, event: 'night' },
    ]
    
    for (const { hour, event } of events) {
      if (prevHour < hour && newHour >= hour) {
        this.callbacks.onTimeOfDayChange?.(event)
        break
      }
    }
  }
  
  /**
   * 获取当前天空颜色
   */
  getSkyColor(): number {
    return this.currentConfig.sky
  }
  
  /**
   * 获取当前环境光强度
   */
  getAmbient(): number {
    return this.currentConfig.ambient
  }
  
  /**
   * 获取当前着色
   */
  getTint(): number {
    return this.currentConfig.tint
  }
  
  /**
   * 获取完整配置
   */
  getConfig(): DaylightConfig {
    return { ...this.currentConfig }
  }
  
  /**
   * 是否是夜晚
   */
  isNightTime(): boolean {
    return this.isNight
  }
  
  /**
   * 获取当前时间段描述
   */
  getTimeOfDayName(): string {
    const hour = this.currentHour
    if (hour >= 5 && hour < 7) return '黎明'
    if (hour >= 7 && hour < 10) return '早晨'
    if (hour >= 10 && hour < 12) return '上午'
    if (hour >= 12 && hour < 14) return '正午'
    if (hour >= 14 && hour < 17) return '下午'
    if (hour >= 17 && hour < 19) return '黄昏'
    if (hour >= 19 && hour < 21) return '傍晚'
    return '夜晚'
  }
  
  /**
   * 计算建筑灯光强度
   * 夜间返回1，白天返回0
   */
  getBuildingLightIntensity(): number {
    const hour = this.currentHour
    
    if (hour >= 6 && hour < 18) {
      return 0  // 白天不亮灯
    } else if (hour >= 18 && hour < 19) {
      return (hour - 18)  // 18-19点渐亮
    } else if (hour >= 19 || hour < 5) {
      return 1  // 夜间全亮
    } else if (hour >= 5 && hour < 6) {
      return 1 - (hour - 5)  // 5-6点渐灭
    }
    
    return 0
  }
  
  /**
   * 将颜色转为CSS字符串
   */
  static colorToCSS(color: number): string {
    const r = (color >> 16) & 0xFF
    const g = (color >> 8) & 0xFF
    const b = color & 0xFF
    return `rgb(${r}, ${g}, ${b})`
  }
  
  /**
   * 将颜色转为十六进制字符串
   */
  static colorToHex(color: number): string {
    return '#' + color.toString(16).padStart(6, '0')
  }
}
