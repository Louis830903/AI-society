"""
层级计划系统
===========
智能体的日计划生成与分解

参考：斯坦福 Generative Agents 论文 (arxiv:2304.03442)

层级结构：
1. 日计划（broad strokes）：4-6个大块时间安排
2. 小时计划（hourly chunks）：按小时细化
3. 任务计划（micro tasks）：5-15分钟的具体行动
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from loguru import logger

if TYPE_CHECKING:
    from app.agents.models import Agent


@dataclass
class PlanBlock:
    """计划时间块"""
    start_time: str  # "HH:MM" 格式
    end_time: str    # "HH:MM" 格式
    activity: str    # 活动描述
    location: str = ""  # 地点
    
    def __post_init__(self):
        """验证时间格式"""
        # 简单验证
        if not re.match(r'^\d{2}:\d{2}$', self.start_time):
            logger.warning(f"无效的开始时间格式: {self.start_time}")
        if not re.match(r'^\d{2}:\d{2}$', self.end_time):
            logger.warning(f"无效的结束时间格式: {self.end_time}")
    
    def get_start_datetime(self, plan_date: date) -> datetime:
        """获取开始时间的datetime对象"""
        hour, minute = map(int, self.start_time.split(":"))
        return datetime.combine(plan_date, time(hour, minute))
    
    def get_end_datetime(self, plan_date: date) -> datetime:
        """获取结束时间的datetime对象"""
        hour, minute = map(int, self.end_time.split(":"))
        return datetime.combine(plan_date, time(hour, minute))
    
    def duration_minutes(self) -> int:
        """计算持续时间（分钟）"""
        try:
            start_h, start_m = map(int, self.start_time.split(":"))
            end_h, end_m = map(int, self.end_time.split(":"))
            return (end_h * 60 + end_m) - (start_h * 60 + start_m)
        except Exception:
            return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "start": self.start_time,
            "end": self.end_time,
            "activity": self.activity,
            "location": self.location,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanBlock":
        """从字典创建"""
        return cls(
            start_time=data.get("start", "00:00"),
            end_time=data.get("end", "00:00"),
            activity=data.get("activity", ""),
            location=data.get("location", ""),
        )


@dataclass
class DailyPlan:
    """日计划"""
    plan_date: date
    broad_strokes: List[PlanBlock] = field(default_factory=list)  # 粗粒度计划
    hourly_chunks: List[PlanBlock] = field(default_factory=list)  # 小时级计划
    current_tasks: List[PlanBlock] = field(default_factory=list)  # 当前细粒度任务
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_current_block(self, current_time: datetime) -> Optional[PlanBlock]:
        """
        获取当前时间应该执行的计划块
        
        首先检查细粒度任务，然后是小时计划，最后是粗粒度计划
        """
        time_str = current_time.strftime("%H:%M")
        
        # 优先检查细粒度任务
        for task in self.current_tasks:
            if task.start_time <= time_str < task.end_time:
                return task
        
        # 检查小时计划
        for chunk in self.hourly_chunks:
            if chunk.start_time <= time_str < chunk.end_time:
                return chunk
        
        # 检查粗粒度计划
        for block in self.broad_strokes:
            if block.start_time <= time_str < block.end_time:
                return block
        
        return None
    
    def get_current_task(self, current_time: Optional[datetime] = None) -> Optional[PlanBlock]:
        """
        获取当前应该执行的任务（get_current_block 的别名）
        
        Args:
            current_time: 当前时间（默认为现在）
        
        Returns:
            当前任务块，如果没有则返回 None
        """
        if current_time is None:
            current_time = datetime.now()
        return self.get_current_block(current_time)
    
    def get_remaining_plan(self, from_time: datetime) -> List[PlanBlock]:
        """获取指定时间之后的剩余计划"""
        time_str = from_time.strftime("%H:%M")
        remaining = []
        
        for block in self.broad_strokes:
            if block.end_time > time_str:
                remaining.append(block)
        
        return remaining
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "date": self.plan_date.isoformat(),
            "broad_strokes": [b.to_dict() for b in self.broad_strokes],
            "hourly_chunks": [h.to_dict() for h in self.hourly_chunks],
            "current_tasks": [t.to_dict() for t in self.current_tasks],
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailyPlan":
        """从字典创建"""
        return cls(
            plan_date=date.fromisoformat(data["date"]),
            broad_strokes=[PlanBlock.from_dict(b) for b in data.get("broad_strokes", [])],
            hourly_chunks=[PlanBlock.from_dict(h) for h in data.get("hourly_chunks", [])],
            current_tasks=[PlanBlock.from_dict(t) for t in data.get("current_tasks", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


def _extract_json_from_response(response: str) -> Optional[Dict]:
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


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


async def generate_daily_plan(agent: "Agent", plan_date: Optional[date] = None) -> DailyPlan:
    """
    为智能体生成日计划
    
    Args:
        agent: 智能体对象
        plan_date: 计划日期（默认为今天）
    
    Returns:
        日计划对象
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    from app.core.locations import location_manager
    
    if plan_date is None:
        plan_date = date.today()
    
    weekday = WEEKDAY_NAMES[plan_date.weekday()]
    
    # 获取家和工作地点
    home_location = "未知"
    work_location = "未知"
    
    if agent.home_location_id:
        home = location_manager.get(agent.home_location_id)
        if home:
            home_location = home.name
    
    if agent.work_location_id:
        work = location_manager.get(agent.work_location_id)
        if work:
            work_location = work.name
    
    # 构建提示词
    prompt = PromptTemplates.render(
        "DAILY_PLAN",
        name=agent.name,
        age=agent.age,
        occupation=agent.occupation,
        personality_description=agent.get_personality_description(),
        date=plan_date.isoformat(),
        weekday=weekday,
        home_location=home_location,
        work_location=work_location,
        balance=f"{agent.balance:.2f}",
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=agent.model_name,
            temperature=0.7,
            max_tokens=800,
        )
        
        json_data = _extract_json_from_response(response.content)
        
        if json_data and "plan" in json_data:
            blocks = []
            for item in json_data["plan"]:
                block = PlanBlock(
                    start_time=item.get("start", "00:00"),
                    end_time=item.get("end", "00:00"),
                    activity=item.get("activity", ""),
                    location=item.get("location", ""),
                )
                blocks.append(block)
            
            plan = DailyPlan(
                plan_date=plan_date,
                broad_strokes=blocks,
            )
            
            logger.info(f"[{agent.name}] 生成日计划: {len(blocks)}个时间块")
            return plan
        
        logger.warning(f"[{agent.name}] 无法解析日计划响应")
        
    except Exception as e:
        logger.error(f"[{agent.name}] 生成日计划失败: {e}")
    
    # 返回空计划
    return DailyPlan(plan_date=plan_date)


