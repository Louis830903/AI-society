/**
 * 建筑物/地点状态管理
 * 
 * 功能：
 * - 管理所有建筑物数据
 * - 支持建筑物 CRUD 操作
 * - 管理选中状态和编辑模式
 */

import { create } from 'zustand'
import type { Location } from '../types'
import { locationApi, CreateLocationParams, UpdateLocationParams } from '../services/api'

// ==================
// 类型定义
// ==================

interface LocationType {
  value: string
  name: string
}

interface ActivityType {
  value: string
  name: string
}

interface LocationState {
  // 数据
  locations: Location[]
  locationTypes: LocationType[]
  activityTypes: ActivityType[]
  
  // 加载状态
  locationsLoaded: boolean
  
  // 选中状态
  selectedLocationId: string | null
  selectedLocation: Location | null
  
  // 编辑模式
  isEditMode: boolean
  isCreating: boolean
  
  // 加载状态
  isLoading: boolean
  error: string | null
  
  // 操作
  fetchLocations: () => Promise<void>
  fetchLocationTypes: () => Promise<void>
  fetchActivityTypes: () => Promise<void>
  selectLocation: (id: string | null) => void
  
  // CRUD 操作
  createLocation: (params: CreateLocationParams) => Promise<Location | null>
  updateLocation: (id: string, params: UpdateLocationParams) => Promise<Location | null>
  updateLocationPosition: (id: string, x: number, y: number) => Promise<boolean>
  deleteLocation: (id: string) => Promise<boolean>
  
  // 编辑模式控制
  setEditMode: (enabled: boolean) => void
  setCreating: (creating: boolean) => void
  
  // 清除
  clearSelection: () => void
  clearError: () => void
}

// ==================
// Store 实现
// ==================

export const useLocationStore = create<LocationState>((set, get) => ({
  // 初始状态
  locations: [],
  locationTypes: [],
  activityTypes: [],
  locationsLoaded: false,
  selectedLocationId: null,
  selectedLocation: null,
  isEditMode: false,
  isCreating: false,
  isLoading: false,
  error: null,
  
  // ==================
  // 获取数据
  // ==================
  
  fetchLocations: async () => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await locationApi.list()
      set({ 
        locations: result.locations,
        locationsLoaded: true,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '获取建筑物列表失败',
        isLoading: false,
      })
    }
  },
  
  fetchLocationTypes: async () => {
    try {
      const result = await locationApi.getTypes()
      set({ locationTypes: result.types })
    } catch (err) {
      console.error('获取地点类型失败:', err)
    }
  },
  
  fetchActivityTypes: async () => {
    try {
      const result = await locationApi.getActivities()
      set({ activityTypes: result.activities })
    } catch (err) {
      console.error('获取活动类型失败:', err)
    }
  },
  
  // ==================
  // 选择建筑物
  // ==================
  
  selectLocation: (id: string | null) => {
    const { locations } = get()
    
    if (id) {
      const location = locations.find(l => l.id === id) || null
      set({ 
        selectedLocationId: id,
        selectedLocation: location,
      })
    } else {
      set({ 
        selectedLocationId: null,
        selectedLocation: null,
        isEditMode: false,
      })
    }
  },
  
  // ==================
  // CRUD 操作
  // ==================
  
  createLocation: async (params: CreateLocationParams) => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await locationApi.create(params)
      
      if (result.success) {
        // 添加到本地列表
        const { locations } = get()
        set({ 
          locations: [...locations, result.location],
          isLoading: false,
          isCreating: false,
        })
        return result.location
      } else {
        set({
          error: result.message || '创建失败',
          isLoading: false,
        })
        return null
      }
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '创建建筑物失败',
        isLoading: false,
      })
      return null
    }
  },
  
  updateLocation: async (id: string, params: UpdateLocationParams) => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await locationApi.update(id, params)
      
      if (result.success) {
        // 更新本地列表
        const { locations, selectedLocationId } = get()
        const updatedLocations = locations.map(l => 
          l.id === id ? result.location : l
        )
        
        set({ 
          locations: updatedLocations,
          selectedLocation: selectedLocationId === id ? result.location : get().selectedLocation,
          isLoading: false,
        })
        return result.location
      } else {
        set({
          error: result.message || '更新失败',
          isLoading: false,
        })
        return null
      }
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '更新建筑物失败',
        isLoading: false,
      })
      return null
    }
  },
  
  updateLocationPosition: async (id: string, x: number, y: number) => {
    try {
      const result = await locationApi.updatePosition(id, x, y)
      
      if (result.success) {
        // 更新本地列表
        const { locations, selectedLocationId } = get()
        const updatedLocations = locations.map(l => 
          l.id === id ? result.location : l
        )
        
        set({ 
          locations: updatedLocations,
          selectedLocation: selectedLocationId === id ? result.location : get().selectedLocation,
        })
        return true
      }
      return false
    } catch (err) {
      console.error('更新位置失败:', err)
      return false
    }
  },
  
  deleteLocation: async (id: string) => {
    set({ isLoading: true, error: null })
    
    try {
      const result = await locationApi.delete(id)
      
      if (result.success) {
        // 从本地列表移除
        const { locations, selectedLocationId } = get()
        const updatedLocations = locations.filter(l => l.id !== id)
        
        set({ 
          locations: updatedLocations,
          selectedLocationId: selectedLocationId === id ? null : selectedLocationId,
          selectedLocation: selectedLocationId === id ? null : get().selectedLocation,
          isLoading: false,
        })
        return true
      } else {
        set({
          error: result.message || '删除失败',
          isLoading: false,
        })
        return false
      }
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '删除建筑物失败',
        isLoading: false,
      })
      return false
    }
  },
  
  // ==================
  // 编辑模式控制
  // ==================
  
  setEditMode: (enabled: boolean) => {
    set({ isEditMode: enabled })
  },
  
  setCreating: (creating: boolean) => {
    set({ isCreating: creating })
  },
  
  // ==================
  // 清除
  // ==================
  
  clearSelection: () => {
    set({ 
      selectedLocationId: null,
      selectedLocation: null,
      isEditMode: false,
    })
  },
  
  clearError: () => {
    set({ error: null })
  },
}))

export default useLocationStore
