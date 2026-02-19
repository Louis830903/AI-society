"""
世界时钟测试
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.core.world import WorldClock, TimeOfDay


class TestWorldClock:
    """世界时钟测试"""
    
    def test_initialization(self):
        """测试初始化"""
        clock = WorldClock(time_scale=10)
        assert clock.time_scale == 10
        assert clock.is_running is False
        assert clock.is_paused is False
    
    def test_now_returns_datetime(self):
        """测试now()返回datetime"""
        clock = WorldClock(time_scale=10)
        result = clock.now()
        assert isinstance(result, datetime)
    
    def test_time_scale_effect(self):
        """测试时间缩放效果"""
        clock = WorldClock(time_scale=10)
        
        # 记录初始时间
        initial_world_time = clock.now()
        
        # 等待一小段时间后，游戏时间应该走得更快
        # （这是个简化测试，实际时间流逝很短）
        current_world_time = clock.now()
        
        assert current_world_time >= initial_world_time
    
    def test_get_world_time(self):
        """测试获取完整世界时间"""
        clock = WorldClock(time_scale=10)
        world_time = clock.get_world_time()
        
        assert world_time.day >= 1
        assert isinstance(world_time.time_of_day, TimeOfDay)
        assert isinstance(world_time.is_daytime, bool)
    
    def test_time_of_day_morning(self):
        """测试上午时间段"""
        start_time = datetime.now(timezone.utc).replace(hour=8, minute=0)
        clock = WorldClock(time_scale=10, start_world_time=start_time)
        
        world_time = clock.get_world_time()
        assert world_time.time_of_day == TimeOfDay.MORNING
    
    def test_time_of_day_night(self):
        """测试夜晚时间段"""
        start_time = datetime.now(timezone.utc).replace(hour=23, minute=0)
        clock = WorldClock(time_scale=10, start_world_time=start_time)
        
        world_time = clock.get_world_time()
        assert world_time.time_of_day == TimeOfDay.NIGHT
    
    def test_is_daytime(self):
        """测试白天判断"""
        # 设置为早上8点
        start_time = datetime.now(timezone.utc).replace(hour=8, minute=0)
        clock = WorldClock(time_scale=1, start_world_time=start_time)
        
        assert clock.is_daytime() is True
    
    def test_is_working_hours(self):
        """测试工作时间判断"""
        # 设置为上午10点
        start_time = datetime.now(timezone.utc).replace(hour=10, minute=0)
        clock = WorldClock(time_scale=1, start_world_time=start_time)
        
        assert clock.is_working_hours() is True
    
    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        clock = WorldClock(time_scale=10)
        
        clock.pause()
        assert clock.is_paused is True
        
        clock.resume()
        assert clock.is_paused is False
    
    def test_set_time_scale(self):
        """测试动态调整时间缩放"""
        clock = WorldClock(time_scale=10)
        
        clock.set_time_scale(20)
        assert clock.time_scale == 20
    
    def test_set_time_scale_validation(self):
        """测试时间缩放验证"""
        clock = WorldClock(time_scale=10)
        
        with pytest.raises(ValueError):
            clock.set_time_scale(0)
        
        with pytest.raises(ValueError):
            clock.set_time_scale(101)
    
    def test_to_dict(self):
        """测试转换为字典"""
        clock = WorldClock(time_scale=10)
        result = clock.to_dict()
        
        assert "time_scale" in result
        assert "is_running" in result
        assert "is_paused" in result
        assert "world_time" in result
