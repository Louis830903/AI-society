"""
LLM路由器
=========
负责管理多个LLM适配器，根据模型名称路由请求

功能：
- 多模型支持（DeepSeek R1、Chat、GPT-4o等）
- 成本跟踪和预算控制
- 请求缓存
- 频率限制
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from loguru import logger

from app.core.config import settings
from app.llm.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from app.llm.adapters.deepseek import DeepSeekAdapter
from app.llm.cache import LLMCache, RateLimiter


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: datetime
    model: str
    tokens: TokenUsage
    cost: float


@dataclass
class CostTracker:
    """
    成本跟踪器
    
    跟踪每月的API调用成本，支持预算预警
    """
    monthly_budget: float = field(default_factory=lambda: settings.monthly_budget)
    records: list = field(default_factory=list)
    
    @property
    def current_month_cost(self) -> float:
        """计算当月总成本"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_cost = sum(
            r.cost for r in self.records 
            if r.timestamp >= month_start
        )
        return monthly_cost
    
    def record(self, model: str, tokens: TokenUsage, cost: float) -> None:
        """记录一次调用成本"""
        self.records.append(CostRecord(
            timestamp=datetime.now(timezone.utc),
            model=model,
            tokens=tokens,
            cost=cost,
        ))
        
        # 保留最近30天的记录
        cutoff = datetime.now(timezone.utc).replace(day=1) - timedelta(days=30)
        self.records = [r for r in self.records if r.timestamp >= cutoff]
    
    def is_budget_warning(self) -> bool:
        """是否触发预算预警"""
        threshold = self.monthly_budget * settings.cost_warning_threshold
        return self.current_month_cost >= threshold
    
    def is_budget_exceeded(self) -> bool:
        """是否超出预算"""
        return self.current_month_cost >= self.monthly_budget
    
    def get_summary(self) -> Dict:
        """获取成本摘要"""
        return {
            "monthly_budget": self.monthly_budget,
            "current_month_cost": round(self.current_month_cost, 4),
            "remaining_budget": round(self.monthly_budget - self.current_month_cost, 4),
            "budget_usage_percent": round(self.current_month_cost / self.monthly_budget * 100, 2),
            "is_warning": self.is_budget_warning(),
            "is_exceeded": self.is_budget_exceeded(),
        }


