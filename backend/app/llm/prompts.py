"""
提示词模板模块
==============
管理所有AI调用的提示词模板

设计原则：
1. 所有提示词都要清晰描述角色和任务
2. 输出格式要明确（通常使用JSON）
3. 包含足够的上下文信息
4. 支持动态参数替换
"""

from string import Template
from typing import Dict, Any


class PromptTemplates:
    """
    提示词模板集合
    
    所有智能体决策相关的提示词模板
    使用Python的string.Template进行参数替换
    """
    
    # ===================
    # 智能体决策提示词（核心）
    # ===================
    
    AGENT_DECISION = Template("""你是一个生活在虚拟小镇的居民。

## 你的身份
- 姓名：$name
- 年龄：$age岁
- 职业：$occupation
- 性格特点：$personality_description

## 你的当前状态
- 位置：$current_location
- 当前时间：$current_time
- 今日已工作：$work_hours_today 小时
- 账户余额：$balance 元

## 你的需求状态（0-100，越高越紧迫）
- 饥饿程度：$hunger
- 疲劳程度：$fatigue
- 社交需求：$social
- 娱乐需求：$entertainment

## 你的近期记忆
$recent_memories

## 你周围的情况
$surroundings

## 小镇可去的地点（只能选择以下地点）
$available_locations

## 可选的行动
1. MOVE: 移动到某个地点（目标必须从上面的地点列表选择）
2. WORK: 工作（如果在工作地点）
3. EAT: 吃饭（如果在餐厅/咖啡馆）
4. REST: 休息
5. CHAT: 与附近的人交谈
6. SHOP: 购物（如果在超市/商场）
7. IDLE: 闲逛/发呆

## 任务
根据你的身份、当前状态、需求和周围环境，决定接下来要做什么。
像一个真实的人一样思考和决策，不要机械地只看数值。
**重要：如果选择MOVE，target必须是上面地点列表中的完整名称**

请按以下JSON格式回答：
{
    "thinking": "你当前的想法和决策理由（1-2句话）",
    "action": "行动类型（如：MOVE/WORK/EAT/REST/CHAT/SHOP/IDLE）",
    "target": "行动目标（地点名称必须从列表中选择，交谈对象用名字）",
    "reason": "简短说明为什么这样决定"
}""")
    
    # ===================
    # 对话生成提示词
    # ===================
    
    CONVERSATION_START = Template("""你正在扮演 $name，一位 $age 岁的 $occupation。

## 你的性格
$personality_description

## 场景
你在 $location 遇到了 $other_name（$other_occupation）。
你们之间的关系：$relationship_description
当前时间：$current_time

## 你对对方的了解
$knowledge_about_other

## 对话历史
这是你们第 $encounter_count 次相遇。
$previous_topics

## 任务
作为 $name，用自然的方式开始一段对话。
考虑你的性格、你们的关系、当前时间和地点。

请直接说出对话内容，不需要加引号或说明谁在说话。
对话应该自然、符合角色性格，1-2句话即可。""")
    
    CONVERSATION_REPLY = Template("""你正在扮演 $name，一位 $age 岁的 $occupation。

## 你的性格
$personality_description

## 场景
你正在 $location 与 $other_name（$other_occupation）交谈。
你们之间的关系：$relationship_description

## 对话记录
$conversation_history

## 任务
作为 $name，继续这段对话。回复对方刚才说的话。
考虑你的性格和你们的关系。

请直接说出回复内容，不需要加引号或说明谁在说话。
回复应该自然、符合角色性格，1-2句话即可。

如果你认为对话应该结束了（比如告别），请在回复后加上 [END]。""")
    
    # ===================
    # 对话分析提示词
    # ===================
    
    ANALYZE_CONVERSATION = Template("""分析以下对话：

## 对话参与者
- $name1（$occupation1）
- $name2（$occupation2）
他们之前的关系亲密度：$previous_closeness（0-100）

## 对话内容
$conversation_text

## 任务
分析这段对话，提取以下信息：

请以JSON格式回答：
{
    "topics": ["讨论的话题列表"],
    "emotions": {
        "$name1": "主要情绪（如：开心/平静/不满/尴尬等）",
        "$name2": "主要情绪"
    },
    "relationship_change": "关系变化数值（-10到+10，正数表示关系变好）",
    "summary": "对话摘要（一句话）",
    "memorable_for_$name1": "对$name1来说值得记住的事",
    "memorable_for_$name2": "对$name2来说值得记住的事"
}""")
    
    # ===================
    # 智能体生成提示词
    # ===================
    
    GENERATE_AGENT = Template("""请为一个虚拟小镇创建一个新居民。

## 小镇需求
当前小镇缺少：$needed_roles
小镇已有人口：$current_population 人

## 现有居民示例（供参考，不要完全模仿）
$existing_agents_sample

## 任务
创建一个新居民，填补小镇的需求。
创造一个有特点、有故事的角色，而不是模板化的人物。

请以JSON格式回答：
{
    "name": "姓名（中文）",
    "age": "年龄（18-70）",
    "gender": "性别（男/女）",
    "occupation": "职业",
    "personality": {
        "openness": "开放性（0-100）",
        "conscientiousness": "尽责性（0-100）",
        "extraversion": "外向性（0-100）",
        "agreeableness": "宜人性（0-100）",
        "neuroticism": "神经质（0-100）"
    },
    "backstory": "背景故事（2-3句话）",
    "traits": ["性格特点1", "性格特点2"],
    "initial_location": "初始位置（选择一个合适的地点）"
}""")
    
    # ===================
    # Phase 6: 智能体架构增强 - 记忆评分
    # ===================
    
    MEMORY_IMPORTANCE_RATING = Template("""On the scale of 1 to 10, where 1 is purely mundane 
(e.g., brushing teeth, making bed, routine commute) and 10 is extremely 
poignant (e.g., a break up, getting promoted, death of a loved one), rate the 
likely poignancy of the following piece of memory.

Memory: $content

Respond with ONLY a single integer from 1 to 10, nothing else.""")

    # ===================
    # Phase 6: 智能体架构增强 - 反思机制
    # ===================
    
    REFLECTION_QUESTIONS = Template("""Given only the information above, what are 3 most salient 
high-level questions we can answer about the subjects in the statements?

Recent memories of $agent_name:
$memories

Output exactly 3 questions, one per line, without numbering.""")

    REFLECTION_INSIGHTS = Template("""$agent_name is reflecting on their recent experiences.

Question: $question

Relevant memories:
$relevant_memories

Based on the memories above, what is a high-level insight or conclusion that $agent_name 
might draw? The insight should be about $agent_name themselves or their relationships.

Respond with a single insight statement in Chinese, starting with "$agent_name" as the subject.""")

    # ===================
    # Phase 6: 智能体架构增强 - 层级计划
    # ===================
    
    DAILY_PLAN = Template("""你是 $name，$age 岁，职业是 $occupation。

## 你的性格特点
$personality_description

## 今日日期
$date（$weekday）

## 你的生活情况
- 家的位置：$home_location
- 工作地点：$work_location
- 当前余额：$balance 元

## 任务
为今天制定一个大致的日程安排（从早上6点到晚上12点）。
考虑你的职业、性格和生活习惯，安排4-6个主要时间块。

请以JSON格式回答：
{
    "plan": [
        {"start": "06:00", "end": "07:00", "activity": "起床洗漱", "location": "家"},
        {"start": "07:00", "end": "08:00", "activity": "吃早餐", "location": "家或咖啡馆"},
        ...
    ]
}""")

    HOURLY_DECOMPOSE = Template("""将以下时间块分解为更具体的小时级活动。

时间块：$start_time - $end_time
活动：$activity
地点：$location

请分解为具体的1小时内的活动安排，以JSON格式回答：
{
    "tasks": [
        {"start": "$start_time", "end": "XX:XX", "task": "具体任务", "location": "具体地点"},
        ...
    ]
}""")

    TASK_DECOMPOSE = Template("""将以下小时活动分解为5-15分钟的具体任务。

时间：$start_time - $end_time
活动：$activity

请分解为更细粒度的任务，以JSON格式回答：
{
    "micro_tasks": [
        {"start": "$start_time", "duration_minutes": 10, "task": "具体动作"},
        ...
    ]
}""")

    # ===================
    # Phase 6: 智能体架构增强 - React & Replan
    # ===================
    
    SHOULD_REACT = Template("""$agent_name 正在 $current_activity。

## 当前观察到的情况
$perception

## $agent_name 的当前计划
$current_plan

## 任务
判断 $agent_name 是否应该对观察到的情况做出反应，还是继续当前的活动。

考虑因素：
- 观察到的事情是否紧急或重要？
- 是否有人在叫 $agent_name 或等待回应？
- 打断当前活动的代价有多大？
- $agent_name 的性格会如何影响这个决定？

请以JSON格式回答：
{
    "should_react": true或false,
    "reaction_type": "continue"（继续当前活动）| "interrupt"（中断去处理）| "note"（记住但继续）,
    "reaction": "如果要反应，描述具体反应内容",
    "reason": "做出这个决定的原因"
}""")

    REPLAN_FROM_NOW = Template("""$agent_name 刚刚 $what_happened，需要重新规划剩余时间。

## 当前时间
$current_time

## 原定计划（剩余部分）
$remaining_plan

## 任务
根据刚才发生的事情，重新规划从现在到今天结束的活动安排。

请以JSON格式回答：
{
    "new_plan": [
        {"start": "$current_time", "end": "XX:XX", "activity": "活动", "location": "地点"},
        ...
    ]
}""")
    
    @classmethod
    def render(cls, template_name: str, **kwargs) -> str:
        """
        渲染提示词模板
        
        Args:
            template_name: 模板名称
            **kwargs: 模板参数
        
        Returns:
            渲染后的提示词字符串
        """
        template = getattr(cls, template_name, None)
        if template is None:
            raise ValueError(f"未知模板: {template_name}")
        
        return template.safe_substitute(**kwargs)


# 便捷函数
def render_prompt(template_name: str, **kwargs) -> str:
    """渲染提示词模板的便捷函数"""
    return PromptTemplates.render(template_name, **kwargs)
