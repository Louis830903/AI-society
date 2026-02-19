/**
 * 像素游戏资源配置
 * 
 * 定义建筑、人物、环境精灵的映射关系
 * 由于使用程序生成的精灵，此文件主要用于配置颜色和尺寸
 */

// 建筑类型配置
export interface BuildingConfig {
  name: string
  color: number        // 主色调 (hex)
  roofColor: number    // 屋顶色 (hex)
  width: number        // 精灵宽度
  height: number       // 精灵高度
  icon: string         // 图标字符
}

// 建筑类型到配置映射
export const BUILDING_CONFIGS: Record<string, BuildingConfig> = {
  home: {
    name: '住宅',
    color: 0x8BC34A,       // 绿色
    roofColor: 0x689F38,
    width: 48,
    height: 56,
    icon: '🏠',
  },
  apartment: {
    name: '公寓',
    color: 0x78909C,       // 灰蓝色
    roofColor: 0x546E7A,
    width: 64,
    height: 80,
    icon: '🏢',
  },
  cafe: {
    name: '咖啡馆',
    color: 0xFFB74D,       // 橙色
    roofColor: 0xF57C00,
    width: 48,
    height: 48,
    icon: '☕',
  },
  restaurant: {
    name: '餐厅',
    color: 0xEF5350,       // 红色
    roofColor: 0xC62828,
    width: 56,
    height: 56,
    icon: '🍽️',
  },
  office: {
    name: '办公室',
    color: 0x42A5F5,       // 蓝色
    roofColor: 0x1976D2,
    width: 64,
    height: 72,
    icon: '🏢',
  },
  shop: {
    name: '商店',
    color: 0xAB47BC,       // 紫色
    roofColor: 0x7B1FA2,
    width: 48,
    height: 48,
    icon: '🛒',
  },
  park: {
    name: '公园',
    color: 0x66BB6A,       // 翠绿
    roofColor: 0x388E3C,
    width: 80,
    height: 64,
    icon: '🌳',
  },
  school: {
    name: '学校',
    color: 0xFDD835,       // 黄色
    roofColor: 0xF9A825,
    width: 72,
    height: 64,
    icon: '📚',
  },
  hospital: {
    name: '医院',
    color: 0xEC407A,       // 粉色
    roofColor: 0xC2185B,
    width: 64,
    height: 72,
    icon: '🏥',
  },
  default: {
    name: '建筑',
    color: 0x90A4AE,       // 灰色
    roofColor: 0x607D8B,
    width: 48,
    height: 48,
    icon: '📍',
  },
}

// 智能体配置
export interface CharacterConfig {
  skinColor: number
  hairColor: number
  shirtColor: number
}

// 预定义的人物颜色方案
export const CHARACTER_PALETTES: CharacterConfig[] = [
  { skinColor: 0xFFDDB4, hairColor: 0x4A3728, shirtColor: 0x3498DB },  // 浅肤色、棕发、蓝衣
  { skinColor: 0xFFDDB4, hairColor: 0x1A1A1A, shirtColor: 0xE74C3C },  // 浅肤色、黑发、红衣
  { skinColor: 0xD4A574, hairColor: 0x2C2C2C, shirtColor: 0x2ECC71 },  // 深肤色、黑发、绿衣
  { skinColor: 0xFFDDB4, hairColor: 0xFFD700, shirtColor: 0x9B59B6 },  // 浅肤色、金发、紫衣
  { skinColor: 0xFFDDB4, hairColor: 0x8B4513, shirtColor: 0xF39C12 },  // 浅肤色、褐发、橙衣
  { skinColor: 0xD4A574, hairColor: 0x1A1A1A, shirtColor: 0x1ABC9C },  // 深肤色、黑发、青衣
]

// 天气粒子配置
export interface WeatherParticleConfig {
  count: number
  color: number
  speed: { min: number; max: number }
  size: { min: number; max: number }
}

export const WEATHER_CONFIGS: Record<string, WeatherParticleConfig> = {
  sunny: {
    count: 0,
    color: 0xFFFFFF,
    speed: { min: 0, max: 0 },
    size: { min: 0, max: 0 },
  },
  cloudy: {
    count: 8,
    color: 0xCCCCCC,
    speed: { min: 0.2, max: 0.5 },
    size: { min: 40, max: 80 },
  },
  rainy: {
    count: 150,
    color: 0xAABBDD,
    speed: { min: 8, max: 15 },
    size: { min: 2, max: 4 },
  },
}

// 昼夜光照配置
export interface DaylightConfig {
  sky: number           // 天空背景色
  ambient: number       // 环境光强度 (0-1)
  tint: number          // 精灵着色
}

