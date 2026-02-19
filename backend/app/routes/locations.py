"""
地点API路由
==========
提供地点查询和管理接口
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.locations import (
    location_manager, 
    LocationType, 
    ActivityType, 
    Location,
    OpeningHours,
)
from app.agents.manager import agent_manager


router = APIRouter()


# ===================
# Pydantic 模型定义
# ===================

class PositionSchema(BaseModel):
    """坐标"""
    x: float
    y: float


class SizeSchema(BaseModel):
    """尺寸"""
    width: int
    height: int


class OpenHoursSchema(BaseModel):
    """营业时间（简化版）"""
    open: int
    close: int


class LocationSchema(BaseModel):
    """地点信息 - 符合前端期望格式"""
    id: str
    name: str
    type: str
    description: str
    position: PositionSchema
    size: SizeSchema
    capacity: int
    current_occupants: int
    activities: List[str]
    open_hours: Optional[OpenHoursSchema] = None
    is_open_now: bool = True


# ===================
# 创建/更新请求模型
# ===================

class CreateLocationRequest(BaseModel):
    """创建地点请求"""
    name: str = Field(..., description="地点名称", min_length=1, max_length=50)
    type: str = Field(..., description="地点类型")
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")
    width: int = Field(default=2, description="宽度", ge=1, le=10)
    height: int = Field(default=2, description="高度", ge=1, le=10)
    capacity: int = Field(default=10, description="容量", ge=1, le=100)
    activities: List[str] = Field(default=[], description="支持的活动列表")
    description: str = Field(default="", description="描述", max_length=200)
    open_hour: int = Field(default=0, description="开门时间", ge=0, le=23)
    close_hour: int = Field(default=24, description="关门时间", ge=0, le=24)


class UpdateLocationRequest(BaseModel):
    """更新地点请求"""
    name: Optional[str] = Field(None, description="地点名称", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="描述", max_length=200)
    capacity: Optional[int] = Field(None, description="容量", ge=1, le=100)
    activities: Optional[List[str]] = Field(None, description="支持的活动列表")
    open_hour: Optional[int] = Field(None, description="开门时间", ge=0, le=23)
    close_hour: Optional[int] = Field(None, description="关门时间", ge=0, le=24)


class UpdatePositionRequest(BaseModel):
    """更新位置请求"""
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")


def location_to_schema(loc) -> dict:
    """将Location对象转换为前端期望的格式"""
    return {
        "id": loc.id,
        "name": loc.name,
        "type": loc.type.value,
        "description": loc.description,
        "position": {"x": loc.x, "y": loc.y},
        "size": {"width": loc.width, "height": loc.height},
        "capacity": loc.capacity,
        "current_occupants": len(loc.current_agents),
        "activities": [a.value for a in loc.activities],
        "open_hours": {
            "open": loc.opening_hours.open_hour,
            "close": loc.opening_hours.close_hour,
        } if loc.opening_hours else None,
        "is_open_now": True,
    }


class LocationListResponse(BaseModel):
    """地点列表响应"""
    locations: List[LocationSchema]
    total: int


# ===================
# API 端点
# ===================

@router.get("", response_model=LocationListResponse)
async def list_locations(
    location_type: Optional[str] = Query(None, description="按类型筛选"),
    activity: Optional[str] = Query(None, description="按支持的活动筛选"),
    available_only: bool = Query(False, description="只显示未满的地点"),
):
    """
    获取地点列表
    
    支持按类型、活动筛选，可以只显示未满的地点
    """
    locations = list(location_manager.locations.values())
    
    # 类型筛选
    if location_type:
        try:
            loc_type = LocationType(location_type)
            locations = [l for l in locations if l.type == loc_type]
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的地点类型: {location_type}"
            )
    
    # 活动筛选
    if activity:
        try:
            act = ActivityType(activity)
            locations = [l for l in locations if l.can_do_activity(act)]
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的活动类型: {activity}"
            )
    
    # 可用性筛选
    if available_only:
        locations = [l for l in locations if not l.is_full]
    
    return {
        "locations": [location_to_schema(l) for l in locations],
        "total": len(locations),
    }


@router.get("/types")
async def list_location_types():
    """获取所有地点类型"""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in LocationType
        ]
    }


@router.get("/activities")
async def list_activity_types():
    """获取所有活动类型"""
    return {
        "activities": [
            {"value": a.value, "name": a.name}
            for a in ActivityType
        ]
    }


@router.get("/stats")
async def get_location_stats():
    """
    获取地点统计信息
    """
    locations = list(location_manager.locations.values())
    
    # 按类型统计
    by_type = {}
    for loc in locations:
        type_name = loc.type.value
        if type_name not in by_type:
            by_type[type_name] = {"count": 0, "total_capacity": 0, "current_occupants": 0}
        by_type[type_name]["count"] += 1
        by_type[type_name]["total_capacity"] += loc.capacity
        by_type[type_name]["current_occupants"] += len(loc.current_agents)
    
    return {
        "total_locations": len(locations),
        "total_capacity": sum(l.capacity for l in locations),
        "current_occupants": sum(len(l.current_agents) for l in locations),
        "by_type": by_type,
    }


@router.get("/{location_id}")
async def get_location(location_id: str):
    """
    获取单个地点详情
    
    Args:
        location_id: 地点ID
    """
    location = location_manager.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"地点 {location_id} 不存在")
    
    return location_to_schema(location)


@router.get("/{location_id}/agents")
async def get_location_agents(location_id: str):
    """
    获取地点内的智能体列表
    """
    location = location_manager.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"地点 {location_id} 不存在")
    
    return {
        "location_id": location_id,
        "location_name": location.name,
        "agent_ids": list(location.current_agents),
        "count": len(location.current_agents),
        "capacity": location.capacity,
    }


@router.get("/at/{x}/{y}")
async def get_location_at_position(x: float, y: float):
    """
    获取指定坐标处的地点
    """
    location = location_manager.get_location_at(x, y)
    if not location:
        return {"location": None, "message": f"坐标 ({x}, {y}) 处没有地点"}
    
    return {"location": location_to_schema(location)}


@router.get("/nearest/{x}/{y}")
async def get_nearest_location(
    x: float, 
    y: float,
    location_type: Optional[str] = None,
    activity: Optional[str] = None,
):
    """
    获取最近的地点
    
    可以按类型或活动筛选
    """
    loc_type = None
    act = None
    
    if location_type:
        try:
            loc_type = LocationType(location_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的地点类型: {location_type}")
    
    if activity:
        try:
            act = ActivityType(activity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的活动类型: {activity}")
    
    nearest = location_manager.get_nearest_location(x, y, loc_type, act)
    
    if not nearest:
        return {"location": None, "message": "没有找到符合条件的地点"}
    
    # 计算距离
    cx, cy = nearest.center
    distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    
    return {
        "location": location_to_schema(nearest),
        "distance": round(distance, 2),
    }


# ===================
# 建筑物 CRUD 端点
# ===================

@router.post("", summary="创建新建筑物")
async def create_location(request: CreateLocationRequest):
    """
    创建新建筑物
    
    Args:
        request: 创建请求，包含名称、类型、位置等属性
        
    Returns:
        创建的建筑物信息
    """
    # 验证地点类型
    try:
        loc_type = LocationType(request.type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的地点类型: {request.type}。有效类型: {[t.value for t in LocationType]}"
        )
    
    # 验证活动类型
    activities = []
    for act in request.activities:
        try:
            activities.append(ActivityType(act))
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的活动类型: {act}。有效类型: {[a.value for a in ActivityType]}"
            )
    
    # 生成唯一ID
    location_id = location_manager.generate_id(loc_type)
    
    # 创建地点对象
    location = Location(
        id=location_id,
        name=request.name,
        type=loc_type,
        x=request.x,
        y=request.y,
        width=request.width,
        height=request.height,
        capacity=request.capacity,
        activities=activities,
        opening_hours=OpeningHours(
            open_hour=request.open_hour,
            close_hour=request.close_hour,
        ),
        description=request.description,
    )
    
    # 添加到管理器
    location_manager.add_location(location)
    
    # 持久化保存
    location_manager.save_to_file()
    
    return {
        "success": True,
        "message": f"成功创建建筑物: {location.name}",
        "location": location_to_schema(location),
    }


@router.put("/{location_id}", summary="更新建筑物属性")
async def update_location(location_id: str, request: UpdateLocationRequest):
    """
    更新建筑物属性
    
    Args:
        location_id: 建筑物ID
        request: 更新请求，包含要修改的字段
        
    Returns:
        更新后的建筑物信息
    """
    # 检查地点是否存在
    location = location_manager.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"建筑物 {location_id} 不存在")
    
    # 构建更新字典
    updates = {}
    
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.capacity is not None:
        updates["capacity"] = request.capacity
    if request.activities is not None:
        # 验证活动类型
        for act in request.activities:
            try:
                ActivityType(act)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"无效的活动类型: {act}"
                )
        updates["activities"] = request.activities
    if request.open_hour is not None or request.close_hour is not None:
        updates["opening_hours"] = {
            "open_hour": request.open_hour if request.open_hour is not None else location.opening_hours.open_hour,
            "close_hour": request.close_hour if request.close_hour is not None else location.opening_hours.close_hour,
        }
    
    # 执行更新
    updated = location_manager.update_location(location_id, updates)
    
    return {
        "success": True,
        "message": f"成功更新建筑物: {updated.name}",
        "location": location_to_schema(updated),
    }


@router.patch("/{location_id}/position", summary="更新建筑物位置")
async def update_location_position(location_id: str, request: UpdatePositionRequest):
    """
    更新建筑物位置（用于拖拽）
    
    Args:
        location_id: 建筑物ID
        request: 新的位置坐标
        
    Returns:
        更新后的建筑物信息
    """
    # 检查地点是否存在
    location = location_manager.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"建筑物 {location_id} 不存在")
    
    # 执行位置更新
    updated = location_manager.update_location(location_id, {
        "x": request.x,
        "y": request.y,
    })
    
    return {
        "success": True,
        "message": f"成功更新建筑物位置: ({request.x}, {request.y})",
        "location": location_to_schema(updated),
    }


@router.delete("/{location_id}", summary="删除建筑物")
async def delete_location(
    location_id: str,
    relocate_agents: bool = Query(True, description="是否将内部智能体转移到最近的公共区域"),
):
    """
    删除建筑物
    
    Args:
        location_id: 建筑物ID
        relocate_agents: 是否将内部智能体转移到其他地点
        
    Returns:
        删除结果
    """
    # 检查地点是否存在
    location = location_manager.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"建筑物 {location_id} 不存在")
    
    # 获取内部智能体
    agent_ids = list(location.current_agents)
    relocated_count = 0
    
    # 如果需要转移智能体
    if relocate_agents and agent_ids:
        # 找到最近的公共区域（公园/广场）
        cx, cy = location.center
        nearest_public = location_manager.get_nearest_location(
            cx, cy, 
            loc_type=LocationType.PARK
        )
        if not nearest_public:
            nearest_public = location_manager.get_nearest_location(
                cx, cy, 
                loc_type=LocationType.PLAZA
            )
        
        # 转移智能体
        for agent_id in agent_ids:
            agent = agent_manager.get(agent_id)
            if agent and nearest_public:
                # 更新智能体位置
                agent.position.location_id = nearest_public.id
                agent.position.location_name = nearest_public.name
                px, py = nearest_public.center
                agent.position.x = px
                agent.position.y = py
                
                # 更新地点内的智能体
                location.leave(agent_id)
                nearest_public.enter(agent_id)
                relocated_count += 1
    
    location_name = location.name
    
    # 移除地点
    location_manager.remove_location(location_id)
    
    # 持久化保存
    location_manager.save_to_file()
    
    return {
        "success": True,
        "message": f"成功删除建筑物: {location_name}",
        "location_id": location_id,
        "relocated_agents": relocated_count,
    }
