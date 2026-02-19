"""
事件总线测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from app.core.events import EventBus, Event, EventType


class TestEvent:
    """事件数据类测试"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = Event(
            event_type=EventType.AGENT_MOVED,
            data={"agent_id": "123", "x": 10, "y": 20}
        )
        
        assert event.event_type == EventType.AGENT_MOVED
        assert event.data["agent_id"] == "123"
        assert event.event_id is not None
        assert event.timestamp is not None
    
    def test_event_to_dict(self):
        """测试事件转字典"""
        event = Event(
            event_type=EventType.AGENT_MOVED,
            data={"x": 10},
            source="test"
        )
        
        result = event.to_dict()
        
        assert "event_id" in result
        assert result["event_type"] == "agent.moved"
        assert result["data"]["x"] == 10
        assert result["source"] == "test"


class TestEventBus:
    """事件总线测试"""
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        bus = EventBus()
        received_events = []
        
        @bus.subscribe(EventType.AGENT_MOVED)
        async def handler(event: Event):
            received_events.append(event)
        
        event = Event(
            event_type=EventType.AGENT_MOVED,
            data={"test": True}
        )
        
        asyncio.run(bus.publish(event))
        
        assert len(received_events) == 1
        assert received_events[0].data["test"] is True
    
    def test_multiple_handlers(self):
        """测试多个处理器"""
        bus = EventBus()
        call_count = {"count": 0}
        
        @bus.subscribe(EventType.WORLD_TICK)
        async def handler1(event: Event):
            call_count["count"] += 1
        
        @bus.subscribe(EventType.WORLD_TICK)
        async def handler2(event: Event):
            call_count["count"] += 1
        
        event = Event(event_type=EventType.WORLD_TICK, data={})
        asyncio.run(bus.publish(event))
        
        assert call_count["count"] == 2
    
    def test_handler_error_isolation(self):
        """测试处理器错误隔离"""
        bus = EventBus()
        second_handler_called = {"called": False}
        
        @bus.subscribe(EventType.WORLD_TICK)
        async def bad_handler(event: Event):
            raise Exception("故意抛出异常")
        
        @bus.subscribe(EventType.WORLD_TICK)
        async def good_handler(event: Event):
            second_handler_called["called"] = True
        
        event = Event(event_type=EventType.WORLD_TICK, data={})
        asyncio.run(bus.publish(event))
        
        # 第一个处理器出错不应影响第二个
        assert second_handler_called["called"] is True
    
    def test_event_history(self):
        """测试事件历史"""
        bus = EventBus()
        
        for i in range(5):
            event = Event(event_type=EventType.WORLD_TICK, data={"index": i})
            asyncio.run(bus.publish(event))
        
        history = bus.get_history()
        assert len(history) == 5
        
        history = bus.get_history(limit=3)
        assert len(history) == 3
    
    def test_event_history_filter(self):
        """测试事件历史过滤"""
        bus = EventBus()
        
        asyncio.run(bus.publish(Event(event_type=EventType.WORLD_TICK, data={})))
        asyncio.run(bus.publish(Event(event_type=EventType.AGENT_MOVED, data={})))
        asyncio.run(bus.publish(Event(event_type=EventType.WORLD_TICK, data={})))
        
        tick_events = bus.get_history(event_type=EventType.WORLD_TICK)
        assert len(tick_events) == 2
    
    def test_remove_handler(self):
        """测试移除处理器"""
        bus = EventBus()
        call_count = {"count": 0}
        
        async def handler(event: Event):
            call_count["count"] += 1
        
        bus.add_handler(EventType.WORLD_TICK, handler)
        
        event = Event(event_type=EventType.WORLD_TICK, data={})
        asyncio.run(bus.publish(event))
        assert call_count["count"] == 1
        
        bus.remove_handler(EventType.WORLD_TICK, handler)
        asyncio.run(bus.publish(event))
        assert call_count["count"] == 1  # 不再增加
    
    def test_clear_history(self):
        """测试清空历史"""
        bus = EventBus()
        
        asyncio.run(bus.publish(Event(event_type=EventType.WORLD_TICK, data={})))
        assert len(bus.get_history()) == 1
        
        bus.clear_history()
        assert len(bus.get_history()) == 0
