"""
地点模块测试
"""

import pytest
from app.core.locations import (
    Location, 
    LocationType, 
    ActivityType, 
    OpeningHours,
    LocationManager,
)


class TestOpeningHours:
    """营业时间测试"""
    
    def test_default_24h(self):
        """测试默认24小时营业"""
        hours = OpeningHours()
        assert hours.is_open(0, 0) is True
        assert hours.is_open(12, 3) is True
        assert hours.is_open(23, 6) is True
    
    def test_normal_hours(self):
        """测试正常营业时间"""
        hours = OpeningHours(open_hour=9, close_hour=18)
        assert hours.is_open(8, 0) is False
        assert hours.is_open(9, 0) is True
        assert hours.is_open(17, 0) is True
        assert hours.is_open(18, 0) is False
    
    def test_overnight_hours(self):
        """测试跨夜营业时间"""
        hours = OpeningHours(open_hour=22, close_hour=4)
        assert hours.is_open(21, 0) is False
        assert hours.is_open(22, 0) is True
        assert hours.is_open(23, 0) is True
        assert hours.is_open(2, 0) is True
        assert hours.is_open(4, 0) is False
    
    def test_weekday_restriction(self):
        """测试工作日限制"""
        hours = OpeningHours(
            open_hour=9, 
            close_hour=18, 
            open_days={0, 1, 2, 3, 4}  # 周一到周五
        )
        assert hours.is_open(12, 0) is True  # 周一
        assert hours.is_open(12, 5) is False  # 周六
        assert hours.is_open(12, 6) is False  # 周日


