"""
自动扩展API
==========
提供社会平衡检测和自动扩展功能的API
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.agents.balance_detector import social_balance_detector, SocialBalanceReport
from app.agents.auto_expander import auto_expander, ExpansionEvent
from app.agents.manager import agent_manager


router = APIRouter(prefix="/expansion", tags=["自动扩展"])


# ===================
# 响应模型
# ===================

class OccupationGapResponse(BaseModel):
    """职业缺口响应"""
    occupation: str
    location_type: str
    location_name: str
    current_count: int
    needed_count: int
    gap: int
    priority: float


class SocialIsolateResponse(BaseModel):
    """社交孤岛响应"""
    agent_id: str
    agent_name: str
    social_need: float
    relationship_count: int
    loneliness_score: float
    recommended_match_traits: List[str]


class PopulationImbalanceResponse(BaseModel):
    """人口失衡响应"""
    category: str
    current_distribution: dict
    imbalance_score: float
    recommendations: List[str]


class BalanceReportResponse(BaseModel):
    """平衡报告响应"""
    timestamp: str
    total_population: int
    occupation_gaps: List[OccupationGapResponse]
    social_isolates_count: int
    population_imbalances: List[PopulationImbalanceResponse]
    overall_health_score: float
    urgent_needs: List[str]


class ExpansionEventResponse(BaseModel):
    """扩展事件响应"""
    event_type: str
    agent_id: str
    agent_name: str
    reason: str
    timestamp: str
    details: dict


class ExpanderStatusResponse(BaseModel):
    """扩展器状态响应"""
    is_running: bool
    last_check: Optional[str]
    last_expansion: Optional[str]
    check_interval: int
    current_population: int
    min_population: int
    max_population: int
    recent_events_count: int


class AutoBalanceResponse(BaseModel):
    """自动平衡响应"""
    created: int
    removed: int
    health_score: float


class CreateAgentRequest(BaseModel):
    """创建智能体请求"""
    occupation: Optional[str] = Field(None, description="指定职业")
    use_llm: bool = Field(default=False, description="是否使用LLM生成")
    for_isolate_id: Optional[str] = Field(None, description="为指定孤独者创建朋友")


class CreateAgentResponse(BaseModel):
    """创建智能体响应"""
    success: bool
    agent_id: Optional[str]
    agent_name: Optional[str]
    message: str


# ===================
# 社会平衡检测API
# ===================

@router.get("/balance/report", response_model=BalanceReportResponse)
async def get_balance_report():
    """
    获取社会平衡报告
    
    包含职业缺口、社交孤岛、人口失衡等信息
    """
    report = social_balance_detector.generate_report()
    
    return BalanceReportResponse(
        timestamp=report.timestamp.isoformat(),
        total_population=report.total_population,
        occupation_gaps=[
            OccupationGapResponse(
                occupation=g.occupation,
                location_type=g.location_type,
                location_name=g.location_name,
                current_count=g.current_count,
                needed_count=g.needed_count,
                gap=g.gap,
                priority=g.priority,
            )
            for g in report.occupation_gaps
        ],
        social_isolates_count=len(report.social_isolates),
        population_imbalances=[
            PopulationImbalanceResponse(
                category=i.category,
                current_distribution=i.current_distribution,
                imbalance_score=i.imbalance_score,
                recommendations=i.recommendations,
            )
            for i in report.population_imbalances
        ],
        overall_health_score=report.overall_health_score,
        urgent_needs=report.urgent_needs,
    )


@router.get("/balance/gaps", response_model=List[OccupationGapResponse])
async def get_occupation_gaps():
    """获取职业缺口列表"""
    gaps = social_balance_detector.detect_occupation_gaps()
    
    return [
        OccupationGapResponse(
            occupation=g.occupation,
            location_type=g.location_type,
            location_name=g.location_name,
            current_count=g.current_count,
            needed_count=g.needed_count,
            gap=g.gap,
            priority=g.priority,
        )
        for g in gaps
    ]


@router.get("/balance/isolates", response_model=List[SocialIsolateResponse])
async def get_social_isolates(
    threshold: float = Query(0.6, ge=0, le=1, description="孤独阈值"),
):
    """
    获取社交孤岛列表
    
    - **threshold**: 孤独分数阈值，越高越孤独
    """
    isolates = social_balance_detector.detect_social_isolates(
        loneliness_threshold=threshold
    )
    
    return [
        SocialIsolateResponse(
            agent_id=i.agent_id,
            agent_name=i.agent_name,
            social_need=i.social_need,
            relationship_count=i.relationship_count,
            loneliness_score=i.loneliness_score,
            recommended_match_traits=i.recommended_match_traits,
        )
        for i in isolates
    ]


@router.get("/balance/imbalances", response_model=List[PopulationImbalanceResponse])
async def get_population_imbalances():
    """获取人口失衡列表"""
    imbalances = social_balance_detector.detect_population_imbalances()
    
    return [
        PopulationImbalanceResponse(
            category=i.category,
            current_distribution=i.current_distribution,
            imbalance_score=i.imbalance_score,
            recommendations=i.recommendations,
        )
        for i in imbalances
    ]


# ===================
# 自动扩展API
# ===================

@router.get("/status", response_model=ExpanderStatusResponse)
async def get_expander_status():
    """获取扩展器状态"""
    status = auto_expander.get_status()
    return ExpanderStatusResponse(**status)


@router.post("/start")
async def start_auto_expander(background_tasks: BackgroundTasks):
    """
    启动自动扩展器
    
    在后台运行定时检查任务
    """
    if auto_expander._is_running:
        return {"message": "Auto expander is already running"}
    
    background_tasks.add_task(auto_expander.start)
    
    return {"message": "Auto expander started"}


@router.post("/stop")
async def stop_auto_expander():
    """停止自动扩展器"""
    if not auto_expander._is_running:
        return {"message": "Auto expander is not running"}
    
    auto_expander.stop()
    
    return {"message": "Auto expander stopped"}


@router.post("/balance", response_model=AutoBalanceResponse)
async def trigger_auto_balance():
    """
    手动触发自动平衡
    
    立即执行一次社会平衡检查和调整
    """
    stats = await auto_expander.auto_balance()
    report = social_balance_detector.last_report
    
    return AutoBalanceResponse(
        created=stats["created"],
        removed=stats["removed"],
        health_score=report.overall_health_score if report else 0,
    )


@router.get("/events", response_model=List[ExpansionEventResponse])
async def get_expansion_events(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
):
    """获取最近的扩展事件"""
    events = auto_expander.get_recent_events(limit)
    
    return [
        ExpansionEventResponse(
            event_type=e.event_type,
            agent_id=e.agent_id,
            agent_name=e.agent_name,
            reason=e.reason,
            timestamp=e.timestamp.isoformat(),
            details=e.details,
        )
        for e in reversed(events)  # 最新的在前
    ]


# ===================
# 手动创建API
# ===================

@router.post("/create", response_model=CreateAgentResponse)
async def create_agent_manually(request: CreateAgentRequest):
    """
    手动创建智能体
    
    - **occupation**: 指定职业（可选）
    - **use_llm**: 是否使用LLM生成更独特的角色
    - **for_isolate_id**: 为指定的孤独者创建朋友
    """
    # 检查人口上限
    if agent_manager.count() >= auto_expander._max_population:
        return CreateAgentResponse(
            success=False,
            agent_id=None,
            agent_name=None,
            message="已达人口上限",
        )
    
    try:
        if request.for_isolate_id:
            # 为孤独者创建朋友
            isolates = social_balance_detector.detect_social_isolates()
            target_isolate = None
            
            for isolate in isolates:
                if isolate.agent_id == request.for_isolate_id:
                    target_isolate = isolate
                    break
            
            if not target_isolate:
                return CreateAgentResponse(
                    success=False,
                    agent_id=None,
                    agent_name=None,
                    message="未找到指定的孤独者",
                )
            
            agent = await auto_expander.create_friend_for_isolate(
                target_isolate,
                use_llm=request.use_llm,
            )
        
        elif request.occupation:
            # 为职业缺口创建
            from app.agents.balance_detector import OccupationGap
            
            gap = OccupationGap(
                occupation=request.occupation,
                location_type="",
                location_name="手动创建",
                current_count=0,
                needed_count=1,
                priority=1.0,
            )
            
            agent = await auto_expander.create_agent_for_gap(
                gap,
                use_llm=request.use_llm,
            )
        
        else:
            # 随机创建
            from app.agents.generator import generate_single_agent
            
            agent = await generate_single_agent(use_llm=request.use_llm)
        
        if agent:
            return CreateAgentResponse(
                success=True,
                agent_id=agent.id,
                agent_name=agent.name,
                message=f"成功创建智能体: {agent.name} ({agent.occupation})",
            )
        else:
            return CreateAgentResponse(
                success=False,
                agent_id=None,
                agent_name=None,
                message="创建失败",
            )
    
    except Exception as e:
        return CreateAgentResponse(
            success=False,
            agent_id=None,
            agent_name=None,
            message=f"创建错误: {str(e)}",
        )


@router.delete("/agent/{agent_id}")
async def remove_agent_manually(
    agent_id: str,
    reason: str = Query("管理员手动移除", description="移除原因"),
):
    """
    手动移除智能体
    
    - **agent_id**: 智能体ID
    - **reason**: 移除原因
    """
    agent = agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    success = await auto_expander.process_agent_leaving(agent, reason)
    
    if success:
        return {
            "success": True,
            "message": f"成功移除智能体: {agent.name}",
            "agent_id": agent_id,
        }
    else:
        return {
            "success": False,
            "message": "移除失败（可能已达最低人口限制）",
            "agent_id": agent_id,
        }
