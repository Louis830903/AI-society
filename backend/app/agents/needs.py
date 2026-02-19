"""
需求系统
=======
智能体的内在驱动力系统

需求类型：
- 生理需求：饥饿、疲劳
- 社交需求：社交渴望
- 心理需求：娱乐、成就感
- 经济需求：收入、消费

需求值范围：0-100
- 0: 完全满足
- 100: 极度渴望

需求随时间增长，通过特定行为满足
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random

from loguru import logger


class NeedType(str, Enum):
    """需求类型枚举"""
    HUNGER = "hunger"  # 饥饿
    FATIGUE = "fatigue"  # 疲劳
    SOCIAL = "social"  # 社交
    ENTERTAINMENT = "entertainment"  # 娱乐
    HYGIENE = "hygiene"  # 卫生（洗漱）
    COMFORT = "comfort"  # 舒适（居家）


# 需求配置
NEED_CONFIG = {
    NeedType.HUNGER: {
        "name": "饥饿",
        "growth_rate": 4.0,  # 每小时增长量（游戏时间）
        "urgent_threshold": 70,  # 紧急阈值
        "critical_threshold": 90,  # 临界阈值
        "decay_activities": ["eat", "cook"],  # 满足该需求的活动
        "decay_amount": 60,  # 活动满足量
    },
    NeedType.FATIGUE: {
        "name": "疲劳",
        "growth_rate": 2.5,
        "urgent_threshold": 75,
        "critical_threshold": 95,
        "decay_activities": ["sleep", "rest", "nap"],
        "decay_amount": 80,
    },
    NeedType.SOCIAL: {
        "name": "社交",
        "growth_rate": 1.5,
        "urgent_threshold": 65,
        "critical_threshold": 85,
        "decay_activities": ["chat", "socialize", "party"],
        "decay_amount": 40,
    },
    NeedType.ENTERTAINMENT: {
        "name": "娱乐",
        "growth_rate": 1.8,
        "urgent_threshold": 60,
        "critical_threshold": 80,
        "decay_activities": ["play", "watch", "read", "game"],
        "decay_amount": 35,
    },
    NeedType.HYGIENE: {
        "name": "卫生",
        "growth_rate": 1.0,
        "urgent_threshold": 70,
        "critical_threshold": 90,
        "decay_activities": ["shower", "bath", "wash"],
        "decay_amount": 70,
    },
    NeedType.COMFORT: {
        "name": "舒适",
        "growth_rate": 0.8,
        "urgent_threshold": 55,
        "critical_threshold": 75,
        "decay_activities": ["rest", "home", "relax"],
        "decay_amount": 30,
    },
}


@dataclass
class NeedState:
    """单个需求的状态"""
    value: float = 0.0  # 当前值 (0=满足, 100=极度渴望)
    last_satisfied: Optional[datetime] = None  # 上次满足时间
    
    def is_urgent(self, config: dict) -> bool:
        """是否达到紧急状态"""
        return self.value >= config["urgent_threshold"]
    
    def is_critical(self, config: dict) -> bool:
        """是否达到临界状态"""
        return self.value >= config["critical_threshold"]


@dataclass
class Needs:
    """
    智能体需求系统
    
    管理所有需求状态，随时间变化，通过行为满足
    """
    
    # 核心需求
    hunger: float = 20.0  # 饥饿
    fatigue: float = 15.0  # 疲劳
    social: float = 30.0  # 社交
    entertainment: float = 25.0  # 娱乐
    hygiene: float = 10.0  # 卫生
    comfort: float = 20.0  # 舒适
    
    # 追踪数据
    _last_update: datetime = field(default_factory=lambda: datetime.now())
    _satisfaction_history: Dict[NeedType, List[datetime]] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证数值范围"""
        for need in NeedType:
            value = getattr(self, need.value, 0)
            if not 0 <= value <= 100:
                setattr(self, need.value, max(0, min(100, value)))
    
    def get(self, need: NeedType) -> float:
        """获取需求值"""
        return getattr(self, need.value)
    
    def set(self, need: NeedType, value: float) -> None:
        """设置需求值"""
        setattr(self, need.value, max(0, min(100, value)))
    
    def update(self, elapsed_hours: float, personality=None) -> Dict[NeedType, float]:
        """
        更新需求值（随时间增长）
        
        Args:
            elapsed_hours: 经过的游戏时间（小时）
            personality: 人格对象（影响需求增长速度）
        
        Returns:
            各需求的变化量
        """
        changes = {}
        
        for need in NeedType:
            config = NEED_CONFIG[need]
            base_rate = config["growth_rate"]
            
            # 人格影响
            rate_modifier = 1.0
            if personality:
                if need == NeedType.SOCIAL:
                    # 外向者社交需求增长更快
                    rate_modifier = 0.7 + (personality.extraversion / 100) * 0.6
                elif need == NeedType.ENTERTAINMENT:
                    # 开放者娱乐需求增长更快
                    rate_modifier = 0.8 + (personality.openness / 100) * 0.4
                elif need == NeedType.FATIGUE:
                    # 神经质者更容易疲劳
                    rate_modifier = 0.9 + (personality.neuroticism / 100) * 0.2
            
            # 计算增长
            growth = base_rate * rate_modifier * elapsed_hours
            
            # 添加随机波动 (±10%)
            growth *= random.uniform(0.9, 1.1)
            
            old_value = self.get(need)
            new_value = min(100, old_value + growth)
            self.set(need, new_value)
            
            changes[need] = new_value - old_value
        
        self._last_update = datetime.now()
        return changes
    
    def satisfy(self, need: NeedType, amount: Optional[float] = None) -> float:
        """
        满足需求
        
        Args:
            need: 需求类型
            amount: 满足量，为空则使用默认值
        
        Returns:
            实际减少的值
        """
        config = NEED_CONFIG[need]
        decay = amount if amount is not None else config["decay_amount"]
        
        old_value = self.get(need)
        new_value = max(0, old_value - decay)
        self.set(need, new_value)
        
        # 记录满足历史
        if need not in self._satisfaction_history:
            self._satisfaction_history[need] = []
        self._satisfaction_history[need].append(datetime.now())
        
        # 只保留最近10次
        self._satisfaction_history[need] = self._satisfaction_history[need][-10:]
        
        actual_decrease = old_value - new_value
        logger.debug(f"需求满足: {need.value} -{actual_decrease:.1f} ({old_value:.1f} → {new_value:.1f})")
        
        return actual_decrease
    
    def satisfy_by_activity(self, activity: str) -> Dict[NeedType, float]:
        """
        根据活动满足相关需求
        
        Args:
            activity: 活动名称
        
        Returns:
            各需求的减少量
        """
        activity_lower = activity.lower()
        changes = {}
        
        for need in NeedType:
            config = NEED_CONFIG[need]
            if any(act in activity_lower for act in config["decay_activities"]):
                decrease = self.satisfy(need)
                changes[need] = decrease
        
        return changes
    
    # ===================
    # 状态分析
    # ===================
    
    def get_urgent_needs(self) -> List[Tuple[NeedType, float]]:
        """
        获取紧急需求列表
        
        Returns:
            [(需求类型, 当前值)] 按紧急程度排序
        """
        urgent = []
        for need in NeedType:
            config = NEED_CONFIG[need]
            value = self.get(need)
            if value >= config["urgent_threshold"]:
                urgent.append((need, value))
        
        return sorted(urgent, key=lambda x: x[1], reverse=True)
    
    def get_most_urgent(self) -> Optional[Tuple[NeedType, float]]:
        """获取最紧急的需求"""
        urgent = self.get_urgent_needs()
        return urgent[0] if urgent else None
    
    def get_priority_order(self) -> List[Tuple[NeedType, float, str]]:
        """
        获取需求优先级排序
        
        Returns:
            [(需求类型, 当前值, 状态)] 按处理优先级排序
        """
        priorities = []
        
        for need in NeedType:
            config = NEED_CONFIG[need]
            value = self.get(need)
            
            if value >= config["critical_threshold"]:
                status = "critical"
                priority_score = value * 2
            elif value >= config["urgent_threshold"]:
                status = "urgent"
                priority_score = value * 1.5
            else:
                status = "normal"
                priority_score = value
            
            priorities.append((need, value, status, priority_score))
        
        # 按优先级分数排序
        priorities.sort(key=lambda x: x[3], reverse=True)
        
        return [(p[0], p[1], p[2]) for p in priorities]
    
    def get_overall_wellbeing(self) -> float:
        """
        计算整体幸福指数
        
        Returns:
            0-100，越高越好
        """
        total = sum(self.get(need) for need in NeedType)
        # 反转：需求值低=幸福度高
        wellbeing = 100 - (total / len(NeedType))
        return round(wellbeing, 1)
    
    def get_status_description(self) -> str:
        """
        生成需求状态的自然语言描述
        
        用于LLM提示词
        """
        lines = []
        for need in NeedType:
            config = NEED_CONFIG[need]
            value = self.get(need)
            
            if value >= config["critical_threshold"]:
                desc = "极度需要"
            elif value >= config["urgent_threshold"]:
                desc = "比较需要"
            elif value >= 40:
                desc = "有些需要"
            else:
                desc = "暂时满足"
            
            lines.append(f"- {config['name']}：{value:.0f}/100（{desc}）")
        
        return "\n".join(lines)
    
    # ===================
    # 序列化
    # ===================
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            need.value: self.get(need)
            for need in NeedType
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Needs":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    @classmethod
    def random(cls, max_value: float = 50) -> "Needs":
        """
        生成随机初始需求
        
        Args:
            max_value: 最大初始值（避免一开始就很紧急）
        """
        return cls(
            hunger=random.uniform(10, max_value),
            fatigue=random.uniform(5, max_value * 0.8),
            social=random.uniform(15, max_value),
            entertainment=random.uniform(10, max_value),
            hygiene=random.uniform(5, max_value * 0.6),
            comfort=random.uniform(10, max_value * 0.8),
        )
    
    @classmethod
    def morning_state(cls) -> "Needs":
        """早晨刚起床的状态"""
        return cls(
            hunger=45,  # 有点饿
            fatigue=10,  # 睡眠充足
            social=35,
            entertainment=30,
            hygiene=50,  # 需要洗漱
            comfort=20,
        )
    
    @classmethod
    def evening_state(cls) -> "Needs":
        """傍晚下班后的状态"""
        return cls(
            hunger=55,
            fatigue=60,
            social=50,
            entertainment=55,
            hygiene=40,
            comfort=45,
        )
