"""
智能体API路由
=============
提供智能体的CRUD操作和状态查询接口

端点：
- GET /api/agents - 智能体列表
- GET /api/agents/count - 数量统计
- GET /api/agents/{id} - 详情
- POST /api/agents/generate - 生成新智能体
- POST /api/agents/generate/batch - 批量生成
- GET /api/agents/{id}/activities - 活动历史（Phase 7）
"""

from datetime import datetime, date as date_type
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

from app.agents import (
    agent_manager,
    Agent,
    AgentState,
    generate_single_agent,
    generate_initial_agents,
    Personality,
    Position,
)
from app.core.config import settings
from app.core.locations import location_manager


router = APIRouter()


# ===================
# Pydantic 模型定义
# ===================

class PersonalitySchema(BaseModel):
    """大五人格模型"""
    openness: int = Field(ge=0, le=100, description="开放性")
    conscientiousness: int = Field(ge=0, le=100, description="尽责性")
    extraversion: int = Field(ge=0, le=100, description="外向性")
    agreeableness: int = Field(ge=0, le=100, description="宜人性")
    neuroticism: int = Field(ge=0, le=100, description="神经质")


class NeedsSchema(BaseModel):
    """需求状态"""
    hunger: float = Field(ge=0, le=100, description="饥饿程度")
    fatigue: float = Field(ge=0, le=100, description="疲劳程度")
    social: float = Field(ge=0, le=100, description="社交需求")
    entertainment: float = Field(ge=0, le=100, description="娱乐需求")


class PositionSchema(BaseModel):
    """位置信息"""
    x: float = Field(description="X坐标")
    y: float = Field(description="Y坐标")
    location_id: Optional[str] = Field(default=None, description="所在地点ID")
    location_name: Optional[str] = Field(default=None, description="所在地点名称")


class AgentBriefSchema(BaseModel):
    """智能体简要信息（用于列表显示）"""
    id: str
    name: str
    age: int
    occupation: str
    position: PositionSchema
    current_action: Optional[str] = None
    is_in_conversation: bool = False


class AgentDetailSchema(BaseModel):
    """智能体详细信息"""
    id: str
    name: str
    age: int
    gender: str
    occupation: str
    personality: PersonalitySchema
    needs: NeedsSchema
    position: PositionSchema
    balance: float = Field(description="账户余额")
    model_name: str = Field(description="使用的LLM模型")
    current_thinking: Optional[str] = Field(default=None, description="当前想法")
    current_action: Optional[str] = Field(default=None, description="当前行动")
    backstory: Optional[str] = Field(default=None, description="背景故事")
    traits: List[str] = Field(default_factory=list, description="性格特点")
    created_at: str
    state: str
    wellbeing: float = Field(description="幸福指数")


class GenerateRequest(BaseModel):
    """生成智能体请求"""
    use_llm: bool = Field(default=False, description="是否使用LLM生成")
    occupation: Optional[str] = Field(default=None, description="指定职业")


class BatchGenerateRequest(BaseModel):
    """批量生成请求"""
    count: int = Field(ge=1, le=50, description="生成数量")
    use_llm_ratio: float = Field(default=0.2, ge=0, le=1, description="LLM生成比例")


class CreateAgentRequest(BaseModel):
    """创建智能体请求"""
    name: str = Field(..., description="姓名", min_length=1, max_length=20)
    age: int = Field(default=25, ge=18, le=80, description="年龄")
    gender: str = Field(default="男", description="性别")
    occupation: str = Field(default="自由职业", description="职业")
    backstory: str = Field(default="", description="背景故事", max_length=500)
    traits: List[str] = Field(default=[], description="性格标签")
    balance: float = Field(default=1000.0, ge=0, description="初始资金")
    # 人格参数（大五人格模型）
    openness: int = Field(default=50, ge=0, le=100, description="开放性")
    conscientiousness: int = Field(default=50, ge=0, le=100, description="尽责性")
    extraversion: int = Field(default=50, ge=0, le=100, description="外向性")
    agreeableness: int = Field(default=50, ge=0, le=100, description="宜人性")
    neuroticism: int = Field(default=50, ge=0, le=100, description="神经质")
    # 初始位置（可选）
    location_id: Optional[str] = Field(default=None, description="初始所在地点ID")


