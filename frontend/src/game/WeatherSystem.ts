/**
 * 天气系统
 * 
 * 支持的天气类型:
 * - SUNNY: 晴天（无粒子）
 * - CLOUDY: 多云（云朵精灵）
 * - RAINY: 雨天（雨滴粒子）
 */

import { Container, Graphics } from 'pixi.js'
import { WEATHER_CONFIGS, WeatherParticleConfig } from './assets'

/**
 * 天气类型
 */
export type WeatherType = 'sunny' | 'cloudy' | 'rainy'

/**
 * 粒子对象
 */
interface Particle {
  graphics: Graphics
  x: number
  y: number
  speed: number
  size: number
}

/**
 * 云朵对象
 */
interface Cloud {
  graphics: Graphics
  x: number
  y: number
  speed: number
  width: number
}

/**
 * 天气系统
 */
export class WeatherSystem {
  private container: Container
  private particles: Particle[] = []
  private clouds: Cloud[] = []
  private currentWeather: WeatherType = 'sunny'
  
  private boundsWidth: number = 800
  private boundsHeight: number = 600
  
  constructor(effectLayer: Container) {
    this.container = new Container()
    this.container.label = 'weatherContainer'
    effectLayer.addChild(this.container)
  }
  
  /**
   * 设置边界
   */
  setBounds(width: number, height: number): void {
    this.boundsWidth = width
    this.boundsHeight = height
  }
  
  /**
   * 设置天气
   */
  setWeather(type: WeatherType): void {
    if (type === this.currentWeather) return
    
    // 清除当前粒子
    this.clearParticles()
    
    this.currentWeather = type
    
    // 创建新粒子
    switch (type) {
      case 'rainy':
        this.createRainParticles()
        break
      case 'cloudy':
        this.createClouds()
        break
      case 'sunny':
      default:
        // 晴天无粒子
        break
    }
  }
  
  /**
   * 获取当前天气
   */
  getWeather(): WeatherType {
    return this.currentWeather
  }
  
  /**
   * 创建雨滴粒子
   */
  private createRainParticles(): void {
    const config = WEATHER_CONFIGS.rainy
    
    for (let i = 0; i < config.count; i++) {
      const particle = this.createRainDrop(config)
      this.particles.push(particle)
      this.container.addChild(particle.graphics)
    }
  }
  
  /**
   * 创建单个雨滴
   */
  private createRainDrop(config: WeatherParticleConfig): Particle {
    const size = config.size.min + Math.random() * (config.size.max - config.size.min)
    const speed = config.speed.min + Math.random() * (config.speed.max - config.speed.min)
    
    const graphics = new Graphics()
    graphics.rect(0, 0, 1, size)
    graphics.fill({ color: config.color, alpha: 0.6 })
    
    const x = Math.random() * this.boundsWidth
    const y = Math.random() * this.boundsHeight
    
    graphics.x = x
    graphics.y = y
    
    return { graphics, x, y, speed, size }
  }
  
  /**
   * 创建云朵
   */
  private createClouds(): void {
    const config = WEATHER_CONFIGS.cloudy
    
    for (let i = 0; i < config.count; i++) {
      const cloud = this.createCloud(config)
      this.clouds.push(cloud)
      this.container.addChild(cloud.graphics)
    }
  }
  
  /**
   * 创建单个云朵
   */
  private createCloud(config: WeatherParticleConfig): Cloud {
    const width = config.size.min + Math.random() * (config.size.max - config.size.min)
    const height = width * 0.5
    const speed = config.speed.min + Math.random() * (config.speed.max - config.speed.min)
    
    const graphics = new Graphics()
    
    // 绘制卡通云朵形状
    const cx = width / 2
    const cy = height / 2
    
    // 使用多个圆形组合成云朵
    graphics.circle(cx - width * 0.2, cy, height * 0.4)
    graphics.circle(cx + width * 0.2, cy, height * 0.35)
    graphics.circle(cx, cy - height * 0.15, height * 0.45)
    graphics.fill({ color: config.color, alpha: 0.7 })
    
    const x = Math.random() * (this.boundsWidth + width) - width
    const y = 20 + Math.random() * 80
    
    graphics.x = x
    graphics.y = y
    
    return { graphics, x, y, speed, width }
  }
  
  /**
   * 更新粒子系统
   * @param deltaTime 帧时间差（秒）
   */
  update(deltaTime: number): void {
    // 更新雨滴
    for (const particle of this.particles) {
      particle.y += particle.speed * deltaTime * 60
      particle.graphics.y = particle.y
      
      // 超出边界后重置到顶部
      if (particle.y > this.boundsHeight) {
        particle.y = -particle.size
        particle.x = Math.random() * this.boundsWidth
        particle.graphics.x = particle.x
      }
    }
    
    // 更新云朵
    for (const cloud of this.clouds) {
      cloud.x += cloud.speed * deltaTime * 60
      cloud.graphics.x = cloud.x
      
      // 超出边界后重置到左侧
      if (cloud.x > this.boundsWidth) {
        cloud.x = -cloud.width
      }
    }
  }
  
  /**
   * 清除所有粒子
   */
  private clearParticles(): void {
    // 清除雨滴
    for (const particle of this.particles) {
      this.container.removeChild(particle.graphics)
      particle.graphics.destroy()
    }
    this.particles = []
    
    // 清除云朵
    for (const cloud of this.clouds) {
      this.container.removeChild(cloud.graphics)
      cloud.graphics.destroy()
    }
    this.clouds = []
  }
  
  /**
   * 销毁天气系统
   */
  destroy(): void {
    this.clearParticles()
    this.container.destroy()
  }
  
  /**
   * 获取天气名称
   */
  getWeatherName(): string {
    switch (this.currentWeather) {
      case 'sunny': return '晴天'
      case 'cloudy': return '多云'
      case 'rainy': return '雨天'
      default: return '未知'
    }
  }
  
  /**
   * 随机切换天气
   */
  randomWeather(): void {
    const types: WeatherType[] = ['sunny', 'cloudy', 'rainy']
    const weights = [0.5, 0.3, 0.2]  // 晴天概率较高
    
    const random = Math.random()
    let cumulative = 0
    
    for (let i = 0; i < types.length; i++) {
      cumulative += weights[i]
      if (random < cumulative) {
        this.setWeather(types[i])
        return
      }
    }
    
    this.setWeather('sunny')
  }
}
