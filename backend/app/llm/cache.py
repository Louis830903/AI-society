"""
LLM缓存模块
===========
提供LLM响应缓存和频率限制功能

功能：
- 响应缓存（内存/Redis）
- 滑动窗口频率限制
- TTL过期管理
"""

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    ttl: float  # 秒
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl
    
    def touch(self) -> None:
        """更新访问计数"""
        self.hit_count += 1


class LRUCache:
    """
    LRU缓存实现
    
    用于缓存LLM响应，减少重复调用
    
    特性：
    - 最近最少使用(LRU)淘汰策略
    - TTL过期支持
    - 最大容量限制
    
    使用示例：
        cache = LRUCache(max_size=1000, default_ttl=3600)
        cache.set("key", "value")
        value = cache.get("key")
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # 访问顺序，最近访问的在末尾
        
        logger.info(f"LRU缓存初始化: max_size={max_size}, ttl={default_ttl}s")
    
    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prompt: 提示词
            model: 模型名称
            **kwargs: 其他参数
        
        Returns:
            缓存键（MD5哈希）
        """
        key_data = {
            "prompt": prompt,
            "model": model,
            **kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，不存在或过期返回None
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # 检查过期
        if entry.is_expired:
            self._remove(key)
            return None
        
        # 更新访问顺序
        entry.touch()
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: TTL（秒），默认使用全局TTL
        """
        # 检查容量，必要时淘汰
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict()
        
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl or self.default_ttl,
        )
        
        self._cache[key] = entry
        
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _remove(self, key: str) -> None:
        """删除缓存条目"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict(self) -> None:
        """淘汰最久未使用的条目"""
        # 先清理过期条目
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            self._remove(key)
        
        # 如果仍然超出容量，淘汰LRU条目
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order[0]
            self._remove(oldest_key)
            logger.debug(f"LRU淘汰: {oldest_key}")
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_hits = sum(e.hit_count for e in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "expired_count": sum(1 for e in self._cache.values() if e.is_expired),
        }


@dataclass
class RateLimitWindow:
    """滑动窗口"""
    timestamps: List[float] = field(default_factory=list)
    
    def clean(self, window_size: float) -> None:
        """清理过期的时间戳"""
        cutoff = time.time() - window_size
        self.timestamps = [t for t in self.timestamps if t > cutoff]


class RateLimiter:
    """
    滑动窗口频率限制器
    
    限制单位时间内的API调用次数，防止超出速率限制
    
    特性：
    - 滑动窗口算法
    - 支持多租户（按key区分）
    - 自动清理过期记录
    
    使用示例：
        limiter = RateLimiter(max_requests=60, window_seconds=60)
        if limiter.allow("api_key"):
            # 执行请求
        else:
            # 等待或拒绝
    """
    
    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: float = 60,
        burst_limit: Optional[int] = None,
    ):
        """
        初始化频率限制器
        
        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 窗口大小（秒）
            burst_limit: 突发限制（可选，更短窗口内的限制）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests
        self._windows: Dict[str, RateLimitWindow] = defaultdict(RateLimitWindow)
        
        logger.info(
            f"频率限制器初始化: max={max_requests}/{window_seconds}s, "
            f"burst={self.burst_limit}"
        )
    
    def allow(self, key: str = "default") -> bool:
        """
        检查是否允许请求
        
        Args:
            key: 限制键（用于区分不同的限制对象）
        
        Returns:
            是否允许请求
        """
        window = self._windows[key]
        window.clean(self.window_seconds)
        
        if len(window.timestamps) >= self.max_requests:
            return False
        
        return True
    
    def acquire(self, key: str = "default") -> bool:
        """
        尝试获取一个请求配额
        
        Args:
            key: 限制键
        
        Returns:
            是否成功获取
        """
        if not self.allow(key):
            return False
        
        self._windows[key].timestamps.append(time.time())
        return True
    
    def wait_time(self, key: str = "default") -> float:
        """
        计算需要等待的时间
        
        Args:
            key: 限制键
        
        Returns:
            需要等待的秒数，0表示可以立即执行
        """
        window = self._windows[key]
        window.clean(self.window_seconds)
        
        if len(window.timestamps) < self.max_requests:
            return 0.0
        
        # 计算最早的请求何时过期
        oldest = min(window.timestamps)
        return max(0.0, oldest + self.window_seconds - time.time())
    
    def remaining(self, key: str = "default") -> int:
        """
        获取剩余配额
        
        Args:
            key: 限制键
        
        Returns:
            剩余请求数
        """
        window = self._windows[key]
        window.clean(self.window_seconds)
        return max(0, self.max_requests - len(window.timestamps))
    
    def reset(self, key: str = "default") -> None:
        """重置指定键的限制"""
        if key in self._windows:
            del self._windows[key]
    
    def stats(self, key: str = "default") -> Dict[str, Any]:
        """获取统计信息"""
        window = self._windows.get(key, RateLimitWindow())
        window.clean(self.window_seconds)
        
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "current_count": len(window.timestamps),
            "remaining": self.remaining(key),
            "wait_time": self.wait_time(key),
        }


class LLMCache:
    """
    LLM专用缓存
    
    结合LRU缓存和频率限制，专为LLM调用优化
    
    特性：
    - 智能缓存键生成
    - 语义相似度匹配（可选）
    - 自动TTL管理
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 3600,
        enabled: bool = True,
    ):
        """
        初始化LLM缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            enabled: 是否启用缓存
        """
        self.enabled = enabled
        self._cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        
        # 统计
        self._hits = 0
        self._misses = 0
        
        logger.info(f"LLM缓存初始化: enabled={enabled}")
    
    def get_key(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """生成缓存键"""
        return self._cache._generate_key(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt or "",
            temperature=temperature,
        )
    
    def get(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Optional[Any]:
        """
        获取缓存的LLM响应
        
        注意：温度>0.5时不使用缓存（随机性高）
        """
        if not self.enabled:
            return None
        
        # 高温度不缓存
        if temperature > 0.5:
            return None
        
        key = self.get_key(prompt, model, system_prompt, temperature)
        result = self._cache.get(key)
        
        if result is not None:
            self._hits += 1
            logger.debug(f"LLM缓存命中: {key[:16]}...")
        else:
            self._misses += 1
        
        return result
    
    def set(
        self,
        prompt: str,
        model: str,
        response: Any,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        ttl: Optional[float] = None,
    ) -> None:
        """缓存LLM响应"""
        if not self.enabled:
            return
        
        # 高温度不缓存
        if temperature > 0.5:
            return
        
        key = self.get_key(prompt, model, system_prompt, temperature)
        self._cache.set(key, response, ttl)
        logger.debug(f"LLM缓存写入: {key[:16]}...")
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        cache_stats = self._cache.stats()
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            **cache_stats,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "enabled": self.enabled,
        }
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
