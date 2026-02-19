"""
数据库模型定义
=============
SQLAlchemy ORM模型，映射到PostgreSQL表

表结构：
- agents: 智能体基本信息
- agent_personalities: 智能体人格（大五模型）
- agent_needs: 智能体需求状态
- relationships: 智能体间关系
- conversations: 对话记录
- messages: 对话消息
- memories: 智能体记忆
- world_states: 世界状态快照
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ===================
# 基类
# ===================

class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""
    pass


# ===================
# 枚举类型
# ===================

import enum

class AgentStateEnum(str, enum.Enum):
    """智能体状态"""
    ACTIVE = "active"
    SLEEPING = "sleeping"
    BUSY = "busy"
    IN_CONVERSATION = "in_conversation"
    PAUSED = "paused"
    OFFLINE = "offline"


class ActionTypeEnum(str, enum.Enum):
    """行为类型"""
    IDLE = "idle"
    MOVE = "move"
    WORK = "work"
    EAT = "eat"
    SLEEP = "sleep"
    REST = "rest"
    CHAT = "chat"
    SHOP = "shop"
    EXERCISE = "exercise"
    ENTERTAINMENT = "entertainment"
    WAITING = "waiting"


class ConversationStateEnum(str, enum.Enum):
    """对话状态"""
    PENDING = "pending"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"
    INTERRUPTED = "interrupted"


class MemoryTypeEnum(str, enum.Enum):
    """记忆类型"""
    EVENT = "event"
    CONVERSATION = "conversation"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    PLAN = "plan"


class ActivityTypeEnum(str, enum.Enum):
    """活动类型"""
    DECISION = "decision"       # 决策
    CONVERSATION = "conversation"  # 对话
    REFLECTION = "reflection"   # 反思
    REACTION = "reaction"       # 反应
    PLAN = "plan"              # 计划


# ===================
# 智能体表
# ===================

class AgentModel(Base):
    """
    智能体表
    
    存储智能体的基本信息和状态
    """
    __tablename__ = "agents"
    
    # 主键
    id: Mapped[str] = mapped_column(String(8), primary_key=True, default=lambda: str(uuid4())[:8])
    
    # 身份信息
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    age: Mapped[int] = mapped_column(Integer, default=25)
    gender: Mapped[str] = mapped_column(String(10), default="男")
    occupation: Mapped[str] = mapped_column(String(50), default="自由职业", index=True)
    backstory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traits: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # 人格特质（大五模型）
    openness: Mapped[int] = mapped_column(Integer, default=50)
    conscientiousness: Mapped[int] = mapped_column(Integer, default=50)
    extraversion: Mapped[int] = mapped_column(Integer, default=50)
    agreeableness: Mapped[int] = mapped_column(Integer, default=50)
    neuroticism: Mapped[int] = mapped_column(Integer, default=50)
    
    # 需求状态
    hunger: Mapped[float] = mapped_column(Float, default=50.0)
    fatigue: Mapped[float] = mapped_column(Float, default=50.0)
    social: Mapped[float] = mapped_column(Float, default=50.0)
    entertainment: Mapped[float] = mapped_column(Float, default=50.0)
    hygiene: Mapped[float] = mapped_column(Float, default=50.0)
    comfort: Mapped[float] = mapped_column(Float, default=50.0)
    
    # 经济状态
    balance: Mapped[float] = mapped_column(Float, default=10000.0)
    daily_income: Mapped[float] = mapped_column(Float, default=0.0)
    daily_expense: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 位置信息
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    location_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    home_location_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    work_location_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # 行为状态
    state: Mapped[str] = mapped_column(String(20), default="active", index=True)
    current_action_type: Mapped[str] = mapped_column(String(20), default="idle")
    current_action_target: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_action_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_action_duration: Mapped[int] = mapped_column(Integer, default=0)
    current_thinking: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # LLM配置
    model_name: Mapped[str] = mapped_column(String(50), default="deepseek-reasoner")
    
    # 时间追踪
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_decision_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    work_hours_today: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 关系
    relationships_as_source: Mapped[List["RelationshipModel"]] = relationship(
        "RelationshipModel",
        foreign_keys="RelationshipModel.source_agent_id",
        back_populates="source_agent",
        cascade="all, delete-orphan",
    )
    memories: Mapped[List["MemoryModel"]] = relationship(
        "MemoryModel",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    
    # 索引
    __table_args__ = (
        Index("ix_agents_state_location", "state", "location_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, occupation={self.occupation})>"


# ===================
# 关系表
# ===================

class RelationshipModel(Base):
    """
    智能体关系表
    
    存储智能体之间的双向关系
    """
    __tablename__ = "relationships"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 关系双方
    source_agent_id: Mapped[str] = mapped_column(
        String(8), 
        ForeignKey("agents.id", ondelete="CASCADE"), 
        index=True
    )
    target_agent_id: Mapped[str] = mapped_column(String(8), index=True)
    target_agent_name: Mapped[str] = mapped_column(String(50))
    
    # 关系值
    closeness: Mapped[int] = mapped_column(Integer, default=50)  # 亲密度 0-100
    trust: Mapped[int] = mapped_column(Integer, default=50)  # 信任度 0-100
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_interaction: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    source_agent: Mapped["AgentModel"] = relationship(
        "AgentModel",
        foreign_keys=[source_agent_id],
        back_populates="relationships_as_source",
    )
    
    __table_args__ = (
        UniqueConstraint("source_agent_id", "target_agent_id", name="uq_relationship_pair"),
        Index("ix_relationships_closeness", "closeness"),
    )
    
    def __repr__(self) -> str:
        return f"<Relationship({self.source_agent_id} -> {self.target_agent_id}, closeness={self.closeness})>"


# ===================
# 对话表
# ===================

class ConversationModel(Base):
    """
    对话表
    
    存储对话的元数据和摘要
    """
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String(8), primary_key=True, default=lambda: str(uuid4())[:8])
    
    # 参与者
    participant_a_id: Mapped[str] = mapped_column(String(8), index=True)
    participant_a_name: Mapped[str] = mapped_column(String(50))
    participant_b_id: Mapped[str] = mapped_column(String(8), index=True)
    participant_b_name: Mapped[str] = mapped_column(String(50))
    
    # 状态
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    
    # 场景
    location: Mapped[str] = mapped_column(String(50), default="")
    location_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    game_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 分析结果
    topics: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    overall_emotion: Mapped[str] = mapped_column(String(20), default="中性")
    relationship_change: Mapped[int] = mapped_column(Integer, default=0)
    is_memorable: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 记忆点
    memorable_for_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    memorable_for_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 统计
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    encounter_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # 关系
    messages: Mapped[List["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.timestamp",
    )
    
    __table_args__ = (
        Index("ix_conversations_participants", "participant_a_id", "participant_b_id"),
        Index("ix_conversations_state_time", "state", "started_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, {self.participant_a_name} <-> {self.participant_b_name})>"


# ===================
# 消息表
# ===================

class MessageModel(Base):
    """
    消息表
    
    存储对话中的每条消息
    """
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String(8), primary_key=True, default=lambda: str(uuid4())[:8])
    
    # 所属对话
    conversation_id: Mapped[str] = mapped_column(
        String(8), 
        ForeignKey("conversations.id", ondelete="CASCADE"), 
        index=True
    )
    
    # 消息内容
    speaker_id: Mapped[str] = mapped_column(String(8), index=True)
    speaker_name: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 元数据
    emotion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_end_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 时间
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    # 关系
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel",
        back_populates="messages",
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, speaker={self.speaker_name})>"


# ===================
# 记忆表
# ===================

class MemoryModel(Base):
    """
    记忆表
    
    存储智能体的记忆内容
    """
    __tablename__ = "memories"
    
    id: Mapped[str] = mapped_column(String(8), primary_key=True, default=lambda: str(uuid4())[:8])
    
    # 所属智能体
    agent_id: Mapped[str] = mapped_column(
        String(8), 
        ForeignKey("agents.id", ondelete="CASCADE"), 
        index=True
    )
    
    # 记忆内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(20), default="event", index=True)
    
    # 重要性和检索
    importance: Mapped[float] = mapped_column(Float, default=5.0, index=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 关联信息
    keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    related_agents: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 向量ID（用于向量数据库检索）
    vector_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 时间
    game_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    agent: Mapped["AgentModel"] = relationship(
        "AgentModel",
        back_populates="memories",
    )
    
    __table_args__ = (
        Index("ix_memories_agent_type", "agent_id", "memory_type"),
        Index("ix_memories_agent_importance", "agent_id", "importance"),
    )
    
    def __repr__(self) -> str:
        return f"<Memory(id={self.id}, type={self.memory_type}, importance={self.importance})>"


# ===================
# 世界状态表
# ===================

class WorldStateModel(Base):
    """
    世界状态快照表
    
    用于保存和恢复世界状态
    """
    __tablename__ = "world_states"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 时间信息
    game_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    real_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 状态数据（JSON格式）
    clock_state: Mapped[dict] = mapped_column(JSONB, nullable=True)  # 时钟状态
    cost_tracker_state: Mapped[dict] = mapped_column(JSONB, nullable=True)  # 成本统计
    
    # 元数据
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_auto_save: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    __table_args__ = (
        Index("ix_world_states_game_time", "game_time"),
    )
    
    def __repr__(self) -> str:
        return f"<WorldState(id={self.id}, game_time={self.game_time})>"


# ===================
# LLM调用记录表
# ===================

class LLMCallModel(Base):
    """
    LLM调用记录表
    
    记录每次LLM调用的详情和成本
    """
    __tablename__ = "llm_calls"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 调用信息
    model_name: Mapped[str] = mapped_column(String(50), index=True)
    call_type: Mapped[str] = mapped_column(String(50), index=True)  # decision, conversation, etc.
    agent_id: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    
    # Token统计
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # 成本
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 响应时间
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    __table_args__ = (
        Index("ix_llm_calls_model_time", "model_name", "created_at"),
        Index("ix_llm_calls_date", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<LLMCall(model={self.model_name}, cost={self.cost})>"


# ===================
# 活动日志表
# ===================

class ActivityLogModel(Base):
    """
    智能体活动日志表
    
    记录智能体的每一个活动，供观察者查看
    活动类型：决策、对话、反思、反应、计划
    """
    __tablename__ = "activity_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 所属智能体
    agent_id: Mapped[str] = mapped_column(
        String(8), 
        ForeignKey("agents.id", ondelete="CASCADE"), 
        index=True
    )
    agent_name: Mapped[str] = mapped_column(String(50))
    
    # 活动类型: decision, conversation, reflection, reaction, plan
    activity_type: Mapped[str] = mapped_column(String(20), index=True)
    
    # 活动内容
    action: Mapped[str] = mapped_column(String(50))  # 具体动作: move, eat, chat等
    target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 目标
    location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 地点
    
    # 思考过程（决策时的thinking）
    thinking: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 对话相关
    conversation_id: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    conversation_partner: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 反思相关
    reflection_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间
    game_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    __table_args__ = (
        Index("ix_activity_logs_agent_time", "agent_id", "game_time"),
        Index("ix_activity_logs_agent_type", "agent_id", "activity_type"),
    )
    
    def __repr__(self) -> str:
        return f"<ActivityLog(agent={self.agent_name}, type={self.activity_type}, action={self.action})>"
