/**
 * 等距视角坐标转换工具
 * 
 * 标准等距比例 2:1（角度约 26.57 度）
 * 坐标系: 笛卡尔 (x, y) <-> 等距 (isoX, isoY)
 */

import { ISOMETRIC_CONFIG } from './assets'

/**
 * 笛卡尔坐标转等距坐标
 * @param x 笛卡尔 X 坐标
 * @param y 笛卡尔 Y 坐标
 * @returns 等距坐标 { isoX, isoY }
 */
export function cartesianToIso(x: number, y: number): { isoX: number; isoY: number } {
  const { tileWidth, tileHeight } = ISOMETRIC_CONFIG
  
  // 标准等距转换公式
  const isoX = (x - y) * (tileWidth / 2)
  const isoY = (x + y) * (tileHeight / 2)
  
  return { isoX, isoY }
}

/**
 * 等距坐标转笛卡尔坐标
 * @param isoX 等距 X 坐标
 * @param isoY 等距 Y 坐标
 * @returns 笛卡尔坐标 { x, y }
 */
export function isoToCartesian(isoX: number, isoY: number): { x: number; y: number } {
  const { tileWidth, tileHeight } = ISOMETRIC_CONFIG
  
  // 逆向转换
  const x = (isoX / (tileWidth / 2) + isoY / (tileHeight / 2)) / 2
  const y = (isoY / (tileHeight / 2) - isoX / (tileWidth / 2)) / 2
  
  return { x, y }
}

/**
 * 屏幕坐标转世界坐标（考虑摄像机偏移和缩放）
 * @param screenX 屏幕 X 坐标
 * @param screenY 屏幕 Y 坐标
 * @param cameraX 摄像机 X 偏移
 * @param cameraY 摄像机 Y 偏移
 * @param scale 缩放比例
 * @param canvasWidth 画布宽度
 * @param canvasHeight 画布高度
 * @returns 世界等距坐标 { worldX, worldY }
 */
export function screenToWorld(
  screenX: number,
  screenY: number,
  cameraX: number,
  cameraY: number,
  scale: number,
  canvasWidth: number,
  canvasHeight: number
): { worldX: number; worldY: number } {
  // 转换为以画布中心为原点的坐标
  const centerX = canvasWidth / 2
  const centerY = canvasHeight / 2
  
  // 考虑摄像机和缩放
  const worldX = (screenX - centerX - cameraX) / scale
  const worldY = (screenY - centerY - cameraY) / scale
  
  return { worldX, worldY }
}

/**
 * 世界坐标转屏幕坐标
 * @param worldX 世界 X 坐标
 * @param worldY 世界 Y 坐标
 * @param cameraX 摄像机 X 偏移
 * @param cameraY 摄像机 Y 偏移
 * @param scale 缩放比例
 * @param canvasWidth 画布宽度
 * @param canvasHeight 画布高度
 * @returns 屏幕坐标 { screenX, screenY }
 */
export function worldToScreen(
  worldX: number,
  worldY: number,
  cameraX: number,
  cameraY: number,
  scale: number,
  canvasWidth: number,
  canvasHeight: number
): { screenX: number; screenY: number } {
  const centerX = canvasWidth / 2
  const centerY = canvasHeight / 2
  
  const screenX = worldX * scale + centerX + cameraX
  const screenY = worldY * scale + centerY + cameraY
  
  return { screenX, screenY }
}

/**
 * 计算深度排序值（用于 Y 轴排序）
 * 在等距视图中，Y 值越大的对象应该显示在前面
 * @param isoX 等距 X 坐标
 * @param isoY 等距 Y 坐标
 * @returns 深度值（越大越靠前）
 */
export function calculateDepth(isoX: number, isoY: number): number {
  // 使用等距 Y 坐标作为主要深度
  // 加上一个小的 X 偏移避免同行重叠
  return isoY * 1000 + isoX * 0.1
}

/**
 * 按深度排序精灵数组
 * @param sprites 具有 x, y 属性的精灵数组
 */
export function sortByDepth<T extends { x: number; y: number }>(sprites: T[]): void {
  sprites.sort((a, b) => {
    const depthA = calculateDepth(a.x, a.y)
    const depthB = calculateDepth(b.x, b.y)
    return depthA - depthB
  })
}

/**
 * 后端世界坐标（0-100）转前端等距坐标
 * @param backendX 后端 X 坐标 (0-100)
 * @param backendY 后端 Y 坐标 (0-100)
 * @returns 前端等距坐标
 */
export function backendToIsometric(backendX: number, backendY: number): { isoX: number; isoY: number } {
  // 后端坐标范围 0-100，缩放到合适的瓦片网格
  // 使用 0.5 的缩放因子让地图更紧凑
  const scaleFactor = 0.5
  const gridX = backendX * scaleFactor
  const gridY = backendY * scaleFactor
  
  return cartesianToIso(gridX, gridY)
}

/**
 * 前端等距坐标转后端世界坐标（0-100）
 * 这是 backendToIsometric 的反向操作
 * @param isoX 前端等距 X 坐标
 * @param isoY 前端等距 Y 坐标
 * @returns 后端世界坐标 { backendX, backendY }
 */
export function isometricToBackend(isoX: number, isoY: number): { backendX: number; backendY: number } {
  // 先转换为笛卡尔坐标
  const { x, y } = isoToCartesian(isoX, isoY)
  
  // 反向应用缩放因子
  const scaleFactor = 0.5
  const backendX = Math.round(x / scaleFactor)
  const backendY = Math.round(y / scaleFactor)
  
  // 限制在 0-100 范围内
  return {
    backendX: Math.max(0, Math.min(100, backendX)),
    backendY: Math.max(0, Math.min(100, backendY)),
  }
}

/**
 * 检查点是否在等距瓦片内
 * @param pointX 点的等距 X 坐标
 * @param pointY 点的等距 Y 坐标
 * @param tileX 瓦片中心等距 X 坐标
 * @param tileY 瓦片中心等距 Y 坐标
 * @returns 是否在瓦片内
 */
export function isPointInTile(
  pointX: number,
  pointY: number,
  tileX: number,
  tileY: number
): boolean {
  const { tileWidth, tileHeight } = ISOMETRIC_CONFIG
  
  // 菱形边界检测
  const dx = Math.abs(pointX - tileX)
  const dy = Math.abs(pointY - tileY)
  
  return (dx / (tileWidth / 2) + dy / (tileHeight / 2)) <= 1
}

/**
 * 计算两个等距坐标之间的距离
 */
export function isoDistance(
  x1: number,
  y1: number,
  x2: number,
  y2: number
): number {
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
}

/**
 * 计算从 A 到 B 的方向角（弧度）
 */
export function isoDirection(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number
): number {
  return Math.atan2(toY - fromY, toX - fromX)
}

/**
 * 获取移动方向（8方向）
 * @returns 方向名称: 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'
 */
export function getMovementDirection(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number
): string {
  const angle = isoDirection(fromX, fromY, toX, toY)
  const deg = (angle * 180 / Math.PI + 360) % 360
  
  // 8方向划分（每个方向 45 度）
  if (deg >= 337.5 || deg < 22.5) return 'E'
  if (deg >= 22.5 && deg < 67.5) return 'SE'
  if (deg >= 67.5 && deg < 112.5) return 'S'
  if (deg >= 112.5 && deg < 157.5) return 'SW'
  if (deg >= 157.5 && deg < 202.5) return 'W'
  if (deg >= 202.5 && deg < 247.5) return 'NW'
  if (deg >= 247.5 && deg < 292.5) return 'N'
  return 'NE'
}
