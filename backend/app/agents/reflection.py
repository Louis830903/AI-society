"""
反思机制模块
===========
智能体定期总结经历，形成高层次认知

参考：斯坦福 Generative Agents 论文 (arxiv:2304.03442)

核心流程：
1. 检查累积重要性是否超过阈值
2. 从近期记忆中生成高层次问题
3. 检索相关记忆回答问题
4. 生成洞察并存入记忆流
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from loguru import logger

if TYPE_CHECKING:
    from app.agents.models import Agent


@dataclass
class ReflectionResult:
    """反思结果"""
    questions: List[str]  # 生成的高层次问题
    insights: List[str]   # 生成的洞察
    memories_created: int  # 创建的反思记忆数量


class ReflectionEngine:
    """
    反思引擎
    
    负责智能体的反思过程：
    - 检测是否需要反思
    - 生成高层次问题
    - 检索相关记忆
    - 生成洞察
    """
    
    def __init__(self, importance_threshold: float = 150.0):
        """
        初始化反思引擎
        
        Args:
            importance_threshold: 触发反思的累积重要性阈值
        """
        self.importance_threshold = importance_threshold
    
    def should_reflect(self, agent: "Agent") -> bool:
        """
        检查智能体是否应该进行反思
        
        Args:
            agent: 智能体对象
        
        Returns:
            是否应该反思
        """
        accumulated = agent.memory.accumulated_importance
        return accumulated >= self.importance_threshold
    
    async def generate_questions(
        self,
        agent: "Agent",
        num_questions: int = 3,
    ) -> List[str]:
        """
        从近期记忆中生成高层次问题
        
        Args:
            agent: 智能体对象
            num_questions: 生成问题数量
        
        Returns:
            问题列表
        """
        from app.llm import llm_router
        from app.llm.prompts import PromptTemplates
        
        # 获取近期记忆
        recent_memories = agent.memory.retrieve_recent(limit=100)
        if not recent_memories:
            return []
        
        # 构建记忆文本
        memories_text = "\n".join([
            f"- {m.content}" for m in recent_memories[:50]
        ])
        
        # 生成问题
        prompt = PromptTemplates.render(
            "REFLECTION_QUESTIONS",
            agent_name=agent.name,
            memories=memories_text,
        )
        
        try:
            response = await llm_router.generate(
                prompt=prompt,
                model_name=agent.model_name,
                temperature=0.7,
                max_tokens=200,
            )
            
            # 解析问题（每行一个）
            questions = [
                line.strip()
                for line in response.content.strip().split("\n")
                if line.strip() and "?" in line
            ]
            
            logger.debug(f"[{agent.name}] 生成反思问题: {questions}")
            return questions[:num_questions]
            
        except Exception as e:
            logger.error(f"[{agent.name}] 生成反思问题失败: {e}")
            return []
    
    async def generate_insight(
        self,
        agent: "Agent",
        question: str,
    ) -> Optional[str]:
        """
        针对一个问题生成洞察
        
        Args:
            agent: 智能体对象
            question: 需要回答的问题
        
        Returns:
            洞察文本，失败返回None
        """
        from app.llm import llm_router
        from app.llm.prompts import PromptTemplates
        
        # 检索与问题相关的记忆
        relevant_results = agent.memory.retrieve_relevant(question, limit=10)
        if not relevant_results:
            return None
        
        # 构建相关记忆文本
        relevant_text = "\n".join([
            f"- {m.content}" for m, _ in relevant_results
        ])
        
        # 生成洞察
        prompt = PromptTemplates.render(
            "REFLECTION_INSIGHTS",
            agent_name=agent.name,
            question=question,
            relevant_memories=relevant_text,
        )
        
        try:
            response = await llm_router.generate(
                prompt=prompt,
                model_name=agent.model_name,
                temperature=0.7,
                max_tokens=150,
            )
            
            insight = response.content.strip()
            logger.debug(f"[{agent.name}] 生成洞察: {insight}")
            return insight
            
        except Exception as e:
            logger.error(f"[{agent.name}] 生成洞察失败: {e}")
            return None
    
    async def run_reflection(self, agent: "Agent") -> ReflectionResult:
        """
        执行完整的反思流程
        
        Args:
            agent: 智能体对象
        
        Returns:
            反思结果
        """
        from app.agents.memory import MemoryType
        
        logger.info(f"[{agent.name}] 开始反思 (累积重要性: {agent.memory.accumulated_importance:.1f})")
        
        # 1. 生成问题
        questions = await self.generate_questions(agent)
        if not questions:
            logger.warning(f"[{agent.name}] 反思失败：无法生成问题")
            return ReflectionResult(questions=[], insights=[], memories_created=0)
        
        # 2. 为每个问题生成洞察
        insights = []
        memories_created = 0
        
        for question in questions:
            insight = await self.generate_insight(agent, question)
            if insight:
                insights.append(insight)
                
                # 3. 将洞察存入记忆流（作为反思类型记忆）
                agent.memory.create_and_add(
                    content=insight,
                    memory_type=MemoryType.REFLECTION,
                    importance=8.0,  # 反思记忆默认高重要性
                )
                memories_created += 1
        
        # 4. 重置累积重要性
        old_accumulated = agent.memory.reset_accumulated_importance()
        
        logger.info(
            f"[{agent.name}] 反思完成: {len(questions)}个问题, "
            f"{len(insights)}个洞察, 重置累积重要性 {old_accumulated:.1f} -> 0"
        )
        
        return ReflectionResult(
            questions=questions,
            insights=insights,
            memories_created=memories_created,
        )


# 全局反思引擎实例
reflection_engine = ReflectionEngine()


async def maybe_reflect(agent: "Agent") -> Optional[ReflectionResult]:
    """
    检查并可能执行反思的便捷函数
    
    Args:
        agent: 智能体对象
    
    Returns:
        如果执行了反思返回结果，否则返回None
    """
    if reflection_engine.should_reflect(agent):
        return await reflection_engine.run_reflection(agent)
    return None
