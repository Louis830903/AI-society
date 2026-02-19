"""
反应决策模块
===========
智能体的实时反应与重规划能力

参考：斯坦福 Generative Agents 论文 (arxiv:2304.03442)

核心流程：
1. 感知环境
2. 判断是否需要反应
3. 生成反应行动
4. 可能触发重规划
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from app.agents.models import Agent
    from app.agents.perception import Perception
    from app.agents.planning import PlanBlock


class ReactionType(str, Enum):
    """反应类型"""
    CONTINUE = "continue"       # 继续当前活动
    INTERRUPT = "interrupt"     # 中断当前活动去处理
    NOTE = "note"              # 记住但继续（记录到记忆但不中断）


@dataclass
class ReactionDecision:
    """反应决策结果"""
    should_react: bool
    reaction_type: ReactionType
    reaction: Optional[str] = None  # 反应内容/行动
    reason: str = ""               # 决策理由


def _extract_json_from_response(response: str) -> Optional[dict]:
    """从LLM响应中提取JSON"""
    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试从Markdown代码块提取
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    matches = re.findall(code_block_pattern, response)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # 尝试找到JSON对象
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, response)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


async def should_react(
    agent: "Agent",
    perception: "Perception",
    current_plan: Optional["PlanBlock"] = None,
) -> ReactionDecision:
    """
    判断智能体是否应该对观察到的情况做出反应
    
    Args:
        agent: 智能体对象
        perception: 感知结果
        current_plan: 当前计划块（可选）
    
    Returns:
        反应决策
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    
    # 如果感知为空，直接继续
    if perception.is_empty():
        return ReactionDecision(
            should_react=False,
            reaction_type=ReactionType.CONTINUE,
            reason="没有需要反应的事情",
        )
    
    # 如果有人在等待回应，优先处理
    if perception.being_addressed:
        return ReactionDecision(
            should_react=True,
            reaction_type=ReactionType.INTERRUPT,
            reaction=f"回应{perception.addressed_by}",
            reason=f"{perception.addressed_by}在等待回应",
        )
    
    # 获取当前活动描述
    current_activity = "空闲"
    if agent.current_action and agent.current_action.thinking:
        current_activity = agent.current_action.thinking
    elif agent.current_action:
        current_activity = agent.current_action.type.value
    
    # 获取当前计划描述
    plan_text = "无特定计划"
    if current_plan:
        plan_text = f"{current_plan.start_time}-{current_plan.end_time}: {current_plan.activity}"
    elif agent.daily_plan:
        from datetime import datetime
        current_block = agent.daily_plan.get_current_block(datetime.now())
        if current_block:
            plan_text = f"{current_block.start_time}-{current_block.end_time}: {current_block.activity}"
    
    # 构建提示词
    prompt = PromptTemplates.render(
        "SHOULD_REACT",
        agent_name=agent.name,
        current_activity=current_activity,
        perception=perception.to_description(),
        current_plan=plan_text,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=agent.model_name,
            temperature=0.5,
            max_tokens=300,
        )
        
        json_data = _extract_json_from_response(response.content)
        
        if json_data:
            should_react_value = json_data.get("should_react", False)
            
            # 解析反应类型
            reaction_type_str = json_data.get("reaction_type", "continue").lower()
            if reaction_type_str == "interrupt":
                reaction_type = ReactionType.INTERRUPT
            elif reaction_type_str == "note":
                reaction_type = ReactionType.NOTE
            else:
                reaction_type = ReactionType.CONTINUE
            
            decision = ReactionDecision(
                should_react=should_react_value,
                reaction_type=reaction_type,
                reaction=json_data.get("reaction"),
                reason=json_data.get("reason", ""),
            )
            
            logger.debug(
                f"[{agent.name}] 反应决策: should_react={decision.should_react}, "
                f"type={decision.reaction_type.value}, reason={decision.reason}"
            )
            
            return decision
        
        logger.warning(f"[{agent.name}] 无法解析反应决策响应")
        
    except Exception as e:
        logger.error(f"[{agent.name}] 反应决策失败: {e}")
    
    # 默认继续当前活动
    return ReactionDecision(
        should_react=False,
        reaction_type=ReactionType.CONTINUE,
        reason="决策过程出错，默认继续",
    )


async def execute_reaction(
    agent: "Agent",
    decision: ReactionDecision,
) -> bool:
    """
    执行反应决策
    
    Args:
        agent: 智能体对象
        decision: 反应决策
    
    Returns:
        是否成功执行
    """
    from app.agents.memory import MemoryType
    from app.agents.planning import replan_from_now
    from datetime import datetime
    
    if not decision.should_react:
        return True
    
    if decision.reaction_type == ReactionType.NOTE:
        # 只记录到记忆，不中断当前活动
        if decision.reaction:
            agent.add_memory(
                f"注意到：{decision.reaction}",
                MemoryType.OBSERVATION,
                importance=4.0,
            )
        logger.info(f"[{agent.name}] 记录观察但继续当前活动")
        return True
    
    elif decision.reaction_type == ReactionType.INTERRUPT:
        # 中断当前活动
        if agent.current_action:
            # 记录中断
            agent.add_memory(
                f"中断了{agent.current_action.type.value}：{decision.reason}",
                MemoryType.EVENT,
                importance=5.0,
            )
        
        # 记录反应
        if decision.reaction:
            agent.add_memory(
                f"反应：{decision.reaction}",
                MemoryType.EVENT,
                importance=5.0,
            )
        
        # 触发重规划
        if agent.daily_plan and decision.reaction:
            new_blocks = await replan_from_now(
                agent,
                datetime.now(),
                decision.reaction,
            )
            if new_blocks:
                # 更新日计划的剩余部分
                agent.daily_plan.broad_strokes = new_blocks
        
        logger.info(f"[{agent.name}] 中断活动并反应: {decision.reaction}")
        return True
    
    return True


class ReactAndReplanEngine:
    """
    反应与重规划引擎
    
    集成感知、反应决策和重规划的完整流程
    """
    
    async def tick(self, agent: "Agent") -> Optional[ReactionDecision]:
        """
        执行一个感知-反应周期
        
        Args:
            agent: 智能体对象
        
        Returns:
            如果执行了反应，返回决策结果
        """
        from app.agents.perception import perceive_environment
        
        # 1. 感知环境
        perception = await perceive_environment(agent)
        
        # 2. 如果感知为空，跳过
        if perception.is_empty():
            return None
        
        # 3. 获取当前计划块
        current_plan = None
        if agent.daily_plan:
            from datetime import datetime
            current_plan = agent.daily_plan.get_current_block(datetime.now())
        
        # 4. 决定是否反应
        decision = await should_react(agent, perception, current_plan)
        
        # 5. 执行反应
        if decision.should_react:
            await execute_reaction(agent, decision)
        
        return decision


# 全局引擎实例
react_replan_engine = ReactAndReplanEngine()


async def maybe_react(agent: "Agent") -> Optional[ReactionDecision]:
    """
    检查并可能执行反应的便捷函数
    
    Args:
        agent: 智能体对象
    
    Returns:
        如果执行了反应，返回决策结果
    """
    return await react_replan_engine.tick(agent)
