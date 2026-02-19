"""
记忆系统
=======
智能体的短期和长期记忆管理

记忆类型：
- 事件记忆：发生的具体事件
- 对话记忆：与他人的对话
- 观察记忆：观察到的环境信息
- 情感记忆：情感体验
- 社交记忆：关于他人的印象
- 反思记忆：高层次的自我认知（Phase 6新增）

记忆特性：
- 重要性评分：决定记忆保留优先级（支持LLM动态评分）
- 时间衰减：旧记忆逐渐淡化
- 关联性：相关记忆可以互相增强
- 累积追踪：累积重要性触发反思（Phase 6新增）
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4
import random

from loguru import logger


# ===================
# Phase 6: 记忆重要性评分
# ===================

async def rate_importance(content: str, agent_name: str = "") -> int:
    """
    使用LLM评估记忆内容的重要性
    
    Args:
        content: 记忆内容
        agent_name: 智能体名称（可选，用于上下文）
    
    Returns:
        1-10的重要性评分
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    from app.core.config import settings
    
    prompt = PromptTemplates.render("MEMORY_IMPORTANCE_RATING", content=content)
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=settings.importance_rating_model,
            temperature=0.3,
            max_tokens=10,
        )
        
        # 从响应中提取数字
        match = re.search(r'\b([1-9]|10)\b', response.content)
        if match:
            rating = int(match.group(1))
            logger.debug(f"记忆重要性评分: {rating} - {content[:30]}...")
            return rating
        
        # 默认返回5
        logger.warning(f"无法解析重要性评分响应: {response.content}")
        return 5
        
    except Exception as e:
        logger.error(f"记忆重要性评分失败: {e}")
        return 5  # 失败时返回中等重要性


class MemoryType(str, Enum):
    """记忆类型枚举"""
    EVENT = "event"  # 事件记忆
    CONVERSATION = "conversation"  # 对话记忆
    OBSERVATION = "observation"  # 观察记忆
    EMOTION = "emotion"  # 情感记忆
    SOCIAL = "social"  # 社交记忆（关于他人）
    REFLECTION = "reflection"  # 反思记忆


