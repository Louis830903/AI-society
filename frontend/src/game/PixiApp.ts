/**
 * PixiJS 应用管理器
 * 
 * 单例模式管理 PIXI.Application 实例
 * 配置像素渲染模式（关闭抗锯齿）
 */

import { Application, Container } from 'pixi.js'
import { LayerManager } from './LayerManager'
import { DaylightSystem } from './DaylightSystem'
import { WeatherSystem } from './WeatherSystem'
import { TweenManager } from './TweenManager'

export interface PixiAppConfig {
  width: number
  height: number
  backgroundColor: number
  resolution?: number
  antialias?: boolean
}

/**
 * PixiJS 应用管理器单例
 * 
 * 注意：为了兼容 React StrictMode 的双重调用，
 * 销毁时使用安全方式，避免崩溃
 */
class PixiAppManager {
  private static instance: PixiAppManager
  
  private app: Application | null = null
  private _layerManager: LayerManager | null = null
  private _daylightSystem: DaylightSystem | null = null
  private _weatherSystem: WeatherSystem | null = null
  private _tweenManager: TweenManager | null = null
  private initialized = false
  private initializing = false  // 防止重复初始化
  private destroyed = false     // 标记是否被销毁，用于中止正在进行的初始化
  private initPromise: Promise<Application | null> | null = null  // 缓存初始化 Promise
  
  // 外部更新回调列表
  private updateCallbacks: Array<(deltaTime: number) => void> = []
  
  private constructor() {}
  
  static getInstance(): PixiAppManager {
    if (!PixiAppManager.instance) {
      PixiAppManager.instance = new PixiAppManager()
    }
    return PixiAppManager.instance
  }
  
  /**
   * 初始化 PixiJS 应用
   */
  async init(config: PixiAppConfig): Promise<Application> {
    // 重置销毁标志
    this.destroyed = false
    
    // 已初始化，直接返回
    if (this.initialized && this.app) {
      return this.app
    }
    
    // 正在初始化，等待并返回结果
    if (this.initializing && this.initPromise) {
      const result = await this.initPromise
      if (result) return result
      // 如果返回 null，说明被销毁了，重新初始化
    }
    
    this.initializing = true
    
    // 创建初始化 Promise
    this.initPromise = this._doInit(config)
    
    const result = await this.initPromise
    if (!result) {
      throw new Error('PixiJS 初始化被中止')
    }
    return result
  }
  
  /**
   * 实际执行初始化
   */
  private async _doInit(config: PixiAppConfig): Promise<Application | null> {
    try {
      // 创建 PixiJS 8 应用
      const app = new Application()
      
      await app.init({
        width: config.width,
        height: config.height,
        backgroundColor: config.backgroundColor,
        resolution: config.resolution ?? window.devicePixelRatio,
        autoDensity: true,
        antialias: false,  // 关闭抗锯齿以保持像素风格
        roundPixels: true, // 像素对齐
      })
      
      // 检查是否被销毁
      if (this.destroyed) {
        // 销毁刚创建的 app
        try {
          app.destroy(false)
        } catch (e) {
          // 忽略
        }
        return null
      }
      
      // 保存 app 引用
      this.app = app
      
      // 初始化层管理器
      this._layerManager = new LayerManager(this.app.stage)
      
      // 初始化昼夜系统
      this._daylightSystem = new DaylightSystem()
      
      // 初始化天气系统
      this._weatherSystem = new WeatherSystem(this._layerManager.effectLayer)
      
      // 初始化补间管理器
      this._tweenManager = new TweenManager()
      
      // 设置游戏循环
      this.app.ticker.add((ticker) => {
        const deltaTime = ticker.deltaMS / 1000  // 转换为秒
        this._tweenManager?.update(deltaTime)
        this._weatherSystem?.update(deltaTime)
        
        // 调用外部注册的更新回调
        for (const callback of this.updateCallbacks) {
          callback(deltaTime)
        }
      })
      
      this.initialized = true
      return this.app
    } catch (e) {
      console.error('[PixiApp] init error:', e)
      return null
    } finally {
      this.initializing = false
      this.initPromise = null
    }
  }
  
  /**
   * 获取 PixiJS 应用实例
   */
  getApp(): Application | null {
    return this.app
  }
  
  /**
   * 获取主舞台
   */
  getStage(): Container | null {
    return this.app?.stage ?? null
  }
  
  /**
   * 获取层管理器
   */
  get layerManager(): LayerManager | null {
    return this._layerManager
  }
  
  /**
   * 获取昼夜系统
   */
  get daylightSystem(): DaylightSystem | null {
    return this._daylightSystem
  }
  
  /**
   * 获取天气系统
   */
  get weatherSystem(): WeatherSystem | null {
    return this._weatherSystem
  }
  
  /**
   * 获取补间管理器
   */
  get tweenManager(): TweenManager | null {
    return this._tweenManager
  }
  
  /**
   * 注册更新回调（每帧调用）
   */
  addUpdateCallback(callback: (deltaTime: number) => void): void {
    if (!this.updateCallbacks.includes(callback)) {
      this.updateCallbacks.push(callback)
    }
  }
  
  /**
   * 移除更新回调
   */
  removeUpdateCallback(callback: (deltaTime: number) => void): void {
    const index = this.updateCallbacks.indexOf(callback)
    if (index !== -1) {
      this.updateCallbacks.splice(index, 1)
    }
  }
  
  /**
   * 调整画布尺寸
   */
  resize(width: number, height: number): void {
    if (!this.app) return
    
    this.app.renderer.resize(width, height)
    
    // 更新天气系统边界
    this._weatherSystem?.setBounds(width, height)
  }
  
  /**
   * 更新背景色（昼夜系统使用）
   */
  setBackgroundColor(color: number): void {
    if (!this.app) return
    this.app.renderer.background.color = color
  }
  
  /**
   * 获取画布 DOM 元素
   */
  getCanvas(): HTMLCanvasElement | null {
    return this.app?.canvas ?? null
  }
  
  /**
   * 销毁应用
   * 使用 try-catch 安全处理，兼容 React StrictMode
   */
  destroy(): void {
    // 标记为已销毁，中止正在进行的初始化
    this.destroyed = true
    
    // 清空回调列表
    this.updateCallbacks = []
    
    if (this.app) {
      try {
        // 先销毁子系统
        this._weatherSystem?.destroy()
        this._tweenManager?.clear()
        
        // 停止 ticker
        if (this.app.ticker) {
          this.app.ticker.stop()
        }
        
        // 安全销毁 PixiJS 应用
        // 使用简化的销毁选项避免内部错误
        this.app.destroy(false)
      } catch (e) {
        // React StrictMode 下可能会出现错误，静默忽略
        console.warn('[PixiApp] destroy warning:', e)
      }
      
      this.app = null
      this._layerManager = null
      this._daylightSystem = null
      this._weatherSystem = null
      this._tweenManager = null
      this.initialized = false
    }
  }
  
  /**
   * 检查是否已初始化
   */
  isInitialized(): boolean {
    return this.initialized
  }
}

// 导出单例访问
export const pixiApp = PixiAppManager.getInstance()

// 导出类型
export type { PixiAppManager }
