"""
对话生成器
=========
使用LLM生成自然的对话内容

功能：
- 生成开场白
- 生成回复
- 检测对话结束信号
- 记录对话活动日志（Phase 7）
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger

from app.conversations.models import Conversation, Message
from app.llm import llm_router
from app.llm.prompts import PromptTemplates


@dataclass
class GeneratedReply:
    """生成的回复"""
    content: str  # 回复内容
    is_end_signal: bool = False  # 是否是结束信号
    emotion: Optional[str] = None  # 情绪
    raw_response: str = ""  # 原始响应


def extract_end_signal(text: str) -> Tuple[str, bool]:
    """
    从文本中提取结束信号
    
    检测 [END] 标记或告别语
    
    Returns:
        (清理后的文本, 是否结束)
    """
    # 检查 [END] 标记
    if "[END]" in text:
        clean_text = text.replace("[END]", "").strip()
        return clean_text, True
    
    # 检查常见告别语
    farewell_patterns = [
        r'(再见|拜拜|回头见|下次见|告辞|失陪|先走了|我走了|我先走)',
        r'(那我先|我得走了|时间不早了|该走了)',
    ]
    
    for pattern in farewell_patterns:
        if re.search(pattern, text):
            return text, True
    
    return text, False


async def generate_opening(
    speaker_name: str,
    speaker_age: int,
    speaker_occupation: str,
    speaker_personality: str,
    listener_name: str,
    listener_occupation: str,
    relationship: str,
    location: str,
    current_time: str,
    knowledge_about_other: str = "",
    encounter_count: int = 1,
    previous_topics: str = "",
    model_name: Optional[str] = None,
) -> GeneratedReply:
    """
    生成对话开场白
    
    Args:
        speaker_name: 说话者名字
        speaker_age: 说话者年龄
        speaker_occupation: 说话者职业
        speaker_personality: 说话者性格描述
        listener_name: 听者名字
        listener_occupation: 听者职业
        relationship: 关系描述
        location: 地点
        current_time: 当前时间
        knowledge_about_other: 对对方的了解
        encounter_count: 相遇次数
        previous_topics: 之前聊过的话题
        model_name: 使用的模型
    
    Returns:
        GeneratedReply 对象
    """
    prompt = PromptTemplates.render(
        "CONVERSATION_START",
        name=speaker_name,
        age=speaker_age,
        occupation=speaker_occupation,
        personality_description=speaker_personality,
        location=location,
        other_name=listener_name,
        other_occupation=listener_occupation,
        relationship_description=relationship,
        current_time=current_time,
        knowledge_about_other=knowledge_about_other or "不太了解此人",
        encounter_count=encounter_count,
        previous_topics=previous_topics or "（这是第一次交谈）",
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=model_name,
            temperature=0.8,  # 稍高的温度让对话更自然
            max_tokens=200,
        )
        
        content, is_end = extract_end_signal(response.content.strip())
        
        return GeneratedReply(
            content=content,
            is_end_signal=is_end,
            raw_response=response.content,
        )
        
    except Exception as e:
        logger.error(f"生成开场白失败: {e}")
        # 返回通用开场白
        return GeneratedReply(
            content=f"你好，{listener_name}！",
            is_end_signal=False,
        )


async def generate_reply(
    speaker_name: str,
    speaker_age: int,
    speaker_occupation: str,
    speaker_personality: str,
    listener_name: str,
    listener_occupation: str,
    relationship: str,
    location: str,
    conversation_history: str,
    model_name: Optional[str] = None,
) -> GeneratedReply:
    """
    生成对话回复
    
    Args:
        speaker_name: 说话者名字
        speaker_age: 说话者年龄
        speaker_occupation: 说话者职业
        speaker_personality: 说话者性格描述
        listener_name: 听者名字
        listener_occupation: 听者职业
        relationship: 关系描述
        location: 地点
        conversation_history: 对话历史
        model_name: 使用的模型
    
    Returns:
        GeneratedReply 对象
    """
    prompt = PromptTemplates.render(
        "CONVERSATION_REPLY",
        name=speaker_name,
        age=speaker_age,
        occupation=speaker_occupation,
        personality_description=speaker_personality,
        location=location,
        other_name=listener_name,
        other_occupation=listener_occupation,
        relationship_description=relationship,
        conversation_history=conversation_history,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=model_name,
            temperature=0.8,
            max_tokens=200,
        )
        
        content, is_end = extract_end_signal(response.content.strip())
        
        return GeneratedReply(
            content=content,
            is_end_signal=is_end,
            raw_response=response.content,
        )
        
    except Exception as e:
        logger.error(f"生成回复失败: {e}")
        return GeneratedReply(
            content="嗯，是这样的。",
            is_end_signal=False,
        )


class ConversationGenerator:
    """
    对话生成器
    
    封装对话生成逻辑，与Agent和Conversation模型集成
    """
    
    def __init__(self, conversation: Conversation):
        """
        初始化生成器
        
        Args:
            conversation: 对话对象
        """
        self.conversation = conversation
    
    async def generate_next_message(
        self,
        speaker_personality: str = "",
        speaker_model: Optional[str] = None,
    ) -> Optional[Message]:
        """
        生成下一条消息
        
        自动判断当前轮到谁说话，并生成相应内容
        
        Args:
            speaker_personality: 说话者性格描述
            speaker_model: 说话者使用的模型
        
        Returns:
            生成的消息对象
        """
        conv = self.conversation
        
        # 确定说话者
        current_speaker_id = conv.current_speaker_id
        if not current_speaker_id:
            return None
        
        speaker = conv.get_participant(current_speaker_id)
        listener = conv.get_other_participant(current_speaker_id)
        
        if not speaker or not listener:
            return None
        
        # 判断是开场白还是回复
        if not conv.messages:
            # 生成开场白
            reply = await generate_opening(
                speaker_name=speaker.agent_name,
                speaker_age=25,  # 默认年龄，实际使用时应传入
                speaker_occupation=speaker.occupation,
                speaker_personality=speaker_personality or speaker.personality_description,
                listener_name=listener.agent_name,
                listener_occupation=listener.occupation,
                relationship=speaker.relationship_to_other,
                location=conv.location,
                current_time=conv.game_time.strftime("%H:%M") if conv.game_time else "某时",
                encounter_count=conv.encounter_count,
                model_name=speaker_model,
            )
        else:
            # 生成回复
            history = conv.get_history_text()
            
            reply = await generate_reply(
                speaker_name=speaker.agent_name,
                speaker_age=25,
                speaker_occupation=speaker.occupation,
                speaker_personality=speaker_personality or speaker.personality_description,
                listener_name=listener.agent_name,
                listener_occupation=listener.occupation,
                relationship=speaker.relationship_to_other,
                location=conv.location,
                conversation_history=history,
                model_name=speaker_model,
            )
        
        # 添加消息到对话
        message = conv.add_message(
            speaker_id=speaker.agent_id,
            speaker_name=speaker.agent_name,
            content=reply.content,
            emotion=reply.emotion,
            is_end_signal=reply.is_end_signal,
        )
        
        # Phase 7: 记录对话活动到日志
        await self._log_conversation_activity(
            speaker_id=speaker.agent_id,
            speaker_name=speaker.agent_name,
            conversation_id=conv.id,
            partner_name=listener.agent_name,
            message_content=reply.content,
            location=conv.location,
        )
        
        logger.debug(f"[{speaker.agent_name}] {reply.content[:50]}...")
        
        return message
    
    async def run_conversation(
        self,
        max_turns: int = 10,
        speaker_a_personality: str = "",
        speaker_b_personality: str = "",
        speaker_a_model: Optional[str] = None,
        speaker_b_model: Optional[str] = None,
    ) -> Conversation:
        """
        运行完整对话
        
        Args:
            max_turns: 最大轮次
            speaker_a_personality: A的性格描述
            speaker_b_personality: B的性格描述
            speaker_a_model: A使用的模型
            speaker_b_model: B使用的模型
        
        Returns:
            完成的对话对象
        """
        conv = self.conversation
        
        for turn in range(max_turns):
            current_speaker_id = conv.current_speaker_id
            
            if not current_speaker_id:
                break
            
            # 确定当前说话者的参数
            if conv.participant_a and current_speaker_id == conv.participant_a.agent_id:
                personality = speaker_a_personality
                model = speaker_a_model
            else:
                personality = speaker_b_personality
                model = speaker_b_model
            
            # 生成消息
            message = await self.generate_next_message(
                speaker_personality=personality,
                speaker_model=model,
            )
            
            if not message:
                break
            
            # 检查是否结束
            if message.is_end_signal:
                # 让对方也有机会告别
                if turn < max_turns - 1:
                    farewell = await self.generate_next_message(
                        speaker_personality=speaker_b_personality if conv.participant_a and current_speaker_id == conv.participant_a.agent_id else speaker_a_personality,
                        speaker_model=speaker_b_model if conv.participant_a and current_speaker_id == conv.participant_a.agent_id else speaker_a_model,
                    )
                break
        
        return conv
    
    async def _log_conversation_activity(
        self,
        speaker_id: str,
        speaker_name: str,
        conversation_id: str,
        partner_name: str,
        message_content: str,
        location: str,
    ) -> None:
        """
        记录对话活动到数据库
        
        Phase 7: 观察者功能增强
        """
        try:
            from app.database import get_async_session
            from app.database.crud.activity_logs import ActivityLogCRUD
            from app.core.world import world_clock
            
            async with get_async_session() as db:
                await ActivityLogCRUD.log_conversation(
                    db=db,
                    agent_id=speaker_id,
                    agent_name=speaker_name,
                    game_time=world_clock.get_time(),
                    conversation_id=conversation_id,
                    conversation_partner=partner_name,
                    message_content=message_content,
                    location=location,
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"记录对话活动失败: {e}")
