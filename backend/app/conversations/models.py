"""
对话数据模型
===========
定义对话的完整数据结构

对话组成：
- Conversation: 一次完整对话
- Message: 单条消息
- 参与者信息
- 对话元数据（地点、时间、话题等）
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import uuid4


class MessageRole(str, Enum):
    """消息角色"""
    SPEAKER = "speaker"  # 说话者
    LISTENER = "listener"  # 听者
    SYSTEM = "system"  # 系统消息


class ConversationState(str, Enum):
    """对话状态"""
    PENDING = "pending"  # 等待开始
    ACTIVE = "active"  # 进行中
    ENDING = "ending"  # 即将结束
    ENDED = "ended"  # 已结束
    INTERRUPTED = "interrupted"  # 被打断


@dataclass
class Message:
    """
    单条消息
    
    Attributes:
        id: 消息ID
        role: 消息角色
        speaker_id: 说话者ID
        speaker_name: 说话者名字
        content: 消息内容
        timestamp: 消息时间
        emotion: 说话时的情绪
        is_end_signal: 是否为结束信号（如告别）
    """
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    role: MessageRole = MessageRole.SPEAKER
    speaker_id: str = ""
    speaker_name: str = ""
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    emotion: Optional[str] = None
    is_end_signal: bool = False
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role.value,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion,
            "is_end_signal": self.is_end_signal,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """从字典创建"""
        data = data.copy()
        if "role" in data:
            data["role"] = MessageRole(data["role"])
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ConversationParticipant:
    """对话参与者信息"""
    agent_id: str
    agent_name: str
    occupation: str = ""
    personality_description: str = ""
    relationship_to_other: str = "陌生人"  # 与对方的关系描述
    closeness: int = 50  # 亲密度 0-100
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "occupation": self.occupation,
            "personality_description": self.personality_description,
            "relationship_to_other": self.relationship_to_other,
            "closeness": self.closeness,
        }


@dataclass
class Conversation:
    """
    完整对话模型
    
    代表两个智能体之间的一次对话
    
    Attributes:
        id: 对话ID
        participant_a: 参与者A（发起者）
        participant_b: 参与者B
        messages: 消息列表
        state: 对话状态
        location: 发生地点
        location_id: 地点ID
        started_at: 开始时间
        ended_at: 结束时间
        topics: 讨论的话题
        overall_emotion: 整体情感倾向
        relationship_change: 关系变化值
        is_memorable: 是否值得记忆
        summary: 对话摘要
    """
    
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    # 参与者
    participant_a: Optional[ConversationParticipant] = None
    participant_b: Optional[ConversationParticipant] = None
    
    # 消息
    messages: List[Message] = field(default_factory=list)
    
    # 状态
    state: ConversationState = ConversationState.PENDING
    
    # 场景信息
    location: str = ""
    location_id: Optional[str] = None
    game_time: Optional[datetime] = None  # 游戏内时间
    
    # 时间追踪
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # 分析结果
    topics: List[str] = field(default_factory=list)
    overall_emotion: str = "中性"
    relationship_change: int = 0  # -10 到 +10
    is_memorable: bool = False
    summary: str = ""
    
    # 记忆点（双方各自的记忆）
    memorable_for_a: str = ""
    memorable_for_b: str = ""
    
    # 追踪
    encounter_count: int = 1  # 这是第几次相遇
    
    def __post_init__(self):
        """初始化后处理"""
        if self.state == ConversationState.PENDING and self.messages:
            self.state = ConversationState.ACTIVE
    
    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages)
    
    @property
    def duration_seconds(self) -> float:
        """对话持续时间（秒）"""
        if not self.messages:
            return 0
        
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    @property
    def current_speaker_id(self) -> Optional[str]:
        """当前应该说话的人"""
        if not self.messages:
            return self.participant_a.agent_id if self.participant_a else None
        
        last_speaker = self.messages[-1].speaker_id
        if self.participant_a and last_speaker == self.participant_a.agent_id:
            return self.participant_b.agent_id if self.participant_b else None
        return self.participant_a.agent_id if self.participant_a else None
    
    def add_message(
        self,
        speaker_id: str,
        speaker_name: str,
        content: str,
        emotion: Optional[str] = None,
        is_end_signal: bool = False,
    ) -> Message:
        """
        添加一条消息
        
        Args:
            speaker_id: 说话者ID
            speaker_name: 说话者名字
            content: 消息内容
            emotion: 情绪
            is_end_signal: 是否是结束信号
        
        Returns:
            创建的消息对象
        """
        message = Message(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            content=content,
            emotion=emotion,
            is_end_signal=is_end_signal,
        )
        
        self.messages.append(message)
        
        # 更新状态
        if self.state == ConversationState.PENDING:
            self.state = ConversationState.ACTIVE
        
        if is_end_signal:
            self.state = ConversationState.ENDING
        
        # 发布消息事件（延迟导入避免循环依赖）
        try:
            from app.core.events import event_bus, Event, EventType
            asyncio.create_task(event_bus.publish(Event(
                event_type=EventType.CONVERSATION_MESSAGE,
                data={
                    "conversation_id": self.id,
                    "message_id": message.id,
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "content": content,
                    "emotion": emotion,
                    "location": self.location,
                    "participant_a_id": self.participant_a.agent_id if self.participant_a else None,
                    "participant_b_id": self.participant_b.agent_id if self.participant_b else None,
                }
            )))
        except RuntimeError:
            # 没有运行中的事件循环（如在测试中）
            pass
        
        return message
    
    def end(self) -> None:
        """结束对话"""
        self.state = ConversationState.ENDED
        self.ended_at = datetime.now()
    
    def interrupt(self) -> None:
        """中断对话"""
        self.state = ConversationState.INTERRUPTED
        self.ended_at = datetime.now()
    
    def get_participant(self, agent_id: str) -> Optional[ConversationParticipant]:
        """获取参与者信息"""
        if self.participant_a and self.participant_a.agent_id == agent_id:
            return self.participant_a
        if self.participant_b and self.participant_b.agent_id == agent_id:
            return self.participant_b
        return None
    
    def get_other_participant(self, agent_id: str) -> Optional[ConversationParticipant]:
        """获取另一个参与者"""
        if self.participant_a and self.participant_a.agent_id == agent_id:
            return self.participant_b
        if self.participant_b and self.participant_b.agent_id == agent_id:
            return self.participant_a
        return None
    
    def get_history_text(self, max_messages: int = 20) -> str:
        """
        获取对话历史的文本形式
        
        用于LLM提示词
        """
        if not self.messages:
            return "（对话刚开始）"
        
        recent = self.messages[-max_messages:]
        lines = []
        
        for msg in recent:
            lines.append(f"{msg.speaker_name}：{msg.content}")
        
        return "\n".join(lines)
    
    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None
    
    def is_turn_of(self, agent_id: str) -> bool:
        """检查是否轮到某个智能体说话"""
        return self.current_speaker_id == agent_id
    
    # ===================
    # 序列化
    # ===================
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "participant_a": self.participant_a.to_dict() if self.participant_a else None,
            "participant_b": self.participant_b.to_dict() if self.participant_b else None,
            "messages": [m.to_dict() for m in self.messages],
            "state": self.state.value,
            "location": self.location,
            "location_id": self.location_id,
            "game_time": self.game_time.isoformat() if self.game_time else None,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "topics": self.topics,
            "overall_emotion": self.overall_emotion,
            "relationship_change": self.relationship_change,
            "is_memorable": self.is_memorable,
            "summary": self.summary,
            "memorable_for_a": self.memorable_for_a,
            "memorable_for_b": self.memorable_for_b,
            "encounter_count": self.encounter_count,
            "message_count": self.message_count,
            "duration_seconds": self.duration_seconds,
        }
    
    def to_brief_dict(self) -> dict:
        """转换为简要信息"""
        return {
            "id": self.id,
            "participant_a_name": self.participant_a.agent_name if self.participant_a else "",
            "participant_b_name": self.participant_b.agent_name if self.participant_b else "",
            "state": self.state.value,
            "location": self.location,
            "message_count": self.message_count,
            "started_at": self.started_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """从字典创建"""
        data = data.copy()
        
        # 处理枚举
        if "state" in data:
            data["state"] = ConversationState(data["state"])
        
        # 处理日期
        for date_field in ["started_at", "ended_at", "game_time"]:
            if date_field in data and data[date_field]:
                data[date_field] = datetime.fromisoformat(data[date_field])
        
        # 处理参与者
        if "participant_a" in data and data["participant_a"]:
            data["participant_a"] = ConversationParticipant(**data["participant_a"])
        if "participant_b" in data and data["participant_b"]:
            data["participant_b"] = ConversationParticipant(**data["participant_b"])
        
        # 处理消息
        if "messages" in data:
            data["messages"] = [Message.from_dict(m) for m in data["messages"]]
        
        # 移除计算属性
        data.pop("message_count", None)
        data.pop("duration_seconds", None)
        
        return cls(**data)