async def decompose_to_hourly(
    agent: "Agent",
    plan_block: PlanBlock,
) -> List[PlanBlock]:
    """
    将粗粒度计划块分解为小时级任务
    
    Args:
        agent: 智能体对象
        plan_block: 要分解的计划块
    
    Returns:
        小时级任务列表
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    
    # 如果时间块小于1小时，不需要分解
    if plan_block.duration_minutes() <= 60:
        return [plan_block]
    
    prompt = PromptTemplates.render(
        "HOURLY_DECOMPOSE",
        start_time=plan_block.start_time,
        end_time=plan_block.end_time,
        activity=plan_block.activity,
        location=plan_block.location,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=agent.model_name,
            temperature=0.5,
            max_tokens=500,
        )
        
        json_data = _extract_json_from_response(response.content)
        
        if json_data and "tasks" in json_data:
            tasks = []
            for item in json_data["tasks"]:
                task = PlanBlock(
                    start_time=item.get("start", "00:00"),
                    end_time=item.get("end", "00:00"),
                    activity=item.get("task", item.get("activity", "")),
                    location=item.get("location", plan_block.location),
                )
                tasks.append(task)
            
            return tasks
        
    except Exception as e:
        logger.error(f"[{agent.name}] 分解小时计划失败: {e}")
    
    return [plan_block]


async def decompose_to_tasks(
    agent: "Agent",
    hourly_block: PlanBlock,
) -> List[PlanBlock]:
    """
    将小时计划分解为5-15分钟的具体任务
    
    Args:
        agent: 智能体对象
        hourly_block: 要分解的小时块
    
    Returns:
        细粒度任务列表
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    
    # 如果时间块小于15分钟，不需要分解
    if hourly_block.duration_minutes() <= 15:
        return [hourly_block]
    
    prompt = PromptTemplates.render(
        "TASK_DECOMPOSE",
        start_time=hourly_block.start_time,
        end_time=hourly_block.end_time,
        activity=hourly_block.activity,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=agent.model_name,
            temperature=0.5,
            max_tokens=400,
        )
        
        json_data = _extract_json_from_response(response.content)
        
        if json_data and "micro_tasks" in json_data:
            tasks = []
            current_time = hourly_block.start_time
            
            for item in json_data["micro_tasks"]:
                start = item.get("start", current_time)
                duration = item.get("duration_minutes", 10)
                
                # 计算结束时间
                start_h, start_m = map(int, start.split(":"))
                end_m = start_m + duration
                end_h = start_h + end_m // 60
                end_m = end_m % 60
                end_time = f"{end_h:02d}:{end_m:02d}"
                
                task = PlanBlock(
                    start_time=start,
                    end_time=end_time,
                    activity=item.get("task", ""),
                    location=hourly_block.location,
                )
                tasks.append(task)
                current_time = end_time
            
            return tasks
        
    except Exception as e:
        logger.error(f"[{agent.name}] 分解细粒度任务失败: {e}")
    
    return [hourly_block]


