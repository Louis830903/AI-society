"""
配置管理模块
============
使用 pydantic-settings 管理所有配置项，支持环境变量覆盖

配置优先级：
1. 环境变量
2. .env 文件
3. 默认值
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    
    所有配置项都可以通过环境变量覆盖，环境变量名为大写字母
    例如：time_scale -> TIME_SCALE
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===================
    # 应用基础配置
    # ===================
    app_name: str = Field(default="AI Society", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")
    
    # ===================
    # 时间系统配置
    # ===================
    time_scale: int = Field(
        default=10, 
        ge=1, 
        le=100,
        description="时间缩放比例：现实1分钟 = 游戏time_scale分钟"
    )
    
    # ===================
    # DeepSeek API 配置
    # ===================
    deepseek_api_key: str = Field(
        default="", 
        description="DeepSeek API密钥"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API基础URL"
    )
    default_model: str = Field(
        default="deepseek-reasoner",  # DeepSeek R1
        description="默认使用的LLM模型"
    )
    
    # ===================
    # 成本控制配置
    # ===================
    monthly_budget: float = Field(
        default=200.0,
        ge=0,
        description="月度预算（美元）"
    )
    cost_warning_threshold: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="成本预警阈值（占月度预算百分比）"
    )
    
    # ===================
    # 数据库配置
    # ===================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/aisociety",
        description="PostgreSQL 数据库连接URL"
    )
    
    # ===================
    # Redis 配置
    # ===================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接URL"
    )
    
    # ===================
    # Qdrant 向量数据库配置
    # ===================
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant 向量数据库URL"
    )
    qdrant_collection: str = Field(
        default="agent_memories",
        description="Qdrant 集合名称"
    )
    
    # ===================
    # 智能体配置
    # ===================
    initial_agent_count: int = Field(
        default=50,
        ge=1,
        le=200,
        description="初始智能体数量"
    )
    max_agent_count: int = Field(
        default=100,
        ge=1,
        le=500,
        description="最大智能体数量"
    )
    decision_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="智能体决策间隔（现实秒数）"
    )
    
    # ===================
    # 对话配置
    # ===================
    max_conversation_turns: int = Field(
        default=6,
        ge=2,
        le=20,
        description="对话最大轮次"
    )
    conversation_trigger_distance: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="触发对话的距离阈值"
    )
    
    # ===================
    # 经济系统配置
    # ===================
    daily_expense_base: float = Field(
        default=185.0,
        ge=0,
        description="日均基础开销（元）：房租+吃饭+交通"
    )
    programmer_hourly_wage: float = Field(
        default=150.0,
        ge=0,
        description="程序员时薪（元），作为基准工资"
    )
    initial_balance: float = Field(
        default=10000.0,
        ge=0,
        description="智能体初始账户余额（元）"
    )
    
    # ===================
    # 地图配置
    # ===================
    map_width: int = Field(
        default=100,
        ge=50,
        le=500,
        description="地图宽度（单位格）"
    )
    map_height: int = Field(
        default=100,
        ge=50,
        le=500,
        description="地图高度（单位格）"
    )
    locations_file: str = Field(
        default="data/locations.json",
        description="地点配置文件路径"
    )
    
    # ===================
    # 日志配置
    # ===================
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="日志文件路径（为空则只输出到控制台）"
    )
    
    # ===================
    # Phase 6: 智能体架构增强配置
    # ===================
    reflection_importance_threshold: float = Field(
        default=150.0,
        ge=50,
        le=500,
        description="反思触发阈值（累积重要性超过此值触发反思）"
    )
    daily_plan_start_hour: int = Field(
        default=6,
        ge=0,
        le=23,
        description="每日计划生成的起始小时"
    )
    perception_radius: float = Field(
        default=50.0,
        ge=10,
        le=200,
        description="智能体感知半径（地图单位）"
    )
    react_check_interval: int = Field(
        default=5,
        ge=1,
        le=30,
        description="反应检查间隔（秒）"
    )
    importance_rating_model: str = Field(
        default="deepseek-chat",
        description="用于记忆重要性评分的模型（轻量模型节省成本）"
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例
    
    使用 lru_cache 确保只创建一个 Settings 实例
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


# 导出配置单例，方便直接导入使用
settings = get_settings()
