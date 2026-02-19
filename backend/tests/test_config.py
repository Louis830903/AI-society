"""
配置模块测试
"""

import os
import pytest
from app.core.config import Settings, get_settings


class TestSettings:
    """配置类测试"""
    
    def test_default_values(self):
        """测试默认配置值"""
        settings = Settings()
        
        assert settings.time_scale == 10
        assert settings.default_model == "deepseek-reasoner"
        assert settings.monthly_budget == 200.0
        assert settings.initial_agent_count == 50
    
    def test_time_scale_validation(self):
        """测试时间缩放验证"""
        # 有效值
        settings = Settings(time_scale=1)
        assert settings.time_scale == 1
        
        settings = Settings(time_scale=100)
        assert settings.time_scale == 100
    
    def test_cost_warning_threshold(self):
        """测试成本预警阈值"""
        settings = Settings(cost_warning_threshold=0.5)
        assert settings.cost_warning_threshold == 0.5
    
    def test_settings_singleton(self):
        """测试配置单例"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
