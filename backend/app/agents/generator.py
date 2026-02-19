"""
智能体生成器
===========
使用LLM生成独特的智能体，或使用预设模板快速生成

生成方式：
1. LLM生成：调用AI生成独特的人物设定
2. 模板生成：使用预定义的角色模板快速生成
3. 混合生成：模板+随机变化
"""

import asyncio
import json
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from loguru import logger

from app.agents.models import Agent, Position
from app.agents.personality import Personality
from app.agents.needs import Needs
from app.agents.manager import agent_manager
from app.core.config import settings
from app.core.locations import location_manager, LocationType
from app.llm import llm_router
from app.llm.prompts import PromptTemplates


# 预定义的职业列表（确保小镇多样性）
OCCUPATIONS = [
    # 服务业
    "咖啡师", "厨师", "服务员", "理发师", "快递员",
    # 技术类
    "程序员", "设计师", "工程师", "数据分析师",
    # 文化类
    "作家", "画家", "音乐人", "摄影师", "教师",
    # 商业类
    "店主", "销售员", "会计", "创业者",
    # 医疗类
    "医生", "护士", "心理咨询师",
    # 其他
    "自由职业", "退休老人", "大学生", "保安",
]

# 中文名字库
SURNAMES = ["张", "李", "王", "刘", "陈", "杨", "黄", "赵", "周", "吴",
            "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "郑"]

MALE_NAMES = ["伟", "强", "磊", "军", "勇", "杰", "涛", "明", "超", "华",
              "浩", "宇", "轩", "博", "睿", "俊", "辉", "阳", "帆", "鹏"]

FEMALE_NAMES = ["芳", "娜", "敏", "静", "丽", "艳", "玲", "婷", "雪", "琳",
                "颖", "慧", "洁", "萍", "红", "梅", "倩", "薇", "云", "晴"]

# 性格特点标签库
TRAIT_TAGS = [
    "开朗", "内向", "幽默", "严肃", "热心", "冷漠", "乐观", "悲观",
    "勤劳", "懒散", "细心", "粗心", "果断", "犹豫", "大方", "节俭",
    "健谈", "沉默", "冒险", "谨慎", "理性", "感性", "独立", "依赖",
    "有创意", "务实", "完美主义", "随性", "好奇", "保守",
]


def generate_random_name(gender: str = "男") -> str:
    """生成随机中文名字"""
    surname = random.choice(SURNAMES)
    if gender == "女":
        given = random.choice(FEMALE_NAMES)
        if random.random() < 0.3:
            given += random.choice(FEMALE_NAMES)
    else:
        given = random.choice(MALE_NAMES)
        if random.random() < 0.3:
            given += random.choice(MALE_NAMES)
    return surname + given


def generate_backstory(name: str, age: int, occupation: str, personality: Personality) -> str:
    """生成简单的背景故事"""
    templates = [
        f"{name}是一位{age}岁的{occupation}，在小镇上生活了多年。",
        f"作为一名{occupation}，{name}对自己的工作充满热情。",
        f"{name}今年{age}岁，是这个小镇的居民之一。",
        f"从事{occupation}工作的{name}，在小镇上有着自己的生活圈子。",
    ]
    
    base = random.choice(templates)
    
    # 根据人格添加描述
    if personality.extraversion > 70:
        base += "性格外向，喜欢结交朋友。"
    elif personality.extraversion < 30:
        base += "性格内向，喜欢独处。"
    
    if personality.openness > 70:
        base += "对新事物充满好奇。"
    
    return base


async def generate_agent_with_llm(
    needed_roles: str = "",
    existing_sample: str = "",
    max_retries: int = 2,
) -> Optional[Agent]:
    """
    使用LLM生成智能体
    
    Args:
        needed_roles: 小镇需要的角色
        existing_sample: 现有居民示例
        max_retries: 最大重试次数
    
    Returns:
        生成的Agent对象
    """
    prompt = PromptTemplates.render(
        "GENERATE_AGENT",
        needed_roles=needed_roles or "各种职业都需要",
        current_population=agent_manager.count(),
        existing_agents_sample=existing_sample or "暂无",
    )
    
    for attempt in range(max_retries + 1):
        try:
            response = await llm_router.generate(
                prompt=prompt,
                temperature=0.9,  # 高温度增加多样性
                max_tokens=800,
            )
            
            # 解析JSON
            content = response.content
            
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                
                # 创建Agent
                agent = Agent(
                    name=data.get("name", generate_random_name()),
                    age=int(data.get("age", random.randint(20, 60))),
                    gender=data.get("gender", random.choice(["男", "女"])),
                    occupation=data.get("occupation", random.choice(OCCUPATIONS)),
                    backstory=data.get("backstory", ""),
                    traits=data.get("traits", []),
                    personality=Personality(
                        openness=int(data.get("personality", {}).get("openness", 50)),
                        conscientiousness=int(data.get("personality", {}).get("conscientiousness", 50)),
                        extraversion=int(data.get("personality", {}).get("extraversion", 50)),
                        agreeableness=int(data.get("personality", {}).get("agreeableness", 50)),
                        neuroticism=int(data.get("personality", {}).get("neuroticism", 50)),
                    ),
                    needs=Needs.random(),
                )
                
                logger.info(f"LLM生成智能体: {agent.name} ({agent.occupation})")
                return agent
        
        except Exception as e:
            logger.warning(f"LLM生成智能体失败 (尝试 {attempt + 1}): {e}")
    
    return None


def generate_agent_from_template(
    occupation: Optional[str] = None,
    gender: Optional[str] = None,
    archetype: Optional[str] = None,
) -> Agent:
    """
    使用模板快速生成智能体
    
    Args:
        occupation: 指定职业
        gender: 指定性别
        archetype: 人格原型
    
    Returns:
        生成的Agent对象
    """
    gender = gender or random.choice(["男", "女"])
    name = generate_random_name(gender)
    occupation = occupation or random.choice(OCCUPATIONS)
    
    # 根据职业调整年龄范围
    if occupation in ["大学生"]:
        age = random.randint(18, 24)
    elif occupation in ["退休老人"]:
        age = random.randint(60, 80)
    else:
        age = random.randint(22, 55)
    
    # 生成人格
    if archetype:
        personality = Personality.from_archetype(archetype)
    else:
        personality = Personality.random()
    
    # 生成背景故事
    backstory = generate_backstory(name, age, occupation, personality)
    
    # 随机选择性格标签
    traits = random.sample(TRAIT_TAGS, k=random.randint(2, 4))
    
    agent = Agent(
        name=name,
        age=age,
        gender=gender,
        occupation=occupation,
        backstory=backstory,
        traits=traits,
        personality=personality,
        needs=Needs.random(max_value=40),
        balance=settings.initial_balance * random.uniform(0.5, 1.5),
    )
    
    return agent


def assign_location(agent: Agent) -> None:
    """
    为智能体分配初始位置
    
    根据职业分配家和工作地点
    """
    # 获取可用地点
    apartments = location_manager.get_locations_by_type(LocationType.APARTMENT)
    
    # 分配住所
    if apartments:
        home = random.choice(apartments)
        if not home.is_full:
            agent.home_location_id = home.id
            agent.move_to(home.x, home.y, home.id, home.name)
            home.enter(agent.id)
    
    # 根据职业分配工作地点
    work_locations = {
        "程序员": ["office"],
        "设计师": ["office"],
        "工程师": ["office"],
        "数据分析师": ["office"],
        "咖啡师": ["cafe"],
        "厨师": ["restaurant"],
        "服务员": ["restaurant", "cafe"],
        "店主": ["shop", "supermarket"],
        "销售员": ["shop", "supermarket"],
        "医生": ["hospital"],
        "护士": ["hospital"],
        "教师": ["school"],
        "保安": ["office", "supermarket"],
    }
    
    work_types = work_locations.get(agent.occupation, [])
    if work_types:
        for work_type in work_types:
            try:
                loc_type = LocationType(work_type)
                locations = location_manager.get_locations_by_type(loc_type)
            except ValueError:
                locations = []
            if locations:
                work = random.choice(locations)
                agent.work_location_id = work.id
                break


async def generate_initial_agents(
    count: int = None,
    use_llm_ratio: float = 0.2,
    occupation_distribution: Optional[Dict[str, int]] = None,
) -> List[Agent]:
    """
    生成初始智能体群体
    
    Args:
        count: 生成数量，默认使用配置
        use_llm_ratio: 使用LLM生成的比例
        occupation_distribution: 职业分布（可选）
    
    Returns:
        生成的智能体列表
    """
    count = count or settings.initial_agent_count
    agents = []
    
    # 计算LLM生成数量
    llm_count = int(count * use_llm_ratio)
    template_count = count - llm_count
    
    logger.info(f"开始生成 {count} 个智能体 (LLM: {llm_count}, 模板: {template_count})")
    
    # 确保职业多样性
    used_names: Set[str] = set()
    occupation_counts: Dict[str, int] = {}
    
    # 模板生成
    for i in range(template_count):
        # 选择还没满的职业
        available_occupations = [
            occ for occ in OCCUPATIONS
            if occupation_counts.get(occ, 0) < 3
        ]
        
        if not available_occupations:
            available_occupations = OCCUPATIONS
        
        occupation = random.choice(available_occupations)
        
        # 生成智能体
        agent = generate_agent_from_template(occupation=occupation)
        
        # 确保名字唯一
        while agent.name in used_names:
            agent.name = generate_random_name(agent.gender)
        
        used_names.add(agent.name)
        occupation_counts[occupation] = occupation_counts.get(occupation, 0) + 1
        
        # 分配位置
        assign_location(agent)
        
        # 添加到管理器
        agent_manager.add(agent)
        agents.append(agent)
        
        if (i + 1) % 10 == 0:
            logger.info(f"模板生成进度: {i + 1}/{template_count}")
    
    # LLM生成（更独特的角色）
    if llm_count > 0:
        # 获取现有居民样本
        sample_agents = random.sample(agents, min(3, len(agents)))
        existing_sample = "\n".join([
            f"- {a.name}（{a.occupation}，{a.age}岁）"
            for a in sample_agents
        ])
        
        # 确定需要的角色
        needed = []
        for occ in OCCUPATIONS:
            if occupation_counts.get(occ, 0) == 0:
                needed.append(occ)
        
        for i in range(llm_count):
            needed_roles = random.choice(needed) if needed else "有特色的角色"
            
            agent = await generate_agent_with_llm(
                needed_roles=needed_roles,
                existing_sample=existing_sample,
            )
            
            if agent:
                # 确保名字唯一
                while agent.name in used_names:
                    agent.name = generate_random_name(agent.gender)
                
                used_names.add(agent.name)
                
                # 分配位置
                assign_location(agent)
                
                # 添加到管理器
                agent_manager.add(agent)
                agents.append(agent)
            else:
                # 回退到模板生成
                agent = generate_agent_from_template()
                while agent.name in used_names:
                    agent.name = generate_random_name(agent.gender)
                used_names.add(agent.name)
                assign_location(agent)
                agent_manager.add(agent)
                agents.append(agent)
            
            # 控制API调用频率
            await asyncio.sleep(0.5)
    
    logger.info(f"智能体生成完成，共 {len(agents)} 个")
    return agents


async def generate_single_agent(
    use_llm: bool = False,
    occupation: Optional[str] = None,
) -> Agent:
    """
    生成单个智能体
    
    Args:
        use_llm: 是否使用LLM生成
        occupation: 指定职业
    
    Returns:
        生成的Agent
    """
    if use_llm:
        agent = await generate_agent_with_llm(needed_roles=occupation or "")
        if agent:
            assign_location(agent)
            agent_manager.add(agent)
            return agent
    
    # 回退到模板
    agent = generate_agent_from_template(occupation=occupation)
    assign_location(agent)
    agent_manager.add(agent)
    return agent
