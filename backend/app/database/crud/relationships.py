"""
关系CRUD操作
============
智能体关系的数据库操作
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RelationshipModel


class RelationshipCRUD:
    """关系CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(
        db: AsyncSession,
        source_agent_id: str,
        target_agent_id: str,
        target_agent_name: str,
        closeness: int = 50,
        trust: int = 50,
        description: Optional[str] = None,
    ) -> RelationshipModel:
        """
        创建关系记录
        
        Args:
            db: 数据库会话
            source_agent_id: 源智能体ID
            target_agent_id: 目标智能体ID
            target_agent_name: 目标智能体名称
            closeness: 亲密度
            trust: 信任度
            description: 关系描述
            
        Returns:
            创建的关系记录
        """
        db_relationship = RelationshipModel(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            target_agent_name=target_agent_name,
            closeness=closeness,
            trust=trust,
            description=description,
        )
        db.add(db_relationship)
        await db.commit()
        await db.refresh(db_relationship)
        return db_relationship
    
    @staticmethod
    async def create_bidirectional(
        db: AsyncSession,
        agent_a_id: str,
        agent_a_name: str,
        agent_b_id: str,
        agent_b_name: str,
        closeness: int = 50,
        trust: int = 50,
    ) -> Tuple[RelationshipModel, RelationshipModel]:
        """
        创建双向关系
        
        Args:
            db: 数据库会话
            agent_a_id: 智能体A的ID
            agent_a_name: 智能体A的名称
            agent_b_id: 智能体B的ID
            agent_b_name: 智能体B的名称
            closeness: 初始亲密度
            trust: 初始信任度
            
        Returns:
            双向关系记录元组
        """
        # A -> B
        rel_a_to_b = RelationshipModel(
            source_agent_id=agent_a_id,
            target_agent_id=agent_b_id,
            target_agent_name=agent_b_name,
            closeness=closeness,
            trust=trust,
        )
        # B -> A
        rel_b_to_a = RelationshipModel(
            source_agent_id=agent_b_id,
            target_agent_id=agent_a_id,
            target_agent_name=agent_a_name,
            closeness=closeness,
            trust=trust,
        )
        db.add(rel_a_to_b)
        db.add(rel_b_to_a)
        await db.commit()
        await db.refresh(rel_a_to_b)
        await db.refresh(rel_b_to_a)
        return rel_a_to_b, rel_b_to_a
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, relationship_id: int) -> Optional[RelationshipModel]:
        """根据ID获取关系"""
        result = await db.execute(
            select(RelationshipModel).where(RelationshipModel.id == relationship_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_relationship(
        db: AsyncSession,
        source_agent_id: str,
        target_agent_id: str,
    ) -> Optional[RelationshipModel]:
        """
        获取特定的关系记录
        
        Args:
            db: 数据库会话
            source_agent_id: 源智能体ID
            target_agent_id: 目标智能体ID
            
        Returns:
            关系记录或None
        """
        result = await db.execute(
            select(RelationshipModel).where(
                and_(
                    RelationshipModel.source_agent_id == source_agent_id,
                    RelationshipModel.target_agent_id == target_agent_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_agent_relationships(
        db: AsyncSession,
        agent_id: str,
        min_closeness: Optional[int] = None,
        limit: int = 100,
    ) -> List[RelationshipModel]:
        """
        获取智能体的所有关系
        
        Args:
            db: 数据库会话
            agent_id: 智能体ID
            min_closeness: 最小亲密度过滤
            limit: 返回数量限制
            
        Returns:
            关系列表
        """
        query = select(RelationshipModel).where(
            RelationshipModel.source_agent_id == agent_id
        )
        
        if min_closeness is not None:
            query = query.where(RelationshipModel.closeness >= min_closeness)
        
        query = query.order_by(RelationshipModel.closeness.desc()).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_friends(
        db: AsyncSession,
        agent_id: str,
        min_closeness: int = 60,
        limit: int = 20,
    ) -> List[RelationshipModel]:
        """获取智能体的朋友（高亲密度关系）"""
        return await RelationshipCRUD.get_agent_relationships(
            db, agent_id, min_closeness=min_closeness, limit=limit
        )
    
    @staticmethod
    async def get_strangers(
        db: AsyncSession,
        agent_id: str,
        max_closeness: int = 30,
        limit: int = 20,
    ) -> List[RelationshipModel]:
        """获取智能体的陌生人（低亲密度关系）"""
        query = select(RelationshipModel).where(
            and_(
                RelationshipModel.source_agent_id == agent_id,
                RelationshipModel.closeness <= max_closeness,
            )
        ).order_by(RelationshipModel.closeness.asc()).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_all_relationships(
        db: AsyncSession,
        limit: int = 1000,
    ) -> List[RelationshipModel]:
        """获取所有关系（用于社交网络图）"""
        result = await db.execute(
            select(RelationshipModel).limit(limit)
        )
        return list(result.scalars().all())
    
    # ===================
    # 更新操作
    # ===================
    
    @staticmethod
    async def update_relationship(
        db: AsyncSession,
        source_agent_id: str,
        target_agent_id: str,
        closeness_delta: int = 0,
        trust_delta: int = 0,
        description: Optional[str] = None,
    ) -> Optional[RelationshipModel]:
        """
        更新关系值
        
        Args:
            db: 数据库会话
            source_agent_id: 源智能体ID
            target_agent_id: 目标智能体ID
            closeness_delta: 亲密度变化量
            trust_delta: 信任度变化量
            description: 新的关系描述
            
        Returns:
            更新后的关系记录
        """
        relationship = await RelationshipCRUD.get_relationship(
            db, source_agent_id, target_agent_id
        )
        
        if not relationship:
            return None
        
        # 更新亲密度（限制在0-100）
        if closeness_delta != 0:
            new_closeness = relationship.closeness + closeness_delta
            relationship.closeness = max(0, min(100, new_closeness))
        
        # 更新信任度（限制在0-100）
        if trust_delta != 0:
            new_trust = relationship.trust + trust_delta
            relationship.trust = max(0, min(100, new_trust))
        
        # 更新描述
        if description is not None:
            relationship.description = description
        
        # 更新交互次数和时间
        relationship.interaction_count += 1
        relationship.last_interaction = datetime.now()
        relationship.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(relationship)
        return relationship
    
    @staticmethod
    async def update_bidirectional(
        db: AsyncSession,
        agent_a_id: str,
        agent_b_id: str,
        closeness_delta: int = 0,
        trust_delta: int = 0,
    ) -> Tuple[Optional[RelationshipModel], Optional[RelationshipModel]]:
        """
        双向更新关系值
        
        Returns:
            (A->B关系, B->A关系) 元组
        """
        rel_a_to_b = await RelationshipCRUD.update_relationship(
            db, agent_a_id, agent_b_id, closeness_delta, trust_delta
        )
        rel_b_to_a = await RelationshipCRUD.update_relationship(
            db, agent_b_id, agent_a_id, closeness_delta, trust_delta
        )
        return rel_a_to_b, rel_b_to_a
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete_relationship(
        db: AsyncSession,
        source_agent_id: str,
        target_agent_id: str,
    ) -> bool:
        """删除单向关系"""
        result = await db.execute(
            delete(RelationshipModel).where(
                and_(
                    RelationshipModel.source_agent_id == source_agent_id,
                    RelationshipModel.target_agent_id == target_agent_id,
                )
            )
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def delete_bidirectional(
        db: AsyncSession,
        agent_a_id: str,
        agent_b_id: str,
    ) -> int:
        """删除双向关系"""
        result = await db.execute(
            delete(RelationshipModel).where(
                or_(
                    and_(
                        RelationshipModel.source_agent_id == agent_a_id,
                        RelationshipModel.target_agent_id == agent_b_id,
                    ),
                    and_(
                        RelationshipModel.source_agent_id == agent_b_id,
                        RelationshipModel.target_agent_id == agent_a_id,
                    ),
                )
            )
        )
        await db.commit()
        return result.rowcount
    
    @staticmethod
    async def delete_agent_relationships(
        db: AsyncSession,
        agent_id: str,
    ) -> int:
        """删除智能体的所有关系"""
        result = await db.execute(
            delete(RelationshipModel).where(
                or_(
                    RelationshipModel.source_agent_id == agent_id,
                    RelationshipModel.target_agent_id == agent_id,
                )
            )
        )
        await db.commit()
        return result.rowcount
    
    # ===================
    # 统计操作
    # ===================
    
    @staticmethod
    async def get_relationship_stats(
        db: AsyncSession,
        agent_id: str,
    ) -> dict:
        """
        获取智能体的关系统计
        
        Returns:
            包含统计信息的字典
        """
        result = await db.execute(
            select(
                func.count(RelationshipModel.id).label("total"),
                func.avg(RelationshipModel.closeness).label("avg_closeness"),
                func.avg(RelationshipModel.trust).label("avg_trust"),
                func.sum(RelationshipModel.interaction_count).label("total_interactions"),
            ).where(RelationshipModel.source_agent_id == agent_id)
        )
        row = result.one()
        
        return {
            "total_relationships": row.total or 0,
            "avg_closeness": float(row.avg_closeness) if row.avg_closeness else 50.0,
            "avg_trust": float(row.avg_trust) if row.avg_trust else 50.0,
            "total_interactions": row.total_interactions or 0,
        }
    
    @staticmethod
    async def get_social_network_edges(
        db: AsyncSession,
        min_closeness: int = 40,
    ) -> List[dict]:
        """
        获取社交网络边数据
        
        Args:
            min_closeness: 最小亲密度阈值
            
        Returns:
            边数据列表 [{"source": id, "target": id, "weight": closeness}, ...]
        """
        result = await db.execute(
            select(
                RelationshipModel.source_agent_id,
                RelationshipModel.target_agent_id,
                RelationshipModel.closeness,
            ).where(RelationshipModel.closeness >= min_closeness)
        )
        
        edges = []
        for row in result.all():
            edges.append({
                "source": row.source_agent_id,
                "target": row.target_agent_id,
                "weight": row.closeness,
            })
        
        return edges
