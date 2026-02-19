"""
世界状态服务
============
世界状态的保存、恢复和管理

功能：
- 完整世界状态快照
- 自动保存
- 手动保存
- 状态恢复
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud import WorldStateCRUD, AgentCRUD, RelationshipCRUD, LLMCallCRUD
from app.database.models import WorldStateModel

logger = logging.getLogger(__name__)


class WorldStateService:
    """世界状态服务"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化世界状态服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    # ===================
    # 保存状态
    # ===================
    
    async def save_state(
        self,
        game_time: datetime,
        clock_state: dict,
        cost_tracker_state: dict,
        description: Optional[str] = None,
        is_auto_save: bool = True,
    ) -> WorldStateModel:
        """
        保存世界状态
        
        Args:
            game_time: 游戏时间
            clock_state: 时钟状态
            cost_tracker_state: 成本统计状态
            description: 保存描述
            is_auto_save: 是否自动保存
            
        Returns:
            保存的状态记录
        """
        if is_auto_save:
            state = await WorldStateCRUD.auto_save(
                db=self.db,
                game_time=game_time,
                clock_state=clock_state,
                cost_tracker_state=cost_tracker_state,
            )
        else:
            state = await WorldStateCRUD.manual_save(
                db=self.db,
                game_time=game_time,
                clock_state=clock_state,
                cost_tracker_state=cost_tracker_state,
                description=description or "Manual save",
            )
        
        logger.info(f"Saved world state at {game_time}, auto={is_auto_save}")
        return state
    
    async def quick_save(
        self,
        game_time: datetime,
        clock_state: dict,
        cost_tracker_state: dict,
    ) -> WorldStateModel:
        """快速保存（手动）"""
        return await self.save_state(
            game_time=game_time,
            clock_state=clock_state,
            cost_tracker_state=cost_tracker_state,
            description="Quick save",
            is_auto_save=False,
        )
    
    # ===================
    # 加载状态
    # ===================
    
    async def load_latest(self) -> Optional[Dict[str, Any]]:
        """
        加载最新状态
        
        Returns:
            状态数据字典或None
        """
        state = await WorldStateCRUD.get_latest(self.db)
        
        if not state:
            logger.warning("No world state found")
            return None
        
        return self._state_to_dict(state)
    
    async def load_by_id(self, state_id: int) -> Optional[Dict[str, Any]]:
        """根据ID加载状态"""
        state = await WorldStateCRUD.get_by_id(self.db, state_id)
        
        if not state:
            return None
        
        return self._state_to_dict(state)
    
    async def load_latest_manual(self) -> Optional[Dict[str, Any]]:
        """加载最新的手动保存"""
        state = await WorldStateCRUD.get_latest_manual(self.db)
        
        if not state:
            return None
        
        return self._state_to_dict(state)
    
    def _state_to_dict(self, state: WorldStateModel) -> Dict[str, Any]:
        """转换状态模型为字典"""
        return {
            "id": state.id,
            "game_time": state.game_time.isoformat() if state.game_time else None,
            "real_time": state.real_time.isoformat() if state.real_time else None,
            "clock_state": state.clock_state,
            "cost_tracker_state": state.cost_tracker_state,
            "description": state.description,
            "is_auto_save": state.is_auto_save,
            "created_at": state.created_at.isoformat() if state.created_at else None,
        }
    
    # ===================
    # 完整状态快照
    # ===================
    
    async def create_full_snapshot(
        self,
        game_time: datetime,
        clock_state: dict,
        cost_tracker_state: dict,
    ) -> Dict[str, Any]:
        """
        创建完整的世界状态快照
        
        包含所有智能体、关系等数据
        
        Returns:
            完整快照数据
        """
        # 1. 保存基本状态
        state = await self.save_state(
            game_time=game_time,
            clock_state=clock_state,
            cost_tracker_state=cost_tracker_state,
            description="Full snapshot",
            is_auto_save=False,
        )
        
        # 2. 获取所有智能体
        agents = await AgentCRUD.get_all(self.db, limit=500)
        
        # 3. 获取所有关系
        relationships = await RelationshipCRUD.get_all_relationships(self.db, limit=5000)
        
        # 4. 获取LLM调用统计
        llm_stats = await LLMCallCRUD.get_stats(self.db)
        
        snapshot = {
            "state_id": state.id,
            "game_time": game_time.isoformat(),
            "created_at": datetime.now().isoformat(),
            "agents_count": len(agents),
            "relationships_count": len(relationships),
            "clock_state": clock_state,
            "cost_tracker_state": cost_tracker_state,
            "llm_stats": llm_stats,
        }
        
        logger.info(f"Created full snapshot with {len(agents)} agents")
        return snapshot
    
    async def export_full_state(self) -> Dict[str, Any]:
        """
        导出完整世界状态（用于备份）
        
        Returns:
            完整状态数据
        """
        # 获取所有智能体
        agents = await AgentCRUD.get_all(self.db, limit=500)
        agents_data = [self._agent_to_export_dict(a) for a in agents]
        
        # 获取所有关系
        relationships = await RelationshipCRUD.get_all_relationships(self.db, limit=5000)
        relationships_data = [
            {
                "source_agent_id": r.source_agent_id,
                "target_agent_id": r.target_agent_id,
                "target_agent_name": r.target_agent_name,
                "closeness": r.closeness,
                "trust": r.trust,
                "interaction_count": r.interaction_count,
            }
            for r in relationships
        ]
        
        # 获取最新状态
        latest_state = await WorldStateCRUD.get_latest(self.db)
        
        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "agents": agents_data,
            "relationships": relationships_data,
            "world_state": self._state_to_dict(latest_state) if latest_state else None,
        }
    
    def _agent_to_export_dict(self, agent) -> Dict[str, Any]:
        """转换智能体为导出格式"""
        return {
            "id": agent.id,
            "name": agent.name,
            "age": agent.age,
            "gender": agent.gender,
            "occupation": agent.occupation,
            "backstory": agent.backstory,
            "traits": agent.traits,
            # 人格
            "personality": {
                "openness": agent.openness,
                "conscientiousness": agent.conscientiousness,
                "extraversion": agent.extraversion,
                "agreeableness": agent.agreeableness,
                "neuroticism": agent.neuroticism,
            },
            # 需求
            "needs": {
                "hunger": agent.hunger,
                "fatigue": agent.fatigue,
                "social": agent.social,
                "entertainment": agent.entertainment,
                "hygiene": agent.hygiene,
                "comfort": agent.comfort,
            },
            # 经济
            "economy": {
                "balance": agent.balance,
                "daily_income": agent.daily_income,
                "daily_expense": agent.daily_expense,
            },
            # 位置
            "location": {
                "x": agent.position_x,
                "y": agent.position_y,
                "location_id": agent.location_id,
                "location_name": agent.location_name,
            },
            # 状态
            "state": agent.state,
            "current_action": {
                "type": agent.current_action_type,
                "target": agent.current_action_target,
            },
        }
    
    # ===================
    # 状态管理
    # ===================
    
    async def list_saves(
        self,
        limit: int = 20,
        manual_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        列出保存记录
        
        Args:
            limit: 返回数量
            manual_only: 仅返回手动保存
            
        Returns:
            保存记录列表
        """
        states = await WorldStateCRUD.get_all(
            db=self.db,
            limit=limit,
            auto_save_only=False if manual_only else None,
        )
        
        return [
            {
                "id": s.id,
                "game_time": s.game_time.isoformat() if s.game_time else None,
                "description": s.description,
                "is_auto_save": s.is_auto_save,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in states
        ]
    
    async def delete_save(self, state_id: int) -> bool:
        """删除保存记录"""
        return await WorldStateCRUD.delete(self.db, state_id)
    
    async def cleanup_auto_saves(self, keep_count: int = 10) -> int:
        """清理旧的自动保存"""
        count = await WorldStateCRUD.cleanup_old_auto_saves(self.db, keep_count)
        logger.info(f"Cleaned up {count} old auto saves")
        return count
    
    # ===================
    # 统计
    # ===================
    
    async def get_save_stats(self) -> Dict[str, int]:
        """获取保存统计"""
        total = await WorldStateCRUD.count(self.db)
        auto_saves = await WorldStateCRUD.count(self.db, auto_save_only=True)
        manual_saves = await WorldStateCRUD.count(self.db, auto_save_only=False)
        
        return {
            "total": total,
            "auto_saves": auto_saves,
            "manual_saves": manual_saves,
        }


# ===================
# 工厂函数
# ===================

def create_world_state_service(db: AsyncSession) -> WorldStateService:
    """创建世界状态服务实例"""
    return WorldStateService(db)
