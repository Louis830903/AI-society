"""
对话API路由
==========
提供对话相关的HTTP API接口

接口：
- 创建对话
- 获取对话详情
- 获取活跃对话列表
- 获取对话历史
- 发送消息
- 结束对话
- 分析对话
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.conversations import (
    Conversation,
    ConversationState,
    conversation_manager,
    generate_opening,
    generate_reply,
    ConversationGenerator,
    analyze_conversation,
    ConversationAnalysis,
)
from app.conversations.analyzer import quick_analyze, apply_analysis_to_conversation

router = APIRouter(
    tags=["对话系统"],
)


# ==================
# 请求/响应模型
# ==================

class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    agent_a_id: str = Field(..., description="发起者ID")
    agent_a_name: str = Field(..., description="发起者名字")
    agent_b_id: str = Field(..., description="接收者ID")
    agent_b_name: str = Field(..., description="接收者名字")
    location: str = Field("", description="地点")
    location_id: Optional[str] = Field(None, description="地点ID")


class CreateConversationResponse(BaseModel):
    """创建对话响应"""
    success: bool
    conversation_id: Optional[str] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    speaker_id: str
    speaker_name: str
    content: str
    emotion: Optional[str] = None
    is_end_signal: bool = False


class ConversationResponse(BaseModel):
    """对话响应"""
    id: str
    participant_a_id: str
    participant_a_name: str
    participant_b_id: str
    participant_b_name: str
    state: str
    location: str
    message_count: int
    messages: List[dict]
    started_at: str
    ended_at: Optional[str] = None
    topics: List[str] = []
    overall_emotion: str = "中性"
    relationship_change: int = 0
    summary: str = ""


class ConversationBriefResponse(BaseModel):
    """对话简要响应"""
    id: str
    participant_a_name: str
    participant_b_name: str
    state: str
    location: str
    message_count: int
    started_at: str


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    speaker_id: str = Field(..., description="说话者ID")
    content: str = Field(..., description="消息内容")
    emotion: Optional[str] = Field(None, description="情绪")


class GenerateMessageRequest(BaseModel):
    """生成消息请求（使用LLM）"""
    speaker_personality: str = Field("", description="说话者性格描述")
    speaker_model: Optional[str] = Field(None, description="使用的LLM模型")


class StatsResponse(BaseModel):
    """统计响应"""
    active_conversations: int
    agents_in_conversation: int
    pending_requests: int
    history_count: int
    total_messages_active: int
    total_messages_history: int


# ==================
# API端点
# ==================

@router.post("/", response_model=CreateConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """
    创建新对话
    
    - **agent_a_id**: 发起者ID
    - **agent_a_name**: 发起者名字
    - **agent_b_id**: 接收者ID
    - **agent_b_name**: 接收者名字
    - **location**: 发生地点
    """
    try:
        conversation = conversation_manager.create_conversation(
            agent_a_id=request.agent_a_id,
            agent_a_name=request.agent_a_name,
            agent_b_id=request.agent_b_id,
            agent_b_name=request.agent_b_name,
            location=request.location,
            location_id=request.location_id,
            game_time=datetime.now(),
        )
        
        return CreateConversationResponse(
            success=True,
            conversation_id=conversation.id,
        )
        
    except ValueError as e:
        return CreateConversationResponse(
            success=False,
            error=str(e),
        )


@router.get("/", response_model=List[ConversationBriefResponse])
async def list_active_conversations():
    """获取所有活跃对话列表"""
    conversations = conversation_manager.get_active_conversations()
    
    return [
        ConversationBriefResponse(
            id=c.id,
            participant_a_name=c.participant_a.agent_name if c.participant_a else "",
            participant_b_name=c.participant_b.agent_name if c.participant_b else "",
            state=c.state.value,
            location=c.location,
            message_count=c.message_count,
            started_at=c.started_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取对话系统统计信息"""
    stats = conversation_manager.get_stats()
    return StatsResponse(**stats)


