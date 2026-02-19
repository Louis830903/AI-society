"""
世界状态API路由
===============
提供世界时间、状态查询和控制接口
包含世界控制功能：广播、规则、事件
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime

from app.core.config import settings
from app.core.events import event_bus, Event, EventType
from app.core.world import world_clock
from app.core.locations import location_manager
from app.llm.router import llm_router
from app.agents import agent_manager


router = APIRouter()


# ===================
# Pydantic 模型
# ===================

class WorldTimeResponse(BaseModel):
    """世界时间响应"""
    datetime: str
    day: int
    time_of_day: str
    is_daytime: bool
    formatted_time: str
    formatted_date: str


class ClockStatusResponse(BaseModel):
    """时钟状态响应"""
    time_scale: int
    is_running: bool
    is_paused: bool
    world_time: WorldTimeResponse


class CostSummaryResponse(BaseModel):
    """成本摘要响应"""
    monthly_budget: float
    current_month_cost: float
    remaining_budget: float
    budget_usage_percent: float
    is_warning: bool
    is_exceeded: bool


class WorldStatusResponse(BaseModel):
    """世界状态完整响应"""
    app_name: str
    version: str
    clock: ClockStatusResponse
    cost: CostSummaryResponse
    locations_count: int
    agents_count: int


# ===================
# 世界控制请求模型
# ===================

class BroadcastRequest(BaseModel):
    """世界广播请求"""
    message: str = Field(..., description="广播消息内容", min_length=1, max_length=500)
    priority: str = Field(default="normal", description="优先级: low/normal/high/urgent")
    affect_memory: bool = Field(default=True, description="是否写入智能体记忆")


class WorldRule(BaseModel):
    """世界规则"""
    id: str = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    description: str = Field(default="", description="规则描述")
    enabled: bool = Field(default=True, description="是否启用")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="规则参数")


class UpdateRulesRequest(BaseModel):
    """更新规则请求"""
    rules: List[WorldRule] = Field(..., description="规则列表")


class TriggerEventRequest(BaseModel):
    """触发世界事件请求"""
    event_name: str = Field(..., description="事件名称", min_length=1, max_length=100)
    event_type: str = Field(default="announcement", description="事件类型: announcement/disaster/celebration/economic")
    description: str = Field(default="", description="事件描述", max_length=500)
    duration_hours: int = Field(default=0, description="持续时间（游戏小时），0表示即时事件")
    affect_all_agents: bool = Field(default=True, description="是否影响所有智能体")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="事件参数")


# ===================
# 世界规则存储（简单内存存储）
# ===================

# 预设的世界规则
_world_rules: Dict[str, WorldRule] = {
    "curfew": WorldRule(
        id="curfew",
        name="宵禁",
        description="夜间限制智能体外出活动",
        enabled=False,
        parameters={"start_hour": 22, "end_hour": 6}
    ),
    "festival": WorldRule(
        id="festival",
        name="节日庆典",
        description="节日期间智能体更倾向于社交活动",
        enabled=False,
        parameters={"social_bonus": 20, "work_penalty": 10}
    ),
    "economic_crisis": WorldRule(
        id="economic_crisis",
        name="经济危机",
        description="所有交易价格上涨",
        enabled=False,
        parameters={"price_multiplier": 1.5}
    ),
    "free_day": WorldRule(
        id="free_day",
        name="休息日",
        description="所有智能体倾向于休闲活动",
        enabled=False,
        parameters={"work_probability": 0.2}
    ),
}


# ===================
# API 端点
# ===================

@router.get("/status")
async def get_world_status():
    """
    获取完整的世界状态
    
    返回世界时钟状态、当前时间、成本统计、地点数量等信息
    """
    return {
        "app_name": settings.app_name,
        "version": "0.1.0",
        "clock": world_clock.to_dict(),
        "cost": llm_router.get_cost_summary(),
        "locations_count": len(location_manager.locations),
        "agents_count": 0,  # TODO: 阶段3实现
        "models": llm_router.list_models(),
        "config": {
            "time_scale": settings.time_scale,
            "default_model": settings.default_model,
            "monthly_budget": settings.monthly_budget,
            "initial_agent_count": settings.initial_agent_count,
            "max_agent_count": settings.max_agent_count,
        },
    }


@router.get("/time")
async def get_world_time():
    """
    获取当前世界时间
    
    Returns:
        世界时间信息，包括日期、天数、时间段等
    """
    return world_clock.get_world_time().to_dict()


@router.get("/clock")
async def get_clock_status():
    """
    获取时钟状态
    
    Returns:
        时钟运行状态，包括是否暂停、时间缩放等
    """
    return world_clock.to_dict()


@router.post("/pause")
async def pause_world():
    """
    暂停世界时钟
    
    暂停后智能体决策也会暂停
    
    Returns:
        操作结果和当前时钟状态
    """
    world_clock.pause()
    
    # 发布暂停事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_TIME_CHANGED,
        data={"action": "paused", "clock": world_clock.to_dict()},
        source="api",
    ))
    
    return {
        "status": "paused", 
        "message": "世界时钟已暂停",
        "clock": world_clock.to_dict()
    }


@router.post("/resume")
async def resume_world():
    """
    恢复世界时钟
    
    Returns:
        操作结果和当前时钟状态
    """
    world_clock.resume()
    
    # 发布恢复事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_TIME_CHANGED,
        data={"action": "resumed", "clock": world_clock.to_dict()},
        source="api",
    ))
    
    return {
        "status": "resumed", 
        "message": "世界时钟已恢复",
        "clock": world_clock.to_dict()
    }


@router.post("/time-scale/{scale}")
async def set_time_scale(scale: int):
    """
    设置时间缩放比例
    
    Args:
        scale: 新的缩放比例（1-100）
    
    Returns:
        操作结果
    
    Raises:
        HTTPException: 400 如果 scale 不在有效范围内
    """
    if scale < 1 or scale > 100:
        raise HTTPException(
            status_code=400,
            detail="时间缩放比例必须在 1-100 之间"
        )
    
    old_scale = world_clock.time_scale
    world_clock.set_time_scale(scale)
    
    # 发布时间缩放变化事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_TIME_CHANGED,
        data={
            "action": "time_scale_changed",
            "old_scale": old_scale,
            "new_scale": scale,
        },
        source="api",
    ))
    
    return {
        "status": "ok", 
        "message": f"时间缩放已调整: {old_scale} -> {scale}",
        "time_scale": scale
    }


@router.get("/events")
async def get_recent_events(
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
):
    """
    获取最近的事件历史
    
    Args:
        event_type: 可选的事件类型筛选
        limit: 返回的最大数量
    
    Returns:
        事件列表
    
    Raises:
        HTTPException: 400 如果事件类型无效
    """
    if event_type:
        try:
            et = EventType(event_type)
            events = event_bus.get_history(event_type=et, limit=limit)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的事件类型: {event_type}"
            )
    else:
        events = event_bus.get_history(limit=limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


@router.get("/event-types")
async def list_event_types():
    """获取所有事件类型"""
    return {
        "event_types": [
            {"value": et.value, "name": et.name}
            for et in EventType
        ]
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 实时事件推送
    
    建立连接后会接收所有世界事件
    
    客户端可以发送以下命令：
    - {"type": "ping"}: 心跳检测
    - {"type": "get_time"}: 获取当前时间
    - {"type": "get_status"}: 获取完整状态
    """
    await websocket.accept()
    event_bus.register_websocket(websocket)
    logger.info("WebSocket客户端已连接")
    
    # 发送初始状态（统一使用 event_type 格式，与其他事件消息保持一致）
    try:
        await websocket.send_json({
            "event_type": "system.connected",
            "event_id": None,
            "data": {
                "message": "欢迎连接到 AI Society",
                "world_time": world_clock.get_world_time().to_dict(),
            },
            "timestamp": None,
            "source": "system",
        })
    except Exception as e:
        logger.error(f"发送初始状态失败: {e}")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "get_time":
                await websocket.send_json({
                    "type": "world_time",
                    "data": world_clock.get_world_time().to_dict(),
                })
            
            elif msg_type == "get_status":
                await websocket.send_json({
                    "type": "world_status",
                    "data": {
                        "clock": world_clock.to_dict(),
                        "locations_count": len(location_manager.locations),
                    },
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知命令: {msg_type}",
                })
                
    except WebSocketDisconnect:
        event_bus.unregister_websocket(websocket)
        logger.info("WebSocket客户端已断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        event_bus.unregister_websocket(websocket)


# ===================
# 世界控制 API
# ===================

@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest):
    """
    发送世界广播
    
    向所有智能体发布通知消息，可选择是否写入智能体记忆
    
    Args:
        message: 广播消息内容
        priority: 优先级 (low/normal/high/urgent)
        affect_memory: 是否写入智能体记忆
    
    Returns:
        广播结果和影响的智能体数量
    """
    from app.agents.memory import Memory, MemoryType
    
    # 验证优先级
    valid_priorities = ["low", "normal", "high", "urgent"]
    if request.priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"无效的优先级，必须是: {', '.join(valid_priorities)}"
        )
    
    agents = agent_manager.get_all()
    affected_count = 0
    
    # 如果需要写入记忆，为每个智能体添加记忆
    if request.affect_memory:
        importance_map = {"low": 3, "normal": 5, "high": 7, "urgent": 9}
        importance = importance_map.get(request.priority, 5)
        
        for agent in agents:
            memory = Memory(
                type=MemoryType.EVENT,
                content=f"[世界广播] {request.message}",
                importance=importance,
                keywords={"广播", "公告", request.priority},
            )
            agent.memory.add(memory)
            affected_count += 1
    else:
        affected_count = len(agents)
    
    # 发布广播事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_BROADCAST,
        data={
            "message": request.message,
            "priority": request.priority,
            "affect_memory": request.affect_memory,
            "affected_agents": affected_count,
            "timestamp": datetime.now().isoformat(),
        },
        source="api",
    ))
    
    logger.info(f"世界广播已发送: {request.message[:50]}... (影响 {affected_count} 个智能体)")
    
    return {
        "success": True,
        "message": "广播已发送",
        "affected_agents": affected_count,
        "priority": request.priority,
        "content": request.message,
    }


