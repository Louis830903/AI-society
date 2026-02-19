"""
对话事件处理器
==============
处理CHAT决策，自动启动对话生成

核心功能：
- 订阅 chat.requested 事件
- 查找目标智能体
- 创建并运行对话
- 保存对话到数据库
"""

import asyncio
from typing import Optional
from datetime import datetime

from loguru import logger

from app.core.events import event_bus, Event, EventType
from app.core.world import world_clock
from app.conversations.manager import conversation_manager
from app.conversations.generator import ConversationGenerator
from app.database.crud import conversations as crud_conversations


class ConversationEventHandler:
    """
    对话事件处理器
    
    负责处理CHAT决策并启动对话生成
    """
    
    def __init__(self):
        """初始化处理器"""
        self._running_conversations: set = set()  # 正在进行的对话ID
        logger.info("对话事件处理器初始化完成")
    
    async def handle_chat_request(self, event_data: dict) -> None:
        """
        处理聊天请求事件
        
        Args:
            event_data: 事件数据，包含 initiator_id 和 target_name
        """
        from app.agents.manager import agent_manager
        
        logger.info(f"收到聊天请求事件: {event_data}")
        
        initiator_id = event_data.get("initiator_id")
        target_name = event_data.get("target_name")
        
        if not initiator_id or not target_name:
            logger.warning(f"聊天请求缺少必要信息: {event_data}")
            return
        
        # 获取发起者
        initiator = agent_manager.get_agent(initiator_id)
        if not initiator:
            logger.warning(f"找不到聊天发起者: {initiator_id}")
            return
        
        # 根据名字查找目标智能体
        target = None
        for agent in agent_manager.agents.values():
            if agent.name == target_name:
                target = agent
                break
        
        if not target:
            logger.warning(f"[{initiator.name}] 找不到聊天对象: {target_name}")
            # 设置发起者行为为IDLE（聊天失败）
            from app.agents.models import ActionType
            initiator.set_action(
                ActionType.IDLE,
                duration_minutes=5,
                thinking=f"想找{target_name}聊天，但找不到人",
            )
            return
        
        # 注意：不检查发起者的 is_in_conversation 状态，因为是决策系统先设置了状态再发事件
        # 只检查目标是否在对话中
        if conversation_manager.is_in_conversation(target.id):
            logger.debug(f"[{target.name}] 已在对话中，跳过")
            # 重置发起者状态为IDLE
            from app.agents.models import ActionType
            initiator.set_action(
                ActionType.IDLE,
                duration_minutes=5,
                thinking=f"想找{target_name}聊天，但对方正忙",
            )
            return
        
        # 启动对话任务（异步执行，不阻塞决策循环）
        asyncio.create_task(
            self._run_conversation(initiator, target)
        )
    
    async def _run_conversation(self, initiator, target) -> None:
        """
        运行完整对话流程
        
        Args:
            initiator: 发起对话的智能体
            target: 目标智能体
        """
        from app.agents.models import ActionType
        
        conversation = None
        
        try:
            # 获取当前游戏时间
            game_time = world_clock.get_time()
            
            # 获取发起者当前位置
            location = initiator.current_location or "某处"
            location_id = initiator.current_location_id
            
            # 创建对话
            try:
                conversation = conversation_manager.create_conversation(
                    agent_a_id=initiator.id,
                    agent_a_name=initiator.name,
                    agent_b_id=target.id,
                    agent_b_name=target.name,
                    location=location,
                    location_id=location_id,
                    game_time=game_time,
                )
            except ValueError as e:
                logger.warning(f"创建对话失败: {e}")
                return
            
            self._running_conversations.add(conversation.id)
            
            logger.info(f"开始对话: [{initiator.name}] <-> [{target.name}] @ {location}")
            
            # 设置目标智能体也进入聊天状态
            target.set_action(
                ActionType.CHAT,
                target=initiator.name,
                target_name=initiator.name,
                duration_minutes=15,
                thinking=f"和{initiator.name}聊天",
            )
            
            # 创建对话生成器
            generator = ConversationGenerator(conversation)
            
            # 获取智能体性格描述
            initiator_personality = self._get_personality_description(initiator)
            target_personality = self._get_personality_description(target)
            
            # 运行对话（生成多轮对话）
            completed_conversation = await generator.run_conversation(
                max_turns=10,
                speaker_a_personality=initiator_personality,
                speaker_b_personality=target_personality,
            )
            
            # 对话完成，结束对话
            conversation_manager.end_conversation(
                conversation.id,
                reason="normal",
            )
            
            # 保存对话到数据库
            await self._save_conversation_to_db(completed_conversation)
            
            # 更新智能体记忆
            await self._update_agent_memories(initiator, target, completed_conversation)
            
            logger.info(
                f"对话完成: [{initiator.name}] <-> [{target.name}] "
                f"({completed_conversation.message_count}条消息)"
            )
            
        except Exception as e:
            logger.error(f"对话执行失败: {e}", exc_info=True)
            
            # 尝试清理
            if conversation:
                try:
                    conversation_manager.end_conversation(conversation.id, reason="error")
                except:
                    pass
                    
        finally:
            if conversation:
                self._running_conversations.discard(conversation.id)
    
    def _get_personality_description(self, agent) -> str:
        """
        获取智能体性格描述
        
        Args:
            agent: 智能体对象
        
        Returns:
            性格描述字符串
        """
        traits = agent.personality.traits if agent.personality else []
        if traits:
            return "、".join(traits[:3])  # 取前3个特质
        return "普通人"
    
    async def _save_conversation_to_db(self, conversation) -> None:
        """
        保存对话到数据库
        
        Args:
            conversation: 对话对象
        """
        try:
            from app.database.database import get_db_context
            
            async with get_db_context() as db:
                # 保存对话记录
                await crud_conversations.create_conversation(db, conversation)
                
                # 保存所有消息
                for message in conversation.messages:
                    await crud_conversations.create_message(db, conversation.id, message)
                
                logger.debug(f"对话已保存到数据库: {conversation.id}")
                
        except Exception as e:
            logger.error(f"保存对话到数据库失败: {e}")
    
    async def _update_agent_memories(self, initiator, target, conversation) -> None:
        """
        更新智能体记忆
        
        Args:
            initiator: 发起者
            target: 目标
            conversation: 对话对象
        """
        from app.agents.models import MemoryType
        
        try:
            # 为发起者添加记忆
            memory_content = f"和{target.name}聊了天"
            if conversation.messages:
                # 取最后一条消息作为记忆的一部分
                last_msg = conversation.messages[-1]
                if last_msg.content and len(last_msg.content) > 10:
                    memory_content = f"和{target.name}聊天，聊了{len(conversation.messages)}句话"
            
            initiator.add_memory(
                memory_content,
                MemoryType.SOCIAL,
                importance=5.0,
                keywords=[target.name, "聊天", "社交"],
            )
            
            # 为目标添加记忆
            target.add_memory(
                f"和{initiator.name}聊了天",
                MemoryType.SOCIAL,
                importance=5.0,
                keywords=[initiator.name, "聊天", "社交"],
            )
            
            logger.debug(f"已更新 [{initiator.name}] 和 [{target.name}] 的聊天记忆")
            
        except Exception as e:
            logger.error(f"更新智能体记忆失败: {e}")


# 单例实例
conversation_handler = ConversationEventHandler()


async def setup_conversation_handlers() -> None:
    """
    设置对话事件处理器
    
    在应用启动时调用
    """
    # 订阅 chat.requested 事件
    @event_bus.subscribe(EventType.CHAT_REQUESTED)
    async def on_chat_requested(event: Event):
        await conversation_handler.handle_chat_request(event.data)
    
    logger.info("对话事件处理器已设置")