class LLMRouter:
    """
    LLM路由器
    
    管理多个LLM适配器，提供统一的调用接口
    
    特性：
    - 多模型路由
    - 成本跟踪
    - 响应缓存
    - 频率限制
    
    使用示例：
        router = LLMRouter()
        response = await router.generate(
            model_name="deepseek-reasoner",
            prompt="你好，请自我介绍"
        )
    """
    
    def __init__(
        self,
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        cache_ttl: float = 3600,
        rate_limit_rpm: int = 60,
    ):
        """
        初始化路由器
        
        Args:
            cache_enabled: 是否启用缓存
            cache_max_size: 缓存最大条目数
            cache_ttl: 缓存TTL（秒）
            rate_limit_rpm: 每分钟最大请求数
        """
        self.adapters: Dict[str, LLMAdapter] = {}
        self.cost_tracker = CostTracker()
        self.default_model = settings.default_model
        
        # 初始化缓存
        self.cache = LLMCache(
            max_size=cache_max_size,
            default_ttl=cache_ttl,
            enabled=cache_enabled,
        )
        
        # 初始化频率限制器
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_rpm,
            window_seconds=60,
        )
        
        # 注册默认适配器
        self._register_default_adapters()
        
        logger.info(
            f"LLM路由器初始化完成，默认模型: {self.default_model}, "
            f"缓存: {cache_enabled}, 频率限制: {rate_limit_rpm}/min"
        )
    
    def _register_default_adapters(self) -> None:
        """注册默认的LLM适配器"""
        # DeepSeek R1（默认）
        self.register_adapter(
            "deepseek-reasoner",
            DeepSeekAdapter("deepseek-reasoner")
        )
        
        # DeepSeek Chat
        self.register_adapter(
            "deepseek-chat",
            DeepSeekAdapter("deepseek-chat")
        )
    
    def register_adapter(self, name: str, adapter: LLMAdapter) -> None:
        """
        注册LLM适配器
        
        Args:
            name: 适配器名称（用于路由）
            adapter: 适配器实例
        """
        self.adapters[name] = adapter
        logger.info(f"注册LLM适配器: {name}")
    
    def get_adapter(self, model_name: Optional[str] = None) -> LLMAdapter:
        """
        获取适配器
        
        Args:
            model_name: 模型名称，为空则使用默认模型
        
        Returns:
            LLMAdapter 实例
        
        Raises:
            ValueError: 未知模型名称
        """
        name = model_name or self.default_model
        
        if name not in self.adapters:
            raise ValueError(f"未知模型: {name}，可用模型: {list(self.adapters.keys())}")
        
        return self.adapters[name]
    
    async def generate(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        调用LLM生成文本
        
        Args:
            prompt: 用户提示词
            model_name: 模型名称（可选，默认使用配置的默认模型）
            system_prompt: 系统提示词（可选）
            temperature: 温度参数
            max_tokens: 最大输出token数
            use_cache: 是否使用缓存（默认True）
        
        Returns:
            LLMResponse 对象
        
        Raises:
            ValueError: 预算超支或频率限制时抛出
        """
        # 检查预算
        if self.cost_tracker.is_budget_exceeded():
            raise ValueError("本月API预算已超支，请等待下月或增加预算")
        
        # 预算预警
        if self.cost_tracker.is_budget_warning():
            logger.warning(f"接近月度预算上限: {self.cost_tracker.get_summary()}")
        
        # 获取适配器
        adapter = self.get_adapter(model_name)
        model = adapter.model_name
        
        # 尝试从缓存获取
        if use_cache:
            cached_response = self.cache.get(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
            )
            if cached_response is not None:
                logger.debug(f"使用缓存响应: model={model}")
                return cached_response
        
        # 检查频率限制
        if not self.rate_limiter.allow(model):
            wait_time = self.rate_limiter.wait_time(model)
            if wait_time > 0:
                logger.warning(f"频率限制，等待 {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # 获取配额
        self.rate_limiter.acquire(model)
        
        # 调用模型
        response = await adapter.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # 计算并记录成本
        cost = adapter.calculate_cost(response.usage)
        self.cost_tracker.record(adapter.model_name, response.usage, cost)
        
        # 持久化到数据库
        await self._persist_llm_call(
            model_name=adapter.model_name,
            call_type="generate",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            reasoning_tokens=response.usage.reasoning_tokens,
            cost=cost,
        )
        
        # 缓存响应
        if use_cache:
            self.cache.set(
                prompt=prompt,
                model=model,
                response=response,
                system_prompt=system_prompt,
                temperature=temperature,
            )
        
        logger.debug(f"LLM调用完成: model={adapter.model_name}, cost=${cost:.4f}")
        
        return response
    
    def get_cost_summary(self) -> Dict:
        """获取成本摘要"""
        return self.cost_tracker.get_summary()
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache.stats()
    
    def get_rate_limit_stats(self, model: Optional[str] = None) -> Dict:
        """获取频率限制统计"""
        key = model or self.default_model
        return self.rate_limiter.stats(key)
    
    def get_full_stats(self) -> Dict:
        """获取完整统计信息"""
        return {
            "cost": self.get_cost_summary(),
            "cache": self.get_cache_stats(),
            "rate_limit": {
                name: self.rate_limiter.stats(name)
                for name in self.adapters.keys()
            },
            "models": self.list_models(),
        }
    
    def list_models(self) -> Dict[str, Dict]:
        """列出所有可用模型及其定价"""
        return {
            name: adapter.get_pricing()
            for name, adapter in self.adapters.items()
        }
    
    async def _persist_llm_call(
        self,
        model_name: str,
        call_type: str,
        input_tokens: int,
        output_tokens: int,
        reasoning_tokens: int,
        cost: float,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        持久化LLM调用记录到数据库
        
        Args:
            model_name: 模型名称
            call_type: 调用类型
            input_tokens: 输入token数
            output_tokens: 输出token数
            reasoning_tokens: 推理token数
            cost: 成本
            agent_id: 智能体ID（可选）
        """
        try:
            from app.database import get_async_session
            from app.database.crud.world_state import LLMCallCRUD
            
            async with get_async_session() as db:
                await LLMCallCRUD.create(
                    db=db,
                    model_name=model_name,
                    call_type=call_type,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    reasoning_tokens=reasoning_tokens,
                    cost=cost,
                    agent_id=agent_id,
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"持久化LLM调用记录失败: {e}")
    
    async def get_cost_summary_from_db(self) -> Dict:
        """
        从数据库获取成本摘要（持久化版本）
        
        Returns:
            成本摘要字典
        """
        try:
            from app.database import get_async_session
            from app.database.crud.world_state import LLMCallCRUD
            
            async with get_async_session() as db:
                # 获取本月统计
                first_day = datetime.now(timezone.utc).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                stats = await LLMCallCRUD.get_stats(db, start_time=first_day)
                
                current_month_cost = stats.get("total_cost", 0.0)
                monthly_budget = self.cost_tracker.monthly_budget
                
                return {
                    "monthly_budget": monthly_budget,
                    "current_month_cost": round(current_month_cost, 4),
                    "remaining_budget": round(monthly_budget - current_month_cost, 4),
                    "budget_usage_percent": round(
                        current_month_cost / monthly_budget * 100 if monthly_budget > 0 else 0, 2
                    ),
                    "is_warning": current_month_cost >= monthly_budget * settings.cost_warning_threshold,
                    "is_exceeded": current_month_cost >= monthly_budget,
                    "total_calls": stats.get("total_calls", 0),
                    "total_tokens": stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0),
                }
        except Exception as e:
            logger.warning(f"从数据库获取成本统计失败: {e}")
            # 回退到内存统计
            return self.cost_tracker.get_summary()


# 创建全局路由器单例
llm_router = LLMRouter()