@router.get("/rules")
async def get_world_rules():
    """
    获取所有世界规则
    
    Returns:
        规则列表和当前启用状态
    """
    rules = [rule.model_dump() for rule in _world_rules.values()]
    enabled_rules = [r for r in rules if r["enabled"]]
    
    return {
        "rules": rules,
        "total": len(rules),
        "enabled_count": len(enabled_rules),
    }


@router.put("/rules/{rule_id}")
async def update_world_rule(rule_id: str, enabled: bool):
    """
    更新单个世界规则的启用状态
    
    Args:
        rule_id: 规则ID
        enabled: 是否启用
    
    Returns:
        更新后的规则
    """
    if rule_id not in _world_rules:
        raise HTTPException(
            status_code=404,
            detail=f"规则不存在: {rule_id}"
        )
    
    old_enabled = _world_rules[rule_id].enabled
    _world_rules[rule_id].enabled = enabled
    
    # 发布规则变更事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_RULE_CHANGED,
        data={
            "rule_id": rule_id,
            "rule_name": _world_rules[rule_id].name,
            "old_enabled": old_enabled,
            "new_enabled": enabled,
        },
        source="api",
    ))
    
    action = "启用" if enabled else "禁用"
    logger.info(f"世界规则已{action}: {_world_rules[rule_id].name}")
    
    return {
        "success": True,
        "message": f"规则已{action}",
        "rule": _world_rules[rule_id].model_dump(),
    }


