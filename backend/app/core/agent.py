from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Occupation(str, Enum):
    PROGRAMMER = "programmer"
    DESIGNER = "designer"
    WAITER = "waiter"
    STUDENT = "student"
    ARTIST = "artist"
    TEACHER = "teacher"
    RETIRED = "retired"


@dataclass
class Personality:
    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int


@dataclass
class Needs:
    energy: int = 100
    social: int = 50


@dataclass
class Economy:
    money: float = 0.0
    income_per_hour: float = 0.0
    base_daily_cost: float = 0.0  # 房租+吃饭等基础开销（现实世界对齐）


@dataclass
class AgentState:
    id: str
    name: str
    age: int
    gender: Gender
    occupation: Occupation
    personality: Personality
    skills: Dict[str, int]
    life_goal: str

    # 状态
    x: float
    y: float
    needs: Needs = field(default_factory=Needs)
    economy: Economy = field(default_factory=Economy)

    current_action: str = "idle"
    current_thinking: str = ""
    current_emotion: str = "neutral"

    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # 记忆索引（具体内容在记忆模块）
    recent_memory_ids: List[str] = field(default_factory=list)

    # 使用的模型标识，例如 "deepseek-chat" / "deepseek-reasoner" / "openai-gpt4o"
    model_name: str = "deepseek-chat"


@dataclass
class AgentDecision:
    action: str
    target: Optional[str]
    reason: str
    thinking: str


@dataclass
class AgentContext:
    world_time: datetime
    location_name: str
    nearby_agent_summaries: List[str]
    recent_memories: List[str]
