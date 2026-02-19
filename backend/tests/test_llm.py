"""
LLM模块测试
===========
测试LLM路由器、缓存、频率限制等功能
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.llm.cache import LRUCache, RateLimiter, LLMCache
from app.llm.adapters.base import LLMResponse, TokenUsage
from app.llm.prompts import PromptTemplates, render_prompt


# ==================
# LRU缓存测试
# ==================

class TestLRUCache:
    """LRU缓存测试"""
    
    def test_basic_set_get(self):
        """测试基本的设置和获取"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
    
    def test_max_size_eviction(self):
        """测试超出容量时的LRU淘汰"""
        cache = LRUCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 访问key1，使其成为最近访问
        cache.get("key1")
        
        # 添加新条目，应该淘汰key2（最久未访问）
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # 被淘汰
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = LRUCache(max_size=10, default_ttl=0.1)  # 100ms TTL
        cache.set("key1", "value1")
        
        assert cache.get("key1") == "value1"
        
        # 等待过期
        time.sleep(0.15)
        
        assert cache.get("key1") is None
    
    def test_custom_ttl(self):
        """测试自定义TTL"""
        cache = LRUCache(max_size=10, default_ttl=1.0)
        cache.set("key1", "value1", ttl=0.1)
        cache.set("key2", "value2")  # 使用默认TTL
        
        time.sleep(0.15)
        
        assert cache.get("key1") is None  # 自定义TTL已过期
        assert cache.get("key2") == "value2"  # 默认TTL未过期
    
    def test_stats(self):
        """测试统计功能"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.get("key1")
        cache.get("key1")
        
        stats = cache.stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["total_hits"] == 2
    
    def test_clear(self):
        """测试清空缓存"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.stats()["size"] == 0


# ==================
# 频率限制器测试
# ==================

class TestRateLimiter:
    """频率限制器测试"""
    
    def test_allow_within_limit(self):
        """测试在限制内允许请求"""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        
        for _ in range(5):
            assert limiter.allow() is True
    
    def test_deny_over_limit(self):
        """测试超出限制时拒绝"""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)
        
        # 消耗所有配额
        for _ in range(3):
            limiter.acquire()
        
        # 下一个请求应该被拒绝
        assert limiter.allow() is False
    
    def test_window_sliding(self):
        """测试滑动窗口"""
        limiter = RateLimiter(max_requests=2, window_seconds=0.1)
        
        limiter.acquire()
        limiter.acquire()
        assert limiter.allow() is False
        
        # 等待窗口滑动
        time.sleep(0.15)
        
        assert limiter.allow() is True
    
    def test_remaining(self):
        """测试剩余配额"""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        
        assert limiter.remaining() == 5
        
        limiter.acquire()
        limiter.acquire()
        
        assert limiter.remaining() == 3
    
    def test_wait_time(self):
        """测试等待时间计算"""
        limiter = RateLimiter(max_requests=2, window_seconds=1.0)
        
        limiter.acquire()
        limiter.acquire()
        
        wait = limiter.wait_time()
        assert 0 < wait <= 1.0
    
    def test_multiple_keys(self):
        """测试多租户支持"""
        limiter = RateLimiter(max_requests=2, window_seconds=1.0)
        
        limiter.acquire("user1")
        limiter.acquire("user1")
        
        assert limiter.allow("user1") is False
        assert limiter.allow("user2") is True
    
    def test_reset(self):
        """测试重置"""
        limiter = RateLimiter(max_requests=2, window_seconds=1.0)
        
        limiter.acquire()
        limiter.acquire()
        assert limiter.allow() is False
        
        limiter.reset()
        assert limiter.allow() is True


# ==================
# LLM缓存测试
# ==================

class TestLLMCache:
    """LLM专用缓存测试"""
    
    def test_cache_enabled(self):
        """测试缓存启用"""
        cache = LLMCache(enabled=True)
        
        response = MagicMock()
        cache.set("test prompt", "model", response, temperature=0.3)
        
        result = cache.get("test prompt", "model", temperature=0.3)
        assert result is response
    
    def test_cache_disabled(self):
        """测试缓存禁用"""
        cache = LLMCache(enabled=False)
        
        response = MagicMock()
        cache.set("test prompt", "model", response, temperature=0.3)
        
        result = cache.get("test prompt", "model", temperature=0.3)
        assert result is None
    
    def test_high_temperature_no_cache(self):
        """测试高温度不缓存"""
        cache = LLMCache(enabled=True)
        
        response = MagicMock()
        cache.set("test prompt", "model", response, temperature=0.8)
        
        result = cache.get("test prompt", "model", temperature=0.8)
        assert result is None
    
    def test_different_params_different_keys(self):
        """测试不同参数生成不同缓存键"""
        cache = LLMCache(enabled=True)
        
        response1 = MagicMock()
        response2 = MagicMock()
        
        cache.set("prompt", "model1", response1, temperature=0.3)
        cache.set("prompt", "model2", response2, temperature=0.3)
        
        assert cache.get("prompt", "model1", temperature=0.3) is response1
        assert cache.get("prompt", "model2", temperature=0.3) is response2
    
    def test_stats(self):
        """测试统计"""
        cache = LLMCache(enabled=True)
        
        cache.set("prompt", "model", MagicMock(), temperature=0.3)
        cache.get("prompt", "model", temperature=0.3)  # hit
        cache.get("other", "model", temperature=0.3)  # miss
        
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0


# ==================
# 提示词模板测试
# ==================