@dataclass
class Memory:
    """
    单条记忆
    
    Attributes:
        id: 唯一标识
        type: 记忆类型
        content: 记忆内容（自然语言描述）
        importance: 重要性 (0-10)
        timestamp: 记忆形成的游戏时间
        created_at: 实际创建时间
        related_agents: 相关的智能体ID列表
        location: 发生地点
        emotion: 当时的情绪
        keywords: 关键词（用于检索）
        access_count: 被访问次数
        last_accessed: 最后访问时间
    """
    
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    type: MemoryType = MemoryType.EVENT
    content: str = ""
    importance: float = 5.0  # 0-10
    timestamp: Optional[datetime] = None  # 游戏内时间
    created_at: datetime = field(default_factory=datetime.now)
    
    # 关联信息
    related_agents: List[str] = field(default_factory=list)
    location: Optional[str] = None
    emotion: Optional[str] = None
    keywords: Set[str] = field(default_factory=set)
    
    # 访问追踪
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 自动提取关键词
        if not self.keywords:
            self._extract_keywords()
    
    def _extract_keywords(self) -> None:
        """从内容中提取关键词"""
        # 简单的关键词提取：分词后取长度>=2的词
        words = self.content.replace("，", " ").replace("。", " ").split()
        self.keywords = {w for w in words if len(w) >= 2}
    
    def access(self) -> None:
        """记录一次访问"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def get_recency_score(self) -> float:
        """
        计算时效性分数
        
        越新的记忆分数越高
        Returns:
            0-1 之间的值
        """
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        # 指数衰减：24小时后降到约0.37
        return max(0.01, min(1.0, 2.71828 ** (-age_hours / 24)))
    
    def get_relevance_score(self, query_keywords: Set[str]) -> float:
        """
        计算与查询的相关性分数
        
        Args:
            query_keywords: 查询关键词集合
        
        Returns:
            0-1 之间的值
        """
        if not query_keywords or not self.keywords:
            return 0.0
        
        intersection = len(self.keywords & query_keywords)
        union = len(self.keywords | query_keywords)
        
        return intersection / union if union > 0 else 0.0
    
    def get_retrieval_score(
        self,
        query_keywords: Optional[Set[str]] = None,
        importance_weight: float = 0.4,
        recency_weight: float = 0.3,
        relevance_weight: float = 0.3,
    ) -> float:
        """
        计算综合检索分数
        
        Args:
            query_keywords: 查询关键词
            importance_weight: 重要性权重
            recency_weight: 时效性权重
            relevance_weight: 相关性权重
        
        Returns:
            综合分数
        """
        # 归一化重要性到0-1
        importance_score = self.importance / 10.0
        recency_score = self.get_recency_score()
        
        if query_keywords:
            relevance_score = self.get_relevance_score(query_keywords)
        else:
            relevance_score = 0.5  # 无查询时给默认值
        
        return (
            importance_score * importance_weight +
            recency_score * recency_weight +
            relevance_score * relevance_weight
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat(),
            "related_agents": self.related_agents,
            "location": self.location,
            "emotion": self.emotion,
            "keywords": list(self.keywords),
            "access_count": self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """从字典创建"""
        data = data.copy()
        if "type" in data:
            data["type"] = MemoryType(data["type"])
        if "timestamp" in data and data["timestamp"]:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "keywords" in data:
            data["keywords"] = set(data["keywords"])
        return cls(**data)


class MemoryManager:
    """
    记忆管理器
    
    管理单个智能体的所有记忆
    
    功能：
    - 添加新记忆
    - 检索相关记忆
    - 记忆衰减与遗忘
    - 记忆整合（反思）
    - 累积重要性追踪（Phase 6新增）
    """
    
    def __init__(
        self,
        max_memories: int = 200,
        short_term_limit: int = 20,
        importance_threshold: float = 3.0,
    ):
        """
        初始化记忆管理器
        
        Args:
            max_memories: 最大记忆数量
            short_term_limit: 短期记忆容量
            importance_threshold: 进入长期记忆的重要性阈值
        """
        self.max_memories = max_memories
        self.short_term_limit = short_term_limit
        self.importance_threshold = importance_threshold
        
        self._memories: Dict[str, Memory] = {}  # id -> Memory
        self._by_type: Dict[MemoryType, List[str]] = {t: [] for t in MemoryType}
        self._by_agent: Dict[str, List[str]] = {}  # agent_id -> memory_ids
        
        # Phase 6: 累积重要性追踪（用于触发反思）
        self.accumulated_importance: float = 0.0
        self.last_reflection_time: Optional[datetime] = None
    
    def add(self, memory: Memory) -> str:
        """
        添加新记忆
        
        Args:
            memory: 记忆对象
        
        Returns:
            记忆ID
        """
        # 检查容量
        if len(self._memories) >= self.max_memories:
            self._forget_least_important()
        
        self._memories[memory.id] = memory
        self._by_type[memory.type].append(memory.id)
        
        # 索引相关智能体
        for agent_id in memory.related_agents:
            if agent_id not in self._by_agent:
                self._by_agent[agent_id] = []
            self._by_agent[agent_id].append(memory.id)
        
        # Phase 6: 累积重要性
        self.accumulated_importance += memory.importance
        
        logger.debug(f"添加记忆: type={memory.type.value}, importance={memory.importance}, accumulated={self.accumulated_importance:.1f}")
        
        return memory.id
    
    def reset_accumulated_importance(self) -> float:
        """
        重置累积重要性（反思后调用）
        
        Returns:
            重置前的累积值
        """
        old_value = self.accumulated_importance
        self.accumulated_importance = 0.0
        self.last_reflection_time = datetime.now()
        return old_value
    
    def create_and_add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EVENT,
        importance: float = 5.0,
        related_agents: Optional[List[str]] = None,
        location: Optional[str] = None,
        emotion: Optional[str] = None,
        game_time: Optional[datetime] = None,
    ) -> Memory:
        """
        创建并添加记忆的便捷方法
        
        Returns:
            创建的记忆对象
        """
        memory = Memory(
            type=memory_type,
            content=content,
            importance=importance,
            related_agents=related_agents or [],
            location=location,
            emotion=emotion,
            timestamp=game_time,
        )
        self.add(memory)
        return memory
    
    def get(self, memory_id: str) -> Optional[Memory]:
        """获取指定记忆"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access()
        return memory
    
    def remove(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id not in self._memories:
            return False
        
        memory = self._memories[memory_id]
        
        # 从索引中移除
        if memory_id in self._by_type[memory.type]:
            self._by_type[memory.type].remove(memory_id)
        
        for agent_id in memory.related_agents:
            if agent_id in self._by_agent and memory_id in self._by_agent[agent_id]:
                self._by_agent[agent_id].remove(memory_id)
        
        del self._memories[memory_id]
        return True
    
    def _forget_least_important(self) -> None:
        """遗忘最不重要的记忆"""
        if not self._memories:
            return
        
        # 按检索分数排序，移除最低的
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda m: m.get_retrieval_score(),
        )
        
        # 移除最不重要的10%
        to_remove = max(1, len(sorted_memories) // 10)
        for memory in sorted_memories[:to_remove]:
            self.remove(memory.id)
            logger.debug(f"遗忘记忆: {memory.id}")
    
    # ===================
    # 检索方法
    # ===================
    
    def retrieve_recent(self, limit: int = 10) -> List[Memory]:
        """
        获取最近的记忆
        
        Args:
            limit: 返回数量
        
        Returns:
            按时间倒序排列的记忆列表
        """
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda m: m.created_at,
            reverse=True,
        )
        return sorted_memories[:limit]
    
    def retrieve_by_type(
        self,
        memory_type: MemoryType,
        limit: int = 20,
    ) -> List[Memory]:
        """按类型检索记忆"""
        memory_ids = self._by_type.get(memory_type, [])
        memories = [self._memories[mid] for mid in memory_ids if mid in self._memories]
        
        # 按重要性排序
        memories.sort(key=lambda m: m.importance, reverse=True)
        return memories[:limit]
    
    def retrieve_by_agent(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> List[Memory]:
        """检索关于某个智能体的记忆"""
        memory_ids = self._by_agent.get(agent_id, [])
        memories = [self._memories[mid] for mid in memory_ids if mid in self._memories]
        
        # 按时间倒序
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]
    
    def retrieve_relevant(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.1,
    ) -> List[Tuple[Memory, float]]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            limit: 返回数量
            min_score: 最小分数阈值
        
        Returns:
            [(记忆, 分数)] 列表
        """
        # 提取查询关键词
        query_keywords = set(query.replace("，", " ").replace("。", " ").split())
        query_keywords = {w for w in query_keywords if len(w) >= 2}
        
        # 计算每个记忆的相关性
        scored_memories = []
        for memory in self._memories.values():
            score = memory.get_retrieval_score(query_keywords)
            if score >= min_score:
                scored_memories.append((memory, score))
                memory.access()
        
        # 按分数排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        return scored_memories[:limit]
    
    def get_context_for_llm(self, limit: int = 10) -> str:
        """
        生成用于LLM提示词的记忆上下文
        
        Returns:
            格式化的记忆描述
        """
        recent = self.retrieve_recent(limit)
        
        if not recent:
            return "（暂无近期记忆）"
        
        lines = []
        for memory in recent:
            time_str = memory.timestamp.strftime("%H:%M") if memory.timestamp else "某时"
            lines.append(f"- [{time_str}] {memory.content}")
        
        return "\n".join(lines)
    
    def get_social_context(self, agent_id: str) -> str:
        """
        获取关于某人的社交上下文
        
        Args:
            agent_id: 目标智能体ID
        
        Returns:
            关于此人的记忆摘要
        """
        memories = self.retrieve_by_agent(agent_id, limit=5)
        
        if not memories:
            return "（初次见面，没有关于此人的记忆）"
        
        lines = []
        for memory in memories:
            lines.append(f"- {memory.content}")
        
        return "\n".join(lines)
    
    # ===================
    # 统计与管理
    # ===================
    
    def count(self) -> int:
        """获取记忆总数"""
        return len(self._memories)
    
    def count_by_type(self) -> Dict[str, int]:
        """按类型统计记忆数量"""
        return {
            t.value: len(ids)
            for t, ids in self._by_type.items()
        }
    
    def get_stats(self) -> dict:
        """获取记忆统计"""
        return {
            "total": self.count(),
            "max": self.max_memories,
            "by_type": self.count_by_type(),
            "avg_importance": (
                sum(m.importance for m in self._memories.values()) / len(self._memories)
                if self._memories else 0
            ),
            "accumulated_importance": self.accumulated_importance,
        }
    
    def clear(self) -> None:
        """清空所有记忆"""
        self._memories.clear()
        self._by_type = {t: [] for t in MemoryType}
        self._by_agent.clear()
        self.accumulated_importance = 0.0
    
    def to_list(self) -> List[dict]:
        """导出所有记忆"""
        return [m.to_dict() for m in self._memories.values()]
    
    def load_from_list(self, data: List[dict]) -> int:
        """
        从列表加载记忆
        
        Returns:
            加载的记忆数量
        """
        count = 0
        for item in data:
            try:
                memory = Memory.from_dict(item)
                self.add(memory)
                count += 1
            except Exception as e:
                logger.warning(f"加载记忆失败: {e}")
        return count
