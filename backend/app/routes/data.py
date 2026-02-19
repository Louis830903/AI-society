"""
数据导出和存档管理API
====================
提供世界状态保存、恢复和数据导出功能
"""

from datetime import datetime
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database.crud import WorldStateCRUD, LLMCallCRUD
from app.services.world_state_service import WorldStateService, create_world_state_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


# ===================
# 请求/响应模型
# ===================

class SaveStateRequest(BaseModel):
    """保存状态请求"""
    game_time: datetime = Field(..., description="游戏时间")
    clock_state: dict = Field(default_factory=dict, description="时钟状态")
    cost_tracker_state: dict = Field(default_factory=dict, description="成本统计状态")
    description: Optional[str] = Field(None, description="保存描述")
    is_auto_save: bool = Field(default=False, description="是否自动保存")


class SaveStateResponse(BaseModel):
    """保存状态响应"""
    id: int
    game_time: str
    description: Optional[str]
    is_auto_save: bool
    created_at: str


class WorldStateResponse(BaseModel):
    """世界状态响应"""
    id: int
    game_time: Optional[str]
    real_time: Optional[str]
    clock_state: Optional[dict]
    cost_tracker_state: Optional[dict]
    description: Optional[str]
    is_auto_save: bool
    created_at: Optional[str]


class SaveListItem(BaseModel):
    """保存列表项"""
    id: int
    game_time: Optional[str]
    description: Optional[str]
    is_auto_save: bool
    created_at: Optional[str]


class SaveStatsResponse(BaseModel):
    """保存统计响应"""
    total: int
    auto_saves: int
    manual_saves: int


class LLMStatsResponse(BaseModel):
    """LLM调用统计响应"""
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_reasoning_tokens: int
    total_cost: float
    avg_response_time_ms: float


class ModelStatsItem(BaseModel):
    """模型统计项"""
    model_name: str
    calls: int
    cost: float
    input_tokens: int
    output_tokens: int


class ExportResponse(BaseModel):
    """导出响应"""
    version: str
    exported_at: str
    agents_count: int
    relationships_count: int


# ===================
# 存档管理API
# ===================

