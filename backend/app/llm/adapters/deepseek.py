"""
DeepSeek适配器
==============
支持 DeepSeek R1（推理模型）和 DeepSeek Chat

模型说明：
- deepseek-reasoner (R1): 推理能力强，适合复杂决策
- deepseek-chat: 普通对话，响应快速，成本更低

定价（2024年）：
- R1: $0.55/百万输入token, $2.19/百万输出token
- Chat: $0.14/百万输入token, $0.28/百万输出token
"""

from typing import Optional

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.llm.adapters.base import LLMAdapter, LLMResponse, TokenUsage


class DeepSeekAdapter(LLMAdapter):
    """
    DeepSeek模型适配器
    
    支持R1推理模型和Chat对话模型
    通过OpenAI兼容接口调用
    """
    
    # 模型定价配置
    PRICING = {
        "deepseek-reasoner": {
            "input_price_per_million": 0.55,
            "output_price_per_million": 2.19,
        },
        "deepseek-chat": {
            "input_price_per_million": 0.14,
            "output_price_per_million": 0.28,
        },
    }
    
    def __init__(self, model_name: str = "deepseek-reasoner"):
        """
        初始化DeepSeek适配器
        
        Args:
            model_name: 模型名称，默认为 deepseek-reasoner (R1)
        """
        self.model_name = model_name
        
        # 设置定价
        pricing = self.PRICING.get(model_name, self.PRICING["deepseek-reasoner"])
        self.input_price_per_million = pricing["input_price_per_million"]
        self.output_price_per_million = pricing["output_price_per_million"]
        
        # 创建OpenAI兼容客户端
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        
        logger.info(f"DeepSeek适配器初始化: model={model_name}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        调用DeepSeek生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大输出token数
        
        Returns:
            LLMResponse 对象
        """
        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        logger.debug(f"调用DeepSeek: model={self.model_name}, prompt_length={len(prompt)}")
        
        try:
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # 提取响应内容
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # 提取推理内容（R1模型特有）
            reasoning = None
            if hasattr(choice.message, "reasoning_content"):
                reasoning = choice.message.reasoning_content
            
            # 提取token使用情况
            usage = response.usage
            reasoning_tokens = 0
            if hasattr(usage, "reasoning_tokens"):
                reasoning_tokens = usage.reasoning_tokens or 0
            
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                reasoning_tokens=reasoning_tokens,
            )
            
            logger.debug(
                f"DeepSeek响应: tokens={token_usage.total_tokens}, "
                f"reasoning_tokens={reasoning_tokens}"
            )
            
            return LLMResponse(
                content=content,
                reasoning=reasoning,
                usage=token_usage,
                model=response.model,
                finish_reason=choice.finish_reason or "stop",
            )
            
        except Exception as e:
            logger.error(f"DeepSeek调用失败: {e}")
            raise
    
    def calculate_cost(self, usage: TokenUsage) -> float:
        """
        计算成本，R1模型需要额外计算推理token
        
        Args:
            usage: Token使用情况
        
        Returns:
            成本（美元）
        """
        input_cost = (usage.prompt_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (usage.completion_tokens / 1_000_000) * self.output_price_per_million
        
        # R1模型的推理token按输出价格计费
        if self.model_name == "deepseek-reasoner" and usage.reasoning_tokens > 0:
            reasoning_cost = (usage.reasoning_tokens / 1_000_000) * self.output_price_per_million
            return input_cost + output_cost + reasoning_cost
        
        return input_cost + output_cost