@router.post("/event")
async def trigger_world_event(request: TriggerEventRequest):
    """
    触发世界事件
    
    触发一个全局事件，可以是公告、灾难、庆典或经济事件
    
    Args:
        event_name: 事件名称
        event_type: 事件类型 (announcement/disaster/celebration/economic)
        description: 事件描述
        duration_hours: 持续时间（游戏小时）
        affect_all_agents: 是否影响所有智能体
        parameters: 事件参数
    
    Returns:
        事件触发结果
    """
    from app.agents.memory import Memory, MemoryType
    
    # 验证事件类型
    valid_types = ["announcement", "disaster", "celebration", "economic"]
    if request.event_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的事件类型，必须是: {', '.join(valid_types)}"
        )
    
    # 计算事件重要性
    importance_map = {
        "announcement": 5,
        "disaster": 9,
        "celebration": 7,
        "economic": 6,
    }
    importance = importance_map.get(request.event_type, 5)
    
    affected_count = 0
    
    # 为智能体添加事件记忆
    if request.affect_all_agents:
        agents = agent_manager.get_all()
        event_content = f"[{request.event_name}] {request.description}" if request.description else f"[{request.event_name}]"
        
        for agent in agents:
            memory = Memory(
                type=MemoryType.EVENT,
                content=event_content,
                importance=importance,
                keywords={request.event_type, request.event_name, "世界事件"},
            )
            agent.memory.add(memory)
            affected_count += 1
    
    # 发布世界事件
    await event_bus.publish(Event(
        event_type=EventType.WORLD_EVENT,
        data={
            "event_name": request.event_name,
            "event_type": request.event_type,
            "description": request.description,
            "duration_hours": request.duration_hours,
            "affected_agents": affected_count,
            "parameters": request.parameters,
            "timestamp": datetime.now().isoformat(),
        },
        source="api",
    ))
    
    logger.info(f"世界事件已触发: {request.event_name} ({request.event_type})")
    
    return {
        "success": True,
        "message": f"事件已触发: {request.event_name}",
        "event_name": request.event_name,
        "event_type": request.event_type,
        "affected_agents": affected_count,
        "duration_hours": request.duration_hours,
    }


@router.get("/control/status")
async def get_control_status():
    """
    获取世界控制状态概览
    
    Returns:
        世界控制相关的状态信息
    """
    agents = agent_manager.get_all()
    enabled_rules = [r for r in _world_rules.values() if r.enabled]
    
    return {
        "agents_count": len(agents),
        "active_rules": [r.model_dump() for r in enabled_rules],
        "active_rules_count": len(enabled_rules),
        "clock_status": world_clock.to_dict(),
        "is_paused": world_clock.is_paused,
    }

