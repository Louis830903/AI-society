"""
对话模块
=======
包含对话数据模型、对话管理、对话生成和对话分析

核心功能：
- Conversation: 对话数据模型
- ConversationManager: 对话管理器
- 对话生成: 使用LLM生成自然对话
- 对话分析: 提取情感、话题，计算关系影响
"""

from app.conversations.models import (
    Conversation,
    ConversationState,
    Message,
    MessageRole,
)
from app.conversations.manager import ConversationManager, conversation_manager
from app.conversations.generator import (
    generate_opening,
    generate_reply,
    ConversationGenerator,
)
from app.conversations.analyzer import (
    analyze_conversation,
    ConversationAnalysis,
)

__all__ = [
    # 数据模型
    "Conversation",
    "ConversationState",
    "Message",
    "MessageRole",
    # 管理器
    "ConversationManager",
    "conversation_manager",
    # 生成器
    "generate_opening",
    "generate_reply",
    "ConversationGenerator",
    # 分析器
    "analyze_conversation",
    "ConversationAnalysis",
]
