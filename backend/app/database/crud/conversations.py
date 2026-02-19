"""
对话CRUD操作
===========
提供对话和消息的数据库操作
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import ConversationModel, MessageModel
from app.conversations.models import Conversation, Message, ConversationParticipant, ConversationState, MessageRole
from loguru import logger


class ConversationCRUD:
    """对话CRUD操作类"""
    
    # ===================
    # 创建操作
    # ===================
    
    @staticmethod
    async def create(db: AsyncSession, conversation: Conversation) -> ConversationModel:
        """创建对话记录"""
        db_conv = ConversationModel(
            id=conversation.id,
            participant_a_id=conversation.participant_a.agent_id if conversation.participant_a else "",
            participant_a_name=conversation.participant_a.agent_name if conversation.participant_a else "",
            participant_b_id=conversation.participant_b.agent_id if conversation.participant_b else "",
            participant_b_name=conversation.participant_b.agent_name if conversation.participant_b else "",
            state=conversation.state.value,
            location=conversation.location,
            location_id=conversation.location_id,
            game_time=conversation.game_time,
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            topics=conversation.topics,
            overall_emotion=conversation.overall_emotion,
            relationship_change=conversation.relationship_change,
            is_memorable=conversation.is_memorable,
            summary=conversation.summary,
            memorable_for_a=conversation.memorable_for_a,
            memorable_for_b=conversation.memorable_for_b,
            message_count=len(conversation.messages),
            encounter_count=conversation.encounter_count,
        )
        
        db.add(db_conv)
        await db.flush()
        
        # 创建消息
        for msg in conversation.messages:
            await ConversationCRUD.add_message(db, conversation.id, msg)
        
        logger.debug(f"创建对话记录: {conversation.id}")
        return db_conv
    
    @staticmethod
    async def add_message(db: AsyncSession, conversation_id: str, message: Message) -> MessageModel:
        """添加消息到对话"""
        db_msg = MessageModel(
            id=message.id,
            conversation_id=conversation_id,
            speaker_id=message.speaker_id,
            speaker_name=message.speaker_name,
            content=message.content,
            emotion=message.emotion,
            is_end_signal=message.is_end_signal,
            timestamp=message.timestamp,
        )
        
        db.add(db_msg)
        
        # 更新对话消息计数
        await db.execute(
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(message_count=ConversationModel.message_count + 1)
        )
        
        await db.flush()
        return db_msg
    
    # ===================
    # 查询操作
    # ===================
    
    @staticmethod
    async def get_by_id(db: AsyncSession, conv_id: str, include_messages: bool = True) -> Optional[ConversationModel]:
        """获取对话详情"""
        query = select(ConversationModel).where(ConversationModel.id == conv_id)
        if include_messages:
            query = query.options(selectinload(ConversationModel.messages))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active(db: AsyncSession) -> List[ConversationModel]:
        """获取活跃对话"""
        result = await db.execute(
            select(ConversationModel)
            .where(ConversationModel.state.in_(['pending', 'active', 'ending']))
            .options(selectinload(ConversationModel.messages))
            .order_by(ConversationModel.started_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_history(
        db: AsyncSession,
        limit: int = 50,
        agent_id: Optional[str] = None,
    ) -> List[ConversationModel]:
        """获取对话历史"""
        query = select(ConversationModel).where(ConversationModel.state == 'ended')
        
        if agent_id:
            query = query.where(
                (ConversationModel.participant_a_id == agent_id) |
                (ConversationModel.participant_b_id == agent_id)
            )
        
        query = query.order_by(ConversationModel.ended_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_agent_conversations(db: AsyncSession, agent_id: str, limit: int = 20) -> List[ConversationModel]:
        """获取智能体的对话历史"""
        result = await db.execute(
            select(ConversationModel)
            .where(
                (ConversationModel.participant_a_id == agent_id) |
                (ConversationModel.participant_b_id == agent_id)
            )
            .order_by(ConversationModel.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def count(db: AsyncSession, state: Optional[str] = None) -> int:
        """统计对话数量"""
        query = select(func.count(ConversationModel.id))
        if state:
            query = query.where(ConversationModel.state == state)
        result = await db.execute(query)
        return result.scalar() or 0
    
    # ===================
    # 更新操作
    # ===================
    
    @staticmethod
    async def update(db: AsyncSession, conversation: Conversation) -> Optional[ConversationModel]:
        """更新对话"""
        await db.execute(
            update(ConversationModel)
            .where(ConversationModel.id == conversation.id)
            .values(
                state=conversation.state.value,
                ended_at=conversation.ended_at,
                topics=conversation.topics,
                overall_emotion=conversation.overall_emotion,
                relationship_change=conversation.relationship_change,
                is_memorable=conversation.is_memorable,
                summary=conversation.summary,
                memorable_for_a=conversation.memorable_for_a,
                memorable_for_b=conversation.memorable_for_b,
                message_count=len(conversation.messages),
            )
        )
        await db.flush()
        return await ConversationCRUD.get_by_id(db, conversation.id)
    
    @staticmethod
    async def end_conversation(db: AsyncSession, conv_id: str) -> None:
        """结束对话"""
        await db.execute(
            update(ConversationModel)
            .where(ConversationModel.id == conv_id)
            .values(state='ended', ended_at=datetime.now())
        )
        await db.flush()
    
    # ===================
    # 删除操作
    # ===================
    
    @staticmethod
    async def delete(db: AsyncSession, conv_id: str) -> bool:
        """删除对话及其所有消息"""
        result = await db.execute(
            delete(ConversationModel).where(ConversationModel.id == conv_id)
        )
        await db.flush()
        return result.rowcount > 0
    
    # ===================
    # 转换方法
    # ===================
    
    @staticmethod
    def model_to_conversation(db_conv: ConversationModel) -> Conversation:
        """转换为Conversation对象"""
        return Conversation(
            id=db_conv.id,
            participant_a=ConversationParticipant(
                agent_id=db_conv.participant_a_id,
                agent_name=db_conv.participant_a_name,
            ) if db_conv.participant_a_id else None,
            participant_b=ConversationParticipant(
                agent_id=db_conv.participant_b_id,
                agent_name=db_conv.participant_b_name,
            ) if db_conv.participant_b_id else None,
            messages=[
                Message(
                    id=msg.id,
                    speaker_id=msg.speaker_id,
                    speaker_name=msg.speaker_name,
                    content=msg.content,
                    emotion=msg.emotion,
                    is_end_signal=msg.is_end_signal,
                    timestamp=msg.timestamp,
                )
                for msg in (db_conv.messages or [])
            ],
            state=ConversationState(db_conv.state),
            location=db_conv.location,
            location_id=db_conv.location_id,
            game_time=db_conv.game_time,
            started_at=db_conv.started_at,
            ended_at=db_conv.ended_at,
            topics=db_conv.topics or [],
            overall_emotion=db_conv.overall_emotion,
            relationship_change=db_conv.relationship_change,
            is_memorable=db_conv.is_memorable,
            summary=db_conv.summary or "",
            memorable_for_a=db_conv.memorable_for_a or "",
            memorable_for_b=db_conv.memorable_for_b or "",
            encounter_count=db_conv.encounter_count,
        )