@router.get("/history", response_model=List[ConversationBriefResponse])
async def get_conversation_history(
    agent_id: Optional[str] = Query(None, description="筛选特定智能体"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
):
    """获取对话历史"""
    conversations = conversation_manager.get_history(agent_id=agent_id, limit=limit)
    
    return [
        ConversationBriefResponse(
            id=c.id,
            participant_a_name=c.participant_a.agent_name if c.participant_a else "",
            participant_b_name=c.participant_b.agent_name if c.participant_b else "",
            state=c.state.value,
            location=c.location,
            message_count=c.message_count,
            started_at=c.started_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    conversation = conversation_manager.get(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return ConversationResponse(
        id=conversation.id,
        participant_a_id=conversation.participant_a.agent_id if conversation.participant_a else "",
        participant_a_name=conversation.participant_a.agent_name if conversation.participant_a else "",
        participant_b_id=conversation.participant_b.agent_id if conversation.participant_b else "",
        participant_b_name=conversation.participant_b.agent_name if conversation.participant_b else "",
        state=conversation.state.value,
        location=conversation.location,
        message_count=conversation.message_count,
        messages=[m.to_dict() for m in conversation.messages],
        started_at=conversation.started_at.isoformat(),
        ended_at=conversation.ended_at.isoformat() if conversation.ended_at else None,
        topics=conversation.topics,
        overall_emotion=conversation.overall_emotion,
        relationship_change=conversation.relationship_change,
        summary=conversation.summary,
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    发送消息（手动）
    
    手动发送一条消息到对话中
    """
    conversation = conversation_manager.get(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    if conversation.state not in [ConversationState.PENDING, ConversationState.ACTIVE]:
        raise HTTPException(status_code=400, detail="对话已结束")
    
    # 确定说话者名字
    speaker_name = ""
    if conversation.participant_a and conversation.participant_a.agent_id == request.speaker_id:
        speaker_name = conversation.participant_a.agent_name
    elif conversation.participant_b and conversation.participant_b.agent_id == request.speaker_id:
        speaker_name = conversation.participant_b.agent_name
    else:
        raise HTTPException(status_code=400, detail="说话者不是对话参与者")
    
    # 添加消息
    message = conversation.add_message(
        speaker_id=request.speaker_id,
        speaker_name=speaker_name,
        content=request.content,
        emotion=request.emotion,
    )
    
    return MessageResponse(
        id=message.id,
        speaker_id=message.speaker_id,
        speaker_name=message.speaker_name,
        content=message.content,
        emotion=message.emotion,
        is_end_signal=message.is_end_signal,
    )


@router.post("/{conversation_id}/generate", response_model=MessageResponse)
async def generate_message(conversation_id: str, request: GenerateMessageRequest):
    """
    生成消息（使用LLM）
    
    自动为当前应该说话的人生成一条消息
    """
    conversation = conversation_manager.get(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    if conversation.state not in [ConversationState.PENDING, ConversationState.ACTIVE]:
        raise HTTPException(status_code=400, detail="对话已结束")
    
    generator = ConversationGenerator(conversation)
    
    message = await generator.generate_next_message(
        speaker_personality=request.speaker_personality,
        speaker_model=request.speaker_model,
    )
    
    if not message:
        raise HTTPException(status_code=500, detail="生成消息失败")
    
    return MessageResponse(
        id=message.id,
        speaker_id=message.speaker_id,
        speaker_name=message.speaker_name,
        content=message.content,
        emotion=message.emotion,
        is_end_signal=message.is_end_signal,
    )


@router.post("/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    reason: str = Query("normal", description="结束原因"),
):
    """结束对话"""
    conversation = conversation_manager.end_conversation(conversation_id, reason=reason)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return {"success": True, "message": "对话已结束"}


@router.post("/{conversation_id}/analyze")
async def analyze(
    conversation_id: str,
    use_llm: bool = Query(True, description="是否使用LLM分析"),
    model_name: Optional[str] = Query(None, description="使用的模型"),
):
    """
    分析对话
    
    提取话题、情绪、关系变化等
    """
    conversation = conversation_manager.get(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    if use_llm:
        analysis = await analyze_conversation(conversation, model_name=model_name)
    else:
        analysis = quick_analyze(conversation)
    
    # 应用分析结果
    apply_analysis_to_conversation(conversation, analysis)
    
    return analysis.to_dict()


@router.get("/agent/{agent_id}/current")
async def get_agent_conversation(agent_id: str):
    """获取智能体当前参与的对话"""
    conversation = conversation_manager.get_by_agent(agent_id)
    
    if not conversation:
        return {"in_conversation": False}
    
    return {
        "in_conversation": True,
        "conversation_id": conversation.id,
        "other_participant": (
            conversation.participant_b.agent_name
            if conversation.participant_a and conversation.participant_a.agent_id == agent_id
            else conversation.participant_a.agent_name if conversation.participant_a else ""
        ),
        "message_count": conversation.message_count,
    }


@router.get("/between/{agent_a_id}/{agent_b_id}")
async def get_conversations_between(agent_a_id: str, agent_b_id: str):
    """获取两个智能体之间的所有对话"""
    conversations = conversation_manager.get_conversation_between(agent_a_id, agent_b_id)
    
    return {
        "count": len(conversations),
        "conversations": [c.to_brief_dict() for c in conversations],
    }


@router.post("/cleanup")
async def cleanup_stale(
    max_duration_seconds: float = Query(600, description="最大持续时间（秒）"),
):
    """清理超时对话"""
    count = conversation_manager.clear_stale_conversations(max_duration_seconds)
    
    return {"success": True, "cleaned": count}