class UpdateAgentRequest(BaseModel):
    """更新智能体请求"""
    name: Optional[str] = Field(None, description="姓名", min_length=1, max_length=20)
    occupation: Optional[str] = Field(None, description="职业")
    backstory: Optional[str] = Field(None, description="背景故事", max_length=500)
    traits: Optional[List[str]] = Field(None, description="性格标签")
    balance: Optional[float] = Field(None, ge=0, description="资金")
    # 人格参数
    openness: Optional[int] = Field(None, ge=0, le=100, description="开放性")
    conscientiousness: Optional[int] = Field(None, ge=0, le=100, description="尽责性")
    extraversion: Optional[int] = Field(None, ge=0, le=100, description="外向性")
    agreeableness: Optional[int] = Field(None, ge=0, le=100, description="宜人性")
    neuroticism: Optional[int] = Field(None, ge=0, le=100, description="神经质")


class CommandRequest(BaseModel):
    """智能体指令请求"""
    command_type: str = Field(..., description="指令类型: move/talk/activity/custom")
    target: Optional[str] = Field(None, description="目标（地点名/智能体名/活动名）")
    custom_text: Optional[str] = Field(None, description="自由文本指令", max_length=200)


class AgentStatsSchema(BaseModel):
    """智能体统计"""
    total: int
    max: int
    by_occupation: dict
    by_state: dict
    by_location: dict
    avg_balance: float
    avg_wellbeing: float


class AgentListResponse(BaseModel):
    """智能体列表响应"""
    agents: List[dict]
    total: int


# ===================
# 辅助函数
# ===================

def agent_to_brief(agent: Agent) -> dict:
    """转换为简要信息（符合前端期望格式）"""
    return {
        "id": agent.id,
        "name": agent.name,
        "age": agent.age,
        "gender": agent.gender,
        "occupation": agent.occupation,
        "state": agent.state.value,
        "current_location": agent.position.location_name or "未知",
        "current_action": agent.current_action.type.value,
    }


def agent_to_detail(agent: Agent) -> dict:
    """转换为详细信息"""
    return {
        "id": agent.id,
        "name": agent.name,
        "age": agent.age,
        "gender": agent.gender,
        "occupation": agent.occupation,
        "personality": agent.personality.to_dict(),
        "needs": {
            "hunger": agent.needs.hunger,
            "fatigue": agent.needs.fatigue,
            "social": agent.needs.social,
            "entertainment": agent.needs.entertainment,
        },
        "position": {
            "x": agent.position.x,
            "y": agent.position.y,
            "location_id": agent.position.location_id,
            "location_name": agent.position.location_name,
        },
        "balance": agent.balance,
        "model_name": agent.model_name,
        "current_thinking": agent.current_action.thinking,
        "current_action": agent.current_action.type.value,
        "backstory": agent.backstory,
        "traits": agent.traits,
        "created_at": agent.created_at.isoformat(),
        "state": agent.state.value,
        "wellbeing": agent.get_wellbeing(),
    }


# ===================
# API 端点
# ===================

@router.get("", response_model=AgentListResponse, summary="获取智能体列表")
async def list_agents(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    occupation: Optional[str] = Query(None, description="按职业筛选"),
    location: Optional[str] = Query(None, description="按地点筛选"),
    state: Optional[str] = Query(None, description="按状态筛选"),
):
    """
    获取智能体列表
    
    支持分页和筛选
    """
    agents = agent_manager.get_all()
    total = len(agents)
    
    # 筛选
    if occupation:
        agents = [a for a in agents if a.occupation == occupation]
    if location:
        agents = [a for a in agents if a.position.location_name == location]
    if state:
        agents = [a for a in agents if a.state.value == state]
    
    # 分页
    agents = agents[skip:skip + limit]
    
    return {
        "agents": [agent_to_brief(a) for a in agents],
        "total": total,
    }


@router.get("/count", response_model=AgentStatsSchema, summary="获取智能体统计")
async def get_agent_stats():
    """
    获取智能体数量统计
    """
    return agent_manager.get_stats()


@router.get("/occupations", summary="获取职业列表")
async def get_occupations():
    """获取所有智能体的职业列表"""
    agents = agent_manager.get_all()
    occupations = {}
    for agent in agents:
        occ = agent.occupation
        occupations[occ] = occupations.get(occ, 0) + 1
    return {"occupations": occupations}