async def replan_from_now(
    agent: "Agent",
    current_time: datetime,
    what_happened: str,
) -> List[PlanBlock]:
    """
    从当前时间重新规划剩余时间
    
    Args:
        agent: 智能体对象
        current_time: 当前时间
        what_happened: 刚才发生的事情描述
    
    Returns:
        新的计划块列表
    """
    from app.llm import llm_router
    from app.llm.prompts import PromptTemplates
    
    if not agent.daily_plan:
        return []
    
    # 获取剩余计划
    remaining = agent.daily_plan.get_remaining_plan(current_time)
    remaining_text = "\n".join([
        f"- {b.start_time}-{b.end_time}: {b.activity} @ {b.location}"
        for b in remaining
    ]) if remaining else "无剩余计划"
    
    prompt = PromptTemplates.render(
        "REPLAN_FROM_NOW",
        agent_name=agent.name,
        what_happened=what_happened,
        current_time=current_time.strftime("%H:%M"),
        remaining_plan=remaining_text,
    )
    
    try:
        response = await llm_router.generate(
            prompt=prompt,
            model_name=agent.model_name,
            temperature=0.7,
            max_tokens=500,
        )
        
        json_data = _extract_json_from_response(response.content)
        
        if json_data and "new_plan" in json_data:
            new_blocks = []
            for item in json_data["new_plan"]:
                block = PlanBlock(
                    start_time=item.get("start", "00:00"),
                    end_time=item.get("end", "00:00"),
                    activity=item.get("activity", ""),
                    location=item.get("location", ""),
                )
                new_blocks.append(block)
            
            logger.info(f"[{agent.name}] 重新规划: {len(new_blocks)}个新时间块")
            return new_blocks
        
    except Exception as e:
        logger.error(f"[{agent.name}] 重新规划失败: {e}")
    
    return []
