"""
行为决策系统
===========
使用LLM为智能体做行为决策

核心流程（Phase 6 增强）：
1. 感知环境 perceive_environment()
2. 检查是否需要反应 should_react()
3. 如果 interrupt: 执行反应并重规划
4. 检查是否需要反思 maybe_reflect()
5. 收集智能体上下文（状态、需求、记忆、环境）
6. 构建提示词
7. 调用LLM生成决策
8. 解析并执行决策
9. 记录活动日志（Phase 7）
"""

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.agents.models import Agent, AgentState, ActionType, Position
from app.agents.memory import MemoryType
from app.core.config import settings
from app.core.events import event_bus
from app.core.world import world_clock
from app.llm import llm_router
from app.llm.prompts import PromptTemplates

# Phase 6: 导入感知、反应、反思模块
from app.agents.perception import perceive_environment
from app.agents.reaction import should_react, execute_reaction, ReactionType
from app.agents.reflection import maybe_reflect
from app.agents.planning import generate_daily_plan


@dataclass
class Decision:
    """LLM决策结果"""
    thinking: str  # 决策思考过程
    action: ActionType  # 行动类型
    target: Optional[str]  # 行动目标
    reason: str  # 决策理由
    raw_response: str = ""  # 原始LLM响应
    
    @classmethod
    def from_json(cls, data: dict, raw: str = "") -> "Decision":
        """从JSON解析决策"""
        action_str = data.get("action", "IDLE").upper()
        
        # 映射行动类型
        action_mapping = {
            "MOVE": ActionType.MOVE,
            "WORK": ActionType.WORK,
            "EAT": ActionType.EAT,
            "SLEEP": ActionType.SLEEP,
            "REST": ActionType.REST,
            "CHAT": ActionType.CHAT,
            "SHOP": ActionType.SHOP,
            "EXERCISE": ActionType.EXERCISE,
            "ENTERTAINMENT": ActionType.ENTERTAINMENT,
            "IDLE": ActionType.IDLE,
            "WAIT": ActionType.WAITING,
        }
        
        action = action_mapping.get(action_str, ActionType.IDLE)
        
        return cls(
            thinking=data.get("thinking", ""),
            action=action,
            target=data.get("target"),
            reason=data.get("reason", ""),
            raw_response=raw,
        )


def extract_json_from_response(response: str) -> Optional[dict]:
    """
    从LLM响应中提取JSON
    
    支持多种格式：
    - 纯JSON
    - Markdown代码块包裹的JSON
    - 混合文本中的JSON
    """
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
    json_pattern = r'\{[\s\S]*?\}'
    matches = re.findall(json_pattern, response)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


async def make_decision(
    agent: Agent,
    surroundings: str = "",
    retry_count: int = 2,
) -> Optional[Decision]:
    """
    为智能体生成决策
    
    Args:
        agent: 智能体对象
        surroundings: 周围环境描述
        retry_count: 重试次数
    
    Returns:
        Decision对象，失败返回None
    """
    from app.core.locations import location_manager
    
    # 获取游戏时间
    game_time = world_clock.get_time()
    time_str = f"{game_time.hour:02d}:{game_time.minute:02d}"
    
    # 获取可用地点列表
    available_locations = []
    for loc in location_manager.locations.values():
        loc_info = f"- {loc.name}（{loc.type.value}）"
        if loc.is_open_at(game_time.hour, game_time.weekday()):
            available_locations.append(loc_info)
        else:
            available_locations.append(f"- {loc.name}（{loc.type.value}，当前关闭）")
    locations_str = "\n".join(available_locations) if available_locations else "暂无可用地点"
    
    # 构建提示词
    context = agent.get_llm_context()
    context["current_time"] = time_str
    context["surroundings"] = surroundings or "周围没有什么特别的"
    context["available_locations"] = locations_str
    
    prompt = PromptTemplates.render("AGENT_DECISION", **context)
    
    for attempt in range(retry_count + 1):
        try:
            # 调用LLM
            response = await llm_router.generate(
                prompt=prompt,
                model_name=agent.model_name,
                temperature=0.7,
                max_tokens=500,
            )
            
            # 解析响应
            json_data = extract_json_from_response(response.content)
            
            if json_data:
                decision = Decision.from_json(json_data, response.content)
                
                logger.debug(
                    f"[{agent.name}] 决策: {decision.action.value} -> {decision.target} "
                    f"({decision.reason})"
                )
                
                return decision
            else:
                logger.warning(f"[{agent.name}] 无法解析LLM响应: {response.content[:100]}")
                
        except Exception as e:
            logger.error(f"[{agent.name}] 决策失败 (尝试 {attempt + 1}): {e}")
    
    return None


