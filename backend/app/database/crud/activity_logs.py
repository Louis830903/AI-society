"""
活动日志CRUD操作
================
智能体活动日志的创建、查询、统计操作
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, delete, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ActivityLogModel


class ActivityLogCRUD:
    """活动日志CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        activity_type: str,
        action: str,
        game_time: datetime,
        target: Optional[str] = None,
        location: Optional[str] = None,
        thinking: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_partner: Optional[str] = None,
        message_content: Optional[str] = None,
        reflection_content: Optional[str] = None,
    ) -> ActivityLogModel:
        """
        创建活动日志记录
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            agent_name: 智能体名称
            activity_type: 活动类型 (decision, conversation, reflection, reaction, plan)
            action: 具体动作
            game_time: 游戏时间
            target: 目标
            location: 地点
            thinking: 思考过程
            conversation_id: 对话ID
            conversation_partner: 对话对象
            message_content: 消息内容
            reflection_content: 反思内容
            
        Returns:
            创建的活动日志记录
        """
        # 移除时区信息（数据库使用 TIMESTAMP WITHOUT TIME ZONE）
        if game_time.tzinfo is not None:
            game_time = game_time.replace(tzinfo=None)
        
        db_log = ActivityLogModel(
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type=activity_type,
            action=action,
            game_time=game_time,
            target=target,
            location=location,
            thinking=thinking,
            conversation_id=conversation_id,
            conversation_partner=conversation_partner,
            message_content=message_content,
            reflection_content=reflection_content,
        )
        db.add(db_log)
        await db.flush()
        return db_log
    
    @staticmethod
    async def log_decision(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        action: str,
        game_time: datetime,
        target: Optional[str] = None,
        location: Optional[str] = None,
        thinking: Optional[str] = None,
    ) -> ActivityLogModel:
        """记录决策活动"""
        return await ActivityLogCRUD.create(
            db=db,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type="decision",
            action=action,
            game_time=game_time,
            target=target,
            location=location,
            thinking=thinking,
        )
    
    @staticmethod
    async def log_conversation(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        game_time: datetime,
        conversation_id: str,
        conversation_partner: str,
        message_content: str,
        location: Optional[str] = None,
    ) -> ActivityLogModel:
        """记录对话活动"""
        return await ActivityLogCRUD.create(
            db=db,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type="conversation",
            action="chat",
            game_time=game_time,
            location=location,
            conversation_id=conversation_id,
            conversation_partner=conversation_partner,
            message_content=message_content,
        )
    
    @staticmethod
    async def log_reflection(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        game_time: datetime,
        reflection_content: str,
        location: Optional[str] = None,
    ) -> ActivityLogModel:
        """记录反思活动"""
        return await ActivityLogCRUD.create(
            db=db,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type="reflection",
            action="reflect",
            game_time=game_time,
            location=location,
            reflection_content=reflection_content,
        )
    
    @staticmethod
    async def log_reaction(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        action: str,
        game_time: datetime,
        target: Optional[str] = None,
        location: Optional[str] = None,
        thinking: Optional[str] = None,
    ) -> ActivityLogModel:
        """记录反应活动"""
        return await ActivityLogCRUD.create(
            db=db,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type="reaction",
            action=action,
            game_time=game_time,
            target=target,
            location=location,
            thinking=thinking,
        )
    
    @staticmethod
    async def log_plan(
        db: AsyncSession,
        agent_id: str,
        agent_name: str,
        game_time: datetime,
        thinking: str,
        location: Optional[str] = None,
    ) -> ActivityLogModel:
        """记录计划活动"""
        return await ActivityLogCRUD.create(
            db=db,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type="plan",
            action="plan",
            game_time=game_time,
            location=location,
            thinking=thinking,
        )
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_agent(
        db: AsyncSession,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        activity_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ActivityLogModel]:
        """
        获取智能体的活动日志
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            start_time: 开始时间
            end_time: 结束时间
            activity_type: 活动类型筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            活动日志列表
        """
        query = select(ActivityLogModel).where(ActivityLogModel.agent_id == agent_id)
        
        if start_time:
            query = query.where(ActivityLogModel.game_time >= start_time)
        if end_time:
            query = query.where(ActivityLogModel.game_time <= end_time)
        if activity_type:
            query = query.where(ActivityLogModel.activity_type == activity_type)
        
        query = query.order_by(desc(ActivityLogModel.game_time)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_daily(
        db: AsyncSession,
        agent_id: str,
        target_date: Optional[date] = None,
    ) -> List[ActivityLogModel]:
        """
        获取智能体某天的所有活动
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            target_date: 目标日期（默认今天）
            
        Returns:
            当天的活动日志列表
        """
        if target_date is None:
            target_date = date.today()
        
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        return await ActivityLogCRUD.get_by_agent(
            db=db,
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,  # 一天内的活动不设上限
        )
    
    @staticmethod
    async def get_recent(
        db: AsyncSession,
        agent_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> List[ActivityLogModel]:
        """获取智能体最近N小时的活动"""
        start_time = datetime.now() - timedelta(hours=hours)
        return await ActivityLogCRUD.get_by_agent(
            db=db,
            agent_id=agent_id,
            start_time=start_time,
            limit=limit,
        )
    
    @staticmethod
    async def get_conversations_by_agent(
        db: AsyncSession,
        agent_id: str,
        limit: int = 50,
    ) -> List[ActivityLogModel]:
        """获取智能体的对话活动"""
        return await ActivityLogCRUD.get_by_agent(
            db=db,
            agent_id=agent_id,
            activity_type="conversation",
            limit=limit,
        )
    
    # ===================
    # 统计操作
    # ===================
    
    @staticmethod
    async def get_daily_summary(
        db: AsyncSession,
        agent_id: str,
        target_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        获取智能体某天的活动汇总
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            target_date: 目标日期
            
        Returns:
            活动汇总字典
        """
        if target_date is None:
            target_date = date.today()
        
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        # 按活动类型统计数量
        type_counts_result = await db.execute(
            select(
                ActivityLogModel.activity_type,
                func.count(ActivityLogModel.id).label('count')
            )
            .where(
                and_(
                    ActivityLogModel.agent_id == agent_id,
                    ActivityLogModel.game_time.between(start_time, end_time)
                )
            )
            .group_by(ActivityLogModel.activity_type)
        )
        type_counts = {row.activity_type: row.count for row in type_counts_result.all()}
        
        # 按动作类型统计
        action_counts_result = await db.execute(
            select(
                ActivityLogModel.action,
                func.count(ActivityLogModel.id).label('count')
            )
            .where(
                and_(
                    ActivityLogModel.agent_id == agent_id,
                    ActivityLogModel.game_time.between(start_time, end_time)
                )
            )
            .group_by(ActivityLogModel.action)
        )
        action_counts = {row.action: row.count for row in action_counts_result.all()}
        
        # 统计对话伙伴
        partners_result = await db.execute(
            select(
                ActivityLogModel.conversation_partner,
                func.count(ActivityLogModel.id).label('count')
            )
            .where(
                and_(
                    ActivityLogModel.agent_id == agent_id,
                    ActivityLogModel.activity_type == "conversation",
                    ActivityLogModel.game_time.between(start_time, end_time),
                    ActivityLogModel.conversation_partner.isnot(None)
                )
            )
            .group_by(ActivityLogModel.conversation_partner)
        )
        conversation_partners = {row.conversation_partner: row.count for row in partners_result.all()}
        
        # 总活动数
        total_result = await db.execute(
            select(func.count(ActivityLogModel.id))
            .where(
                and_(
                    ActivityLogModel.agent_id == agent_id,
                    ActivityLogModel.game_time.between(start_time, end_time)
                )
            )
        )
        total_activities = total_result.scalar() or 0
        
        return {
            "date": target_date.isoformat(),
            "agent_id": agent_id,
            "total_activities": total_activities,
            "by_type": type_counts,
            "by_action": action_counts,
            "conversation_partners": conversation_partners,
        }
    
    @staticmethod
    async def count_by_agent(
        db: AsyncSession,
        agent_id: str,
    ) -> int:
        """统计智能体的总活动数"""
        result = await db.execute(
            select(func.count(ActivityLogModel.id))
            .where(ActivityLogModel.agent_id == agent_id)
        )
        return result.scalar() or 0
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete_by_agent(
        db: AsyncSession,
        agent_id: str,
    ) -> int:
        """删除智能体的所有活动日志"""
        result = await db.execute(
            delete(ActivityLogModel).where(ActivityLogModel.agent_id == agent_id)
        )
        await db.commit()
        return result.rowcount
    
    @staticmethod
    async def cleanup_old_logs(
        db: AsyncSession,
        days_to_keep: int = 30,
    ) -> int:
        """清理超过指定天数的旧日志"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        result = await db.execute(
            delete(ActivityLogModel).where(ActivityLogModel.created_at < cutoff_time)
        )
        await db.commit()
        return result.rowcount
