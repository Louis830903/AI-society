"""
智能体管理器
===========
管理所有智能体的生命周期、行为调度和交互

功能：
- 智能体创建与销毁
- 行为决策调度
- 智能体间交互协调
- 空间关系管理
- 统计信息汇总
- 数据库同步（Phase 7）
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from app.agents.models import Agent, AgentState, ActionType, Position
from app.agents.personality import Personality
from app.agents.needs import Needs
from app.agents.memory import MemoryType
from app.core.config import settings
from app.core.events import event_bus
from app.core.world import world_clock
from app.core.locations import location_manager, Location


@dataclass
class NearbyContext:
    """附近环境上下文"""
    location: Optional[Location]
    agents_here: List[Agent]
    agents_nearby: List[Agent]  # 邻近地点的智能体
    available_activities: List[str]
    
    def to_description(self) -> str:
        """生成自然语言描述"""
        lines = []
        
        if self.location:
            lines.append(f"你现在在「{self.location.name}」")
            if self.location.description:
                lines.append(f"这里{self.location.description}")
        
        if self.agents_here:
            names = [a.name for a in self.agents_here[:5]]
            lines.append(f"这里还有：{', '.join(names)}")
        
        if self.available_activities:
            lines.append(f"可以做的事：{', '.join(self.available_activities)}")
        
        return "\n".join(lines) if lines else "周围没有什么特别的"


class AgentManager:
    """
    智能体管理器
    
    单例模式，管理整个世界的所有智能体
    支持文件持久化，服务重启后可恢复数据
    支持数据库同步，保证活动日志等外键关系正常
    """
    
    # 持久化文件路径
    SAVE_FILE = Path("data/agents_state.json")
    
    def __init__(self):
        """初始化管理器"""
        self._agents: Dict[str, Agent] = {}  # id -> Agent
        self._by_location: Dict[str, Set[str]] = {}  # location_id -> agent_ids
        self._by_name: Dict[str, str] = {}  # name -> id
        
        # 调度状态
        self._decision_queue: List[str] = []  # 待决策的智能体ID队列
        self._is_running: bool = False
        self._decision_interval: float = 6.0  # 决策间隔（现实秒）
        
        # 数据库同步标志
        self._db_sync_pending: bool = False
        
        # 启动时尝试加载已保存的数据
        self._load_from_file()
        
        logger.info("智能体管理器初始化完成")
    
    @property
    def agents(self) -> Dict[str, Agent]:
        """获取所有智能体字典（公开只读访问）"""
        return self._agents
    
    # ==================
    # 持久化方法
    # ==================
    
    def _save_to_file(self) -> None:
        """保存智能体数据到文件"""
        try:
            self.SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "agents": [agent.to_dict() for agent in self._agents.values()],
                "saved_at": datetime.now().isoformat(),
            }
            
            with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存 {len(self._agents)} 个智能体到 {self.SAVE_FILE}")
        except Exception as e:
            logger.error(f"保存智能体数据失败: {e}")
    
    def _load_from_file(self) -> None:
        """从文件加载智能体数据"""
        if not self.SAVE_FILE.exists():
            logger.info("无已保存的智能体数据")
            return
        
        try:
            with open(self.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            agents_data = data.get("agents", [])
            loaded_count = 0
            
            for agent_data in agents_data:
                try:
                    agent = Agent.from_dict(agent_data)
                    self._agents[agent.id] = agent
                    self._by_name[agent.name] = agent.id
                    
                    # 更新位置索引
                    if agent.position.location_id:
                        self._add_to_location(agent.id, agent.position.location_id)
                        # 同步到 location_manager
                        location_manager.enter(agent.position.location_id, agent.id)
                    
                    loaded_count += 1
                except Exception as e:
                    logger.warning(f"加载智能体失败: {e}")
            
            logger.info(f"已从文件加载 {loaded_count} 个智能体")
            
            # 同步到数据库
            self._schedule_db_sync()
        except Exception as e:
            logger.error(f"加载智能体数据失败: {e}")
    
    # ==================
    # 数据库同步方法
    # ==================
    
    def _schedule_db_sync(self) -> None:
        """
        调度数据库同步任务
        使用后台任务异步执行，避免阻塞主线程
        """
        if self._db_sync_pending:
            return
        
        self._db_sync_pending = True
        
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，创建任务
                asyncio.create_task(self._sync_all_to_database())
            except RuntimeError:
                # 如果没有运行的事件循环，使用新的事件循环
                asyncio.run(self._sync_all_to_database())
        except Exception as e:
            logger.warning(f"调度数据库同步失败: {e}")
            self._db_sync_pending = False
    
    async def _sync_all_to_database(self) -> None:
        """
        将所有智能体同步到数据库
        先清空再全量插入，保证数据一致性
        """
        try:
            from app.database import get_async_session
            from app.database.crud.agents import AgentCRUD
            
            async with get_async_session() as db:
                # 清空现有数据
                await AgentCRUD.delete_all(db)
                
                # 批量插入所有智能体
                agents = list(self._agents.values())
                if agents:
                    await AgentCRUD.create_batch(db, agents)
                
                await db.commit()
                
            logger.info(f"已同步 {len(self._agents)} 个智能体到数据库")
        except Exception as e:
            logger.error(f"同步智能体到数据库失败: {e}")
        finally:
            self._db_sync_pending = False
    
    async def _sync_agent_to_database(self, agent: Agent) -> None:
        """
        同步单个智能体到数据库（创建或更新）
        """
        try:
            from app.database import get_async_session
            from app.database.crud.agents import AgentCRUD
            
            async with get_async_session() as db:
                # 检查是否存在
                existing = await AgentCRUD.get_by_id(db, agent.id)
                
                if existing:
                    await AgentCRUD.update(db, agent)
                else:
                    await AgentCRUD.create(db, agent)
                
                await db.commit()
                
            logger.debug(f"智能体 {agent.name} 已同步到数据库")
        except Exception as e:
            logger.warning(f"同步智能体 {agent.name} 到数据库失败: {e}")
    
    async def _delete_agent_from_database(self, agent_id: str) -> None:
        """
        从数据库删除智能体
        """
        try:
            from app.database import get_async_session
            from app.database.crud.agents import AgentCRUD
            
            async with get_async_session() as db:
                await AgentCRUD.delete(db, agent_id)
                await db.commit()
                
            logger.debug(f"智能体 {agent_id} 已从数据库删除")
        except Exception as e:
            logger.warning(f"从数据库删除智能体 {agent_id} 失败: {e}")
    
    def _schedule_single_agent_sync(self, agent: Agent) -> None:
        """
        调度单个智能体的数据库同步
        """
        try:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._sync_agent_to_database(agent))
            except RuntimeError:
                asyncio.run(self._sync_agent_to_database(agent))
        except Exception as e:
            logger.warning(f"调度单个智能体同步失败: {e}")
    
    def _schedule_agent_delete(self, agent_id: str) -> None:
        """
        调度从数据库删除智能体
        """
        try:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._delete_agent_from_database(agent_id))
            except RuntimeError:
                asyncio.run(self._delete_agent_from_database(agent_id))
        except Exception as e:
            logger.warning(f"调度删除智能体失败: {e}")
    
    # ==================
    # 智能体CRUD
    # ==================
    
    def add(self, agent: Agent) -> str:
        """
        添加智能体
        
        Args:
            agent: 智能体对象
        
        Returns:
            智能体ID
        """
        if len(self._agents) >= settings.max_agent_count:
            raise ValueError(f"智能体数量已达上限: {settings.max_agent_count}")
        
        if agent.id in self._agents:
            raise ValueError(f"智能体ID已存在: {agent.id}")
        
        self._agents[agent.id] = agent
        self._by_name[agent.name] = agent.id
        
        # 更新位置索引
        if agent.position.location_id:
            self._add_to_location(agent.id, agent.position.location_id)
        
        # 发布事件
        event_bus.publish_sync("agent.created", {
            "agent_id": agent.id,
            "agent_name": agent.name,
        })
        
        logger.info(f"添加智能体: {agent.name} ({agent.occupation})")
        
        # 持久化保存
        self._save_to_file()
        
        # 同步到数据库
        self._schedule_single_agent_sync(agent)
        
        return agent.id
    
    def remove(self, agent_id: str) -> bool:
        """移除智能体"""
        if agent_id not in self._agents:
            return False
        
        agent = self._agents[agent_id]
        
        # 从索引中移除
        if agent.name in self._by_name:
            del self._by_name[agent.name]
        
        if agent.position.location_id:
            self._remove_from_location(agent_id, agent.position.location_id)
        
        del self._agents[agent_id]
        
        # 发布事件
        event_bus.publish_sync("agent.left", {"agent_id": agent_id})
        
        # 持久化保存
        self._save_to_file()
        
        # 从数据库删除
        self._schedule_agent_delete(agent_id)
        
        return True
    
    def get(self, agent_id: str) -> Optional[Agent]:
        """获取智能体"""
        return self._agents.get(agent_id)
    
    def get_by_name(self, name: str) -> Optional[Agent]:
        """通过名字获取智能体"""
        agent_id = self._by_name.get(name)
        return self._agents.get(agent_id) if agent_id else None
    
    def get_all(self) -> List[Agent]:
        """获取所有智能体"""
        return list(self._agents.values())
    
    def count(self) -> int:
        """获取智能体数量"""
        return len(self._agents)
    
    # ==================
    # 位置管理
    # ==================
    
    def _add_to_location(self, agent_id: str, location_id: str) -> None:
        """将智能体添加到位置索引"""
        if location_id not in self._by_location:
            self._by_location[location_id] = set()
        self._by_location[location_id].add(agent_id)
    
    def _remove_from_location(self, agent_id: str, location_id: str) -> None:
        """从位置索引移除智能体"""
        if location_id in self._by_location:
            self._by_location[location_id].discard(agent_id)
    
    def move_agent(
        self,
        agent_id: str,
        new_location_id: str,
    ) -> bool:
        """
        移动智能体到新位置
        
        Args:
            agent_id: 智能体ID
            new_location_id: 目标位置ID
        
        Returns:
            是否成功
        """
        agent = self.get(agent_id)
        if not agent:
            return False
        
        location = location_manager.get_location(new_location_id)
        if not location:
            return False
        
        # 检查容量
        if location.is_full:
            logger.warning(f"位置已满: {location.name}")
            return False
        
        # 更新位置索引
        old_location_id = agent.position.location_id
        if old_location_id:
            self._remove_from_location(agent_id, old_location_id)
            location_manager.leave(old_location_id, agent_id)
        
        self._add_to_location(agent_id, new_location_id)
        location_manager.enter(new_location_id, agent_id)
        
        # 更新智能体位置
        agent.move_to(
            x=location.x,
            y=location.y,
            location_id=location.id,
            location_name=location.name,
        )
        
        # 发布事件
        event_bus.publish_sync("agent.moved", {
            "agent_id": agent_id,
            "from_location": old_location_id,
            "to_location": new_location_id,
        })
        
        logger.debug(f"{agent.name} 移动到 {location.name}")
        return True
    
    def get_agents_at_location(self, location_id: str) -> List[Agent]:
        """获取指定位置的所有智能体"""
        agent_ids = self._by_location.get(location_id, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_nearby_agents(
        self,
        agent_id: str,
        radius: float = 10.0,
    ) -> List[Agent]:
        """
        获取附近的智能体
        
        Args:
            agent_id: 中心智能体ID
            radius: 搜索半径
        
        Returns:
            附近的智能体列表（不包括自己）
        """
        agent = self.get(agent_id)
        if not agent:
            return []
        
        nearby = []
        for other in self._agents.values():
            if other.id == agent_id:
                continue
            
            distance = agent.position.distance_to(other.position)
            if distance <= radius:
                nearby.append(other)
        
        return nearby
    
    def get_nearby_context(self, agent_id: str) -> NearbyContext:
        """获取智能体的周围环境上下文"""
        agent = self.get(agent_id)
        if not agent:
            return NearbyContext(None, [], [], [])
        
        location = None
        agents_here = []
        available_activities = []
        
        if agent.position.location_id:
            location = location_manager.get_location(agent.position.location_id)
            agents_here = [
                a for a in self.get_agents_at_location(agent.position.location_id)
                if a.id != agent_id
            ]
            if location:
                available_activities = [act.value for act in location.activities]
        
        agents_nearby = self.get_nearby_agents(agent_id, radius=15.0)
        
        return NearbyContext(
            location=location,
            agents_here=agents_here,
            agents_nearby=agents_nearby,
            available_activities=available_activities,
        )
    
    # ==================
    # 需求与状态更新
    # ==================
    
    def update_all_needs(self, elapsed_hours: float) -> None:
        """
        更新所有智能体的需求
        
        Args:
            elapsed_hours: 经过的游戏时间（小时）
        """
        for agent in self._agents.values():
            agent.needs.update(elapsed_hours, agent.personality)
    
    def get_agents_needing_decision(self) -> List[Agent]:
        """获取需要做决策的智能体"""
        result = []
        
        for agent in self._agents.values():
            # 跳过睡眠、暂停、离线状态
            if agent.state in [AgentState.SLEEPING, AgentState.PAUSED, AgentState.OFFLINE]:
                continue
            
            # 检查当前行为是否完成
            if agent.current_action.duration_minutes > 0:
                if not agent.current_action.is_complete(datetime.now()):
                    continue
            
            result.append(agent)
        
        return result
    
    # ==================
    # 统计信息
    # ==================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        by_occupation: Dict[str, int] = {}
        by_state: Dict[str, int] = {}
        by_location: Dict[str, int] = {}
        
        total_balance = 0.0
        total_wellbeing = 0.0
        
        for agent in self._agents.values():
            # 按职业统计
            occ = agent.occupation
            by_occupation[occ] = by_occupation.get(occ, 0) + 1
            
            # 按状态统计
            state = agent.state.value
            by_state[state] = by_state.get(state, 0) + 1
            
            # 按位置统计
            loc = agent.position.location_name or "未知"
            by_location[loc] = by_location.get(loc, 0) + 1
            
            total_balance += agent.balance
            total_wellbeing += agent.get_wellbeing()
        
        count = self.count()
        
        return {
            "total": count,
            "max": settings.max_agent_count,
            "by_occupation": by_occupation,
            "by_state": by_state,
            "by_location": by_location,
            "avg_balance": total_balance / count if count > 0 else 0,
            "avg_wellbeing": total_wellbeing / count if count > 0 else 0,
        }
    
    # ==================
    # 持久化
    # ==================
    
    def save_to_file(self, filepath: str) -> int:
        """
        保存所有智能体到文件
        
        Returns:
            保存的智能体数量
        """
        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "agents": [agent.to_dict() for agent in self._agents.values()],
        }
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存了 {len(data['agents'])} 个智能体到 {filepath}")
        return len(data["agents"])
    
    def load_from_file(self, filepath: str) -> int:
        """
        从文件加载智能体
        
        Returns:
            加载的智能体数量
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"文件不存在: {filepath}")
            return 0
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = 0
        for agent_data in data.get("agents", []):
            try:
                agent = Agent.from_dict(agent_data)
                self.add(agent)
                count += 1
            except Exception as e:
                logger.error(f"加载智能体失败: {e}")
        
        logger.info(f"从 {filepath} 加载了 {count} 个智能体")
        return count
    
    def clear(self) -> None:
        """清空所有智能体"""
        self._agents.clear()
        self._by_location.clear()
        self._by_name.clear()
        logger.info("已清空所有智能体")


# 创建全局单例
agent_manager = AgentManager()
