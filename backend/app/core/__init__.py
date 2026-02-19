"""
核心模块
========
包含世界时钟、配置管理、事件总线、地点管理等核心组件
"""

from app.core.config import settings, get_settings, Settings
from app.core.events import EventBus, Event, EventType, event_bus
from app.core.world import WorldClock, WorldTime, TimeOfDay, world_clock
from app.core.locations import (
    Location, 
    LocationType, 
    ActivityType, 
    OpeningHours,
    LocationManager, 
    location_manager
)

__all__ = [
    # 配置
    "settings", 
    "get_settings",
    "Settings",
    # 事件
    "EventBus", 
    "Event", 
    "EventType",
    "event_bus",
    # 世界时钟
    "WorldClock",
    "WorldTime",
    "TimeOfDay",
    "world_clock",
    # 地点
    "Location",
    "LocationType",
    "ActivityType",
    "OpeningHours",
    "LocationManager",
    "location_manager",
]
