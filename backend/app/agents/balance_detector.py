"""
社会平衡检测器
=============
检测社会中的各种失衡情况，为自动扩展提供依据

检测项目：
- 职业缺口：某些服务岗位人手不足
- 社交孤岛：社交需求高但关系少的智能体
- 人口平衡：年龄、性别、职业分布是否健康
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from loguru import logger

from app.agents.manager import agent_manager
from app.agents.models import Agent
from app.core.locations import location_manager


@dataclass
class OccupationGap:
    """职业缺口"""
    occupation: str
    location_type: str
    location_name: str
    current_count: int
    needed_count: int
    priority: float  # 优先级 0-1
    
    @property
    def gap(self) -> int:
        """缺口数量"""
        return max(0, self.needed_count - self.current_count)


@dataclass
class SocialIsolate:
    """社交孤岛"""
    agent_id: str
    agent_name: str
    social_need: float  # 社交需求 0-100
    relationship_count: int
    loneliness_score: float  # 孤独分数 0-1
    recommended_match_traits: List[str]  # 推荐匹配的特质


@dataclass
class PopulationImbalance:
    """人口失衡"""
    category: str  # "age", "gender", "occupation"
    current_distribution: Dict[str, int]
    ideal_distribution: Dict[str, float]
    imbalance_score: float  # 失衡分数 0-1
    recommendations: List[str]


@dataclass
class SocialBalanceReport:
    """社会平衡报告"""
    timestamp: datetime
    total_population: int
    
    # 检测结果
    occupation_gaps: List[OccupationGap]
    social_isolates: List[SocialIsolate]
    population_imbalances: List[PopulationImbalance]
    
    # 汇总
    overall_health_score: float  # 整体健康分数 0-100
    urgent_needs: List[str]  # 紧急需求
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_population": self.total_population,
            "occupation_gaps": [
                {
                    "occupation": g.occupation,
                    "location": g.location_name,
                    "gap": g.gap,
                    "priority": g.priority,
                }
                for g in self.occupation_gaps
            ],
            "social_isolates_count": len(self.social_isolates),
            "population_imbalances": [
                {
                    "category": i.category,
                    "score": i.imbalance_score,
                    "recommendations": i.recommendations,
                }
                for i in self.population_imbalances
            ],
            "overall_health_score": self.overall_health_score,
            "urgent_needs": self.urgent_needs,
        }


# ===================
# 职业-地点映射配置
# ===================

# 每种地点类型需要的职业及最低人数
LOCATION_OCCUPATION_NEEDS = {
    "cafe": {
        "咖啡师": {"min": 1, "max": 3, "priority": 0.9},
        "服务员": {"min": 1, "max": 2, "priority": 0.7},
    },
    "restaurant": {
        "厨师": {"min": 1, "max": 2, "priority": 0.9},
        "服务员": {"min": 1, "max": 3, "priority": 0.8},
    },
    "hospital": {
        "医生": {"min": 1, "max": 3, "priority": 1.0},
        "护士": {"min": 1, "max": 4, "priority": 0.9},
    },
    "supermarket": {
        "店主": {"min": 1, "max": 1, "priority": 0.8},
        "销售员": {"min": 1, "max": 3, "priority": 0.6},
    },
    "shop": {
        "店主": {"min": 1, "max": 1, "priority": 0.8},
    },
    "office": {
        "程序员": {"min": 2, "max": 10, "priority": 0.5},
        "设计师": {"min": 1, "max": 5, "priority": 0.5},
    },
    "school": {
        "教师": {"min": 1, "max": 5, "priority": 0.8},
    },
}

# 理想的职业分布比例
IDEAL_OCCUPATION_RATIO = {
    "服务业": 0.25,  # 咖啡师、厨师、服务员等
    "技术类": 0.20,  # 程序员、设计师、工程师等
    "文化类": 0.15,  # 作家、画家、教师等
    "商业类": 0.15,  # 店主、销售员等
    "医疗类": 0.10,  # 医生、护士等
    "其他": 0.15,    # 自由职业、学生等
}

# 职业分类
OCCUPATION_CATEGORIES = {
    "服务业": ["咖啡师", "厨师", "服务员", "理发师", "快递员"],
    "技术类": ["程序员", "设计师", "工程师", "数据分析师"],
    "文化类": ["作家", "画家", "音乐人", "摄影师", "教师"],
    "商业类": ["店主", "销售员", "会计", "创业者"],
    "医疗类": ["医生", "护士", "心理咨询师"],
    "其他": ["自由职业", "退休老人", "大学生", "保安"],
}


class SocialBalanceDetector:
    """社会平衡检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self._last_report: Optional[SocialBalanceReport] = None
        self._report_history: List[SocialBalanceReport] = []
    
    # ===================
    # 职业缺口检测
    # ===================
    
    def detect_occupation_gaps(self) -> List[OccupationGap]:
        """
        检测职业缺口
        
        根据各地点的实际需求，检查是否有岗位人手不足
        
        Returns:
            职业缺口列表
        """
        gaps = []
        
        # 获取所有智能体的职业分布
        agents = agent_manager.get_all()
        occupation_by_work_location: Dict[str, Dict[str, int]] = {}
        
        for agent in agents:
            work_loc = agent.work_location_id
            if work_loc:
                if work_loc not in occupation_by_work_location:
                    occupation_by_work_location[work_loc] = {}
                occ = agent.occupation
                occupation_by_work_location[work_loc][occ] = \
                    occupation_by_work_location[work_loc].get(occ, 0) + 1
        
        # 检查每个地点的职业需求
        for location in location_manager.locations.values():
            loc_type = location.type
            
            if loc_type not in LOCATION_OCCUPATION_NEEDS:
                continue
            
            needs = LOCATION_OCCUPATION_NEEDS[loc_type]
            current = occupation_by_work_location.get(location.id, {})
            
            for occupation, config in needs.items():
                current_count = current.get(occupation, 0)
                min_needed = config["min"]
                priority = config["priority"]
                
                if current_count < min_needed:
                    gaps.append(OccupationGap(
                        occupation=occupation,
                        location_type=loc_type,
                        location_name=location.name,
                        current_count=current_count,
                        needed_count=min_needed,
                        priority=priority,
                    ))
        
        # 按优先级排序
        gaps.sort(key=lambda g: (-g.priority, -g.gap))
        
        return gaps
    
    def get_most_needed_occupation(self) -> Optional[Tuple[str, str]]:
        """
        获取最需要的职业
        
        Returns:
            (职业名称, 目标地点ID) 或 None
        """
        gaps = self.detect_occupation_gaps()
        
        if not gaps:
            return None
        
        # 返回优先级最高的缺口
        top_gap = gaps[0]
        
        # 找到对应的地点
        for location in location_manager.locations.values():
            if location.name == top_gap.location_name:
                return (top_gap.occupation, location.id)
        
        return (top_gap.occupation, None)
    
    # ===================
    # 社交孤岛检测
    # ===================
    
    def detect_social_isolates(
        self,
        loneliness_threshold: float = 0.6,
    ) -> List[SocialIsolate]:
        """
        检测社交孤岛
        
        识别社交需求高但关系较少的智能体
        
        Args:
            loneliness_threshold: 孤独阈值
        
        Returns:
            社交孤岛列表
        """
        isolates = []
        agents = agent_manager.get_all()
        
        for agent in agents:
            # 计算孤独分数
            social_need = agent.needs.social  # 社交需求 0-100
            relationship_count = len(agent.relationships)
            
            # 孤独分数：社交需求高但关系少
            # 公式：(社交需求/100) * (1 - min(关系数/10, 1))
            loneliness = (social_need / 100) * (1 - min(relationship_count / 10, 1))
            
            # 考虑外向性：外向的人更需要社交
            extraversion_factor = agent.personality.extraversion / 100
            loneliness = loneliness * (0.5 + 0.5 * extraversion_factor)
            
            if loneliness >= loneliness_threshold:
                # 推荐匹配特质
                recommended_traits = self._get_recommended_match_traits(agent)
                
                isolates.append(SocialIsolate(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    social_need=social_need,
                    relationship_count=relationship_count,
                    loneliness_score=loneliness,
                    recommended_match_traits=recommended_traits,
                ))
        
        # 按孤独分数排序
        isolates.sort(key=lambda i: -i.loneliness_score)
        
        return isolates
    
    def _get_recommended_match_traits(self, agent: Agent) -> List[str]:
        """获取推荐的匹配特质"""
        traits = []
        
        # 外向者适合和外向者交友
        if agent.personality.extraversion > 60:
            traits.append("外向")
        else:
            traits.append("内向")  # 内向者也适合和内向者交友
        
        # 相似职业
        traits.append(f"相似职业:{agent.occupation}")
        
        # 相近年龄
        if agent.age < 30:
            traits.append("年轻人")
        elif agent.age < 50:
            traits.append("中年人")
        else:
            traits.append("年长者")
        
        return traits
    
    def get_loneliest_agent(self) -> Optional[SocialIsolate]:
        """获取最孤独的智能体"""
        isolates = self.detect_social_isolates()
        return isolates[0] if isolates else None
    
    # ===================
    # 人口平衡检测
    # ===================
    
    def detect_population_imbalances(self) -> List[PopulationImbalance]:
        """
        检测人口失衡
        
        检查年龄、性别、职业分布是否健康
        
        Returns:
            人口失衡列表
        """
        imbalances = []
        agents = agent_manager.get_all()
        
        if not agents:
            return imbalances
        
        # 1. 性别分布检测
        gender_dist = self._get_gender_distribution(agents)
        gender_imbalance = self._check_gender_balance(gender_dist)
        if gender_imbalance:
            imbalances.append(gender_imbalance)
        
        # 2. 年龄分布检测
        age_dist = self._get_age_distribution(agents)
        age_imbalance = self._check_age_balance(age_dist)
        if age_imbalance:
            imbalances.append(age_imbalance)
        
        # 3. 职业分布检测
        occ_dist = self._get_occupation_category_distribution(agents)
        occ_imbalance = self._check_occupation_balance(occ_dist)
        if occ_imbalance:
            imbalances.append(occ_imbalance)
        
        return imbalances
    
    def _get_gender_distribution(self, agents: List[Agent]) -> Dict[str, int]:
        """获取性别分布"""
        dist = {"男": 0, "女": 0}
        for agent in agents:
            gender = agent.gender
            dist[gender] = dist.get(gender, 0) + 1
        return dist
    
    def _check_gender_balance(
        self,
        dist: Dict[str, int],
    ) -> Optional[PopulationImbalance]:
        """检查性别平衡"""
        total = sum(dist.values())
        if total == 0:
            return None
        
        male_ratio = dist.get("男", 0) / total
        female_ratio = dist.get("女", 0) / total
        
        # 理想比例 50:50，允许10%偏差
        ideal = {"男": 0.5, "女": 0.5}
        imbalance_score = abs(male_ratio - 0.5) * 2  # 0-1
        
        if imbalance_score > 0.2:  # 偏差超过10%
            recommendations = []
            if male_ratio > 0.6:
                recommendations.append("需要更多女性角色")
            elif female_ratio > 0.6:
                recommendations.append("需要更多男性角色")
            
            return PopulationImbalance(
                category="gender",
                current_distribution=dist,
                ideal_distribution=ideal,
                imbalance_score=imbalance_score,
                recommendations=recommendations,
            )
        
        return None
    
    def _get_age_distribution(self, agents: List[Agent]) -> Dict[str, int]:
        """获取年龄分布"""
        dist = {"青年(18-30)": 0, "中年(31-50)": 0, "中老年(51+)": 0}
        for agent in agents:
            if agent.age <= 30:
                dist["青年(18-30)"] += 1
            elif agent.age <= 50:
                dist["中年(31-50)"] += 1
            else:
                dist["中老年(51+)"] += 1
        return dist
    
    def _check_age_balance(
        self,
        dist: Dict[str, int],
    ) -> Optional[PopulationImbalance]:
        """检查年龄平衡"""
        total = sum(dist.values())
        if total == 0:
            return None
        
        # 理想比例
        ideal = {"青年(18-30)": 0.35, "中年(31-50)": 0.45, "中老年(51+)": 0.20}
        
        # 计算偏差
        max_deviation = 0
        recommendations = []
        
        for category, ideal_ratio in ideal.items():
            actual_ratio = dist.get(category, 0) / total
            deviation = abs(actual_ratio - ideal_ratio)
            max_deviation = max(max_deviation, deviation)
            
            if actual_ratio < ideal_ratio * 0.5:
                recommendations.append(f"需要更多{category}角色")
        
        if max_deviation > 0.2:
            return PopulationImbalance(
                category="age",
                current_distribution=dist,
                ideal_distribution=ideal,
                imbalance_score=max_deviation,
                recommendations=recommendations,
            )
        
        return None
    
    def _get_occupation_category_distribution(
        self,
        agents: List[Agent],
    ) -> Dict[str, int]:
        """获取职业类别分布"""
        dist = {cat: 0 for cat in OCCUPATION_CATEGORIES}
        
        for agent in agents:
            for category, occupations in OCCUPATION_CATEGORIES.items():
                if agent.occupation in occupations:
                    dist[category] += 1
                    break
            else:
                dist["其他"] += 1
        
        return dist
    
    def _check_occupation_balance(
        self,
        dist: Dict[str, int],
    ) -> Optional[PopulationImbalance]:
        """检查职业平衡"""
        total = sum(dist.values())
        if total == 0:
            return None
        
        # 计算偏差
        max_deviation = 0
        recommendations = []
        
        for category, ideal_ratio in IDEAL_OCCUPATION_RATIO.items():
            actual_ratio = dist.get(category, 0) / total
            deviation = abs(actual_ratio - ideal_ratio)
            max_deviation = max(max_deviation, deviation)
            
            if actual_ratio < ideal_ratio * 0.5:
                recommendations.append(f"需要更多{category}人员")
        
        if max_deviation > 0.15:
            return PopulationImbalance(
                category="occupation",
                current_distribution=dist,
                ideal_distribution=IDEAL_OCCUPATION_RATIO,
                imbalance_score=max_deviation,
                recommendations=recommendations,
            )
        
        return None
    
    # ===================
    # 综合报告
    # ===================
    
    def generate_report(self) -> SocialBalanceReport:
        """
        生成社会平衡报告
        
        Returns:
            完整的社会平衡报告
        """
        timestamp = datetime.now()
        total_population = agent_manager.count()
        
        # 执行各项检测
        occupation_gaps = self.detect_occupation_gaps()
        social_isolates = self.detect_social_isolates()
        population_imbalances = self.detect_population_imbalances()
        
        # 计算整体健康分数
        health_score = self._calculate_health_score(
            occupation_gaps,
            social_isolates,
            population_imbalances,
            total_population,
        )
        
        # 汇总紧急需求
        urgent_needs = self._summarize_urgent_needs(
            occupation_gaps,
            social_isolates,
            population_imbalances,
        )
        
        report = SocialBalanceReport(
            timestamp=timestamp,
            total_population=total_population,
            occupation_gaps=occupation_gaps,
            social_isolates=social_isolates,
            population_imbalances=population_imbalances,
            overall_health_score=health_score,
            urgent_needs=urgent_needs,
        )
        
        # 保存报告
        self._last_report = report
        self._report_history.append(report)
        
        # 只保留最近10份报告
        if len(self._report_history) > 10:
            self._report_history = self._report_history[-10:]
        
        logger.info(f"生成社会平衡报告: 健康分数 {health_score:.1f}, 紧急需求 {len(urgent_needs)} 项")
        
        return report
    
    def _calculate_health_score(
        self,
        occupation_gaps: List[OccupationGap],
        social_isolates: List[SocialIsolate],
        population_imbalances: List[PopulationImbalance],
        total_population: int,
    ) -> float:
        """计算整体健康分数 (0-100)"""
        if total_population == 0:
            return 0.0
        
        score = 100.0
        
        # 职业缺口扣分（每个高优先级缺口扣5分）
        for gap in occupation_gaps:
            score -= gap.gap * gap.priority * 5
        
        # 社交孤岛扣分（每个严重孤岛扣3分）
        for isolate in social_isolates:
            if isolate.loneliness_score > 0.8:
                score -= 3
            else:
                score -= 1
        
        # 人口失衡扣分
        for imbalance in population_imbalances:
            score -= imbalance.imbalance_score * 10
        
        return max(0.0, min(100.0, score))
    
    def _summarize_urgent_needs(
        self,
        occupation_gaps: List[OccupationGap],
        social_isolates: List[SocialIsolate],
        population_imbalances: List[PopulationImbalance],
    ) -> List[str]:
        """汇总紧急需求"""
        needs = []
        
        # 高优先级职业缺口
        for gap in occupation_gaps[:3]:
            if gap.priority >= 0.8:
                needs.append(f"急需{gap.occupation}在{gap.location_name}")
        
        # 严重社交孤岛
        severe_isolates = [i for i in social_isolates if i.loneliness_score > 0.8]
        if len(severe_isolates) >= 3:
            needs.append(f"有{len(severe_isolates)}个智能体严重缺乏社交")
        
        # 人口失衡
        for imbalance in population_imbalances:
            if imbalance.imbalance_score > 0.3:
                needs.extend(imbalance.recommendations[:1])
        
        return needs
    
    @property
    def last_report(self) -> Optional[SocialBalanceReport]:
        """获取最近的报告"""
        return self._last_report


# ===================
# 全局实例
# ===================

social_balance_detector = SocialBalanceDetector()
