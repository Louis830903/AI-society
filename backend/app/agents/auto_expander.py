"""
自动扩展器
=========
根据社会平衡检测结果，自动创建或移除智能体

功能：
- 自动创建填补职业缺口
- 为孤独者创建匹配的朋友
- 控制人口上限
- 智能体离开机制
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.agents.manager import agent_manager
from app.agents.models import Agent, AgentState
from app.agents.generator import (
    generate_agent_from_template,
    generate_agent_with_llm,
    assign_location,
    OCCUPATIONS,
)
from app.agents.balance_detector import (
    social_balance_detector,
    SocialBalanceReport,
    OccupationGap,
    SocialIsolate,
)
from app.core.config import settings
from app.core.events import event_bus


@dataclass
class ExpansionEvent:
    """扩展事件"""
    event_type: str  # "agent_joined", "agent_left"
    agent_id: str
    agent_name: str
    reason: str
    timestamp: datetime
    details: dict
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class AutoExpander:
    """自动扩展器"""
    
    def __init__(self):
        """初始化扩展器"""
        self._is_running: bool = False
        self._check_interval: int = 300  # 检查间隔（秒）
        self._last_check: Optional[datetime] = None
        self._expansion_history: List[ExpansionEvent] = []
        
        # 配置
        self._min_population: int = 30  # 最小人口
        self._max_population: int = settings.max_agent_count
        self._expansion_cooldown: int = 60  # 扩展冷却时间（秒）
        self._last_expansion: Optional[datetime] = None
    
    # ===================
    # 智能体创建
    # ===================
    
    async def create_agent_for_gap(
        self,
        gap: OccupationGap,
        use_llm: bool = False,
    ) -> Optional[Agent]:
        """
        为职业缺口创建智能体
        
        Args:
            gap: 职业缺口信息
            use_llm: 是否使用LLM生成
            
        Returns:
            创建的智能体或None
        """
        # 检查人口上限
        if agent_manager.count() >= self._max_population:
            logger.warning("已达人口上限，无法创建新智能体")
            return None
        
        # 检查冷却
        if not self._check_cooldown():
            return None
        
        logger.info(f"为职业缺口创建智能体: {gap.occupation} @ {gap.location_name}")
        
        try:
            if use_llm:
                agent = await generate_agent_with_llm(
                    needed_roles=gap.occupation,
                    existing_sample=self._get_sample_agents(),
                )
            else:
                agent = None
            
            if not agent:
                agent = generate_agent_from_template(occupation=gap.occupation)
            
            # 分配位置
            assign_location(agent)
            
            # 添加到管理器
            agent_manager.add(agent)
            
            # 记录事件
            self._record_expansion_event(
                event_type="agent_joined",
                agent=agent,
                reason=f"填补职业缺口：{gap.location_name}需要{gap.occupation}",
                details={
                    "occupation_gap": gap.occupation,
                    "location": gap.location_name,
                    "priority": gap.priority,
                },
            )
            
            self._last_expansion = datetime.now()
            
            logger.info(f"成功创建智能体: {agent.name} ({agent.occupation})")
            return agent
            
        except Exception as e:
            logger.error(f"创建智能体失败: {e}")
            return None
    
    async def create_friend_for_isolate(
        self,
        isolate: SocialIsolate,
        use_llm: bool = False,
    ) -> Optional[Agent]:
        """
        为社交孤岛创建匹配的朋友
        
        Args:
            isolate: 社交孤岛信息
            use_llm: 是否使用LLM生成
            
        Returns:
            创建的智能体或None
        """
        # 检查人口上限
        if agent_manager.count() >= self._max_population:
            return None
        
        # 检查冷却
        if not self._check_cooldown():
            return None
        
        # 获取孤独者信息
        lonely_agent = agent_manager.get(isolate.agent_id)
        if not lonely_agent:
            return None
        
        logger.info(f"为孤独者 {isolate.agent_name} 创建朋友")
        
        try:
            # 确定匹配条件
            target_gender = self._determine_friend_gender(lonely_agent)
            target_occupation = self._determine_friend_occupation(lonely_agent)
            target_archetype = self._determine_friend_archetype(lonely_agent)
            
            if use_llm:
                agent = await generate_agent_with_llm(
                    needed_roles=f"适合与{lonely_agent.name}交朋友的角色",
                    existing_sample=self._get_sample_agents(),
                )
            else:
                agent = None
            
            if not agent:
                agent = generate_agent_from_template(
                    occupation=target_occupation,
                    gender=target_gender,
                    archetype=target_archetype,
                )
            
            # 分配位置（尽量靠近孤独者）
            assign_location(agent)
            
            # 添加到管理器
            agent_manager.add(agent)
            
            # 初始化关系（给他们一个初始的好感度）
            lonely_agent.add_relationship(
                agent.id,
                agent.name,
                closeness=55,
                trust=50,
            )
            agent.add_relationship(
                lonely_agent.id,
                lonely_agent.name,
                closeness=55,
                trust=50,
            )
            
            # 记录事件
            self._record_expansion_event(
                event_type="agent_joined",
                agent=agent,
                reason=f"为孤独的{isolate.agent_name}创建朋友",
                details={
                    "lonely_agent_id": isolate.agent_id,
                    "lonely_agent_name": isolate.agent_name,
                    "loneliness_score": isolate.loneliness_score,
                },
            )
            
            self._last_expansion = datetime.now()
            
            logger.info(f"成功为 {isolate.agent_name} 创建朋友: {agent.name}")
            return agent
            
        except Exception as e:
            logger.error(f"创建朋友失败: {e}")
            return None
    
    def _determine_friend_gender(self, agent: Agent) -> str:
        """确定朋友性别（随机或异性）"""
        if random.random() < 0.3:
            return "女" if agent.gender == "男" else "男"
        return random.choice(["男", "女"])
    
    def _determine_friend_occupation(self, agent: Agent) -> str:
        """确定朋友职业"""
        # 70%概率选择相似职业
        if random.random() < 0.7:
            return agent.occupation
        return random.choice(OCCUPATIONS)
    
    def _determine_friend_archetype(self, agent: Agent) -> str:
        """确定朋友人格原型"""
        # 相似人格更容易交朋友
        if agent.personality.extraversion > 60:
            return "外向型"
        elif agent.personality.extraversion < 40:
            return "内向型"
        return None
    
    # ===================
    # 智能体离开
    # ===================
    
    async def process_agent_leaving(self, agent: Agent, reason: str) -> bool:
        """
        处理智能体离开
        
        Args:
            agent: 要离开的智能体
            reason: 离开原因
            
        Returns:
            是否成功
        """
        # 检查最小人口
        if agent_manager.count() <= self._min_population:
            logger.warning("人口已达最低限制，无法移除智能体")
            return False
        
        logger.info(f"智能体 {agent.name} 即将离开，原因: {reason}")
        
        # 记录事件
        self._record_expansion_event(
            event_type="agent_left",
            agent=agent,
            reason=reason,
            details={
                "occupation": agent.occupation,
                "age": agent.age,
                "days_active": (datetime.now() - agent.created_at).days if agent.created_at else 0,
            },
        )
        
        # 从管理器移除
        agent_manager.remove(agent.id)
        
        return True
    
    def check_leaving_conditions(self, agent: Agent) -> Optional[str]:
        """
        检查智能体是否满足离开条件
        
        Returns:
            离开原因或None
        """
        # 1. 长期负面状态
        if agent.get_wellbeing() < 20:
            # 连续3天不幸福可能离开
            if random.random() < 0.1:
                return "生活质量太低，决定离开小镇"
        
        # 2. 严重入不敷出
        if agent.balance < -5000:
            if random.random() < 0.2:
                return "经济困难，不得不离开"
        
        # 3. 长期孤独
        if agent.needs.social < 20 and len(agent.relationships) < 2:
            if random.random() < 0.05:
                return "感到孤独，决定去别的地方"
        
        # 4. 年龄因素（退休老人更可能离开）
        if agent.age > 75:
            if random.random() < 0.02:
                return "年事已高，搬去和家人同住"
        
        return None
    
    async def check_and_remove_leaving_agents(self) -> List[Agent]:
        """
        检查并移除满足离开条件的智能体
        
        Returns:
            离开的智能体列表
        """
        leaving_agents = []
        
        for agent in agent_manager.get_all():
            reason = self.check_leaving_conditions(agent)
            if reason:
                if await self.process_agent_leaving(agent, reason):
                    leaving_agents.append(agent)
        
        return leaving_agents
    
    # ===================
    # 自动平衡
    # ===================
    
    async def auto_balance(self) -> Dict[str, int]:
        """
        执行自动平衡
        
        Returns:
            操作统计 {"created": n, "removed": m}
        """
        stats = {"created": 0, "removed": 0}
        
        # 生成平衡报告
        report = social_balance_detector.generate_report()
        
        logger.info(f"社会健康分数: {report.overall_health_score:.1f}")
        
        # 1. 处理职业缺口
        if report.occupation_gaps:
            for gap in report.occupation_gaps[:2]:  # 每次最多填补2个缺口
                if gap.priority >= 0.7:
                    agent = await self.create_agent_for_gap(gap)
                    if agent:
                        stats["created"] += 1
                        await asyncio.sleep(1)  # 控制创建速度
        
        # 2. 处理社交孤岛
        severe_isolates = [
            i for i in report.social_isolates
            if i.loneliness_score > 0.8
        ]
        if len(severe_isolates) >= 3 and stats["created"] == 0:
            # 为最孤独的人创建朋友
            isolate = severe_isolates[0]
            agent = await self.create_friend_for_isolate(isolate)
            if agent:
                stats["created"] += 1
        
        # 3. 检查离开条件
        if report.overall_health_score > 60:
            # 只有在社会相对健康时才允许离开
            leaving = await self.check_and_remove_leaving_agents()
            stats["removed"] = len(leaving)
        
        return stats
    
    # ===================
    # 定时任务
    # ===================
    
    async def start(self):
        """启动自动扩展任务"""
        if self._is_running:
            return
        
        self._is_running = True
        logger.info("自动扩展器启动")
        
        while self._is_running:
            try:
                await asyncio.sleep(self._check_interval)
                
                if not self._is_running:
                    break
                
                # 执行自动平衡
                stats = await self.auto_balance()
                self._last_check = datetime.now()
                
                if stats["created"] > 0 or stats["removed"] > 0:
                    logger.info(f"自动平衡完成: 新增 {stats['created']}, 离开 {stats['removed']}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动扩展错误: {e}")
        
        logger.info("自动扩展器停止")
    
    def stop(self):
        """停止自动扩展任务"""
        self._is_running = False
    
    # ===================
    # 辅助方法
    # ===================
    
    def _check_cooldown(self) -> bool:
        """检查扩展冷却"""
        if self._last_expansion is None:
            return True
        
        elapsed = (datetime.now() - self._last_expansion).total_seconds()
        return elapsed >= self._expansion_cooldown
    
    def _get_sample_agents(self) -> str:
        """获取现有智能体样本"""
        agents = agent_manager.get_all()
        if not agents:
            return "暂无居民"
        
        samples = random.sample(agents, min(3, len(agents)))
        return "\n".join([
            f"- {a.name}（{a.occupation}，{a.age}岁）"
            for a in samples
        ])
    
    def _record_expansion_event(
        self,
        event_type: str,
        agent: Agent,
        reason: str,
        details: dict,
    ):
        """记录扩展事件"""
        event = ExpansionEvent(
            event_type=event_type,
            agent_id=agent.id,
            agent_name=agent.name,
            reason=reason,
            timestamp=datetime.now(),
            details=details,
        )
        
        self._expansion_history.append(event)
        
        # 只保留最近100条记录
        if len(self._expansion_history) > 100:
            self._expansion_history = self._expansion_history[-100:]
        
        # 发布事件
        event_bus.publish(event_type, event.to_dict())
    
    # ===================
    # 查询方法
    # ===================
    
    def get_recent_events(self, limit: int = 20) -> List[ExpansionEvent]:
        """获取最近的扩展事件"""
        return self._expansion_history[-limit:]
    
    def get_status(self) -> dict:
        """获取扩展器状态"""
        return {
            "is_running": self._is_running,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "last_expansion": self._last_expansion.isoformat() if self._last_expansion else None,
            "check_interval": self._check_interval,
            "current_population": agent_manager.count(),
            "min_population": self._min_population,
            "max_population": self._max_population,
            "recent_events_count": len(self._expansion_history),
        }


# ===================
# 全局实例
# ===================

auto_expander = AutoExpander()
