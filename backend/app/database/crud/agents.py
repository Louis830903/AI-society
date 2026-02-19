"""
智能体CRUD操作
=============
提供智能体的数据库增删改查操作
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentModel, RelationshipModel
from app.agents.models import Agent, Position, CurrentAction, ActionType, AgentState, Relationship
from app.agents.personality import Personality
from app.agents.needs import Needs
from loguru import logger


class AgentCRUD:
    """智能体CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(db: AsyncSession, agent: Agent) -> AgentModel:
        """
        创建智能体记录
        
        Args:
            db: 数据库会话
            agent: 智能体对象
        
        Returns:
            创建的数据库模型
        """
        db_agent = AgentModel(
            id=agent.id,
            name=agent.name,
            age=agent.age,
            gender=agent.gender,
            occupation=agent.occupation,
            backstory=agent.backstory,
            traits=agent.traits,
            # 人格
            openness=agent.personality.openness,
            conscientiousness=agent.personality.conscientiousness,
            extraversion=agent.personality.extraversion,
            agreeableness=agent.personality.agreeableness,
            neuroticism=agent.personality.neuroticism,
            # 需求
            hunger=agent.needs.hunger,
            fatigue=agent.needs.fatigue,
            social=agent.needs.social,
            entertainment=agent.needs.entertainment,
            hygiene=agent.needs.hygiene,
            comfort=agent.needs.comfort,
            # 经济
            balance=agent.balance,
            daily_income=agent.daily_income,
            daily_expense=agent.daily_expense,
            # 位置
            position_x=agent.position.x,
            position_y=agent.position.y,
            location_id=agent.position.location_id,
            location_name=agent.position.location_name,
            home_location_id=agent.home_location_id,
            work_location_id=agent.work_location_id,
            # 状态
            state=agent.state.value,
            current_action_type=agent.current_action.type.value,
            current_action_target=agent.current_action.target,
            current_action_started_at=agent.current_action.started_at,
            current_action_duration=agent.current_action.duration_minutes,
            current_thinking=agent.current_action.thinking,
            # LLM
            model_name=agent.model_name,
            # 时间
            created_at=agent.created_at,
            work_hours_today=agent.work_hours_today,
        )
        
        db.add(db_agent)
        await db.flush()
        
        logger.debug(f"创建智能体记录: {agent.id} - {agent.name}")
        return db_agent
    
    @staticmethod
    async def create_batch(db: AsyncSession, agents: List[Agent]) -> List[AgentModel]:
        """批量创建智能体"""
        db_agents = []
        for agent in agents:
            db_agent = await AgentCRUD.create(db, agent)
            db_agents.append(db_agent)
        return db_agents
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, agent_id: str) -> Optional[AgentModel]:
        """根据ID获取智能体"""
        result = await db.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[AgentModel]:
        """根据名字获取智能体"""
        result = await db.execute(
            select(AgentModel).where(AgentModel.name == name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        state: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> List[AgentModel]:
        """
        获取智能体列表
        
        Args:
            db: 数据库会话
            limit: 返回数量限制
            offset: 偏移量
            state: 过滤状态
            location_id: 过滤地点
        """
        query = select(AgentModel)
        
        if state:
            query = query.where(AgentModel.state == state)
        if location_id:
            query = query.where(AgentModel.location_id == location_id)
        
        query = query.order_by(AgentModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def count(db: AsyncSession, state: Optional[str] = None) -> int:
        """获取智能体数量"""
        query = select(func.count(AgentModel.id))
        if state:
            query = query.where(AgentModel.state == state)
        result = await db.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_by_location(db: AsyncSession, location_id: str) -> List[AgentModel]:
        """获取指定地点的所有智能体"""
        result = await db.execute(
            select(AgentModel).where(AgentModel.location_id == location_id)
        )
        return list(result.scalars().all())
    
    # ===================
    # 更新操作
    # ===================
    
    @staticmethod
    async def update(db: AsyncSession, agent: Agent) -> Optional[AgentModel]:
        """
        更新智能体
        
        将Agent对象的所有字段同步到数据库
        """
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == agent.id)
            .values(
                name=agent.name,
                age=agent.age,
                gender=agent.gender,
                occupation=agent.occupation,
                backstory=agent.backstory,
                traits=agent.traits,
                # 人格
                openness=agent.personality.openness,
                conscientiousness=agent.personality.conscientiousness,
                extraversion=agent.personality.extraversion,
                agreeableness=agent.personality.agreeableness,
                neuroticism=agent.personality.neuroticism,
                # 需求
                hunger=agent.needs.hunger,
                fatigue=agent.needs.fatigue,
                social=agent.needs.social,
                entertainment=agent.needs.entertainment,
                hygiene=agent.needs.hygiene,
                comfort=agent.needs.comfort,
                # 经济
                balance=agent.balance,
                daily_income=agent.daily_income,
                daily_expense=agent.daily_expense,
                # 位置
                position_x=agent.position.x,
                position_y=agent.position.y,
                location_id=agent.position.location_id,
                location_name=agent.position.location_name,
                home_location_id=agent.home_location_id,
                work_location_id=agent.work_location_id,
                # 状态
                state=agent.state.value,
                current_action_type=agent.current_action.type.value,
                current_action_target=agent.current_action.target,
                current_action_started_at=agent.current_action.started_at,
                current_action_duration=agent.current_action.duration_minutes,
                current_thinking=agent.current_action.thinking,
                # LLM
                model_name=agent.model_name,
                # 时间
                last_decision_time=agent.last_decision_time,
                work_hours_today=agent.work_hours_today,
                updated_at=datetime.now(),
            )
        )
        await db.flush()
        return await AgentCRUD.get_by_id(db, agent.id)
    
    @staticmethod
    async def update_position(
        db: AsyncSession,
        agent_id: str,
        x: float,
        y: float,
        location_id: Optional[str] = None,
        location_name: Optional[str] = None,
    ) -> None:
        """更新智能体位置"""
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == agent_id)
            .values(
                position_x=x,
                position_y=y,
                location_id=location_id,
                location_name=location_name,
                updated_at=datetime.now(),
            )
        )
        await db.flush()
    
    @staticmethod
    async def update_state(db: AsyncSession, agent_id: str, state: str) -> None:
        """更新智能体状态"""
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == agent_id)
            .values(state=state, updated_at=datetime.now())
        )
        await db.flush()
    
    @staticmethod
    async def update_needs(db: AsyncSession, agent_id: str, needs: Needs) -> None:
        """更新智能体需求"""
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == agent_id)
            .values(
                hunger=needs.hunger,
                fatigue=needs.fatigue,
                social=needs.social,
                entertainment=needs.entertainment,
                hygiene=needs.hygiene,
                comfort=needs.comfort,
                updated_at=datetime.now(),
            )
        )
        await db.flush()
    
    @staticmethod
    async def update_balance(db: AsyncSession, agent_id: str, balance: float) -> None:
        """更新智能体余额"""
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == agent_id)
            .values(balance=balance, updated_at=datetime.now())
        )
        await db.flush()
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete(db: AsyncSession, agent_id: str) -> bool:
        """删除智能体"""
        result = await db.execute(
            delete(AgentModel).where(AgentModel.id == agent_id)
        )
        await db.flush()
        return result.rowcount > 0
    
    @staticmethod
    async def delete_all(db: AsyncSession) -> int:
        """删除所有智能体"""
        result = await db.execute(delete(AgentModel))
        await db.flush()
        return result.rowcount
    
    # ===================
    # 转换方法
    # ===================
    
    @staticmethod
    def model_to_agent(db_agent: AgentModel) -> Agent:
        """
        将数据库模型转换为Agent对象
        """
        return Agent(
            id=db_agent.id,
            name=db_agent.name,
            age=db_agent.age,
            gender=db_agent.gender,
            occupation=db_agent.occupation,
            backstory=db_agent.backstory or "",
            traits=db_agent.traits or [],
            personality=Personality(
                openness=db_agent.openness,
                conscientiousness=db_agent.conscientiousness,
                extraversion=db_agent.extraversion,
                agreeableness=db_agent.agreeableness,
                neuroticism=db_agent.neuroticism,
            ),
            needs=Needs(
                hunger=db_agent.hunger,
                fatigue=db_agent.fatigue,
                social=db_agent.social,
                entertainment=db_agent.entertainment,
                hygiene=db_agent.hygiene,
                comfort=db_agent.comfort,
            ),
            balance=db_agent.balance,
            daily_income=db_agent.daily_income,
            daily_expense=db_agent.daily_expense,
            position=Position(
                x=db_agent.position_x,
                y=db_agent.position_y,
                location_id=db_agent.location_id,
                location_name=db_agent.location_name,
            ),
            home_location_id=db_agent.home_location_id,
            work_location_id=db_agent.work_location_id,
            state=AgentState(db_agent.state),
            current_action=CurrentAction(
                type=ActionType(db_agent.current_action_type),
                target=db_agent.current_action_target,
                started_at=db_agent.current_action_started_at or datetime.now(),
                duration_minutes=db_agent.current_action_duration,
                thinking=db_agent.current_thinking,
            ),
            model_name=db_agent.model_name,
            created_at=db_agent.created_at,
            last_decision_time=db_agent.last_decision_time,
            work_hours_today=db_agent.work_hours_today,
        )