class TestLocation:
    """地点测试"""
    
    def test_create_location(self):
        """测试创建地点"""
        loc = Location(
            id="cafe_1",
            name="测试咖啡馆",
            type=LocationType.CAFE,
            x=10,
            y=20,
            width=4,
            height=4,
            capacity=15,
            activities=[ActivityType.EAT, ActivityType.RELAX],
        )
        
        assert loc.id == "cafe_1"
        assert loc.name == "测试咖啡馆"
        assert loc.type == LocationType.CAFE
        assert loc.capacity == 15
    
    def test_center_calculation(self):
        """测试中心点计算"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.PARK,
            x=10,
            y=20,
            width=10,
            height=6,
        )
        
        assert loc.center == (15.0, 23.0)
    
    def test_bounds(self):
        """测试边界计算"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.PARK,
            x=10,
            y=20,
            width=10,
            height=6,
        )
        
        assert loc.bounds == (10, 20, 20, 26)
    
    def test_contains_point(self):
        """测试点包含检测"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.PARK,
            x=10,
            y=20,
            width=10,
            height=6,
        )
        
        assert loc.contains_point(15, 23) is True
        assert loc.contains_point(10, 20) is True
        assert loc.contains_point(9, 23) is False
        assert loc.contains_point(20, 23) is False  # 边界不包含
    
    def test_enter_and_leave(self):
        """测试进入和离开"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.CAFE,
            x=0,
            y=0,
            capacity=2,
        )
        
        assert loc.enter("agent_1") is True
        assert len(loc.current_agents) == 1
        
        assert loc.enter("agent_2") is True
        assert len(loc.current_agents) == 2
        
        # 容量已满
        assert loc.is_full is True
        assert loc.enter("agent_3") is False
        
        loc.leave("agent_1")
        assert len(loc.current_agents) == 1
        assert loc.is_full is False
    
    def test_occupancy(self):
        """测试占用率"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.CAFE,
            x=0,
            y=0,
            capacity=10,
        )
        
        assert loc.occupancy == 0.0
        
        loc.enter("agent_1")
        loc.enter("agent_2")
        assert loc.occupancy == 0.2
    
    def test_can_do_activity(self):
        """测试活动支持检测"""
        loc = Location(
            id="test",
            name="Test",
            type=LocationType.CAFE,
            x=0,
            y=0,
            activities=[ActivityType.EAT, ActivityType.RELAX],
        )
        
        assert loc.can_do_activity(ActivityType.EAT) is True
        assert loc.can_do_activity(ActivityType.RELAX) is True
        assert loc.can_do_activity(ActivityType.WORK) is False
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        loc = Location(
            id="test",
            name="Test Cafe",
            type=LocationType.CAFE,
            x=10,
            y=20,
            width=4,
            height=4,
            capacity=15,
            activities=[ActivityType.EAT, ActivityType.RELAX],
            description="A test cafe",
        )
        
        data = loc.to_dict()
        assert data["id"] == "test"
        assert data["name"] == "Test Cafe"
        assert data["type"] == "cafe"
        
        # 反序列化
        loc2 = Location.from_dict(data)
        assert loc2.id == loc.id
        assert loc2.name == loc.name
        assert loc2.type == loc.type


class TestLocationManager:
    """地点管理器测试"""
    
    def test_add_and_get_location(self):
        """测试添加和获取地点"""
        manager = LocationManager()
        
        loc = Location(
            id="cafe_1",
            name="Test Cafe",
            type=LocationType.CAFE,
            x=10,
            y=20,
        )
        
        manager.add_location(loc)
        
        assert manager.get_location("cafe_1") is loc
        assert manager.get_location("nonexistent") is None
    
    def test_get_locations_by_type(self):
        """测试按类型获取地点"""
        manager = LocationManager()
        
        manager.add_location(Location(id="cafe_1", name="Cafe 1", type=LocationType.CAFE, x=0, y=0))
        manager.add_location(Location(id="cafe_2", name="Cafe 2", type=LocationType.CAFE, x=10, y=0))
        manager.add_location(Location(id="park_1", name="Park 1", type=LocationType.PARK, x=20, y=0))
        
        cafes = manager.get_locations_by_type(LocationType.CAFE)
        assert len(cafes) == 2
        
        parks = manager.get_locations_by_type(LocationType.PARK)
        assert len(parks) == 1
    
    def test_get_locations_with_activity(self):
        """测试按活动获取地点"""
        manager = LocationManager()
        
        manager.add_location(Location(
            id="cafe_1", name="Cafe", type=LocationType.CAFE, x=0, y=0,
            activities=[ActivityType.EAT, ActivityType.RELAX]
        ))
        manager.add_location(Location(
            id="gym_1", name="Gym", type=LocationType.GYM, x=10, y=0,
            activities=[ActivityType.EXERCISE]
        ))
        
        eat_places = manager.get_locations_with_activity(ActivityType.EAT)
        assert len(eat_places) == 1
        assert eat_places[0].id == "cafe_1"
    
    def test_get_location_at(self):
        """测试按坐标获取地点"""
        manager = LocationManager()
        
        loc = Location(
            id="cafe_1", 
            name="Cafe", 
            type=LocationType.CAFE, 
            x=10, 
            y=20,
            width=5,
            height=5,
        )
        manager.add_location(loc)
        
        # 在地点内
        found = manager.get_location_at(12, 22)
        assert found is loc
        
        # 在地点外
        found = manager.get_location_at(0, 0)
        assert found is None
    
    def test_get_nearest_location(self):
        """测试获取最近地点"""
        manager = LocationManager()
        
        manager.add_location(Location(
            id="cafe_1", name="Cafe 1", type=LocationType.CAFE, x=0, y=0,
            width=2, height=2
        ))
        manager.add_location(Location(
            id="cafe_2", name="Cafe 2", type=LocationType.CAFE, x=100, y=100,
            width=2, height=2
        ))
        
        # 从原点找最近的
        nearest = manager.get_nearest_location(0, 0)
        assert nearest.id == "cafe_1"
        
        # 从远处找最近的
        nearest = manager.get_nearest_location(90, 90)
        assert nearest.id == "cafe_2"