@router.get("/{agent_id}", response_model=AgentDetailSchema, summary="获取智能体详情")
async def get_agent(agent_id: str):
    """
    获取单个智能体详情
    
    Args:
        agent_id: 智能体ID
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    return agent_to_detail(agent)


@router.get("/name/{name}", response_model=AgentDetailSchema, summary="通过名字获取智能体")
async def get_agent_by_name(name: str):
    """通过名字获取智能体详情"""
    agent = agent_manager.get_by_name(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {name} 不存在")
    
    return agent_to_detail(agent)


@router.get("/{agent_id}/memories", summary="获取智能体记忆")
async def get_agent_memories(
    agent_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """
    获取智能体的记忆列表
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    memories = agent.memory.retrieve_recent(limit)
    return [m.to_dict() for m in memories]


@router.get("/{agent_id}/relationships", summary="获取智能体关系")
async def get_agent_relationships(agent_id: str):
    """
    获取智能体的社交关系
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    return [rel.to_dict() for rel in agent.relationships.values()]


@router.post("/generate", summary="生成新智能体")
async def generate_agent(request: GenerateRequest):
    """
    生成单个新智能体
    
    Args:
        use_llm: 是否使用LLM生成（更独特但较慢）
        occupation: 指定职业
    """
    if agent_manager.count() >= settings.max_agent_count:
        raise HTTPException(
            status_code=400,
            detail=f"智能体数量已达上限: {settings.max_agent_count}"
        )
    
    agent = await generate_single_agent(
        use_llm=request.use_llm,
        occupation=request.occupation,
    )
    
    return {
        "status": "success",
        "agent": agent_to_brief(agent),
    }


@router.post("/generate/batch", summary="批量生成智能体")
async def batch_generate_agents(
    request: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    批量生成智能体
    
    这是一个耗时操作，会在后台执行
    """
    current_count = agent_manager.count()
    available = settings.max_agent_count - current_count
    
    if available <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"智能体数量已达上限: {settings.max_agent_count}"
        )
    
    count = min(request.count, available)
    
    # 后台执行生成
    async def generate_task():
        await generate_initial_agents(
            count=count,
            use_llm_ratio=request.use_llm_ratio,
        )
    
    background_tasks.add_task(generate_task)
    
    return {
        "status": "started",
        "message": f"正在后台生成 {count} 个智能体",
        "count": count,
    }


@router.post("/{agent_id}/model", summary="修改智能体模型")
async def change_agent_model(agent_id: str, model_name: str):
    """
    修改智能体使用的LLM模型
    
    Args:
        agent_id: 智能体ID
        model_name: 新的模型名称
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    agent.model_name = model_name
    
    return {"status": "ok", "agent_id": agent_id, "model_name": model_name}


@router.post("/{agent_id}/follow", summary="关注智能体")
async def follow_agent(agent_id: str):
    """
    关注某个智能体（前端用于跟随模式）
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    return {
        "status": "ok",
        "agent_id": agent_id,
        "name": agent.name,
        "message": f"已关注 {agent.name}",
    }


@router.delete("/{agent_id}", summary="删除智能体")
async def delete_agent(agent_id: str):
    """删除指定智能体"""
    if not agent_manager.remove(agent_id):
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    return {"status": "ok", "message": f"已删除智能体 {agent_id}"}


# ===================
# 创建/更新/指令 API
# ===================

@router.post("", summary="创建智能体")
async def create_agent(request: CreateAgentRequest):
    """
    手动创建智能体（带完整表单）
    
    与 /generate 不同，这个端点允许用户完全自定义智能体属性
    """
    # 检查数量限制
    if agent_manager.count() >= settings.max_agent_count:
        raise HTTPException(
            status_code=400,
            detail=f"智能体数量已达上限: {settings.max_agent_count}"
        )
    
    # 检查名字是否重复
    if agent_manager.get_by_name(request.name):
        raise HTTPException(
            status_code=400,
            detail=f"智能体名称已存在: {request.name}"
        )
    
    # 创建人格
    personality = Personality(
        openness=request.openness,
        conscientiousness=request.conscientiousness,
        extraversion=request.extraversion,
        agreeableness=request.agreeableness,
        neuroticism=request.neuroticism,
    )
    
    # 确定初始位置
    position = Position()
    if request.location_id:
        loc = location_manager.get_location(request.location_id)
        if loc:
            position = Position(
                x=loc.x,
                y=loc.y,
                location_id=loc.id,
                location_name=loc.name,
            )
            loc.enter("temp")  # 临时进入，后续会正式分配
    else:
        # 随机分配一个住宅位置
        available_homes = location_manager.get_locations_by_type("apartment")
        if not available_homes:
            available_homes = location_manager.get_locations_by_type("house")
        if available_homes:
            import random
            home = random.choice(available_homes)
            position = Position(
                x=home.x,
                y=home.y,
                location_id=home.id,
                location_name=home.name,
            )
    
    # 创建智能体
    agent = Agent(
        name=request.name,
        age=request.age,
        gender=request.gender,
        occupation=request.occupation,
        backstory=request.backstory,
        traits=request.traits,
        personality=personality,
        balance=request.balance,
        position=position,
        home_location_id=position.location_id,
    )
    
    # 添加到管理器
    try:
        agent_manager.add(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "success": True,
        "message": f"成功创建智能体: {agent.name}",
        "agent": agent_to_detail(agent),
    }


