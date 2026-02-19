"""
智能体模型
=========
定义智能体的完整数据结构

智能体是AI Society的核心实体，具有：
- 身份信息：姓名、年龄、性别、职业
- 人格系统：大五人格特质
- 需求系统：生理和心理需求
- 记忆系统：经历和知识
- 经济状态：账户余额
- 空间位置：当前位置和目标位置
- 行为状态：当前行为和计划
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from uuid import uuid4

from loguru import logger

from app.agents.personality import Personality
from app.agents.needs import Needs, NeedType
from app.agents.memory import Memory, MemoryManager, MemoryType
from app.core.config import settings

# Phase 6: 类型注解导入（避免循环导入）
if TYPE_CHECKING:
    from app.agents.planning import DailyPlan


class ActionType(str, Enum):
    """行为类型枚举"""
    IDLE = "idle"  # 闲逛/发呆
    MOVE = "move"  # 移动中
    WORK = "work"  # 工作
    EAT = "eat"  # 吃饭
    SLEEP = "sleep"  # 睡觉
    REST = "rest"  # 休息
    CHAT = "chat"  # 聊天
    SHOP = "shop"  # 购物
    EXERCISE = "exercise"  # 运动
    ENTERTAINMENT = "entertainment"  # 娱乐
    WAITING = "waiting"  # 等待中


class AgentState(str, Enum):
    """智能体状态枚举"""
    ACTIVE = "active"  # 活跃（正常运行）
    SLEEPING = "sleeping"  # 睡眠中
    BUSY = "busy"  # 忙碌（正在执行长时间任务）
    IN_CONVERSATION = "in_conversation"  # 对话中
    PAUSED = "paused"  # 暂停（由用户或系统暂停）
    OFFLINE = "offline"  # 离线


@dataclass
class Position:
    """位置信息"""
    x: float = 0.0
    y: float = 0.0
    location_id: Optional[str] = None
    location_name: Optional[str] = None
    
    def distance_to(self, other: "Position") -> float:
        """计算到另一位置的距离"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "location_id": self.location_id,
            "location_name": self.location_name,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(**data)


@dataclass
class CurrentAction:
    """当前行为"""
    type: ActionType = ActionType.IDLE
    target: Optional[str] = None  # 目标（地点ID、智能体ID等）
    target_name: Optional[str] = None  # 目标名称
    started_at: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 0  # 预计持续时间（分钟）
    progress: float = 0.0  # 进度 0-100
    thinking: Optional[str] = None  # 当前想法
    
    def is_complete(self, current_time: datetime) -> bool:
        """检查行为是否完成"""
        if self.duration_minutes <= 0:
            return False
        elapsed = (current_time - self.started_at).total_seconds() / 60
        return elapsed >= self.duration_minutes
    
    def update_progress(self, current_time: datetime) -> float:
        """更新并返回进度"""
        if self.duration_minutes <= 0:
            return 0.0
        elapsed = (current_time - self.started_at).total_seconds() / 60
        self.progress = min(100, (elapsed / self.duration_minutes) * 100)
        return self.progress
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "target": self.target,
            "target_name": self.target_name,
            "started_at": self.started_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "progress": self.progress,
            "thinking": self.thinking,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CurrentAction":
        """从字典创建 CurrentAction"""
        action_type = ActionType.IDLE
        if "type" in data:
            try:
                action_type = ActionType(data["type"])
            except ValueError:
                pass
        
        started_at = datetime.now()
        if "started_at" in data and data["started_at"]:
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            type=action_type,
            target=data.get("target"),
            target_name=data.get("target_name"),
            started_at=started_at,
            duration_minutes=data.get("duration_minutes", 0),
            progress=data.get("progress", 0.0),
            thinking=data.get("thinking"),
        )


