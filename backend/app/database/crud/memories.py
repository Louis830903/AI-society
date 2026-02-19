"""
记忆CRUD操作
============
智能体记忆的数据库操作
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MemoryModel


class MemoryCRUD:
    """记忆CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(
        db: AsyncSession,
        agent_id: str,
        content: str,
        memory_type: str = "event",
        importance: float = 5.0,
        keywords: Optional[List[str]] = None,
        related_agents: Optional[List[str]] = None,
        location: Optional[str] = None,
        game_time: Optional[datetime] = None,
        vector_id: Optional[str] = None,
    ) -> MemoryModel:
        """
        创建记忆记录
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            content: 记忆内容
            memory_type: 记忆类型 (event, conversation, observation, reflection, plan)
            importance: 重要性 (1-10)
            keywords: 关键词列表
            related_agents: 相关智能体ID列表
            location: 发生地点
            game_time: 游戏时间
            vector_id: 向量数据库ID
            
        Returns:
            创建的记忆记录
        """
        db_memory = MemoryModel(
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            keywords=keywords,
            related_agents=related_agents,
            location=location,
            game_time=game_time,
            vector_id=vector_id,
        )
        db.add(db_memory)
        await db.commit()
        await db.refresh(db_memory)
        return db_memory
    
    @staticmethod
    async def create_batch(
        db: AsyncSession,
        memories: List[dict],
    ) -> List[MemoryModel]:
        """
        批量创建记忆
        
        Args:
            db: 数据库会话
            memories: 记忆数据列表
            
        Returns:
            创建的记忆记录列表
        """
        db_memories = []
        for mem_data in memories:
            db_memory = MemoryModel(**mem_data)
            db.add(db_memory)
            db_memories.append(db_memory)
        
        await db.commit()
        
        for mem in db_memories:
            await db.refresh(mem)
        
        return db_memories
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, memory_id: str) -> Optional[MemoryModel]:
        """根据ID获取记忆"""
        result = await db.execute(
            select(MemoryModel).where(MemoryModel.id == memory_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_agent_memories(
        db: AsyncSession,
        agent_id: str,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MemoryModel]:
        """
        获取智能体的记忆列表
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            memory_type: 记忆类型过滤
            min_importance: 最小重要性过滤
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            记忆列表
        """
        query = select(MemoryModel).where(MemoryModel.agent_id == agent_id)
        
        if memory_type:
            query = query.where(MemoryModel.memory_type == memory_type)
        
        if min_importance is not None:
            query = query.where(MemoryModel.importance >= min_importance)
        
        query = query.order_by(desc(MemoryModel.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_recent_memories(
        db: AsyncSession,
        agent_id: str,
        limit: int = 10,
    ) -> List[MemoryModel]:
        """获取智能体最近的记忆"""
        result = await db.execute(
            select(MemoryModel)
            .where(MemoryModel.agent_id == agent_id)
            .order_by(desc(MemoryModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_important_memories(
        db: AsyncSession,
        agent_id: str,
        min_importance: float = 7.0,
        limit: int = 20,
    ) -> List[MemoryModel]:
        """获取智能体的重要记忆"""
        result = await db.execute(
            select(MemoryModel)
            .where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.importance >= min_importance,
                )
            )
            .order_by(desc(MemoryModel.importance))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_memories_by_type(
        db: AsyncSession,
        agent_id: str,
        memory_type: str,
        limit: int = 20,
    ) -> List[MemoryModel]:
        """获取指定类型的记忆"""
        result = await db.execute(
            select(MemoryModel)
            .where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.memory_type == memory_type,
                )
            )
            .order_by(desc(MemoryModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_memories_about_agent(
        db: AsyncSession,
        agent_id: str,
        target_agent_id: str,
        limit: int = 20,
    ) -> List[MemoryModel]:
        """获取关于特定智能体的记忆"""
        result = await db.execute(
            select(MemoryModel)
            .where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.related_agents.contains([target_agent_id]),
                )
            )
            .order_by(desc(MemoryModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_memories_by_location(
        db: AsyncSession,
        agent_id: str,
        location: str,
        limit: int = 20,
    ) -> List[MemoryModel]:
        """获取特定地点的记忆"""
        result = await db.execute(
            select(MemoryModel)
            .where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.location == location,
                )
            )
            .order_by(desc(MemoryModel.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def search_by_keywords(
        db: AsyncSession,
        agent_id: str,
        keywords: List[str],
        limit: int = 20,
    ) -> List[MemoryModel]:
        """按关键词搜索记忆"""
        # PostgreSQL数组重叠检查
        result = await db.execute(
            select(MemoryModel)
            .where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.keywords.overlap(keywords),
                )
            )
            .order_by(desc(MemoryModel.importance))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_vector_ids(
        db: AsyncSession,
        vector_ids: List[str],
    ) -> List[MemoryModel]:
        """根据向量ID列表获取记忆"""
        result = await db.execute(
            select(MemoryModel).where(MemoryModel.vector_id.in_(vector_ids))
        )
        return list(result.scalars().all())
    
    # ===================
    # 更新操作
    # ===================
    
    @staticmethod
    async def update(
        db: AsyncSession,
        memory_id: str,
        **kwargs,
    ) -> Optional[MemoryModel]:
        """
        更新记忆
        
        Args:
            db: 数据库会话
            memory_id: 记忆ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的记忆记录
        """
        memory = await MemoryCRUD.get_by_id(db, memory_id)
        if not memory:
            return None
        
        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        
        await db.commit()
        await db.refresh(memory)
        return memory
    
    @staticmethod
    async def increment_access(
        db: AsyncSession,
        memory_id: str,
    ) -> Optional[MemoryModel]:
        """增加记忆访问次数"""
        memory = await MemoryCRUD.get_by_id(db, memory_id)
        if not memory:
            return None
        
        memory.access_count += 1
        memory.accessed_at = datetime.now()
        
        await db.commit()
        await db.refresh(memory)
        return memory
    
    @staticmethod
    async def update_vector_id(
        db: AsyncSession,
        memory_id: str,
        vector_id: str,
    ) -> Optional[MemoryModel]:
        """更新记忆的向量ID"""
        return await MemoryCRUD.update(db, memory_id, vector_id=vector_id)
    
    @staticmethod
    async def update_importance(
        db: AsyncSession,
        memory_id: str,
        importance: float,
    ) -> Optional[MemoryModel]:
        """更新记忆重要性"""
        importance = max(1.0, min(10.0, importance))  # 限制在1-10
        return await MemoryCRUD.update(db, memory_id, importance=importance)
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete(db: AsyncSession, memory_id: str) -> bool:
        """删除记忆"""
        result = await db.execute(
            delete(MemoryModel).where(MemoryModel.id == memory_id)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def delete_agent_memories(
        db: AsyncSession,
        agent_id: str,
        memory_type: Optional[str] = None,
    ) -> int:
        """删除智能体的记忆"""
        query = delete(MemoryModel).where(MemoryModel.agent_id == agent_id)
        
        if memory_type:
            query = query.where(MemoryModel.memory_type == memory_type)
        
        result = await db.execute(query)
        await db.commit()
        return result.rowcount
    
    @staticmethod
    async def delete_old_memories(
        db: AsyncSession,
        agent_id: str,
        keep_count: int = 100,
        min_importance: float = 5.0,
    ) -> int:
        """
        删除旧的低重要性记忆
        
        保留最近的 keep_count 条记忆和所有重要性 >= min_importance 的记忆
        """
        # 获取要保留的记忆ID
        important_ids = await db.execute(
            select(MemoryModel.id).where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.importance >= min_importance,
                )
            )
        )
        important_ids = {row.id for row in important_ids.all()}
        
        recent_ids = await db.execute(
            select(MemoryModel.id)
            .where(MemoryModel.agent_id == agent_id)
            .order_by(desc(MemoryModel.created_at))
            .limit(keep_count)
        )
        recent_ids = {row.id for row in recent_ids.all()}
        
        keep_ids = important_ids | recent_ids
        
        if not keep_ids:
            return 0
        
        # 删除其他记忆
        result = await db.execute(
            delete(MemoryModel).where(
                and_(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.id.not_in(keep_ids),
                )
            )
        )
        await db.commit()
        return result.rowcount
    
    # ===================
    # 统计操作
    # ===================
    
    @staticmethod
    async def get_memory_stats(
        db: AsyncSession,
        agent_id: str,
    ) -> dict:
        """获取智能体的记忆统计"""
        # 总数
        total_result = await db.execute(
            select(func.count(MemoryModel.id)).where(MemoryModel.agent_id == agent_id)
        )
        total = total_result.scalar() or 0
        
        # 按类型统计
        type_result = await db.execute(
            select(MemoryModel.memory_type, func.count(MemoryModel.id))
            .where(MemoryModel.agent_id == agent_id)
            .group_by(MemoryModel.memory_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}
        
        # 平均重要性
        avg_result = await db.execute(
            select(func.avg(MemoryModel.importance)).where(MemoryModel.agent_id == agent_id)
        )
        avg_importance = avg_result.scalar() or 5.0
        
        return {
            "total": total,
            "by_type": type_counts,
            "avg_importance": float(avg_importance),
        }
    
    @staticmethod
    async def count_memories(
        db: AsyncSession,
        agent_id: str,
        memory_type: Optional[str] = None,
    ) -> int:
        """计算记忆数量"""
        query = select(func.count(MemoryModel.id)).where(MemoryModel.agent_id == agent_id)
        
        if memory_type:
            query = query.where(MemoryModel.memory_type == memory_type)
        
        result = await db.execute(query)
        return result.scalar() or 0