// 时间点对应的光照配置 (24小时制)
export const DAYLIGHT_CONFIGS: Record<number, DaylightConfig> = {
  0:  { sky: 0x0D1B2A, ambient: 0.2, tint: 0x3344AA },   // 午夜
  5:  { sky: 0x1A1A2E, ambient: 0.3, tint: 0x6666AA },   // 黎明前
  6:  { sky: 0x2D3561, ambient: 0.5, tint: 0x8888CC },   // 黎明
  7:  { sky: 0xFF9A56, ambient: 0.7, tint: 0xFFCC88 },   // 日出
  8:  { sky: 0xFFB366, ambient: 0.85, tint: 0xFFDDAA },  // 早晨
  10: { sky: 0x87CEEB, ambient: 1.0, tint: 0xFFFFFF },   // 上午
  12: { sky: 0x87CEEB, ambient: 1.0, tint: 0xFFFFFF },   // 正午
  15: { sky: 0x87CEEB, ambient: 1.0, tint: 0xFFFFFF },   // 下午
  17: { sky: 0xFF7B54, ambient: 0.8, tint: 0xFFAA66 },   // 黄昏
  18: { sky: 0xD35400, ambient: 0.6, tint: 0xDD8844 },   // 日落
  19: { sky: 0x2D3561, ambient: 0.5, tint: 0x8888CC },   // 傍晚
  21: { sky: 0x1A1A2E, ambient: 0.3, tint: 0x5555AA },   // 夜晚
  23: { sky: 0x0D1B2A, ambient: 0.2, tint: 0x3344AA },   // 深夜
}

// 等距视角配置
export const ISOMETRIC_CONFIG = {
  tileWidth: 64,        // 瓦片宽度
  tileHeight: 32,       // 瓦片高度（2:1等距比例）
  scale: 1,             // 默认缩放
}

// 动画帧率配置
export const ANIMATION_CONFIG = {
  fps: 8,               // 动画帧率
  idleFrames: 2,        // 待机动画帧数
  walkFrames: 4,        // 行走动画帧数
  workFrames: 4,        // 工作动画帧数
}

// 获取建筑配置
export function getBuildingConfig(type: string): BuildingConfig {
  return BUILDING_CONFIGS[type] || BUILDING_CONFIGS.default
}

// 根据 agent ID 获取人物配色
export function getCharacterPalette(agentId: string): CharacterConfig {
  // 使用 ID 哈希生成稳定索引
  let hash = 0
  for (let i = 0; i < agentId.length; i++) {
    hash = ((hash << 5) - hash) + agentId.charCodeAt(i)
    hash = hash & hash
  }
  const index = Math.abs(hash) % CHARACTER_PALETTES.length
  return CHARACTER_PALETTES[index]
}

// 根据时间获取插值后的光照配置
export function getDaylightConfig(hour: number): DaylightConfig {
  const hours = Object.keys(DAYLIGHT_CONFIGS).map(Number).sort((a, b) => a - b)
  
  // 找到当前时间前后的配置点
  let prevHour = hours[hours.length - 1]
  let nextHour = hours[0]
  
  for (let i = 0; i < hours.length; i++) {
    if (hours[i] <= hour) {
      prevHour = hours[i]
    }
    if (hours[i] > hour) {
      nextHour = hours[i]
      break
    }
  }
  
  // 如果找不到下一个点（当前时间超过最后一个配置），回绕到第一个
  if (nextHour <= prevHour) {
    nextHour = hours[0]
  }
  
  const prevConfig = DAYLIGHT_CONFIGS[prevHour]
  const nextConfig = DAYLIGHT_CONFIGS[nextHour]
  
  // 计算插值比例
  let t: number
  if (nextHour > prevHour) {
    t = (hour - prevHour) / (nextHour - prevHour)
  } else {
    // 跨午夜
    const totalSpan = (24 - prevHour) + nextHour
    const elapsed = hour >= prevHour ? (hour - prevHour) : (24 - prevHour + hour)
    t = elapsed / totalSpan
  }
  
  // 颜色插值
  const lerpColor = (c1: number, c2: number, t: number): number => {
    const r1 = (c1 >> 16) & 0xFF
    const g1 = (c1 >> 8) & 0xFF
    const b1 = c1 & 0xFF
    const r2 = (c2 >> 16) & 0xFF
    const g2 = (c2 >> 8) & 0xFF
    const b2 = c2 & 0xFF
    const r = Math.round(r1 + (r2 - r1) * t)
    const g = Math.round(g1 + (g2 - g1) * t)
    const b = Math.round(b1 + (b2 - b1) * t)
    return (r << 16) | (g << 8) | b
  }
  
  return {
    sky: lerpColor(prevConfig.sky, nextConfig.sky, t),
    ambient: prevConfig.ambient + (nextConfig.ambient - prevConfig.ambient) * t,
    tint: lerpColor(prevConfig.tint, nextConfig.tint, t),
  }
}