@router.put("/{agent_id}", summary="更新智能体属性")
async def update_agent(agent_id: str, request: UpdateAgentRequest):
    """
    更新智能体属性
    
    支持部分更新，只更新请求中提供的字段
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    # 检查名字是否重复（如果要改名）
    if request.name and request.name != agent.name:
        existing = agent_manager.get_by_name(request.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"智能体名称已存在: {request.name}"
            )
        # 更新名字索引
        agent_manager._by_name.pop(agent.name, None)
        agent.name = request.name
        agent_manager._by_name[agent.name] = agent.id
    
    # 更新其他字段
    if request.occupation is not None:
        agent.occupation = request.occupation
    if request.backstory is not None:
        agent.backstory = request.backstory
    if request.traits is not None:
        agent.traits = request.traits
    if request.balance is not None:
        agent.balance = request.balance
    
    # 更新人格参数
    if request.openness is not None:
        agent.personality.openness = request.openness
    if request.conscientiousness is not None:
        agent.personality.conscientiousness = request.conscientiousness
    if request.extraversion is not None:
        agent.personality.extraversion = request.extraversion
    if request.agreeableness is not None:
        agent.personality.agreeableness = request.agreeableness
    if request.neuroticism is not None:
        agent.personality.neuroticism = request.neuroticism
    
    # 持久化保存
    agent_manager._save_to_file()
    
    return {
        "success": True,
        "message": f"成功更新智能体: {agent.name}",
        "agent": agent_to_detail(agent),
    }


@router.post("/{agent_id}/command", summary="给智能体下达指令")
async def command_agent(agent_id: str, request: CommandRequest):
    """
    给智能体下达指令
    
    指令类型：
    - move: 移动到指定地点
    - talk: 与指定智能体交谈
    - activity: 执行指定活动
    - custom: 自由文本指令（通过LLM解析）
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    command_type = request.command_type.lower()
    
    if command_type == "move":
        if not request.target:
            raise HTTPException(status_code=400, detail="移动指令需要指定目标地点")
        
        # 查找目标地点
        target_loc = location_manager.get_by_name(request.target)
        if not target_loc:
            raise HTTPException(status_code=404, detail=f"地点不存在: {request.target}")
        
        # 添加移动记忆
        agent.add_memory(
            content=f"收到指令：前往{request.target}",
            importance=7.0,
        )
        
        # 设置目标（下一次决策时会处理）
        agent.action_queue.append({
            "type": "move",
            "target_location": target_loc.name,
            "target_id": target_loc.id,
        })
        
        return {
            "success": True,
            "message": f"已下达移动指令: 前往{request.target}",
            "command_type": "move",
            "target": request.target,
        }
    
    elif command_type == "talk":
        if not request.target:
            raise HTTPException(status_code=400, detail="交谈指令需要指定目标智能体")
        
        # 查找目标智能体
        target_agent = agent_manager.get_by_name(request.target)
        if not target_agent:
            raise HTTPException(status_code=404, detail=f"智能体不存在: {request.target}")
        
        # 添加交谈意图记忆
        agent.add_memory(
            content=f"收到指令：找{request.target}聊天",
            importance=7.0,
        )
        
        agent.action_queue.append({
            "type": "talk",
            "target_agent": target_agent.name,
            "target_id": target_agent.id,
        })
        
        return {
            "success": True,
            "message": f"已下达交谈指令: 与{request.target}交谈",
            "command_type": "talk",
            "target": request.target,
        }
    
    elif command_type == "activity":
        if not request.target:
            raise HTTPException(status_code=400, detail="活动指令需要指定活动名称")
        
        # 添加活动指令记忆
        agent.add_memory(
            content=f"收到指令：去{request.target}",
            importance=7.0,
        )
        
        agent.action_queue.append({
            "type": "activity",
            "activity": request.target,
        })
        
        return {
            "success": True,
            "message": f"已下达活动指令: {request.target}",
            "command_type": "activity",
            "target": request.target,
        }
    
    elif command_type == "custom":
        if not request.custom_text:
            raise HTTPException(status_code=400, detail="自定义指令需要提供文本内容")
        
        # 添加自定义指令作为高优先级记忆
        agent.add_memory(
            content=f"收到重要指令：{request.custom_text}",
            importance=9.0,
        )
        
        agent.action_queue.append({
            "type": "custom",
            "instruction": request.custom_text,
        })
        
        return {
            "success": True,
            "message": f"已下达自定义指令",
            "command_type": "custom",
            "instruction": request.custom_text,
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的指令类型: {command_type}。支持的类型: move, talk, activity, custom"
        )


