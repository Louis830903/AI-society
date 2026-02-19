/**
 * 等距地面瓦片系统
 * 
 * 渲染等距视角的地面
 */

import { Container, Graphics } from 'pixi.js'
import { ISOMETRIC_CONFIG } from './assets'
import { cartesianToIso } from './IsometricUtils'

/**
 * 瓦片类型
 */
export enum TileType {
  GRASS = 'grass',
  ROAD = 'road',
  WATER = 'water',
  SAND = 'sand',
}

/**
 * 瓦片颜色配置
 */
const TILE_COLORS: Record<TileType, number> = {
  [TileType.GRASS]: 0x7EC850,
  [TileType.ROAD]: 0x8B8B8B,
  [TileType.WATER]: 0x4A90D9,
  [TileType.SAND]: 0xD4B896,
}

/**
 * 瓦片地图
 */
export class TileMap {
  private container: Container
  private tiles: Graphics[] = []
  private tilePool: Graphics[] = []
  
  // 地图尺寸（瓦片数）
  private mapWidth: number
  private mapHeight: number
  
  // 视口信息（保留用于将来的视口裁剪优化）
  private _viewportWidth: number = 800
  private _viewportHeight: number = 600
  private _cameraX: number = 0
  private _cameraY: number = 0
  private _scale: number = 1
  
  constructor(groundLayer: Container, mapWidth: number = 50, mapHeight: number = 50) {
    this.container = new Container()
    this.container.label = 'tileMapContainer'
    groundLayer.addChild(this.container)
    
    this.mapWidth = mapWidth
    this.mapHeight = mapHeight
  }
  
  /**
   * 生成地图
   */
  generate(): void {
    this.clear()
    
    const { tileWidth, tileHeight } = ISOMETRIC_CONFIG
    
    // 生成所有瓦片
    for (let y = 0; y < this.mapHeight; y++) {
      for (let x = 0; x < this.mapWidth; x++) {
        const tile = this.getTileFromPool()
        
        // 决定瓦片类型（简单的随机地形）
        const tileType = this.getTileType(x, y)
        const color = TILE_COLORS[tileType]
        
        // 绘制等距菱形瓦片
        this.drawIsometricTile(tile, tileWidth, tileHeight, color)
        
        // 计算等距位置
        const { isoX, isoY } = cartesianToIso(x, y)
        tile.x = isoX
        tile.y = isoY
        
        this.tiles.push(tile)
        this.container.addChild(tile)
      }
    }
  }
  
  /**
   * 根据坐标决定瓦片类型
   */
  private getTileType(x: number, y: number): TileType {
    // 简单的地形生成：边缘是沙地，中间是草地
    const centerX = this.mapWidth / 2
    const centerY = this.mapHeight / 2
    const distFromCenter = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2)
    const maxDist = Math.min(centerX, centerY)
    
    // 边缘区域
    if (distFromCenter > maxDist * 0.85) {
      return TileType.SAND
    }
    
    // 添加一些道路
    if (Math.abs(x - centerX) < 2 || Math.abs(y - centerY) < 2) {
      return TileType.ROAD
    }
    
    return TileType.GRASS
  }
  
  /**
   * 绘制等距菱形瓦片
   */
  private drawIsometricTile(graphics: Graphics, width: number, height: number, color: number): void {
    graphics.clear()
    
    // 菱形顶点（从顶部顺时针）
    const halfW = width / 2
    const halfH = height / 2
    
    graphics.moveTo(0, -halfH)        // 顶部
    graphics.lineTo(halfW, 0)         // 右边
    graphics.lineTo(0, halfH)         // 底部
    graphics.lineTo(-halfW, 0)        // 左边
    graphics.closePath()
    
    // 填充和描边
    graphics.fill({ color, alpha: 0.9 })
    graphics.stroke({ width: 1, color: this.darkenColor(color, 0.2), alpha: 0.5 })
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
   * 从对象池获取瓦片
   */
  private getTileFromPool(): Graphics {
    if (this.tilePool.length > 0) {
      return this.tilePool.pop()!
    }
    return new Graphics()
  }
  
  /**
   * 归还瓦片到对象池
   */
  private returnToPool(tile: Graphics): void {
    tile.clear()
    this.tilePool.push(tile)
  }
  
  /**
   * 更新视口（用于裁剪优化）
   */
  updateViewport(
    viewportWidth: number,
    viewportHeight: number,
    cameraX: number,
    cameraY: number,
    scale: number
  ): void {
    this._viewportWidth = viewportWidth
    this._viewportHeight = viewportHeight
    this._cameraX = cameraX
    this._cameraY = cameraY
    this._scale = scale
    
    // TODO: 实现视口裁剪优化
    // 只渲染可见区域的瓦片
  }
  
  /**
   * 获取视口状态（供调试使用）
   */
  getViewportState() {
    return {
      viewportWidth: this._viewportWidth,
      viewportHeight: this._viewportHeight,
      cameraX: this._cameraX,
      cameraY: this._cameraY,
      scale: this._scale,
    }
  }
  
  /**
   * 清除所有瓦片
   */
  clear(): void {
    for (const tile of this.tiles) {
      this.container.removeChild(tile)
      this.returnToPool(tile)
    }
    this.tiles = []
  }
  
  /**
   * 应用着色（昼夜系统）
   */
  applyTint(tint: number): void {
    for (const tile of this.tiles) {
      tile.tint = tint
    }
  }
  
  /**
   * 获取容器
   */
  getContainer(): Container {
    return this.container
  }
  
  /**
   * 销毁
   */
  destroy(): void {
    this.clear()
    for (const tile of this.tilePool) {
      tile.destroy()
    }
    this.tilePool = []
    this.container.destroy()
  }
}
