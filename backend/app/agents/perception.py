"""
环境感知模块
===========
智能体感知周围环境的能力

参考：斯坦福 Generative Agents 论文 (arxiv:2304.03442)

感知内容：
- 附近的智能体
- 新发生的事件
- 是否有人在对自己说话
- 环境变化
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional, Set

from loguru import logger

if TYPE_CHECKING:
    from app.agents.models import Agent


@dataclass
class Perception:
    """
    感知结果
    
    包含智能体在当前时刻观察到的所有信息
    """
    # 位置信息
    current_location: str = ""
    current_location_id: Optional[str] = None
    
    # 附近智能体
    agents_nearby: List[str] = field(default_factory=list)  # 智能体名字列表
    agents_nearby_ids: List[str] = field(default_factory=list)  # 智能体ID列表
    
    # 事件与交互
    new_events: List[str] = field(default_factory=list)  # 新发生的事件描述
    being_addressed: bool = False  # 是否有人在叫自己/等待回应
    addressed_by: Optional[str] = None  # 谁在叫自己
    
    # 环境变化
    notable_changes: List[str] = field(default_factory=list)  # 值得注意的变化
    
    # 元信息
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_description(self) -> str:
        """
        生成自然语言描述
        
        Returns:
            感知的文本描述
        """
        lines = []
        
        # 位置
        if self.current_location:
            lines.append(f"当前位置：{self.current_location}")
        
        # 附近的人
        if self.agents_nearby:
            if len(self.agents_nearby) == 1:
                lines.append(f"附近有：{self.agents_nearby[0]}")
            else:
                lines.append(f"附近有：{', '.join(self.agents_nearby)}")
        else:
            lines.append("附近没有其他人")
        
        # 是否被叫到
        if self.being_addressed and self.addressed_by:
            lines.append(f"⚠️ {self.addressed_by} 在等待你的回应")
        
        # 新事件
        if self.new_events:
            lines.append("刚刚发生的事：")
            for event in self.new_events:
                lines.append(f"  - {event}")
        
        # 变化
        if self.notable_changes:
            lines.append("注意到的变化：")
            for change in self.notable_changes:
                lines.append(f"  - {change}")
        
        return "\n".join(lines)
    
    def is_empty(self) -> bool:
        """检查感知是否为空"""
        return (
            not self.agents_nearby
            and not self.new_events
            and not self.being_addressed
            and not self.notable_changes
        )
    
    def has_urgent_matters(self) -> bool:
        """检查是否有紧急事项"""
        return self.being_addressed or len(self.new_events) > 0


class PerceptionSystem:
    """
    感知系统
    
    负责收集智能体周围的环境信息
    """
    
    def __init__(self, perception_radius: float = 50.0):
        """
        初始化感知系统
        
        Args:
            perception_radius: 感知半径
        """
        self.perception_radius = perception_radius
        
        # 追踪最近的事件（用于检测新事件）
        self._recent_events: List[dict] = []
        self._last_event_check: datetime = datetime.now()
    
    def add_event(self, event: dict) -> None:
        """
        添加一个新事件
        
        Args:
            event: 事件字典，应包含 location_id, description 等
        """
        event["timestamp"] = datetime.now()
        self._recent_events.append(event)
        
        # 清理旧事件（保留最近5分钟的）
        cutoff = datetime.now() - timedelta(minutes=5)
        self._recent_events = [
            e for e in self._recent_events
            if e.get("timestamp", datetime.min) > cutoff
        ]
    
    async def perceive(self, agent: "Agent") -> Perception:
        """
        为智能体执行感知
        
        Args:
            agent: 智能体对象
        
        Returns:
            感知结果
        """
        from app.agents.manager import agent_manager
        from app.core.locations import location_manager
        
        perception = Perception(timestamp=datetime.now())
        
        # 1. 获取当前位置信息
        if agent.position.location_id:
            location = location_manager.get(agent.position.location_id)
            if location:
                perception.current_location = location.name
                perception.current_location_id = location.id
        elif agent.position.location_name:
            perception.current_location = agent.position.location_name
        
        # 2. 获取附近的智能体
        nearby_context = agent_manager.get_nearby_context(agent.id)
        
        # 同一位置的智能体
        for nearby_agent in nearby_context.agents_here:
            if nearby_agent.id != agent.id:
                perception.agents_nearby.append(nearby_agent.name)
                perception.agents_nearby_ids.append(nearby_agent.id)
        
        # 邻近位置的智能体
        for nearby_agent in nearby_context.agents_nearby:
            if nearby_agent.id != agent.id:
                perception.agents_nearby.append(nearby_agent.name)
                perception.agents_nearby_ids.append(nearby_agent.id)
        
        # 3. 检查是否有人在等待回应（对话状态）
        if agent.conversation_partner_id:
            partner = agent_manager.get_agent(agent.conversation_partner_id)
            if partner:
                perception.being_addressed = True
                perception.addressed_by = partner.name
        
        # 4. 获取附近的新事件
        cutoff = self._last_event_check
        self._last_event_check = datetime.now()
        
        for event in self._recent_events:
            event_time = event.get("timestamp", datetime.min)
            event_location = event.get("location_id")
            
            # 检查事件是否在感知范围内且是新的
            if event_time > cutoff:
                if event_location == agent.position.location_id or not event_location:
                    description = event.get("description", "发生了一些事")
                    perception.new_events.append(description)
        
        # 5. 检测环境变化（简化版本）
        # TODO: 可以添加更复杂的变化检测，如天气、时间段变化等
        
        logger.debug(
            f"[{agent.name}] 感知结果: 位置={perception.current_location}, "
            f"附近={len(perception.agents_nearby)}人, 事件={len(perception.new_events)}个"
        )
        
        return perception


# 全局感知系统实例
perception_system = PerceptionSystem()


async def perceive_environment(agent: "Agent") -> Perception:
    """
    感知环境的便捷函数
    
    Args:
        agent: 智能体对象
    
    Returns:
        感知结果
    """
    return await perception_system.perceive(agent)
