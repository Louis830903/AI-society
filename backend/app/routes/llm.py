"""
LLM API路由
===========
提供LLM相关的REST API接口

端点：
- GET /api/llm/models - 列出可用模型
- GET /api/llm/stats - 获取LLM统计信息
- POST /api/llm/generate - 调用LLM生成文本
- POST /api/llm/test - 测试LLM连接
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm import llm_router


router = APIRouter(prefix="/api/llm", tags=["LLM"])


# ==================
# 请求/响应模型
# ==================

class GenerateRequest(BaseModel):
    """LLM生成请求"""
    prompt: str = Field(..., description="用户提示词", min_length=1, max_length=10000)
    model_name: Optional[str] = Field(None, description="模型名称，为空使用默认模型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(2048, ge=1, le=8192, description="最大输出token数")
    use_cache: bool = Field(True, description="是否使用缓存")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "你好，请自我介绍",
                "model_name": "deepseek-reasoner",
                "temperature": 0.7,
                "max_tokens": 1024,
            }
        }
    }


class GenerateResponse(BaseModel):
    """LLM生成响应"""
    content: str = Field(..., description="生成的文本内容")
    reasoning: Optional[str] = Field(None, description="推理过程（仅R1模型）")
    model: str = Field(..., description="实际使用的模型")
    usage: dict = Field(..., description="Token使用情况")
    finish_reason: str = Field(..., description="结束原因")


class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    input_price_per_million: float
    output_price_per_million: float


class ModelsResponse(BaseModel):
    """可用模型列表响应"""
    default_model: str
    models: dict


class StatsResponse(BaseModel):
    """LLM统计响应"""
    cost: dict
    cache: dict
    rate_limit: dict
    models: dict


class TestResponse(BaseModel):
    """测试响应"""
    success: bool
    message: str
    model: Optional[str] = None
    latency_ms: Optional[float] = None


# ==================
# API端点
# ==================

@router.get("/models", response_model=ModelsResponse, summary="列出可用模型")
async def list_models():
    """
    获取所有可用的LLM模型及其定价信息
    
    返回：
    - default_model: 默认使用的模型
    - models: 所有可用模型及其定价
    """
    return ModelsResponse(
        default_model=llm_router.default_model,
        models=llm_router.list_models()
    )


@router.get("/stats", response_model=StatsResponse, summary="获取LLM统计")
async def get_stats():
    """
    获取LLM使用统计信息（持久化版本）
    
    包含：
    - cost: 成本统计（月度预算、已用、剩余）- 从数据库查询
    - cache: 缓存统计（命中率、大小）
    - rate_limit: 频率限制状态
    - models: 模型定价信息
    """
    # 获取基础统计
    base_stats = llm_router.get_full_stats()
    # 用数据库的成本统计替换内存统计
    base_stats["cost"] = await llm_router.get_cost_summary_from_db()
    return StatsResponse(**base_stats)


@router.post("/generate", response_model=GenerateResponse, summary="调用LLM生成")
async def generate(request: GenerateRequest):
    """
    调用LLM生成文本
    
    这是核心的LLM调用接口，支持：
    - 多模型选择（默认使用DeepSeek R1）
    - 系统提示词
    - 温度控制
    - 缓存（相同请求会返回缓存结果）
    
    注意：
    - 温度 > 0.5 时不会使用缓存（随机性高）
    - 预算超支时会返回错误
    """
    try:
        response = await llm_router.generate(
            prompt=request.prompt,
            model_name=request.model_name,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_cache=request.use_cache,
        )
        
        return GenerateResponse(
            content=response.content,
            reasoning=response.reasoning,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "reasoning_tokens": response.usage.reasoning_tokens,
            },
            finish_reason=response.finish_reason,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")


@router.post("/test", response_model=TestResponse, summary="测试LLM连接")
async def test_connection(model_name: Optional[str] = None):
    """
    测试LLM连接是否正常
    
    发送一个简单的测试请求，验证API密钥和网络连接
    
    Args:
        model_name: 要测试的模型名称（可选）
    """
    import time
    
    try:
        start = time.time()
        
        response = await llm_router.generate(
            prompt="请回复'OK'",
            model_name=model_name,
            temperature=0.1,
            max_tokens=10,
            use_cache=False,
        )
        
        latency = (time.time() - start) * 1000
        
        return TestResponse(
            success=True,
            message="连接成功",
            model=response.model,
            latency_ms=round(latency, 2),
        )
        
    except Exception as e:
        return TestResponse(
            success=False,
            message=f"连接失败: {str(e)}",
        )


@router.get("/cost", summary="获取成本统计")
async def get_cost_summary():
    """
    获取当月API调用成本统计（持久化版本）
    
    返回：
    - monthly_budget: 月度预算
    - current_month_cost: 当月已用
    - remaining_budget: 剩余预算
    - budget_usage_percent: 预算使用百分比
    - is_warning: 是否触发预警
    - is_exceeded: 是否超支
    - total_calls: 总调用次数
    - total_tokens: 总token数
    """
    return await llm_router.get_cost_summary_from_db()


@router.get("/cache/stats", summary="获取缓存统计")
async def get_cache_stats():
    """
    获取LLM响应缓存统计
    
    返回：
    - size: 当前缓存条目数
    - max_size: 最大容量
    - hits: 命中次数
    - misses: 未命中次数
    - hit_rate: 命中率
    """
    return llm_router.get_cache_stats()


@router.post("/cache/clear", summary="清空缓存")
async def clear_cache():
    """清空LLM响应缓存"""
    llm_router.cache.clear()
    return {"message": "缓存已清空"}
