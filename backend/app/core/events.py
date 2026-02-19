"""
事件总线模块
============
实现发布-订阅模式的事件系统，用于解耦各模块之间的通信

事件类型：
- AGENT_MOVED: 智能体移动
- AGENT_DECIDED: 智能体做出决策
- CONVERSATION_STARTED: 对话开始
- CONVERSATION_MESSAGE: 对话消息
- CONVERSATION_ENDED: 对话结束
- WORLD_TICK: 世界时钟滴答
- AGENT_CREATED: 新智能体创建
- AGENT_LEFT: 智能体离开
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import UUID, uuid4

from loguru import logger


class EventType(str, Enum):
    """事件类型枚举"""
    
    # 智能体相关事件
    AGENT_MOVED = "agent.moved"
    AGENT_DECIDED = "agent.decided"
    AGENT_ACTION = "agent.action"
    AGENT_CREATED = "agent.created"
    AGENT_LEFT = "agent.left"
    AGENT_STATE_CHANGED = "agent.state_changed"
    
    # 对话相关事件
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_ENDED = "conversation.ended"
    CHAT_REQUESTED = "chat.requested"  # 智能体发起聊天请求
    
    # 世界相关事件
    WORLD_TICK = "world.tick"
    WORLD_TIME_CHANGED = "world.time_changed"
    WORLD_BROADCAST = "world.broadcast"  # 世界广播
    WORLD_RULE_CHANGED = "world.rule_changed"  # 世界规则变更
    WORLD_EVENT = "world.event"  # 世界事件触发
    
    # 经济相关事件
    ECONOMY_TRANSACTION = "economy.transaction"
    
    # 系统事件
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


@dataclass
class Event:
    """
    事件数据类
    
    Attributes:
        event_type: 事件类型
        data: 事件携带的数据
        event_id: 事件唯一标识
        timestamp: 事件发生时间
        source: 事件来源（可选）
    """
    event_type: EventType
    data: Dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于WebSocket传输"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# 事件处理器类型：接收Event，返回None或协程
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    事件总线
    
    实现发布-订阅模式，支持异步事件处理
    
    使用示例：
        # 订阅事件
        @event_bus.subscribe(EventType.AGENT_MOVED)
        async def on_agent_moved(event: Event):
            print(f"智能体移动: {event.data}")
        
        # 发布事件
        await event_bus.publish(Event(
            event_type=EventType.AGENT_MOVED,
            data={"agent_id": "123", "x": 10, "y": 20}
        ))
    """
    
    def __init__(self):
        """初始化事件总线"""
        # 事件类型 -> 处理器列表 的映射
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        # 事件历史（用于调试和回放）
        self._history: List[Event] = []
        # 历史记录最大长度
        self._max_history: int = 1000
        # WebSocket连接集合，用于实时推送
        self._ws_connections: set = set()
        # 是否启用历史记录
        self._enable_history: bool = True
    
    def subscribe(self, event_type: EventType) -> Callable[[EventHandler], EventHandler]:
        """
        订阅事件的装饰器
        
        Args:
            event_type: 要订阅的事件类型
        
        Returns:
            装饰器函数
        
        Example:
            @event_bus.subscribe(EventType.AGENT_MOVED)
            async def handle_move(event: Event):
                pass
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self.add_handler(event_type, handler)
            return handler
        return decorator
    
    def add_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        添加事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"注册事件处理器: {event_type.value} -> {handler.__name__}")
    
    def remove_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        移除事件处理器
        
        Args:
            event_type: 事件类型
            handler: 要移除的处理器函数
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"移除事件处理器: {event_type.value} -> {handler.__name__}")
    
    async def publish(self, event: Event) -> None:
        """
        发布事件
        
        会异步调用所有订阅了该事件类型的处理器
        
        Args:
            event: 要发布的事件
        """
        logger.debug(f"发布事件: {event.event_type.value}")
        
        # 记录历史
        if self._enable_history:
            self._history.append(event)
            # 限制历史长度
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        
        # 获取处理器列表
        handlers = self._handlers.get(event.event_type, [])
        
        # 异步执行所有处理器
        if handlers:
            tasks = [self._safe_handle(handler, event) for handler in handlers]
            await asyncio.gather(*tasks)
        
        # 推送到WebSocket连接
        await self._broadcast_to_websockets(event)
    
    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        """
        安全执行处理器，捕获异常防止影响其他处理器
        
        Args:
            handler: 处理器函数
            event: 事件
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"事件处理器异常: {handler.__name__} - {e}")
    
    async def _broadcast_to_websockets(self, event: Event) -> None:
        """
        广播事件到所有WebSocket连接
        
        Args:
            event: 要广播的事件
        """
        if not self._ws_connections:
            return
        
        message = event.to_dict()
        disconnected = set()
        
        for ws in self._ws_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        
        # 移除已断开的连接
        self._ws_connections -= disconnected
    
    def register_websocket(self, ws) -> None:
        """注册WebSocket连接"""
        self._ws_connections.add(ws)
        logger.info(f"WebSocket连接已注册，当前连接数: {len(self._ws_connections)}")
    
    def unregister_websocket(self, ws) -> None:
        """注销WebSocket连接"""
        self._ws_connections.discard(ws)
        logger.info(f"WebSocket连接已注销，当前连接数: {len(self._ws_connections)}")
    
    def get_history(
        self, 
        event_type: Optional[EventType] = None, 
        limit: int = 100
    ) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 过滤特定事件类型（可选）
            limit: 返回的最大事件数量
        
        Returns:
            事件列表
        """
        if event_type:
            filtered = [e for e in self._history if e.event_type == event_type]
            return filtered[-limit:]
        return self._history[-limit:]
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self._history.clear()
        logger.info("事件历史已清空")
    
    def publish_sync(self, event_type_str: str, data: Dict[str, Any], source: Optional[str] = None) -> None:
        """
        同步发布事件（简便方法）
        
        适用于非异步上下文，内部会创建 Event 对象并通过 asyncio 调度发布
        
        Args:
            event_type_str: 事件类型字符串（如 "agent.created"）
            data: 事件数据
            source: 事件来源
        """
        # 尝试匹配已知的 EventType 枚举
        event_type = None
        for et in EventType:
            if et.value == event_type_str:
                event_type = et
                break
        
        if event_type is None:
            # 使用通用事件类型或忽略
            logger.warning(f"未知事件类型: {event_type_str}")
            return
        
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
        )
        
        # 尝试在事件循环中调度
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            # 没有运行的事件循环，记录到历史但不广播
            if self._enable_history:
                self._history.append(event)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]


# 创建全局事件总线单例
event_bus = EventBus()
