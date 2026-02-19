"""
LLM适配器基类
=============
定义所有LLM适配器必须实现的接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class TokenUsage:
    """
    Token使用情况
    
    Attributes:
        prompt_tokens: 输入token数量
        completion_tokens: 输出token数量
        total_tokens: 总token数量
        reasoning_tokens: 推理token数量（仅R1模型）
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: int = 0
    
    @property
    def input_cost(self) -> float:
        """计算输入成本（仅计数，具体定价在适配器中计算）"""
        return self.prompt_tokens
    
    @property
    def output_cost(self) -> float:
        """计算输出成本（仅计数，具体定价在适配器中计算）"""
        return self.completion_tokens


@dataclass
class LLMResponse:
    """
    LLM响应数据类
    
    Attributes:
        content: 响应内容
        reasoning: 推理过程（仅R1等推理模型）
        usage: Token使用情况
        model: 实际使用的模型名称
        finish_reason: 结束原因
    """
    content: str
    usage: TokenUsage
    model: str
    reasoning: Optional[str] = None
    finish_reason: str = "stop"


class LLMAdapter(ABC):
    """
    LLM适配器抽象基类
    
    所有模型适配器必须继承此类并实现以下方法：
    - generate: 生成文本
    - get_pricing: 获取定价信息
    """
    
    # 模型名称
    model_name: str
    
    # 输入定价（每百万token，美元）
    input_price_per_million: float
    
    # 输出定价（每百万token，美元）
    output_price_per_million: float
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            temperature: 温度参数，控制随机性
            max_tokens: 最大输出token数
        
        Returns:
            LLMResponse 对象
        """
        pass
    
    def calculate_cost(self, usage: TokenUsage) -> float:
        """
        计算本次调用成本
        
        Args:
            usage: Token使用情况
        
        Returns:
            成本（美元）
        """
        input_cost = (usage.prompt_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (usage.completion_tokens / 1_000_000) * self.output_price_per_million
        return input_cost + output_cost
    
    def get_pricing(self) -> Dict[str, float]:
        """获取定价信息"""
        return {
            "input_price_per_million": self.input_price_per_million,
            "output_price_per_million": self.output_price_per_million,
        }