class TestPromptTemplates:
    """提示词模板测试"""
    
    def test_render_agent_decision(self):
        """测试智能体决策模板"""
        result = PromptTemplates.render(
            "AGENT_DECISION",
            name="张三",
            age=25,
            occupation="程序员",
            personality_description="开朗、友善",
            current_location="咖啡馆",
            current_time="上午10点",
            work_hours_today=2,
            balance=5000,
            hunger=30,
            fatigue=40,
            social=60,
            entertainment=50,
            recent_memories="今天早上喝了咖啡",
            surroundings="周围有几个人在工作",
        )
        
        assert "张三" in result
        assert "程序员" in result
        assert "咖啡馆" in result
    
    def test_render_conversation_start(self):
        """测试对话开始模板"""
        result = PromptTemplates.render(
            "CONVERSATION_START",
            name="张三",
            age=25,
            occupation="程序员",
            personality_description="开朗",
            location="公园",
            other_name="李四",
            other_occupation="设计师",
            relationship_description="同事",
            current_time="下午3点",
            knowledge_about_other="喜欢运动",
            encounter_count=3,
            previous_topics="上次聊了天气",
        )
        
        assert "张三" in result
        assert "李四" in result
        assert "公园" in result
    
    def test_render_unknown_template(self):
        """测试未知模板"""
        with pytest.raises(ValueError) as exc_info:
            PromptTemplates.render("UNKNOWN_TEMPLATE")
        
        assert "未知模板" in str(exc_info.value)
    
    def test_render_prompt_function(self):
        """测试便捷函数"""
        result = render_prompt(
            "GENERATE_AGENT",
            needed_roles="医生",
            current_population=10,
            existing_agents_sample="张三(程序员)",
        )
        
        assert "医生" in result
        assert "创建一个新居民" in result


# ==================
# LLM路由器测试（Mock）
# ==================

class TestLLMRouterMock:
    """LLM路由器测试（使用Mock）"""
    
    @pytest.fixture
    def mock_response(self):
        """创建模拟响应"""
        return LLMResponse(
            content="测试响应",
            usage=TokenUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
            model="deepseek-reasoner",
        )
    
    @pytest.mark.asyncio
    async def test_generate_with_cache(self, mock_response):
        """测试带缓存的生成"""
        from app.llm.router import LLMRouter
        
        with patch.object(
            LLMRouter, '_register_default_adapters'
        ):
            router = LLMRouter(cache_enabled=True)
            
            # 模拟适配器
            mock_adapter = MagicMock()
            mock_adapter.model_name = "test-model"
            mock_adapter.generate = AsyncMock(return_value=mock_response)
            mock_adapter.calculate_cost = MagicMock(return_value=0.001)
            
            router.adapters["test-model"] = mock_adapter
            router.default_model = "test-model"
            
            # 第一次调用
            result1 = await router.generate("test prompt", temperature=0.3)
            assert result1.content == "测试响应"
            assert mock_adapter.generate.call_count == 1
            
            # 第二次调用（应该命中缓存）
            result2 = await router.generate("test prompt", temperature=0.3)
            assert result2.content == "测试响应"
            assert mock_adapter.generate.call_count == 1  # 未增加
    
    @pytest.mark.asyncio
    async def test_generate_budget_exceeded(self):
        """测试预算超支"""
        from app.llm.router import LLMRouter, CostRecord
        from datetime import datetime, timezone
        
        with patch.object(
            LLMRouter, '_register_default_adapters'
        ):
            router = LLMRouter()
            router.cost_tracker.monthly_budget = 0.001
            
            # 模拟已超支 - 创建正确的CostRecord
            router.cost_tracker.records.append(
                CostRecord(
                    timestamp=datetime.now(timezone.utc),
                    model="test",
                    tokens=TokenUsage(100, 100, 200),
                    cost=1.0
                )
            )
            
            with pytest.raises(ValueError) as exc_info:
                await router.generate("test")
            
            assert "预算已超支" in str(exc_info.value)
    
    def test_list_models(self):
        """测试列出模型"""
        from app.llm.router import LLMRouter
        
        with patch.object(
            LLMRouter, '_register_default_adapters'
        ):
            router = LLMRouter()
            
            mock_adapter = MagicMock()
            mock_adapter.get_pricing = MagicMock(return_value={"input": 0.1})
            router.adapters["model1"] = mock_adapter
            
            models = router.list_models()
            assert "model1" in models
    
    def test_get_full_stats(self):
        """测试获取完整统计"""
        from app.llm.router import LLMRouter
        
        with patch.object(
            LLMRouter, '_register_default_adapters'
        ):
            router = LLMRouter()
            
            stats = router.get_full_stats()
            
            assert "cost" in stats
            assert "cache" in stats
            assert "rate_limit" in stats
            assert "models" in stats


# ==================
# API端点测试
# ==================

class TestLLMAPI:
    """LLM API端点测试"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """创建异步测试客户端"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_list_models(self, client):
        """测试列出模型API"""
        response = await client.get("/api/llm/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "default_model" in data
        assert "models" in data
    
    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """测试获取统计API"""
        response = await client.get("/api/llm/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "cost" in data
        assert "cache" in data
    
    @pytest.mark.asyncio
    async def test_get_cost(self, client):
        """测试获取成本API"""
        response = await client.get("/api/llm/cost")
        
        assert response.status_code == 200
        data = response.json()
        assert "monthly_budget" in data
        assert "current_month_cost" in data
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client):
        """测试获取缓存统计API"""
        response = await client.get("/api/llm/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "size" in data
        assert "hit_rate" in data
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, client):
        """测试清空缓存API"""
        response = await client.post("/api/llm/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "缓存已清空"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