async def execute_decision(
    agent: Agent,
    decision: Decision,
) -> bool:
    """
    执行决策
    
    Args:
        agent: 智能体
        decision: 决策
    
    Returns:
        是否成功执行
    """
    from app.agents.manager import agent_manager
    from app.core.locations import location_manager
    
    action = decision.action
    target = decision.target
    
    # 更新智能体的思考
    agent.current_action.thinking = decision.thinking
    
    # 根据行动类型执行
    if action == ActionType.MOVE:
        # 移动到目标地点
        location = location_manager.get_by_name(target) if target else None
        if location:
            success = agent_manager.move_agent(agent.id, location.id)
            if success:
                agent.set_action(
                    ActionType.MOVE,
                    target=location.id,
                    target_name=location.name,
                    duration_minutes=5,  # 移动时间
                    thinking=decision.thinking,
                )
                agent.add_memory(
                    f"前往{location.name}",
                    MemoryType.EVENT,
                    importance=2.0,
                )
                return True
        
        logger.warning(f"[{agent.name}] 无法移动到: {target}")
        return False
    
    elif action == ActionType.WORK:
        # 工作（需要在工作地点）
        duration = 60  # 工作1小时（游戏时间）
        agent.set_action(
            ActionType.WORK,
            target=agent.position.location_id,
            target_name=agent.position.location_name,
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        agent.add_memory(
            f"在{agent.position.location_name or '这里'}工作",
            MemoryType.EVENT,
            importance=4.0,
        )
        return True
    
    elif action == ActionType.EAT:
        duration = 30  # 吃饭30分钟
        agent.set_action(
            ActionType.EAT,
            target_name=target or "吃东西",
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        # 消费
        agent.spend_money(settings.daily_expense_base / 3, "吃饭")
        agent.add_memory(
            f"吃了{target or '一顿饭'}",
            MemoryType.EVENT,
            importance=2.0,
        )
        return True
    
    elif action == ActionType.SLEEP:
        duration = 480  # 睡眠8小时
        agent.set_action(
            ActionType.SLEEP,
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        agent.add_memory(
            "去睡觉了",
            MemoryType.EVENT,
            importance=2.0,
        )
        return True
    
    elif action == ActionType.REST:
        duration = 30
        agent.set_action(
            ActionType.REST,
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        return True
    
    elif action == ActionType.CHAT:
        # 发起对话（需要对话系统配合）
        agent.set_action(
            ActionType.CHAT,
            target=target,
            target_name=target,
            duration_minutes=15,
            thinking=decision.thinking,
        )
        
        # 发布聊天请求事件（由对话事件处理器处理）
        event_bus.publish_sync("chat.requested", {
            "initiator_id": agent.id,
            "target_name": target,
        })
        
        return True
    
    elif action == ActionType.SHOP:
        duration = 30
        agent.set_action(
            ActionType.SHOP,
            target_name=target,
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        # 随机消费
        amount = settings.daily_expense_base * 0.2
        agent.spend_money(amount, f"购物：{target or '日用品'}")
        agent.add_memory(
            f"买了{target or '一些东西'}",
            MemoryType.EVENT,
            importance=3.0,
        )
        return True
    
    elif action == ActionType.ENTERTAINMENT:
        duration = 60
        agent.set_action(
            ActionType.ENTERTAINMENT,
            target_name=target,
            duration_minutes=duration,
            thinking=decision.thinking,
        )
        agent.add_memory(
            f"享受了{target or '娱乐活动'}",
            MemoryType.EVENT,
            importance=3.0,
        )
        return True
    
    else:
        # IDLE或其他
        agent.set_action(
            ActionType.IDLE,
            duration_minutes=10,
            thinking=decision.thinking,
        )
        return True
    
    return False


class DecisionScheduler:
    """
    决策调度器
    
    按顺序为智能体安排决策
    
    Phase 6 增强：
    - 每日计划触发（早上6点）
    - 感知-反应-反思循环
    """
    
    def __init__(
        self,
        decision_interval: float = 6.0,
        batch_size: int = 5,
    ):
        """
        初始化调度器
        
        Args:
            decision_interval: 每批次间隔（现实秒）
            batch_size: 每批处理的智能体数量
        """
        self.decision_interval = decision_interval
        self.batch_size = batch_size
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        # Phase 6: 追踪上一次检查日计划的游戏日期
        self._last_plan_date: Optional[date] = None
    
    async def start(self) -> None:
        """启动调度器"""
        if self._is_running:
            return
        
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("决策调度器已启动")
    
    def stop(self) -> None:
        """停止调度器"""
        self._is_running = False
        if self._task:
            self._task.cancel()
        logger.info("决策调度器已停止")
    
    async def _run_loop(self) -> None:
        """调度循环"""
        from app.agents.manager import agent_manager
        
        logger.info("决策调度循环开始运行")
        
        while self._is_running:
            try:
                # =====================
                # Phase 6: 检查每日计划触发
                # =====================
                await self._check_daily_plan_trigger()
                
                # 获取需要决策的智能体
                agents = agent_manager.get_agents_needing_decision()
                logger.debug(f"本轮需要决策的智能体: {len(agents)} 个")
                
                if agents:
                    # 分批处理
                    for i in range(0, len(agents), self.batch_size):
                        batch = agents[i:i + self.batch_size]
                        
                        # 并发处理这批智能体
                        tasks = []
                        for agent in batch:
                            ctx = agent_manager.get_nearby_context(agent.id)
                            tasks.append(
                                self._process_agent(agent, ctx.to_description())
                            )
                        
                        await asyncio.gather(*tasks, return_exceptions=True)
                
                # 等待下一个周期
                await asyncio.sleep(self.decision_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"决策调度器错误: {e}")
                await asyncio.sleep(1)
    
    async def _check_daily_plan_trigger(self) -> None:
        """
        检查是否需要触发每日计划生成
        
        触发条件：
        1. 游戏日期变化（新的一天）
        2. 游戏时间达到配置的计划生成时间（默认 6:00）
        """
        from app.agents.manager import agent_manager
        
        game_time = world_clock.get_time()
        game_date = game_time.date()
        game_hour = game_time.hour
        
        # 检查是否是新的一天且达到计划生成时间
        plan_start_hour = settings.daily_plan_start_hour
        
        if (self._last_plan_date != game_date and game_hour >= plan_start_hour):
            logger.info(f"触发每日计划生成: 第{world_clock.get_world_time().day}天 {game_hour}:00")
            
            # 为所有活跃智能体生成日计划
            all_agents = list(agent_manager.agents.values())
            
            for agent in all_agents:
                if agent.state not in [AgentState.OFFLINE, AgentState.SLEEPING]:
                    try:
                        agent.daily_plan = await generate_daily_plan(agent, game_date)
                        logger.debug(f"[{agent.name}] 日计划生成完成")
                    except Exception as e:
                        logger.error(f"[{agent.name}] 日计划生成失败: {e}")
            
            self._last_plan_date = game_date
            
            # 发布事件
            event_bus.publish_sync("daily_plan.generated", {
                "date": game_date.isoformat(),
                "agent_count": len(all_agents),
            })
    
    async def _process_agent(
        self,
        agent: Agent,
        surroundings: str,
    ) -> None:
        """
        处理单个智能体的决策
        
        Phase 6 增强流程：
        1. 感知环境
        2. 检查是否需要反应
        3. 检查是否需要反思
        4. 执行原有决策逻辑
        5. 记录活动日志（Phase 7）
        """
        try:
            # =====================
            # Phase 6 Step 1: 感知环境
            # =====================
            perception = await perceive_environment(agent)
            logger.debug(f"[{agent.name}] 感知: 附近有 {len(perception.agents_nearby)} 人")
            
            # =====================
            # Phase 6 Step 2: 检查是否需要反应
            # =====================
            # 获取当前计划任务（如果有）
            current_plan_desc = None
            if agent.daily_plan:
                current_task = agent.daily_plan.get_current_task()
                if current_task:
                    current_plan_desc = f"{current_task.activity} at {current_task.location}"
            
            reaction_decision = await should_react(agent, perception, current_plan_desc)
            
            if reaction_decision.should_react:
                logger.info(
                    f"[{agent.name}] 反应决策: {reaction_decision.reaction_type.value} - "
                    f"{reaction_decision.reason}"
                )
                
                if reaction_decision.reaction_type == ReactionType.INTERRUPT:
                    # 中断当前行为，执行反应
                    await execute_reaction(agent, reaction_decision)
                    
                    # Phase 7: 记录反应活动
                    await self._log_activity(
                        agent=agent,
                        activity_type="reaction",
                        action=reaction_decision.reaction_type.value,
                        target=None,
                        thinking=reaction_decision.reason,
                    )
                    
                    # 发布反应事件
                    event_bus.publish_sync("agent.reacted", {
                        "agent_id": agent.id,
                        "reaction_type": reaction_decision.reaction_type.value,
                        "reaction": reaction_decision.reaction,
                        "reason": reaction_decision.reason,
                    })
                    
                    # 反应后跳过本轮常规决策
                    return
                    
                elif reaction_decision.reaction_type == ReactionType.NOTE:
                    # 记录但继续当前行为
                    if reaction_decision.reaction:
                        agent.add_memory(
                            reaction_decision.reaction,
                            MemoryType.EVENT,
                            importance=3.0,
                        )
            
            # =====================
            # Phase 6 Step 3: 检查是否需要反思
            # =====================
            reflection_result = await maybe_reflect(agent)
            if reflection_result:
                logger.info(
                    f"[{agent.name}] 完成反思，生成 {len(reflection_result.insights)} 条洞察"
                )
                
                # Phase 7: 记录反思活动
                await self._log_activity(
                    agent=agent,
                    activity_type="reflection",
                    action="reflect",
                    reflection_content="; ".join(reflection_result.insights[:3]),  # 取前3条
                )
            
            # =====================
            # 原有逻辑: 完成当前行为并生成新决策
            # =====================
            # 先完成当前行为（如果已完成）
            if agent.current_action.duration_minutes > 0:
                if agent.current_action.is_complete(datetime.now()):
                    agent.complete_action()
            
            # 生成新决策
            decision = await make_decision(agent, surroundings)
            
            if decision:
                await execute_decision(agent, decision)
                agent.last_decision_time = datetime.now()
                
                # Phase 7: 记录决策活动
                await self._log_activity(
                    agent=agent,
                    activity_type="decision",
                    action=decision.action.value,
                    target=decision.target,
                    thinking=decision.thinking,
                )
                
                # 发布决策事件
                event_bus.publish_sync("agent.decided", {
                    "agent_id": agent.id,
                    "action": decision.action.value,
                    "target": decision.target,
                    "thinking": decision.thinking,
                })
            
        except Exception as e:
            logger.error(f"处理智能体 {agent.name} 决策失败: {e}")
    
    async def _log_activity(
        self,
        agent: Agent,
        activity_type: str,
        action: str,
        target: Optional[str] = None,
        thinking: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_partner: Optional[str] = None,
        message_content: Optional[str] = None,
        reflection_content: Optional[str] = None,
    ) -> None:
        """
        记录活动日志到数据库
        
        Phase 7: 观察者功能增强
        """
        try:
            from app.database import get_async_session
            from app.database.crud.activity_logs import ActivityLogCRUD
            
            async with get_async_session() as db:
                await ActivityLogCRUD.create(
                    db=db,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    activity_type=activity_type,
                    action=action,
                    game_time=world_clock.get_time(),
                    target=target,
                    location=agent.position.location_name,
                    thinking=thinking,
                    conversation_id=conversation_id,
                    conversation_partner=conversation_partner,
                    message_content=message_content,
                    reflection_content=reflection_content,
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"记录活动日志失败: {e}")


# 创建全局调度器
decision_scheduler = DecisionScheduler()
