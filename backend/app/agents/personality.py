"""
人格系统
=======
基于大五人格模型（OCEAN/Big Five）实现智能体人格特质

大五人格维度：
- Openness（开放性）: 想象力、创造力、好奇心
- Conscientiousness（尽责性）: 自律、可靠、勤奋
- Extraversion（外向性）: 社交、活力、健谈
- Agreeableness（宜人性）: 合作、信任、同理心
- Neuroticism（神经质）: 焦虑、情绪波动、敏感

每个维度范围：0-100
- 0-20: 极低
- 21-40: 低
- 41-60: 中等
- 61-80: 高
- 81-100: 极高
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random


class PersonalityTrait(str, Enum):
    """人格特质枚举"""
    OPENNESS = "openness"  # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 宜人性
    NEUROTICISM = "neuroticism"  # 神经质


# 人格特质描述词映射
TRAIT_DESCRIPTORS = {
    PersonalityTrait.OPENNESS: {
        "low": ["保守", "传统", "务实", "脚踏实地"],
        "mid": ["平衡", "适度开放", "有选择地尝新"],
        "high": ["富有想象力", "有创造力", "好奇心强", "思想开放"],
    },
    PersonalityTrait.CONSCIENTIOUSNESS: {
        "low": ["随性", "灵活", "即兴", "不拘小节"],
        "mid": ["适度自律", "基本可靠", "有时拖延"],
        "high": ["自律", "有条理", "可靠", "勤奋", "做事认真"],
    },
    PersonalityTrait.EXTRAVERSION: {
        "low": ["内向", "安静", "独处爱好者", "深思熟虑"],
        "mid": ["外向内向兼具", "社交适度", "选择性社交"],
        "high": ["外向", "健谈", "精力充沛", "喜欢社交", "热情"],
    },
    PersonalityTrait.AGREEABLENESS: {
        "low": ["独立", "直率", "竞争意识强", "质疑型"],
        "mid": ["基本友善", "有时固执", "理性同情"],
        "high": ["友善", "乐于助人", "有同理心", "信任他人", "温和"],
    },
    PersonalityTrait.NEUROTICISM: {
        "low": ["情绪稳定", "冷静", "抗压能力强", "乐观"],
        "mid": ["偶尔焦虑", "情绪正常波动", "压力下可控"],
        "high": ["敏感", "容易焦虑", "情绪波动大", "多虑"],
    },
}


@dataclass
class Personality:
    """
    智能体人格模型
    
    基于大五人格理论，每个维度0-100分
    人格影响：
    - 决策倾向
    - 社交偏好
    - 情绪反应
    - 工作方式
    """
    
    openness: int = 50  # 开放性
    conscientiousness: int = 50  # 尽责性
    extraversion: int = 50  # 外向性
    agreeableness: int = 50  # 宜人性
    neuroticism: int = 50  # 神经质
    
    def __post_init__(self):
        """验证数值范围"""
        for trait in PersonalityTrait:
            value = getattr(self, trait.value)
            if not 0 <= value <= 100:
                raise ValueError(f"{trait.value} 必须在 0-100 之间，当前值: {value}")
    
    def get_trait(self, trait: PersonalityTrait) -> int:
        """获取指定人格特质值"""
        return getattr(self, trait.value)
    
    def set_trait(self, trait: PersonalityTrait, value: int) -> None:
        """设置人格特质值（通常不变，但支持微调）"""
        if not 0 <= value <= 100:
            raise ValueError(f"值必须在 0-100 之间")
        setattr(self, trait.value, value)
    
    def get_level(self, trait: PersonalityTrait) -> str:
        """
        获取特质等级描述
        
        Returns:
            "low" | "mid" | "high"
        """
        value = self.get_trait(trait)
        if value <= 35:
            return "low"
        elif value <= 65:
            return "mid"
        else:
            return "high"
    
    def get_descriptors(self, trait: PersonalityTrait) -> List[str]:
        """获取特质描述词列表"""
        level = self.get_level(trait)
        return TRAIT_DESCRIPTORS[trait][level]
    
    def get_description(self) -> str:
        """
        生成人格的自然语言描述
        
        用于LLM提示词中描述智能体性格
        """
        descriptions = []
        
        for trait in PersonalityTrait:
            descriptors = self.get_descriptors(trait)
            # 随机选择1-2个描述词
            selected = random.sample(descriptors, min(2, len(descriptors)))
            descriptions.extend(selected)
        
        # 去重并随机排序
        unique_descriptions = list(set(descriptions))
        random.shuffle(unique_descriptions)
        
        # 取前4-5个特点
        return "、".join(unique_descriptions[:5])
    
    def get_full_description(self) -> str:
        """获取完整的人格描述（用于详细展示）"""
        lines = []
        for trait in PersonalityTrait:
            value = self.get_trait(trait)
            level = self.get_level(trait)
            trait_names = {
                PersonalityTrait.OPENNESS: "开放性",
                PersonalityTrait.CONSCIENTIOUSNESS: "尽责性",
                PersonalityTrait.EXTRAVERSION: "外向性",
                PersonalityTrait.AGREEABLENESS: "宜人性",
                PersonalityTrait.NEUROTICISM: "神经质",
            }
            lines.append(f"{trait_names[trait]}: {value}/100 ({level})")
        return "\n".join(lines)
    
    # ===================
    # 人格对行为的影响
    # ===================
    
    def social_tendency(self) -> float:
        """
        社交倾向
        
        外向性高 → 更愿意社交
        宜人性高 → 社交更顺利
        神经质高 → 社交焦虑
        
        Returns:
            0-1 之间的值，越高越倾向社交
        """
        base = self.extraversion / 100
        modifier = (self.agreeableness - 50) / 200  # ±0.25
        anxiety = (self.neuroticism - 50) / 400  # ±0.125 负面影响
        
        return max(0, min(1, base + modifier - anxiety))
    
    def work_efficiency(self) -> float:
        """
        工作效率倾向
        
        尽责性高 → 效率高
        开放性适中 → 创新与稳定平衡
        神经质低 → 更专注
        
        Returns:
            0-1 之间的值
        """
        base = self.conscientiousness / 100
        focus = (100 - self.neuroticism) / 200  # 低神经质加成
        
        return max(0, min(1, base * 0.7 + focus * 0.3))
    
    def risk_tolerance(self) -> float:
        """
        风险承受能力
        
        开放性高 → 更愿意冒险
        神经质低 → 更敢冒险
        尽责性高 → 更谨慎
        
        Returns:
            0-1 之间的值
        """
        openness_factor = self.openness / 100
        stability_factor = (100 - self.neuroticism) / 100
        caution_factor = (100 - self.conscientiousness) / 100
        
        return (openness_factor * 0.4 + stability_factor * 0.4 + caution_factor * 0.2)
    
    def emotional_stability(self) -> float:
        """
        情绪稳定性
        
        Returns:
            0-1 之间的值，越高越稳定
        """
        return (100 - self.neuroticism) / 100
    
    def creativity(self) -> float:
        """
        创造力倾向
        
        Returns:
            0-1 之间的值
        """
        return self.openness / 100
    
    # ===================
    # 序列化方法
    # ===================
    
    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {
            trait.value: self.get_trait(trait)
            for trait in PersonalityTrait
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Personality":
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def random(cls, variation: int = 30) -> "Personality":
        """
        生成随机人格
        
        Args:
            variation: 从均值50的最大偏离量
        
        Returns:
            随机生成的人格
        """
        def random_value():
            # 使用正态分布，均值50，大部分值在50±variation内
            value = int(random.gauss(50, variation / 2))
            return max(0, min(100, value))
        
        return cls(
            openness=random_value(),
            conscientiousness=random_value(),
            extraversion=random_value(),
            agreeableness=random_value(),
            neuroticism=random_value(),
        )
    
    @classmethod
    def from_archetype(cls, archetype: str) -> "Personality":
        """
        从预设人格原型创建
        
        Args:
            archetype: 原型名称
        
        原型列表:
        - "leader": 领导者型
        - "creative": 创意型
        - "caretaker": 照顾者型
        - "analyst": 分析师型
        - "adventurer": 冒险者型
        - "peacemaker": 和平者型
        """
        archetypes = {
            "leader": cls(
                openness=65,
                conscientiousness=80,
                extraversion=75,
                agreeableness=55,
                neuroticism=30,
            ),
            "creative": cls(
                openness=90,
                conscientiousness=45,
                extraversion=60,
                agreeableness=65,
                neuroticism=55,
            ),
            "caretaker": cls(
                openness=55,
                conscientiousness=70,
                extraversion=60,
                agreeableness=90,
                neuroticism=45,
            ),
            "analyst": cls(
                openness=70,
                conscientiousness=85,
                extraversion=35,
                agreeableness=50,
                neuroticism=40,
            ),
            "adventurer": cls(
                openness=85,
                conscientiousness=40,
                extraversion=80,
                agreeableness=60,
                neuroticism=35,
            ),
            "peacemaker": cls(
                openness=50,
                conscientiousness=55,
                extraversion=45,
                agreeableness=85,
                neuroticism=50,
            ),
        }
        
        if archetype not in archetypes:
            raise ValueError(f"未知原型: {archetype}，可用: {list(archetypes.keys())}")
        
        # 在原型基础上添加一些随机变化
        base = archetypes[archetype]
        return cls(
            openness=max(0, min(100, base.openness + random.randint(-10, 10))),
            conscientiousness=max(0, min(100, base.conscientiousness + random.randint(-10, 10))),
            extraversion=max(0, min(100, base.extraversion + random.randint(-10, 10))),
            agreeableness=max(0, min(100, base.agreeableness + random.randint(-10, 10))),
            neuroticism=max(0, min(100, base.neuroticism + random.randint(-10, 10))),
        )
