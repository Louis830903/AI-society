"""
世界状态CRUD操作
================
世界状态保存/恢复和LLM调用记录
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorldStateModel, LLMCallModel


class WorldStateCRUD:
    """世界状态CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(
        db: AsyncSession,
        game_time: datetime,
        clock_state: Optional[dict] = None,
        cost_tracker_state: Optional[dict] = None,
        description: Optional[str] = None,
        is_auto_save: bool = True,
    ) -> WorldStateModel:
        """
        创建世界状态快照
        
        Args:
            db: 数据库会话
            game_time: 游戏时间
            clock_state: 时钟状态
            cost_tracker_state: 成本统计状态
            description: 描述
            is_auto_save: 是否自动保存
            
        Returns:
            创建的世界状态记录
        """
        db_state = WorldStateModel(
            game_time=game_time,
            clock_state=clock_state,
            cost_tracker_state=cost_tracker_state,
            description=description,
            is_auto_save=is_auto_save,
        )
        db.add(db_state)
        await db.commit()
        await db.refresh(db_state)
        return db_state
    
    @staticmethod
    async def auto_save(
        db: AsyncSession,
        game_time: datetime,
        clock_state: dict,
        cost_tracker_state: dict,
    ) -> WorldStateModel:
        """自动保存世界状态"""
        return await WorldStateCRUD.create(
            db=db,
            game_time=game_time,
            clock_state=clock_state,
            cost_tracker_state=cost_tracker_state,
            description="Auto save",
            is_auto_save=True,
        )
    
    @staticmethod
    async def manual_save(
        db: AsyncSession,
        game_time: datetime,
        clock_state: dict,
        cost_tracker_state: dict,
        description: str = "Manual save",
    ) -> WorldStateModel:
        """手动保存世界状态"""
        return await WorldStateCRUD.create(
            db=db,
            game_time=game_time,
            clock_state=clock_state,
            cost_tracker_state=cost_tracker_state,
            description=description,
            is_auto_save=False,
        )
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, state_id: int) -> Optional[WorldStateModel]:
        """根据ID获取世界状态"""
        result = await db.execute(
            select(WorldStateModel).where(WorldStateModel.id == state_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_latest(db: AsyncSession) -> Optional[WorldStateModel]:
        """获取最新的世界状态"""
        result = await db.execute(
            select(WorldStateModel)
            .order_by(desc(WorldStateModel.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_latest_manual(db: AsyncSession) -> Optional[WorldStateModel]:
        """获取最新的手动保存状态"""
        result = await db.execute(
            select(WorldStateModel)
            .where(WorldStateModel.is_auto_save == False)
            .order_by(desc(WorldStateModel.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        auto_save_only: Optional[bool] = None,
    ) -> List[WorldStateModel]:
        """获取世界状态列表"""
        query = select(WorldStateModel)
        
        if auto_save_only is not None:
            query = query.where(WorldStateModel.is_auto_save == auto_save_only)
        
        query = query.order_by(desc(WorldStateModel.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_game_time_range(
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WorldStateModel]:
        """根据游戏时间范围获取状态"""
        result = await db.execute(
            select(WorldStateModel)
            .where(WorldStateModel.game_time.between(start_time, end_time))
            .order_by(WorldStateModel.game_time)
        )
        return list(result.scalars().all())
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete(db: AsyncSession, state_id: int) -> bool:
        """删除世界状态"""
        result = await db.execute(
            delete(WorldStateModel).where(WorldStateModel.id == state_id)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def cleanup_old_auto_saves(
        db: AsyncSession,
        keep_count: int = 10,
    ) -> int:
        """清理旧的自动保存，保留最近的 keep_count 条"""
        # 获取要保留的ID
        keep_ids_result = await db.execute(
            select(WorldStateModel.id)
            .where(WorldStateModel.is_auto_save == True)
            .order_by(desc(WorldStateModel.created_at))
            .limit(keep_count)
        )
        keep_ids = {row.id for row in keep_ids_result.all()}
        
        if not keep_ids:
            return 0
        
        # 删除其他自动保存
        result = await db.execute(
            delete(WorldStateModel).where(
                WorldStateModel.is_auto_save == True,
                WorldStateModel.id.not_in(keep_ids),
            )
        )
        await db.commit()
        return result.rowcount
    
    # ===================
    # 统计操作
    # ===================
    
    @staticmethod
    async def count(
        db: AsyncSession,
        auto_save_only: Optional[bool] = None,
    ) -> int:
        """计算世界状态数量"""
        query = select(func.count(WorldStateModel.id))
        
        if auto_save_only is not None:
            query = query.where(WorldStateModel.is_auto_save == auto_save_only)
        
        result = await db.execute(query)
        return result.scalar() or 0


class LLMCallCRUD:
    """LLM调用记录CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(
        db: AsyncSession,
        model_name: str,
        call_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        reasoning_tokens: int = 0,
        cost: float = 0.0,
        response_time_ms: int = 0,
        agent_id: Optional[str] = None,
    ) -> LLMCallModel:
        """
        创建LLM调用记录
        
        Args:
            db: 数据库会话
            model_name: 模型名称
            call_type: 调用类型 (decision, conversation, etc.)
            input_tokens: 输入token数
            output_tokens: 输出token数
            reasoning_tokens: 推理token数
            cost: 成本
            response_time_ms: 响应时间（毫秒）
            agent_id: 相关智能体ID
            
        Returns:
            创建的调用记录
        """
        db_call = LLMCallModel(
            model_name=model_name,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cost=cost,
            response_time_ms=response_time_ms,
            agent_id=agent_id,
        )
        db.add(db_call)
        await db.commit()
        await db.refresh(db_call)
        return db_call
    
    @staticmethod
    async def create_batch(
        db: AsyncSession,
        calls: List[dict],
    ) -> List[LLMCallModel]:
        """批量创建调用记录"""
        db_calls = []
        for call_data in calls:
            db_call = LLMCallModel(**call_data)
            db.add(db_call)
            db_calls.append(db_call)
        
        await db.commit()
        
        for call in db_calls:
            await db.refresh(call)
        
        return db_calls
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, call_id: int) -> Optional[LLMCallModel]:
        """根据ID获取调用记录"""
        result = await db.execute(
            select(LLMCallModel).where(LLMCallModel.id == call_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_recent(
        db: AsyncSession,
        limit: int = 100,
        model_name: Optional[str] = None,
        call_type: Optional[str] = None,
    ) -> List[LLMCallModel]:
        """获取最近的调用记录"""
        query = select(LLMCallModel)
        
        if model_name:
            query = query.where(LLMCallModel.model_name == model_name)
        
        if call_type:
            query = query.where(LLMCallModel.call_type == call_type)
        
        query = query.order_by(desc(LLMCallModel.created_at)).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_agent(
        db: AsyncSession,
        agent_id: str,
        limit: int = 50,
    ) -> List[LLMCallModel]:
        """获取智能体的调用记录"""
        result = await db.execute(
            select(LLMCallModel)
            .where(LLMCallModel.agent_id == agent_id)
            .order_by(desc(LLMCallModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_time_range(
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
    ) -> List[LLMCallModel]:
        """根据时间范围获取调用记录"""
        result = await db.execute(
            select(LLMCallModel)
            .where(LLMCallModel.created_at.between(start_time, end_time))
            .order_by(LLMCallModel.created_at)
        )
        return list(result.scalars().all())
    
    # ===================
    # 统计操作
    # ===================
    
    @staticmethod
    async def get_total_cost(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """获取总成本"""
        query = select(func.sum(LLMCallModel.cost))
        
        if start_time:
            query = query.where(LLMCallModel.created_at >= start_time)
        
        if end_time:
            query = query.where(LLMCallModel.created_at <= end_time)
        
        result = await db.execute(query)
        return result.scalar() or 0.0
    
    @staticmethod
    async def get_daily_cost(db: AsyncSession) -> float:
        """获取今日成本"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return await LLMCallCRUD.get_total_cost(db, start_time=today)
    
    @staticmethod
    async def get_monthly_cost(db: AsyncSession) -> float:
        """获取本月成本"""
        first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return await LLMCallCRUD.get_total_cost(db, start_time=first_day)
    
    @staticmethod
    async def get_stats(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict:
        """
        获取调用统计
        
        Returns:
            包含各种统计信息的字典
        """
        query = select(
            func.count(LLMCallModel.id).label("total_calls"),
            func.sum(LLMCallModel.input_tokens).label("total_input"),
            func.sum(LLMCallModel.output_tokens).label("total_output"),
            func.sum(LLMCallModel.reasoning_tokens).label("total_reasoning"),
            func.sum(LLMCallModel.cost).label("total_cost"),
            func.avg(LLMCallModel.response_time_ms).label("avg_response_time"),
        )
        
        if start_time:
            query = query.where(LLMCallModel.created_at >= start_time)
        
        if end_time:
            query = query.where(LLMCallModel.created_at <= end_time)
        
        result = await db.execute(query)
        row = result.one()
        
        return {
            "total_calls": row.total_calls or 0,
            "total_input_tokens": row.total_input or 0,
            "total_output_tokens": row.total_output or 0,
            "total_reasoning_tokens": row.total_reasoning or 0,
            "total_cost": float(row.total_cost) if row.total_cost else 0.0,
            "avg_response_time_ms": float(row.avg_response_time) if row.avg_response_time else 0.0,
        }
    
    @staticmethod
    async def get_stats_by_model(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
    ) -> List[dict]:
        """按模型分组统计"""
        query = select(
            LLMCallModel.model_name,
            func.count(LLMCallModel.id).label("calls"),
            func.sum(LLMCallModel.cost).label("cost"),
            func.sum(LLMCallModel.input_tokens).label("input_tokens"),
            func.sum(LLMCallModel.output_tokens).label("output_tokens"),
        ).group_by(LLMCallModel.model_name)
        
        if start_time:
            query = query.where(LLMCallModel.created_at >= start_time)
        
        result = await db.execute(query)
        
        stats = []
        for row in result.all():
            stats.append({
                "model_name": row.model_name,
                "calls": row.calls,
                "cost": float(row.cost) if row.cost else 0.0,
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
            })
        
        return stats
    
    @staticmethod
    async def get_stats_by_type(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
    ) -> List[dict]:
        """按调用类型分组统计"""
        query = select(
            LLMCallModel.call_type,
            func.count(LLMCallModel.id).label("calls"),
            func.sum(LLMCallModel.cost).label("cost"),
        ).group_by(LLMCallModel.call_type)
        
        if start_time:
            query = query.where(LLMCallModel.created_at >= start_time)
        
        result = await db.execute(query)
        
        stats = []
        for row in result.all():
            stats.append({
                "call_type": row.call_type,
                "calls": row.calls,
                "cost": float(row.cost) if row.cost else 0.0,
            })
        
        return stats
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete_old_records(
        db: AsyncSession,
        days: int = 30,
    ) -> int:
        """删除旧记录"""
        cutoff = datetime.now() - timedelta(days=days)
        result = await db.execute(
            delete(LLMCallModel).where(LLMCallModel.created_at < cutoff)
        )
        await db.commit()
        return result.rowcount
