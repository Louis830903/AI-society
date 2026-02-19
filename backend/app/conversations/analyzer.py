"""
对话分析器
=========
使用LLM分析对话内容，提取情感、话题和关系影响

功能：
- 提取对话话题
- 分析双方情绪
- 计算关系变化
- 生成对话摘要
- 生成双方的记忆点
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.conversations.models import Conversation
from app.llm import llm_router
from app.llm.prompts import PromptTemplates


@dataclass
class ConversationAnalysis:
    """
    对话分析结果
    
    Attributes:
        topics: 讨论的话题列表
        emotions: 双方的情绪 {agent_name: emotion}
        relationship_change: 关系变化值 (-10 到 +10)
        summary: 对话摘要
        memorable_for_a: A值得记住的事
        memorable_for_b: B值得记住的事
        is_memorable: 是否值得记忆
        overall_emotion: 整体情感倾向
    """
    topics: List[str] = field(default_factory=list)
    emotions: Dict[str, str] = field(default_factory=dict)
    relationship_change: int = 0
    summary: str = ""
    memorable_for_a: str = ""
    memorable_for_b: str = ""
    is_memorable: bool = False
    overall_emotion: str = "中性"
    
    def to_dict(self) -> dict:
        return {
            "topics": self.topics,
            "emotions": self.emotions,
            "relationship_change": self.relationship_change,
            "summary": self.summary,
            "memorable_for_a": self.memorable_for_a,
            "memorable_for_b": self.memorable_for_b,
            "is_memorable": self.is_memorable,
            "overall_emotion": self.overall_emotion,
        }


def parse_analysis_response(response: str, name1: str, name2: str) -> Optional[dict]:
    """
    解析LLM分析响应
    
    Args:
        response: LLM响应文本
        name1: 参与者A的名字
        name2: 参与者B的名字
    
    Returns:
        解析后的字典
    """
    # 尝试直接解析JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试从代码块中提取
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    matches = re.findall(code_block_pattern, response)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # 尝试找到JSON对象
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, response)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


async def analyze_conversation(
    conversation: Conversation,
    model_name: Optional[str] = None,
) -> ConversationAnalysis:
    """
    分析对话内容
    
    Args:
        conversation: 对话对象
        model_name: 使用的模型
    
    Returns:
        ConversationAnalysis 对象
    """
    if not conversation.messages:
        return ConversationAnalysis()
    
    if not conversation.participant_a or not conversation.participant_b:
        return ConversationAnalysis()
    
    name1 = conversation.participant_a.agent_name
    name2 = conversation.participant_b.agent_name
    occupation1 = conversation.participant_a.occupation
    occupation2 = conversation.participant_b.occupation
    previous_closeness = conversation.participant_a.closeness
    
    # 构建对话文本
    conversation_text = conversation.get_history_text()
    
    # 使用提示词模板
    prompt = PromptTemplates.render(
        "ANALYZE_CONVERSATION",
        name1=name1,
        occupation1=occupation1,
        name2=name2,
        occupation2=occupation2,
        previous_closeness=previous_closeness,
        conversation_text=conversation_text,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=model_name,
            temperature=0.3,  # 低温度保证分析的稳定性
            max_tokens=500,
        )
        
        # 解析响应
        data = parse_analysis_response(response.content, name1, name2)
        
        if data:
            # 提取情绪
            emotions = data.get("emotions", {})
            if isinstance(emotions, dict):
                emotion_dict = emotions
            else:
                emotion_dict = {name1: "中性", name2: "中性"}
            
            # 计算是否值得记忆
            relationship_change = int(data.get("relationship_change", 0))
            is_memorable = abs(relationship_change) >= 3 or len(data.get("topics", [])) >= 2
            
            # 确定整体情感
            overall = "中性"
            if relationship_change > 3:
                overall = "积极"
            elif relationship_change < -3:
                overall = "消极"
            
            return ConversationAnalysis(
                topics=data.get("topics", []),
                emotions=emotion_dict,
                relationship_change=relationship_change,
                summary=data.get("summary", ""),
                memorable_for_a=data.get(f"memorable_for_{name1}", data.get("memorable_for_a", "")),
                memorable_for_b=data.get(f"memorable_for_{name2}", data.get("memorable_for_b", "")),
                is_memorable=is_memorable,
                overall_emotion=overall,
            )
        
    except Exception as e:
        logger.error(f"分析对话失败: {e}")
    
    # 返回默认分析
    return ConversationAnalysis(
        summary=f"{name1}与{name2}进行了一段对话",
    )


def apply_analysis_to_conversation(
    conversation: Conversation,
    analysis: ConversationAnalysis,
) -> None:
    """
    将分析结果应用到对话对象
    
    Args:
        conversation: 对话对象
        analysis: 分析结果
    """
    conversation.topics = analysis.topics
    conversation.overall_emotion = analysis.overall_emotion
    conversation.relationship_change = analysis.relationship_change
    conversation.is_memorable = analysis.is_memorable
    conversation.summary = analysis.summary
    conversation.memorable_for_a = analysis.memorable_for_a
    conversation.memorable_for_b = analysis.memorable_for_b


def calculate_relationship_impact(
    analysis: ConversationAnalysis,
    speaker_personality_extraversion: int = 50,
    listener_personality_agreeableness: int = 50,
) -> Tuple[int, int]:
    """
    计算关系影响（考虑人格因素）
    
    Args:
        analysis: 对话分析结果
        speaker_personality_extraversion: 说话者外向性
        listener_personality_agreeableness: 听者宜人性
    
    Returns:
        (亲密度变化, 信任度变化)
    """
    base_change = analysis.relationship_change
    
    # 外向者带来的正面影响更大
    if base_change > 0:
        extraversion_bonus = (speaker_personality_extraversion - 50) / 100
        base_change = int(base_change * (1 + extraversion_bonus * 0.3))
    
    # 宜人者更容易接受关系改善
    if base_change > 0:
        agreeableness_bonus = (listener_personality_agreeableness - 50) / 100
        base_change = int(base_change * (1 + agreeableness_bonus * 0.2))
    
    # 亲密度变化
    closeness_change = base_change
    
    # 信任度变化（通常是亲密度的一半）
    trust_change = base_change // 2
    
    # 限制范围
    closeness_change = max(-10, min(10, closeness_change))
    trust_change = max(-5, min(5, trust_change))
    
    return closeness_change, trust_change


async def analyze_and_apply(
    conversation: Conversation,
    model_name: Optional[str] = None,
) -> ConversationAnalysis:
    """
    分析对话并应用结果
    
    便捷方法，组合分析和应用
    
    Args:
        conversation: 对话对象
        model_name: 使用的模型
    
    Returns:
        ConversationAnalysis 对象
    """
    analysis = await analyze_conversation(conversation, model_name)
    apply_analysis_to_conversation(conversation, analysis)
    return analysis


# ==================
# 简单分析（不使用LLM）
# ==================

def quick_analyze(conversation: Conversation) -> ConversationAnalysis:
    """
    快速分析（不使用LLM）
    
    基于简单规则进行分析，适用于节省API调用
    
    Args:
        conversation: 对话对象
    
    Returns:
        ConversationAnalysis 对象
    """
    if not conversation.messages:
        return ConversationAnalysis()
    
    message_count = len(conversation.messages)
    
    # 根据对话长度估算关系变化
    # 短对话（1-3条）：小变化
    # 中等对话（4-8条）：中等变化
    # 长对话（9+条）：较大变化
    if message_count <= 3:
        relationship_change = 1
    elif message_count <= 8:
        relationship_change = 3
    else:
        relationship_change = 5
    
    # 检测负面词汇
    negative_words = ["讨厌", "烦", "无聊", "算了", "不想", "滚", "傻"]
    all_content = " ".join(m.content for m in conversation.messages)
    
    negative_count = sum(1 for word in negative_words if word in all_content)
    if negative_count > 0:
        relationship_change -= negative_count * 2
    
    # 检测正面词汇
    positive_words = ["谢谢", "太好了", "开心", "高兴", "喜欢", "不错", "棒"]
    positive_count = sum(1 for word in positive_words if word in all_content)
    relationship_change += positive_count
    
    # 限制范围
    relationship_change = max(-10, min(10, relationship_change))
    
    # 确定整体情感
    if relationship_change > 2:
        overall = "积极"
    elif relationship_change < -2:
        overall = "消极"
    else:
        overall = "中性"
    
    # 是否值得记忆
    is_memorable = message_count >= 5 or abs(relationship_change) >= 3
    
    # 生成简单摘要
    name1 = conversation.participant_a.agent_name if conversation.participant_a else "某人"
    name2 = conversation.participant_b.agent_name if conversation.participant_b else "某人"
    summary = f"{name1}和{name2}聊了{message_count}句话"
    
    return ConversationAnalysis(
        relationship_change=relationship_change,
        overall_emotion=overall,
        is_memorable=is_memorable,
        summary=summary,
    )
