"""
对话管理器
=========
管理所有进行中的对话

功能：
- 创建和跟踪对话
- 匹配对话请求
- 维护对话历史
- 处理对话结束
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from app.conversations.models import (
    Conversation,
    ConversationState,
    ConversationParticipant,
    Message,
)
from app.core.events import event_bus, Event, EventType
from app.core.config import settings


class ConversationManager:
    """
    对话管理器
    
    单例模式，管理整个世界的所有对话
    """
    
    def __init__(self):
        """初始化管理器"""
        # 活跃对话 id -> Conversation
        self._active: Dict[str, Conversation] = {}
        
        # 已结束对话历史（保留最近的）
        self._history: List[Conversation] = []
        self._max_history: int = 100
        
        # 正在对话的智能体 agent_id -> conversation_id
        self._agents_in_conversation: Dict[str, str] = {}
        
        # 待匹配的对话请求 initiator_id -> target_id
        self._pending_requests: Dict[str, str] = {}
        
        logger.info("对话管理器初始化完成")
    
    # ==================
    # 对话生命周期
    # ==================
    
    def create_conversation(
        self,
        agent_a_id: str,
        agent_a_name: str,
        agent_b_id: str,
        agent_b_name: str,
        location: str = "",
        location_id: Optional[str] = None,
        game_time: Optional[datetime] = None,
    ) -> Conversation:
        """
        创建新对话
        
        Args:
            agent_a_id: 发起者ID
            agent_a_name: 发起者名字
            agent_b_id: 接收者ID
            agent_b_name: 接收者名字
            location: 地点名称
            location_id: 地点ID
            game_time: 游戏内时间
        
        Returns:
            创建的对话对象
        """
        # 检查是否已在对话中
        if agent_a_id in self._agents_in_conversation:
            raise ValueError(f"{agent_a_name} 已在对话中")
        if agent_b_id in self._agents_in_conversation:
            raise ValueError(f"{agent_b_name} 已在对话中")
        
        # 创建对话
        conversation = Conversation(
            participant_a=ConversationParticipant(
                agent_id=agent_a_id,
                agent_name=agent_a_name,
            ),
            participant_b=ConversationParticipant(
                agent_id=agent_b_id,
                agent_name=agent_b_name,
            ),
            location=location,
            location_id=location_id,
            game_time=game_time,
        )
        
        # 注册
        self._active[conversation.id] = conversation
        self._agents_in_conversation[agent_a_id] = conversation.id
        self._agents_in_conversation[agent_b_id] = conversation.id
        
        # 发布事件（安全处理，可能没有运行中的事件循环）
        try:
            asyncio.create_task(event_bus.publish(Event(
                event_type=EventType.CONVERSATION_STARTED,
                data={
                    "conversation_id": conversation.id,
                    "agent_a_id": agent_a_id,
                    "agent_b_id": agent_b_id,
                    "location": location,
                }
            )))
        except RuntimeError:
            # 没有运行中的事件循环（如在测试中）
            pass
        
        logger.info(f"对话开始: {agent_a_name} 与 {agent_b_name} 在 {location}")
        
        return conversation
    
    def end_conversation(
        self,
        conversation_id: str,
        reason: str = "normal",
    ) -> Optional[Conversation]:
        """
        结束对话
        
        Args:
            conversation_id: 对话ID
            reason: 结束原因（normal/interrupted/timeout）
        
        Returns:
            结束的对话对象
        """
        conversation = self._active.get(conversation_id)
        if not conversation:
            return None
        
        # 更新状态
        if reason == "interrupted":
            conversation.interrupt()
        else:
            conversation.end()
        
        # 从活跃列表移除
        del self._active[conversation_id]
        
        # 从智能体追踪中移除
        if conversation.participant_a:
            self._agents_in_conversation.pop(conversation.participant_a.agent_id, None)
        if conversation.participant_b:
            self._agents_in_conversation.pop(conversation.participant_b.agent_id, None)
        
        # 添加到历史
        self._history.append(conversation)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # 发布事件（安全处理，可能没有运行中的事件循环）
        try:
            asyncio.create_task(event_bus.publish(Event(
                event_type=EventType.CONVERSATION_ENDED,
                data={
                    "conversation_id": conversation_id,
                    "reason": reason,
                    "message_count": conversation.message_count,
                    "relationship_change": conversation.relationship_change,
                }
            )))
        except RuntimeError:
            # 没有运行中的事件循环（如在测试中）
            pass
        
        logger.info(
            f"对话结束: {conversation.participant_a.agent_name if conversation.participant_a else '?'} "
            f"与 {conversation.participant_b.agent_name if conversation.participant_b else '?'} "
            f"({conversation.message_count}条消息, 关系变化{conversation.relationship_change:+d})"
        )
        
        return conversation
    
    # ==================
    # 查询方法
    # ==================
    
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        return self._active.get(conversation_id)
    
    def get_by_agent(self, agent_id: str) -> Optional[Conversation]:
        """获取智能体当前参与的对话"""
        conv_id = self._agents_in_conversation.get(agent_id)
        return self._active.get(conv_id) if conv_id else None
    
    def is_in_conversation(self, agent_id: str) -> bool:
        """检查智能体是否在对话中"""
        return agent_id in self._agents_in_conversation
    
    def get_active_conversations(self) -> List[Conversation]:
        """获取所有活跃对话"""
        return list(self._active.values())
    
    def get_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Conversation]:
        """
        获取对话历史
        
        Args:
            agent_id: 筛选特定智能体的对话
            limit: 返回数量
        """
        if agent_id:
            filtered = [
                c for c in self._history
                if (c.participant_a and c.participant_a.agent_id == agent_id) or
                   (c.participant_b and c.participant_b.agent_id == agent_id)
            ]
            return filtered[-limit:]
        
        return self._history[-limit:]
    
    def get_conversation_between(
        self,
        agent_a_id: str,
        agent_b_id: str,
        include_history: bool = True,
    ) -> List[Conversation]:
        """获取两个智能体之间的所有对话"""
        conversations = []
        
        # 检查活跃对话
        for conv in self._active.values():
            if self._is_between(conv, agent_a_id, agent_b_id):
                conversations.append(conv)
        
        # 检查历史
        if include_history:
            for conv in self._history:
                if self._is_between(conv, agent_a_id, agent_b_id):
                    conversations.append(conv)
        
        return conversations
    
    def _is_between(self, conv: Conversation, agent_a_id: str, agent_b_id: str) -> bool:
        """检查对话是否在两个智能体之间"""
        ids = set()
        if conv.participant_a:
            ids.add(conv.participant_a.agent_id)
        if conv.participant_b:
            ids.add(conv.participant_b.agent_id)
        return {agent_a_id, agent_b_id} == ids
    
    def count_encounters(self, agent_a_id: str, agent_b_id: str) -> int:
        """统计两个智能体相遇的次数"""
        return len(self.get_conversation_between(agent_a_id, agent_b_id, include_history=True))
    
    # ==================
    # 对话请求匹配
    # ==================
    
    def request_conversation(
        self,
        initiator_id: str,
        target_id: str,
    ) -> bool:
        """
        发起对话请求
        
        Args:
            initiator_id: 发起者ID
            target_id: 目标ID
        
        Returns:
            是否成功发起请求
        """
        # 检查双方是否可用
        if self.is_in_conversation(initiator_id):
            return False
        if self.is_in_conversation(target_id):
            return False
        
        self._pending_requests[initiator_id] = target_id
        
        logger.debug(f"对话请求: {initiator_id} -> {target_id}")
        return True
    
    def accept_request(self, target_id: str, initiator_id: str) -> Optional[str]:
        """
        接受对话请求
        
        Returns:
            对话ID（如果成功）
        """
        if self._pending_requests.get(initiator_id) != target_id:
            return None
        
        # 移除请求
        del self._pending_requests[initiator_id]
        
        # 实际创建对话需要在外部完成（需要Agent信息）
        return initiator_id  # 返回发起者ID作为标记
    
    def cancel_request(self, initiator_id: str) -> bool:
        """取消对话请求"""
        if initiator_id in self._pending_requests:
            del self._pending_requests[initiator_id]
            return True
        return False
    
    def get_pending_request_for(self, target_id: str) -> Optional[str]:
        """获取发给某人的待处理请求"""
        for initiator, target in self._pending_requests.items():
            if target == target_id:
                return initiator
        return None
    
    # ==================
    # 统计信息
    # ==================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_messages = sum(c.message_count for c in self._active.values())
        total_history_messages = sum(c.message_count for c in self._history)
        
        return {
            "active_conversations": len(self._active),
            "agents_in_conversation": len(self._agents_in_conversation),
            "pending_requests": len(self._pending_requests),
            "history_count": len(self._history),
            "total_messages_active": total_messages,
            "total_messages_history": total_history_messages,
        }
    
    # ==================
    # 清理
    # ==================
    
    def clear_stale_conversations(self, max_duration_seconds: float = 600) -> int:
        """
        清理超时的对话
        
        Args:
            max_duration_seconds: 最大持续时间（秒）
        
        Returns:
            清理的对话数量
        """
        now = datetime.now()
        stale_ids = []
        
        for conv_id, conv in self._active.items():
            if (now - conv.started_at).total_seconds() > max_duration_seconds:
                stale_ids.append(conv_id)
        
        for conv_id in stale_ids:
            self.end_conversation(conv_id, reason="timeout")
        
        if stale_ids:
            logger.info(f"清理了 {len(stale_ids)} 个超时对话")
        
        return len(stale_ids)
    
    def clear(self) -> None:
        """清空所有对话"""
        self._active.clear()
        self._agents_in_conversation.clear()
        self._pending_requests.clear()
        self._history.clear()


# 创建全局单例
conversation_manager = ConversationManager()
