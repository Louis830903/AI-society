"""
对话模块单元测试
==============
测试对话数据模型、管理器、生成器和分析器
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ==================
# 数据模型测试
# ==================

class TestMessage:
    """测试Message消息模型"""
    
    def test_create_default_message(self):
        """测试创建默认消息"""
        from app.conversations.models import Message, MessageRole
        
        msg = Message()
        
        assert msg.id is not None
        assert len(msg.id) == 8
        assert msg.role == MessageRole.SPEAKER
        assert msg.content == ""
        assert msg.is_end_signal == False
    
    def test_create_message_with_content(self):
        """测试创建带内容的消息"""
        from app.conversations.models import Message
        
        msg = Message(
            speaker_id="agent1",
            speaker_name="张三",
            content="你好！",
            emotion="开心",
        )
        
        assert msg.speaker_id == "agent1"
        assert msg.speaker_name == "张三"
        assert msg.content == "你好！"
        assert msg.emotion == "开心"
    
    def test_message_to_dict(self):
        """测试消息转字典"""
        from app.conversations.models import Message
        
        msg = Message(
            speaker_id="agent1",
            speaker_name="张三",
            content="你好！",
        )
        
        data = msg.to_dict()
        
        assert data["speaker_id"] == "agent1"
        assert data["speaker_name"] == "张三"
        assert data["content"] == "你好！"
        assert "timestamp" in data
    
    def test_message_from_dict(self):
        """测试从字典创建消息"""
        from app.conversations.models import Message, MessageRole
        
        data = {
            "id": "test123",
            "role": "speaker",
            "speaker_id": "agent1",
            "speaker_name": "张三",
            "content": "你好！",
            "timestamp": "2024-01-01T12:00:00",
            "emotion": "平静",
            "is_end_signal": False,
        }
        
        msg = Message.from_dict(data)
        
        assert msg.id == "test123"
        assert msg.role == MessageRole.SPEAKER
        assert msg.speaker_name == "张三"


class TestConversationParticipant:
    """测试对话参与者模型"""
    
    def test_create_participant(self):
        """测试创建参与者"""
        from app.conversations.models import ConversationParticipant
        
        p = ConversationParticipant(
            agent_id="agent1",
            agent_name="张三",
            occupation="程序员",
            relationship_to_other="同事",
            closeness=60,
        )
        
        assert p.agent_id == "agent1"
        assert p.agent_name == "张三"
        assert p.occupation == "程序员"
        assert p.closeness == 60
    
    def test_participant_to_dict(self):
        """测试参与者转字典"""
        from app.conversations.models import ConversationParticipant
        
        p = ConversationParticipant(
            agent_id="agent1",
            agent_name="张三",
        )
        
        data = p.to_dict()
        
        assert data["agent_id"] == "agent1"
        assert data["agent_name"] == "张三"


class TestConversation:
    """测试对话模型"""
    
    def test_create_empty_conversation(self):
        """测试创建空对话"""
        from app.conversations.models import Conversation, ConversationState
        
        conv = Conversation()
        
        assert conv.id is not None
        assert conv.state == ConversationState.PENDING
        assert conv.message_count == 0
        assert conv.messages == []
    
    def test_create_conversation_with_participants(self):
        """测试创建带参与者的对话"""
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(
                agent_id="a1",
                agent_name="张三",
            ),
            participant_b=ConversationParticipant(
                agent_id="a2",
                agent_name="李四",
            ),
            location="咖啡馆",
        )
        
        assert conv.participant_a.agent_name == "张三"
        assert conv.participant_b.agent_name == "李四"
        assert conv.location == "咖啡馆"
    
    def test_add_message(self):
        """测试添加消息"""
        from app.conversations.models import Conversation, ConversationParticipant, ConversationState
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        
        msg = conv.add_message(
            speaker_id="a1",
            speaker_name="张三",
            content="你好！",
        )
        
        assert conv.message_count == 1
        assert conv.state == ConversationState.ACTIVE
        assert msg.content == "你好！"
    
    def test_add_end_signal_message(self):
        """测试添加结束信号消息"""
        from app.conversations.models import Conversation, ConversationParticipant, ConversationState
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        
        conv.add_message("a1", "张三", "再见！", is_end_signal=True)
        
        assert conv.state == ConversationState.ENDING
    
    def test_current_speaker_id(self):
        """测试当前说话者ID"""
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        
        # 初始应该是发起者
        assert conv.current_speaker_id == "a1"
        
        # A说完后轮到B
        conv.add_message("a1", "张三", "你好！")
        assert conv.current_speaker_id == "a2"
        
        # B说完后轮到A
        conv.add_message("a2", "李四", "你好！")
        assert conv.current_speaker_id == "a1"
    
    def test_end_conversation(self):
        """测试结束对话"""
        from app.conversations.models import Conversation, ConversationState
        
        conv = Conversation()
        conv.end()
        
        assert conv.state == ConversationState.ENDED
        assert conv.ended_at is not None
    
    def test_interrupt_conversation(self):
        """测试中断对话"""
        from app.conversations.models import Conversation, ConversationState
        
        conv = Conversation()
        conv.interrupt()
        
        assert conv.state == ConversationState.INTERRUPTED
    
    def test_get_history_text(self):
        """测试获取历史文本"""
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        
        conv.add_message("a1", "张三", "你好！")
        conv.add_message("a2", "李四", "你好啊！")
        
        text = conv.get_history_text()
        
        assert "张三：你好！" in text
        assert "李四：你好啊！" in text
    
    def test_conversation_to_dict(self):
        """测试对话转字典"""
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
            location="公园",
        )
        
        data = conv.to_dict()
        
        assert data["location"] == "公园"
        assert data["participant_a"]["agent_name"] == "张三"
        assert "message_count" in data
    
    def test_conversation_from_dict(self):
        """测试从字典创建对话"""
        from app.conversations.models import Conversation, ConversationState
        
        data = {
            "id": "conv123",
            "participant_a": {"agent_id": "a1", "agent_name": "张三"},
            "participant_b": {"agent_id": "a2", "agent_name": "李四"},
            "messages": [],
            "state": "active",
            "location": "咖啡馆",
            "started_at": "2024-01-01T12:00:00",
        }
        
        conv = Conversation.from_dict(data)
        
        assert conv.id == "conv123"
        assert conv.state == ConversationState.ACTIVE
        assert conv.participant_a.agent_name == "张三"


# ==================
# 管理器测试
# ==================

class TestConversationManager:
    """测试对话管理器"""
    
    @pytest.fixture
    def manager(self):
        """创建新的管理器实例"""
        from app.conversations.manager import ConversationManager
        return ConversationManager()
    
    def test_create_conversation(self, manager):
        """测试创建对话"""
        conv = manager.create_conversation(
            agent_a_id="a1",
            agent_a_name="张三",
            agent_b_id="a2",
            agent_b_name="李四",
            location="咖啡馆",
        )
        
        assert conv is not None
        assert conv.id is not None
        assert manager.is_in_conversation("a1")
        assert manager.is_in_conversation("a2")
    
    def test_cannot_create_duplicate_conversation(self, manager):
        """测试不能创建重复对话"""
        manager.create_conversation("a1", "张三", "a2", "李四")
        
        # a1已在对话中，不能再创建
        with pytest.raises(ValueError):
            manager.create_conversation("a1", "张三", "a3", "王五")
    
    def test_get_conversation(self, manager):
        """测试获取对话"""
        conv = manager.create_conversation("a1", "张三", "a2", "李四")
        
        result = manager.get(conv.id)
        
        assert result is not None
        assert result.id == conv.id
    
    def test_get_by_agent(self, manager):
        """测试根据智能体获取对话"""
        conv = manager.create_conversation("a1", "张三", "a2", "李四")
        
        result = manager.get_by_agent("a1")
        
        assert result is not None
        assert result.id == conv.id
    
    def test_end_conversation(self, manager):
        """测试结束对话"""
        conv = manager.create_conversation("a1", "张三", "a2", "李四")
        
        result = manager.end_conversation(conv.id)
        
        assert result is not None
        assert not manager.is_in_conversation("a1")
        assert not manager.is_in_conversation("a2")
    
    def test_get_active_conversations(self, manager):
        """测试获取活跃对话"""
        manager.create_conversation("a1", "张三", "a2", "李四")
        manager.create_conversation("a3", "王五", "a4", "赵六")
        
        active = manager.get_active_conversations()
        
        assert len(active) == 2
    
    def test_get_history(self, manager):
        """测试获取历史"""
        conv = manager.create_conversation("a1", "张三", "a2", "李四")
        manager.end_conversation(conv.id)
        
        history = manager.get_history()
        
        assert len(history) == 1
    
    def test_count_encounters(self, manager):
        """测试统计相遇次数"""
        conv1 = manager.create_conversation("a1", "张三", "a2", "李四")
        manager.end_conversation(conv1.id)
        
        conv2 = manager.create_conversation("a1", "张三", "a2", "李四")
        manager.end_conversation(conv2.id)
        
        count = manager.count_encounters("a1", "a2")
        
        assert count == 2
    
    def test_request_conversation(self, manager):
        """测试对话请求"""
        result = manager.request_conversation("a1", "a2")
        
        assert result == True
        assert manager.get_pending_request_for("a2") == "a1"
    
    def test_cancel_request(self, manager):
        """测试取消请求"""
        manager.request_conversation("a1", "a2")
        
        result = manager.cancel_request("a1")
        
        assert result == True
        assert manager.get_pending_request_for("a2") is None
    
    def test_stats(self, manager):
        """测试统计信息"""
        manager.create_conversation("a1", "张三", "a2", "李四")
        
        stats = manager.get_stats()
        
        assert stats["active_conversations"] == 1
        assert stats["agents_in_conversation"] == 2
    
    def test_clear(self, manager):
        """测试清空"""
        manager.create_conversation("a1", "张三", "a2", "李四")
        manager.clear()
        
        assert len(manager.get_active_conversations()) == 0


# ==================
# 生成器测试
# ==================

class TestConversationGenerator:
    """测试对话生成器"""
    
    def test_extract_end_signal_with_marker(self):
        """测试提取结束信号（带标记）"""
        from app.conversations.generator import extract_end_signal
        
        text = "好的，再见！[END]"
        clean, is_end = extract_end_signal(text)
        
        assert clean == "好的，再见！"
        assert is_end == True
    
    def test_extract_end_signal_with_farewell(self):
        """测试提取结束信号（告别语）"""
        from app.conversations.generator import extract_end_signal
        
        text = "那我先走了，拜拜！"
        clean, is_end = extract_end_signal(text)
        
        assert is_end == True
    
    def test_extract_end_signal_normal(self):
        """测试正常文本（无结束信号）"""
        from app.conversations.generator import extract_end_signal
        
        text = "今天天气真好啊"
        clean, is_end = extract_end_signal(text)
        
        assert clean == text
        assert is_end == False
    
    @pytest.mark.asyncio
    async def test_generate_opening_fallback(self):
        """测试生成开场白（回退）"""
        from app.conversations.generator import generate_opening
        
        # Mock LLM调用失败
        with patch("app.conversations.generator.llm_router.generate") as mock:
            mock.side_effect = Exception("LLM Error")
            
            reply = await generate_opening(
                speaker_name="张三",
                speaker_age=25,
                speaker_occupation="程序员",
                speaker_personality="外向开朗",
                listener_name="李四",
                listener_occupation="设计师",
                relationship="同事",
                location="咖啡馆",
                current_time="14:00",
            )
            
            assert "李四" in reply.content
            assert reply.is_end_signal == False
    
    @pytest.mark.asyncio
    async def test_generate_reply_fallback(self):
        """测试生成回复（回退）"""
        from app.conversations.generator import generate_reply
        
        with patch("app.conversations.generator.llm_router.generate") as mock:
            mock.side_effect = Exception("LLM Error")
            
            reply = await generate_reply(
                speaker_name="张三",
                speaker_age=25,
                speaker_occupation="程序员",
                speaker_personality="外向开朗",
                listener_name="李四",
                listener_occupation="设计师",
                relationship="同事",
                location="咖啡馆",
                conversation_history="李四：你好！",
            )
            
            assert reply.content != ""
            assert reply.is_end_signal == False


# ==================
# 分析器测试
# ==================

class TestConversationAnalyzer:
    """测试对话分析器"""
    
    def test_parse_analysis_response_json(self):
        """测试解析JSON响应"""
        from app.conversations.analyzer import parse_analysis_response
        
        response = '{"topics": ["天气"], "relationship_change": 2}'
        result = parse_analysis_response(response, "张三", "李四")
        
        assert result is not None
        assert result["topics"] == ["天气"]
        assert result["relationship_change"] == 2
    
    def test_parse_analysis_response_code_block(self):
        """测试解析代码块响应"""
        from app.conversations.analyzer import parse_analysis_response
        
        response = '''分析结果：
```json
{"topics": ["工作"], "relationship_change": 3}
```
'''
        result = parse_analysis_response(response, "张三", "李四")
        
        assert result is not None
        assert result["topics"] == ["工作"]
    
    def test_quick_analyze_short_conversation(self):
        """测试快速分析（短对话）"""
        from app.conversations.analyzer import quick_analyze
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        conv.add_message("a1", "张三", "你好！")
        conv.add_message("a2", "李四", "你好啊！")
        
        analysis = quick_analyze(conv)
        
        assert analysis.relationship_change > 0
        assert analysis.is_memorable == False
    
    def test_quick_analyze_long_conversation(self):
        """测试快速分析（长对话）"""
        from app.conversations.analyzer import quick_analyze
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        
        # 添加多条消息
        for i in range(6):
            conv.add_message(f"a{i%2+1}", "张三" if i%2==0 else "李四", f"消息{i}")
        
        analysis = quick_analyze(conv)
        
        assert analysis.is_memorable == True
    
    def test_quick_analyze_negative_words(self):
        """测试快速分析（负面词汇）"""
        from app.conversations.analyzer import quick_analyze
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        conv.add_message("a1", "张三", "真讨厌，烦死了")
        
        analysis = quick_analyze(conv)
        
        assert analysis.relationship_change < 0
        assert analysis.overall_emotion == "消极"
    
    def test_quick_analyze_positive_words(self):
        """测试快速分析（正面词汇）"""
        from app.conversations.analyzer import quick_analyze
        from app.conversations.models import Conversation, ConversationParticipant
        
        conv = Conversation(
            participant_a=ConversationParticipant(agent_id="a1", agent_name="张三"),
            participant_b=ConversationParticipant(agent_id="a2", agent_name="李四"),
        )
        conv.add_message("a1", "张三", "太好了！谢谢你！")
        conv.add_message("a2", "李四", "不客气，很高兴能帮到你！")
        
        analysis = quick_analyze(conv)
        
        assert analysis.relationship_change > 0
        assert analysis.overall_emotion == "积极"
    
    def test_calculate_relationship_impact(self):
        """测试关系影响计算"""
        from app.conversations.analyzer import calculate_relationship_impact, ConversationAnalysis
        
        analysis = ConversationAnalysis(relationship_change=5)
        
        closeness, trust = calculate_relationship_impact(
            analysis,
            speaker_personality_extraversion=80,
            listener_personality_agreeableness=70,
        )
        
        assert closeness >= 5  # 外向性加成（可能等于5如果计算结果为整数）
        assert trust >= 2


# ==================
# API路由测试
# ==================

@pytest.fixture
async def client():
    """创建测试客户端"""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_manager():
    """每次测试前重置管理器"""
    from app.conversations import conversation_manager
    conversation_manager.clear()
    yield


class TestConversationAPI:
    """测试对话API"""
    
    @pytest.mark.asyncio
    async def test_create_conversation_api(self, client):
        """测试创建对话API"""
        response = await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
            "location": "咖啡馆",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["conversation_id"] is not None
    
    @pytest.mark.asyncio
    async def test_list_active_conversations_api(self, client):
        """测试获取活跃对话列表API"""
        # 先创建一个对话
        await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
        })
        
        response = await client.get("/api/conversations/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_api(self, client):
        """测试获取统计API"""
        response = await client.get("/api/conversations/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_conversations" in data
    
    @pytest.mark.asyncio
    async def test_get_conversation_detail_api(self, client):
        """测试获取对话详情API"""
        # 创建对话
        create_response = await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
            "location": "公园",
        })
        conv_id = create_response.json()["conversation_id"]
        
        response = await client.get(f"/api/conversations/{conv_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "公园"
        assert data["participant_a_name"] == "张三"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, client):
        """测试获取不存在的对话"""
        response = await client.get("/api/conversations/nonexistent")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_send_message_api(self, client):
        """测试发送消息API"""
        # 创建对话
        create_response = await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
        })
        conv_id = create_response.json()["conversation_id"]
        
        # 发送消息
        response = await client.post(f"/api/conversations/{conv_id}/messages", json={
            "speaker_id": "a1",
            "content": "你好！",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "你好！"
        assert data["speaker_name"] == "张三"
    
    @pytest.mark.asyncio
    async def test_end_conversation_api(self, client):
        """测试结束对话API"""
        # 创建对话
        create_response = await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
        })
        conv_id = create_response.json()["conversation_id"]
        
        # 结束对话
        response = await client.post(f"/api/conversations/{conv_id}/end")
        
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    @pytest.mark.asyncio
    async def test_get_agent_conversation_api(self, client):
        """测试获取智能体当前对话API"""
        # 创建对话
        await client.post("/api/conversations/", json={
            "agent_a_id": "a1",
            "agent_a_name": "张三",
            "agent_b_id": "a2",
            "agent_b_name": "李四",
        })
        
        response = await client.get("/api/conversations/agent/a1/current")
        
        assert response.status_code == 200
        data = response.json()
        assert data["in_conversation"] == True
        assert data["other_participant"] == "李四"
    
    @pytest.mark.asyncio
    async def test_get_agent_not_in_conversation(self, client):
        """测试获取不在对话中的智能体"""
        response = await client.get("/api/conversations/agent/unknown/current")
        
        assert response.status_code == 200
        data = response.json()
        assert data["in_conversation"] == False
    
    @pytest.mark.asyncio
    async def test_get_conversations_between_api(self, client):
        """测试获取两个智能体之间的对话API"""
        response = await client.get("/api/conversations/between/a1/a2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_api(self, client):
        """测试清理超时对话API"""
        response = await client.post("/api/conversations/cleanup?max_duration_seconds=600")
        
        assert response.status_code == 200
        assert response.json()["success"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