# ===================
# 活动日志 API (Phase 7)
# ===================

class ActivitySchema(BaseModel):
    """活动日志响应模型"""
    id: int
    agent_id: str
    agent_name: str
    activity_type: str
    action: str
    target: Optional[str] = None
    location: Optional[str] = None
    thinking: Optional[str] = None
    conversation_id: Optional[str] = None
    conversation_partner: Optional[str] = None
    message_content: Optional[str] = None
    reflection_content: Optional[str] = None
    game_time: str
    created_at: str


class ActivityListResponse(BaseModel):
    """活动列表响应"""
    activities: List[ActivitySchema]
    total: int


class DailySummaryResponse(BaseModel):
    """每日活动汇总响应"""
    date: str
    agent_id: str
    total_activities: int
    by_type: dict
    by_action: dict
    conversation_partners: dict


@router.get("/{agent_id}/activities", response_model=ActivityListResponse, summary="获取智能体活动历史")
async def get_agent_activities(
    agent_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    activity_type: Optional[str] = Query(None, description="活动类型筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取智能体的活动历史记录
    
    活动类型:
    - decision: 决策
    - conversation: 对话
    - reflection: 反思
    - reaction: 反应
    - plan: 计划
    """
    # 验证智能体存在
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    try:
        from app.database import get_async_session
        from app.database.crud.activity_logs import ActivityLogCRUD
        
        async with get_async_session() as db:
            activities = await ActivityLogCRUD.get_by_agent(
                db=db,
                agent_id=agent_id,
                start_time=start_time,
                end_time=end_time,
                activity_type=activity_type,
                limit=limit,
                offset=offset,
            )
            
            total = await ActivityLogCRUD.count_by_agent(db, agent_id)
            
            return {
                "activities": [
                    {
                        "id": a.id,
                        "agent_id": a.agent_id,
                        "agent_name": a.agent_name,
                        "activity_type": a.activity_type,
                        "action": a.action,
                        "target": a.target,
                        "location": a.location,
                        "thinking": a.thinking,
                        "conversation_id": a.conversation_id,
                        "conversation_partner": a.conversation_partner,
                        "message_content": a.message_content,
                        "reflection_content": a.reflection_content,
                        "game_time": a.game_time.isoformat() if a.game_time else "",
                        "created_at": a.created_at.isoformat() if a.created_at else "",
                    }
                    for a in activities
                ],
                "total": total,
            }
    except Exception as e:
        # 数据库不可用时返回空数组（优雅降级）
        logger.warning(f"获取活动历史失败（数据库可能未启动）: {e}")
        return {"activities": [], "total": 0}


@router.get("/{agent_id}/activities/daily", response_model=DailySummaryResponse, summary="获取智能体每日活动汇总")
async def get_agent_daily_activities(
    agent_id: str,
    date: Optional[date_type] = Query(None, description="目标日期，默认今天"),
):
    """
    获取智能体某天的活动汇总统计
    
    包含:
    - 各类型活动数量
    - 各动作类型数量
    - 对话伙伴统计
    """
    # 验证智能体存在
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
    
    try:
        from app.database import get_async_session
        from app.database.crud.activity_logs import ActivityLogCRUD
        
        async with get_async_session() as db:
            summary = await ActivityLogCRUD.get_daily_summary(
                db=db,
                agent_id=agent_id,
                target_date=date,
            )
            
            return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活动汇总失败: {str(e)}")
