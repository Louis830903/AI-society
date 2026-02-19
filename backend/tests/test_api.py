"""
API 集成测试
============
使用 pytest 和 httpx 测试 FastAPI 端点
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRootEndpoints:
    """根端点测试"""
    
    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """测试根路径"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI Society"
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """测试健康检查"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestWorldEndpoints:
    """世界端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_world_status(self, client: AsyncClient):
        """测试获取世界状态"""
        response = await client.get("/api/world/status")
        assert response.status_code == 200
        data = response.json()
        assert "clock" in data
        assert "cost" in data
        assert "config" in data
    
    @pytest.mark.asyncio
    async def test_get_world_time(self, client: AsyncClient):
        """测试获取世界时间"""
        response = await client.get("/api/world/time")
        assert response.status_code == 200
        data = response.json()
        assert "datetime" in data
        assert "day" in data
        assert "time_of_day" in data
        assert "is_daytime" in data
    
    @pytest.mark.asyncio
    async def test_get_clock(self, client: AsyncClient):
        """测试获取时钟状态"""
        response = await client.get("/api/world/clock")
        assert response.status_code == 200
        data = response.json()
        assert "time_scale" in data
        assert "is_running" in data
        assert "is_paused" in data
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, client: AsyncClient):
        """测试暂停和恢复"""
        # 暂停
        response = await client.post("/api/world/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        
        # 恢复
        response = await client.post("/api/world/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"
    
    @pytest.mark.asyncio
    async def test_set_time_scale(self, client: AsyncClient):
        """测试设置时间缩放"""
        response = await client.post("/api/world/time-scale/20")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["time_scale"] == 20
        
        # 恢复默认
        await client.post("/api/world/time-scale/10")
    
    @pytest.mark.asyncio
    async def test_set_invalid_time_scale(self, client: AsyncClient):
        """测试设置无效时间缩放"""
        response = await client.post("/api/world/time-scale/101")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_get_events(self, client: AsyncClient):
        """测试获取事件历史"""
        response = await client.get("/api/world/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
    
    @pytest.mark.asyncio
    async def test_get_event_types(self, client: AsyncClient):
        """测试获取事件类型"""
        response = await client.get("/api/world/event-types")
        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data


class TestLocationEndpoints:
    """地点端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_locations(self, client: AsyncClient):
        """测试获取地点列表"""
        response = await client.get("/api/locations")
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_location_types(self, client: AsyncClient):
        """测试获取地点类型"""
        response = await client.get("/api/locations/types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
    
    @pytest.mark.asyncio
    async def test_list_activity_types(self, client: AsyncClient):
        """测试获取活动类型"""
        response = await client.get("/api/locations/activities")
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
    
    @pytest.mark.asyncio
    async def test_get_location_stats(self, client: AsyncClient):
        """测试获取地点统计"""
        response = await client.get("/api/locations/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_locations" in data
        assert "total_capacity" in data
    
    @pytest.mark.asyncio
    async def test_filter_by_type(self, client: AsyncClient):
        """测试按类型筛选"""
        response = await client.get("/api/locations?location_type=cafe")
        assert response.status_code == 200
        data = response.json()
        # 所有返回的地点都应该是咖啡馆
        for loc in data["locations"]:
            assert loc["type"] == "cafe"
    
    @pytest.mark.asyncio
    async def test_filter_by_invalid_type(self, client: AsyncClient):
        """测试无效类型筛选"""
        response = await client.get("/api/locations?location_type=invalid")
        assert response.status_code == 400


class TestAgentEndpoints:
    """智能体端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_agents(self, client: AsyncClient):
        """测试获取智能体列表"""
        response = await client.get("/api/agents")
        assert response.status_code == 200
        # 阶段3实现前返回空列表
    
    @pytest.mark.asyncio
    async def test_get_agent_count(self, client: AsyncClient):
        """测试获取智能体数量"""
        response = await client.get("/api/agents/count")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "max" in data


class TestConversationEndpoints:
    """对话端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient):
        """测试获取对话列表"""
        response = await client.get("/api/conversations/")  # 添加末尾斜杠避免重定向
        assert response.status_code == 200
        # 阶段4实现前返回空列表
    
    @pytest.mark.asyncio
    async def test_get_conversation_stats(self, client: AsyncClient):
        """测试获取对话统计"""
        response = await client.get("/api/conversations/stats")
        assert response.status_code == 200
        data = response.json()
        assert "active_conversations" in data