@router.post("/saves", response_model=SaveStateResponse)
async def save_world_state(
    request: SaveStateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    保存世界状态
    
    - **game_time**: 当前游戏时间
    - **clock_state**: 时钟状态数据
    - **cost_tracker_state**: 成本统计数据
    - **description**: 保存描述（可选）
    - **is_auto_save**: 是否为自动保存
    """
    service = create_world_state_service(db)
    
    state = await service.save_state(
        game_time=request.game_time,
        clock_state=request.clock_state,
        cost_tracker_state=request.cost_tracker_state,
        description=request.description,
        is_auto_save=request.is_auto_save,
    )
    
    return SaveStateResponse(
        id=state.id,
        game_time=state.game_time.isoformat() if state.game_time else "",
        description=state.description,
        is_auto_save=state.is_auto_save,
        created_at=state.created_at.isoformat() if state.created_at else "",
    )


@router.get("/saves", response_model=List[SaveListItem])
async def list_saves(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    manual_only: bool = Query(False, description="仅返回手动保存"),
    db: AsyncSession = Depends(get_db),
):
    """
    列出保存记录
    
    - **limit**: 返回数量上限
    - **manual_only**: 是否仅返回手动保存
    """
    service = create_world_state_service(db)
    saves = await service.list_saves(limit=limit, manual_only=manual_only)
    
    return [SaveListItem(**s) for s in saves]


@router.get("/saves/latest", response_model=WorldStateResponse)
async def get_latest_save(
    db: AsyncSession = Depends(get_db),
):
    """获取最新的保存状态"""
    service = create_world_state_service(db)
    state = await service.load_latest()
    
    if not state:
        raise HTTPException(status_code=404, detail="No saved state found")
    
    return WorldStateResponse(**state)


@router.get("/saves/{state_id}", response_model=WorldStateResponse)
async def get_save_by_id(
    state_id: int,
    db: AsyncSession = Depends(get_db),
):
    """根据ID获取保存状态"""
    service = create_world_state_service(db)
    state = await service.load_by_id(state_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Save not found")
    
    return WorldStateResponse(**state)


@router.delete("/saves/{state_id}")
async def delete_save(
    state_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除保存记录"""
    service = create_world_state_service(db)
    success = await service.delete_save(state_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Save not found")
    
    return {"message": "Save deleted", "id": state_id}


@router.post("/saves/cleanup")
async def cleanup_auto_saves(
    keep_count: int = Query(10, ge=1, le=50, description="保留数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    清理旧的自动保存
    
    保留最近的 keep_count 条自动保存记录
    """
    service = create_world_state_service(db)
    deleted_count = await service.cleanup_auto_saves(keep_count)
    
    return {
        "message": f"Cleaned up {deleted_count} old auto saves",
        "deleted_count": deleted_count,
        "kept_count": keep_count,
    }


@router.get("/saves/stats", response_model=SaveStatsResponse)
async def get_save_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取保存统计"""
    service = create_world_state_service(db)
    stats = await service.get_save_stats()
    
    return SaveStatsResponse(**stats)


# ===================
# 数据导出API
# ===================

@router.get("/export")
async def export_world_data(
    db: AsyncSession = Depends(get_db),
):
    """
    导出完整世界数据
    
    返回包含所有智能体、关系和状态的JSON数据
    可用于备份和数据分析
    """
    service = create_world_state_service(db)
    data = await service.export_full_state()
    
    return data


@router.get("/export/summary", response_model=ExportResponse)
async def get_export_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    获取导出数据摘要
    
    快速查看可导出数据的规模
    """
    service = create_world_state_service(db)
    data = await service.export_full_state()
    
    return ExportResponse(
        version=data.get("version", "1.0"),
        exported_at=data.get("exported_at", ""),
        agents_count=len(data.get("agents", [])),
        relationships_count=len(data.get("relationships", [])),
    )


# ===================
# LLM统计API
# ===================

@router.get("/llm/stats", response_model=LLMStatsResponse)
async def get_llm_stats(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取LLM调用统计
    
    - **start_time**: 统计开始时间（可选）
    - **end_time**: 统计结束时间（可选）
    """
    stats = await LLMCallCRUD.get_stats(db, start_time, end_time)
    
    return LLMStatsResponse(**stats)


@router.get("/llm/stats/daily", response_model=LLMStatsResponse)
async def get_daily_llm_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取今日LLM调用统计"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = await LLMCallCRUD.get_stats(db, start_time=today)
    
    return LLMStatsResponse(**stats)


@router.get("/llm/stats/monthly", response_model=LLMStatsResponse)
async def get_monthly_llm_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取本月LLM调用统计"""
    first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stats = await LLMCallCRUD.get_stats(db, start_time=first_day)
    
    return LLMStatsResponse(**stats)


@router.get("/llm/stats/by-model", response_model=List[ModelStatsItem])
async def get_llm_stats_by_model(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    db: AsyncSession = Depends(get_db),
):
    """按模型分组的LLM调用统计"""
    stats = await LLMCallCRUD.get_stats_by_model(db, start_time)
    
    return [ModelStatsItem(**s) for s in stats]


@router.get("/llm/cost/total")
async def get_total_llm_cost(
    db: AsyncSession = Depends(get_db),
):
    """获取总LLM成本"""
    total = await LLMCallCRUD.get_total_cost(db)
    daily = await LLMCallCRUD.get_daily_cost(db)
    monthly = await LLMCallCRUD.get_monthly_cost(db)
    
    return {
        "total_cost": total,
        "daily_cost": daily,
        "monthly_cost": monthly,
        "currency": "USD",
    }