@dataclass
class Relationship:
    """与其他智能体的关系"""
    agent_id: str
    agent_name: str
    closeness: int = 50  # 亲密度 0-100
    trust: int = 50  # 信任度 0-100
    interaction_count: int = 0  # 互动次数
    last_interaction: Optional[datetime] = None
    
    def update_after_conversation(self, quality: int) -> None:
        """
        对话后更新关系
        
        Args:
            quality: 对话质量 (-10 到 +10)
        """
        self.closeness = max(0, min(100, self.closeness + quality))
        self.trust = max(0, min(100, self.trust + quality // 2))
        self.interaction_count += 1
        self.last_interaction = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "closeness": self.closeness,
            "trust": self.trust,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
        }


@dataclass
class Agent:
    """
    智能体完整模型
    
    这是AI Society中的核心实体，代表一个具有自主意识的AI居民
    """
    
    # ==================
    # 身份信息
    # ==================
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = "未命名"
    age: int = 25
    gender: str = "男"
    occupation: str = "自由职业"
    backstory: str = ""  # 背景故事
    traits: List[str] = field(default_factory=list)  # 性格特点标签
    
    # ==================
    # 核心系统
    # ==================
    personality: Personality = field(default_factory=Personality)
    needs: Needs = field(default_factory=Needs)
    memory: MemoryManager = field(default_factory=MemoryManager)
    
    # ==================
    # 经济状态
    # ==================
    balance: float = field(default_factory=lambda: settings.initial_balance)
    daily_income: float = 0.0  # 当日收入
    daily_expense: float = 0.0  # 当日支出
    
    # ==================
    # 空间位置
    # ==================
    position: Position = field(default_factory=Position)
    home_location_id: Optional[str] = None  # 家的位置
    work_location_id: Optional[str] = None  # 工作地点
    
    # ==================
    # 行为状态
    # ==================
    state: AgentState = AgentState.ACTIVE
    current_action: CurrentAction = field(default_factory=CurrentAction)
    action_queue: List[dict] = field(default_factory=list)  # 计划的行为队列
    
    # ==================
    # Phase 6: 层级计划系统
    # ==================
    daily_plan: Optional["DailyPlan"] = None  # 日计划（使用前向引用）
    
    # ==================
    # 社交关系
    # ==================
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    conversation_partner_id: Optional[str] = None  # 当前对话对象
    
    # ==================
    # LLM配置
    # ==================
    model_name: str = field(default_factory=lambda: settings.default_model)
    
    # ==================
    # 时间追踪
    # ==================
    created_at: datetime = field(default_factory=datetime.now)
    last_decision_time: Optional[datetime] = None
    work_hours_today: float = 0.0  # 今日工作时长
    
    # ==================
    # 方法
    # ==================
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保ID格式正确
        if not self.id:
            self.id = str(uuid4())[:8]
    
    def get_personality_description(self) -> str:
        """获取人格的自然语言描述"""
        return self.personality.get_description()
    
    def get_needs_description(self) -> str:
        """获取需求状态的自然语言描述"""
        return self.needs.get_status_description()
    
    def get_recent_memories(self, limit: int = 10) -> str:
        """获取近期记忆的文本描述"""
        return self.memory.get_context_for_llm(limit)
    
    def get_relationship_with(self, agent_id: str) -> Optional[Relationship]:
        """获取与指定智能体的关系"""
        return self.relationships.get(agent_id)
    
    def update_relationship(
        self,
        agent_id: str,
        agent_name: str,
        closeness_delta: int = 0,
        trust_delta: int = 0,
    ) -> Relationship:
        """
        更新与某个智能体的关系
        
        Args:
            agent_id: 对方ID
            agent_name: 对方名字
            closeness_delta: 亲密度变化
            trust_delta: 信任度变化
        
        Returns:
            更新后的关系对象
        """
        if agent_id not in self.relationships:
            self.relationships[agent_id] = Relationship(
                agent_id=agent_id,
                agent_name=agent_name,
            )
        
        rel = self.relationships[agent_id]
        rel.closeness = max(0, min(100, rel.closeness + closeness_delta))
        rel.trust = max(0, min(100, rel.trust + trust_delta))
        rel.interaction_count += 1
        rel.last_interaction = datetime.now()
        
        return rel
    
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EVENT,
        importance: float = 5.0,
        related_agents: Optional[List[str]] = None,
        game_time: Optional[datetime] = None,
    ) -> Memory:
        """添加新记忆（同步版本，使用预设或指定的importance）"""
        return self.memory.create_and_add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            related_agents=related_agents or [],
            location=self.position.location_name,
            game_time=game_time,
        )
    
    async def add_memory_async(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EVENT,
        importance: Optional[float] = None,
        related_agents: Optional[List[str]] = None,
        game_time: Optional[datetime] = None,
    ) -> Memory:
        """
        添加新记忆（异步版本，支持LLM评分）
        
        Phase 6 增强：当 importance=None 时，使用 LLM 动态评分
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性评分（None 时自动评分）
            related_agents: 相关智能体列表
            game_time: 游戏时间
        
        Returns:
            创建的记忆对象
        """
        from app.agents.memory import rate_importance
        
        # 如果未指定 importance，使用 LLM 评分
        if importance is None:
            try:
                importance = float(await rate_importance(content, self.name))
            except Exception as e:
                logger.warning(f"[{self.name}] 记忆评分失败，使用默认值: {e}")
                importance = 5.0
        
        return self.memory.create_and_add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            related_agents=related_agents or [],
            location=self.position.location_name,
            game_time=game_time,
        )
    
    def set_action(
        self,
        action_type: ActionType,
        target: Optional[str] = None,
        target_name: Optional[str] = None,
        duration_minutes: int = 0,
        thinking: Optional[str] = None,
    ) -> None:
        """设置当前行为"""
        self.current_action = CurrentAction(
            type=action_type,
            target=target,
            target_name=target_name,
            duration_minutes=duration_minutes,
            thinking=thinking,
        )
        
        # 更新状态
        if action_type == ActionType.SLEEP:
            self.state = AgentState.SLEEPING
        elif action_type == ActionType.CHAT:
            self.state = AgentState.IN_CONVERSATION
        elif action_type in [ActionType.WORK, ActionType.MOVE]:
            self.state = AgentState.BUSY
        else:
            self.state = AgentState.ACTIVE
    
    def complete_action(self) -> Optional[CurrentAction]:
        """完成当前行为"""
        completed = self.current_action
        
        # 根据完成的行为满足需求
        if completed.type == ActionType.EAT:
            self.needs.satisfy(NeedType.HUNGER)
        elif completed.type == ActionType.SLEEP:
            self.needs.satisfy(NeedType.FATIGUE, 90)
        elif completed.type == ActionType.REST:
            self.needs.satisfy(NeedType.FATIGUE, 30)
            self.needs.satisfy(NeedType.COMFORT, 20)
        elif completed.type == ActionType.CHAT:
            self.needs.satisfy(NeedType.SOCIAL)
        elif completed.type == ActionType.ENTERTAINMENT:
            self.needs.satisfy(NeedType.ENTERTAINMENT)
        elif completed.type == ActionType.WORK:
            # 工作增加疲劳但获得收入
            hourly_wage = settings.programmer_hourly_wage
            hours = completed.duration_minutes / 60
            income = hourly_wage * hours
            self.balance += income
            self.daily_income += income
            self.work_hours_today += hours
            self.needs.set(NeedType.FATIGUE, self.needs.fatigue + 15)
        
        # 重置行为
        self.current_action = CurrentAction()
        self.state = AgentState.ACTIVE
        
        return completed
    
    def move_to(self, x: float, y: float, location_id: Optional[str] = None, location_name: Optional[str] = None) -> None:
        """移动到指定位置"""
        self.position.x = x
        self.position.y = y
        self.position.location_id = location_id
        self.position.location_name = location_name
    
    def spend_money(self, amount: float, reason: str = "") -> bool:
        """
        消费金钱
        
        Returns:
            是否成功（余额是否足够）
        """
        if self.balance < amount:
            return False
        
        self.balance -= amount
        self.daily_expense += amount
        
        if reason:
            self.add_memory(
                f"消费了 {amount} 元：{reason}",
                MemoryType.EVENT,
                importance=3.0,
            )
        
        return True
    
    def reset_daily_stats(self) -> None:
        """重置每日统计（新的一天开始时调用）"""
        self.daily_income = 0.0
        self.daily_expense = 0.0
        self.work_hours_today = 0.0
    
    def get_wellbeing(self) -> float:
        """获取整体幸福指数"""
        needs_wellbeing = self.needs.get_overall_wellbeing()
        emotional_stability = self.personality.emotional_stability() * 100
        
        # 经济状况影响
        economic_factor = min(100, (self.balance / settings.initial_balance) * 50 + 50)
        
        return (needs_wellbeing * 0.5 + emotional_stability * 0.3 + economic_factor * 0.2)
    
    # ==================
    # LLM上下文生成
    # ==================
    
    def get_llm_context(self) -> dict:
        """
        生成用于LLM决策的完整上下文
        
        Returns:
            包含所有相关信息的字典
        """
        return {
            "name": self.name,
            "age": self.age,
            "occupation": self.occupation,
            "personality_description": self.get_personality_description(),
            "current_location": self.position.location_name or "未知位置",
            "current_time": datetime.now().strftime("%H:%M"),
            "work_hours_today": round(self.work_hours_today, 1),
            "balance": round(self.balance, 2),
            "hunger": round(self.needs.hunger, 0),
            "fatigue": round(self.needs.fatigue, 0),
            "social": round(self.needs.social, 0),
            "entertainment": round(self.needs.entertainment, 0),
            "recent_memories": self.get_recent_memories(),
            "surroundings": "",  # 由AgentManager填充
        }
    
    # ==================
    # 序列化
    # ==================
    
    def to_dict(self) -> dict:
        """转换为字典（用于存储和API）"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "backstory": self.backstory,
            "traits": self.traits,
            "personality": self.personality.to_dict(),
            "needs": self.needs.to_dict(),
            "balance": self.balance,
            "position": self.position.to_dict(),
            "home_location_id": self.home_location_id,
            "work_location_id": self.work_location_id,
            "state": self.state.value,
            "current_action": self.current_action.to_dict(),
            "model_name": self.model_name,
            "created_at": self.created_at.isoformat(),
            "work_hours_today": self.work_hours_today,
            "relationships": {
                k: v.to_dict() for k, v in self.relationships.items()
            },
        }
    
    def to_brief_dict(self) -> dict:
        """转换为简要信息（用于列表显示）"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "occupation": self.occupation,
            "position": self.position.to_dict(),
            "current_action": self.current_action.type.value,
            "is_in_conversation": self.state == AgentState.IN_CONVERSATION,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        """从字典创建智能体"""
        # 处理嵌套对象
        if "personality" in data and isinstance(data["personality"], dict):
            data["personality"] = Personality.from_dict(data["personality"])
        if "needs" in data and isinstance(data["needs"], dict):
            data["needs"] = Needs.from_dict(data["needs"])
        if "position" in data and isinstance(data["position"], dict):
            data["position"] = Position.from_dict(data["position"])
        if "current_action" in data and isinstance(data["current_action"], dict):
            data["current_action"] = CurrentAction.from_dict(data["current_action"])
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "state" in data and isinstance(data["state"], str):
            data["state"] = AgentState(data["state"])
        
        # 移除不是Agent参数的字段
        valid_fields = {f.name for f in Agent.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
