"""
智能体模块
=========
包含智能体数据模型、人格系统、需求系统、记忆系统和行为决策
"""

from app.agents.models import Agent, AgentState, ActionType, Position, CurrentAction
from app.agents.personality import Personality, PersonalityTrait
from app.agents.needs import Needs, NeedType
from app.agents.memory import Memory, MemoryType, MemoryManager
from app.agents.manager import AgentManager, agent_manager
from app.agents.decision import Decision, DecisionScheduler, decision_scheduler, make_decision
from app.agents.generator import (
    generate_agent_from_template,
    generate_agent_with_llm,
    generate_initial_agents,
    generate_single_agent,
)
from app.agents.balance_detector import (
    SocialBalanceDetector,
    social_balance_detector,
    SocialBalanceReport,
    OccupationGap,
    SocialIsolate,
)
from app.agents.auto_expander import (
    AutoExpander,
    auto_expander,
    ExpansionEvent,
)

__all__ = [
    # 核心模型
    "Agent",
    "AgentState",
    "ActionType",
    "Position",
    "CurrentAction",
    # 人格系统
    "Personality",
    "PersonalityTrait",
    # 需求系统
    "Needs",
    "NeedType",
    # 记忆系统
    "Memory",
    "MemoryType",
    "MemoryManager",
    # 管理器
    "AgentManager",
    "agent_manager",
    # 决策系统
    "Decision",
    "DecisionScheduler",
    "decision_scheduler",
    "make_decision",
    # 生成器
    "generate_agent_from_template",
    "generate_agent_with_llm",
    "generate_initial_agents",
    "generate_single_agent",
    # 社会平衡
    "SocialBalanceDetector",
    "social_balance_detector",
    "SocialBalanceReport",
    "OccupationGap",
    "SocialIsolate",
    # 自动扩展
    "AutoExpander",
    "auto_expander",
    "ExpansionEvent",
]
