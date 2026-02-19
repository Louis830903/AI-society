# 智能体系统规格说明

## 概述

智能体（Agent）是AI Society的核心，每个智能体是一个独立的"AI小人"，有自己的身份、性格、目标、记忆，能够自主决策和行动。

就像一个真实的人：
- 有名字、年龄、职业（身份）
- 有开朗/内向、友善/冷漠（性格）
- 有想成为画家、想赚大钱（人生目标）
- 会记住发生过的事（记忆）
- 会根据情况做决定（决策）

## 智能体数据结构

### 基础属性

```python
class AgentProfile:
    """智能体档案（创建后不变）"""
    id: str              # UUID，唯一标识
    name: str            # 姓名，如"李明"
    age: int             # 年龄，18-80
    gender: Gender       # 性别：male/female/other
    occupation: str      # 职业，如"programmer"
    personality: Personality  # 大五人格
    skills: Dict[str, int]    # 技能表，如{"programming": 80, "social": 60}
    life_goal: str       # 人生目标，如"成为知名画家"
    backstory: str       # 背景故事，50-100字
    model_name: str      # 使用的LLM模型标识
```

### 大五人格模型

```python
class Personality:
    """大五人格（Big Five），每项0-100"""
    openness: int         # 开放性：好奇/保守
    conscientiousness: int  # 尽责性：自律/随性
    extraversion: int     # 外向性：外向/内向
    agreeableness: int    # 宜人性：友善/冷漠
    neuroticism: int      # 神经质：敏感/稳定
```

**性格影响行为的规则：**
- 外向性高(>70)：更主动搭讪、参加社交活动
- 外向性低(<30)：更喜欢独处、减少社交
- 宜人性高(>70)：更容易原谅、建立友谊
- 尽责性高(>70)：更准时上班、完成任务
- 神经质高(>70)：情绪波动大、容易焦虑

### 动态状态

```python
class AgentState:
    """智能体当前状态（实时变化）"""
    # 位置
    x: float
    y: float
    current_location: str  # 位置名称，如"咖啡馆"
    
    # 需求值（0-100）
    energy: int = 100      # 能量，低了要吃饭/睡觉
    social: int = 50       # 社交需求，低了要找人聊天
    happiness: int = 70    # 幸福感，综合指标
    
    # 经济状态
    money: float           # 当前余额（元）
    
    # 行为状态
    current_action: str    # 当前动作，如"walking_to_cafe"
    current_target: str    # 动作目标，如"小红"
    current_thinking: str  # 内心想法（显示给观察者）
    current_emotion: str   # 当前情绪
    
    # 时间戳
    last_decision_time: datetime  # 上次决策时间
    last_meal_time: datetime      # 上次吃饭时间
    last_sleep_time: datetime     # 上次睡觉时间
```

### 关系网络

```python
class Relationship:
    """两个智能体之间的关系"""
    agent_a_id: str
    agent_b_id: str
    relationship_type: str  # stranger/acquaintance/friend/close_friend/lover
    strength: int           # 关系强度，0-100
    last_interaction: datetime
    interaction_count: int
    
    # 关系记忆（A对B的印象）
    impression: str         # "他很有趣"、"她总是迟到"
```

**关系强度阈值：**
- 0-10: stranger（陌生人）
- 11-30: acquaintance（认识）
- 31-60: friend（朋友）
- 61-85: close_friend（好友）
- 86-100: best_friend/lover（挚友/恋人）

## 职业系统

### 职业配置表

| 职业 | 工作地点 | 时薪(元) | 工作时间 | 所需技能 |
|------|----------|----------|----------|----------|
| programmer | 办公楼 | 150 | 9:00-18:00 | programming>60 |
| designer | 办公楼 | 120 | 10:00-19:00 | design>60 |
| waiter | 咖啡馆/餐厅 | 40 | 轮班 | social>40 |
| teacher | 学校 | 100 | 8:00-16:00 | teaching>60 |
| artist | 工作室 | 不固定 | 自由 | art>70 |
| student | 学校 | 0（补贴200/天） | 8:00-16:00 | - |
| retired | - | 0（退休金100/天） | 自由 | - |
| unemployed | - | 0 | 自由 | - |

### 职业行为模板

```python
OCCUPATION_SCHEDULES = {
    "programmer": {
        "work_start": "09:00",
        "work_end": "18:00",
        "lunch_break": "12:00-13:00",
        "work_location": "office_building",
        "income_per_hour": 150
    },
    "waiter": {
        "shifts": ["06:00-14:00", "14:00-22:00"],
        "work_location": ["cafe", "restaurant"],
        "income_per_hour": 40
    },
    # ...
}
```

## 技能系统

### 技能列表

| 技能 | 描述 | 影响 |
|------|------|------|
| programming | 编程能力 | 程序员工作效率 |
| design | 设计能力 | 设计师工作效率 |
| art | 艺术能力 | 画家作品质量 |
| social | 社交能力 | 交友速度、对话质量 |
| teaching | 教学能力 | 教师工作效率 |
| cooking | 烹饪能力 | 厨师工作效率 |
| business | 商业能力 | 创业成功率 |

### 技能成长

```python
# 技能通过实践提升
# 每工作1小时（游戏内），相关技能+0.1
# 上限100

def update_skill(agent, skill_name, hours_worked):
    current = agent.skills.get(skill_name, 0)
    growth = hours_worked * 0.1
    agent.skills[skill_name] = min(100, current + growth)
```

## 需求系统

### 需求衰减规则

```python
# 每游戏内10分钟（现实1分钟）执行一次

NEED_DECAY_RULES = {
    "energy": {
        "base_decay": 2,           # 基础衰减
        "working_decay": 5,        # 工作时额外衰减
        "walking_decay": 3,        # 走路时额外衰减
        "resting_recovery": 10,    # 休息时恢复
        "sleeping_recovery": 20,   # 睡觉时恢复
        "eating_recovery": 30      # 吃饭时恢复
    },
    "social": {
        "base_decay": 1,
        "alone_decay": 3,          # 独处时额外衰减
        "conversation_recovery": 15,  # 对话时恢复
        "extraversion_modifier": True  # 外向的人衰减更快
    }
}
```

### 需求触发行为

```python
# 当需求值低于阈值时，智能体会优先满足该需求

NEED_THRESHOLDS = {
    "energy": {
        "critical": 10,   # <10时强制去睡觉/吃饭
        "low": 30,        # <30时优先考虑休息
        "normal": 70      # >70时正常活动
    },
    "social": {
        "critical": 10,   # <10时强制找人说话
        "low": 30,        # <30时倾向社交
        "normal": 60
    }
}
```

## 决策系统

### 决策原则

**重要设计决策：所有智能体行为都由AI决定，不使用规则引擎。**

这意味着：
- 即使是"饿了要吃饭"这样的简单决策，也由AI思考后决定
- AI可能做出"意外"的选择（比如饿了但选择继续工作）
- 这样更接近真实人类行为，更有观察价值

### 决策流程

```
每个决策周期（游戏内10分钟）：

1. 收集上下文
   └─> 当前状态（位置、需求、经济）
   └─> 周围环境（附近的人、当前位置功能）
   └─> 相关记忆（最近发生的事）
   └─> 当前时间（影响可选行为）

2. 调用AI（DeepSeek R1）
   └─> 发送完整上下文
   └─> AI自主思考并决策
   └─> 返回具体行动

3. 执行决策
   └─> 更新智能体状态
   └─> 广播事件
   └─> 记录到记忆
```

### AI决策提示词模板

```python
FULL_AI_DECISION_PROMPT = """
你是{name}，一个生活在AI小镇的居民。请完全沉浸在角色中，像真人一样思考和决策。

## 你是谁
- 年龄：{age}岁，性别：{gender}
- 职业：{occupation}
- 性格特点：
  - 外向程度：{extraversion}/100（{extraversion_desc}）
  - 友善程度：{agreeableness}/100（{agreeableness_desc}）
  - 尽责程度：{conscientiousness}/100（{conscientiousness_desc}）
  - 情绪稳定：{stability}/100（{stability_desc}）
  - 开放程度：{openness}/100（{openness_desc}）
- 人生目标：{life_goal}

## 你的当前状态
- 时间：{world_time}（{time_period}）
- 位置：{location_name}
- 身体状态：
  - 能量：{energy}/100（{energy_desc}）
  - 社交需求：{social}/100（{social_desc}）
  - 幸福感：{happiness}/100
- 经济状况：
  - 余额：¥{money}
  - 状态：{economic_status}

## 你周围的环境
当前位置可以做的事：{location_functions}
附近的人：
{nearby_agents_detail}

## 你最近的记忆
{recent_memories}

## 请做出决策

作为{name}，基于你的性格、当前状态和环境，你现在想做什么？

请像真人一样思考：
- 你可能饿了但选择继续工作（因为项目紧急）
- 你可能想社交但因为心情不好选择独处
- 你可能遇到朋友但因为赶时间只是打个招呼
- 你可能做出任何符合你性格的"意外"选择

用JSON格式回答：
{{
  "thinking": "你的内心独白（详细描述你在想什么，50-100字）",
  "action": "move/talk/work/eat/rest/sleep/solo",
  "target": "目标地点或人物（如果适用）",
  "detail": "具体行为描述（如：走向咖啡馆点一杯拿铁）",
  "reason": "一句话原因"
}}

注意：
1. thinking要详细，展示你的思考过程
2. 决策要符合你的性格，不要总是"理性最优"
3. 可以有情绪化、冲动、矛盾的选择
4. 这是你的生活，做你想做的事
"""
```

### 决策引擎实现

```python
class AgentEngine:
    """智能体决策引擎 - 全AI驱动"""
    
    def __init__(self, llm_router: LLMRouter, event_bus: EventBus):
        self.llm_router = llm_router
        self.event_bus = event_bus
        self.decision_interval = 60  # 现实60秒 = 游戏内10分钟
    
    async def decision_loop(self, agent: AgentState):
        """智能体决策循环 - 所有决策都由AI做出"""
        while agent.is_active:
            try:
                # 1. 收集上下文
                context = await self.build_context(agent)
                
                # 2. 调用AI做决策（核心：不使用规则，全部交给AI）
                decision = await self.ai_decide(agent, context)
                
                # 3. 执行决策
                await self.execute_decision(agent, decision)
                
                # 4. 更新需求（被动衰减，但不触发规则）
                self.passive_needs_decay(agent)
                
                # 5. 经济结算（每游戏日结算一次）
                await self.check_daily_settlement(agent)
                
            except Exception as e:
                logger.error(f"智能体 {agent.name} 决策出错: {e}")
            
            # 6. 等待下一个决策周期
            await asyncio.sleep(self.decision_interval)
    
    async def ai_decide(self, agent: AgentState, context: AgentContext) -> AgentDecision:
        """调用AI做决策 - 核心方法"""
        # 构建提示词
        prompt = self.build_decision_prompt(agent, context)
        
        # 调用智能体配置的模型（默认DeepSeek R1）
        response = await self.llm_router.generate(
            model_name=agent.model_name,
            prompt=prompt
        )
        
        # 解析响应
        decision = self.parse_decision(response)
        
        # 更新智能体的"当前想法"（用于观察者查看）
        agent.current_thinking = decision.thinking
        
        return decision
    
    def passive_needs_decay(self, agent: AgentState):
        """被动需求衰减 - 只是状态变化，不触发行为"""
        # 能量自然衰减
        agent.needs.energy = max(0, agent.needs.energy - 2)
        
        # 社交需求根据性格衰减
        social_decay = 3 if agent.personality.extraversion > 50 else 1
        agent.needs.social = max(0, agent.needs.social - social_decay)
```

### 行为恢复效果

虽然不用规则触发行为，但行为仍会影响状态：

```python
ACTION_EFFECTS = {
    "eat": {
        "energy": +30,
        "money": -30,
        "duration_minutes": 30  # 游戏内30分钟
    },
    "sleep": {
        "energy": +100,  # 恢复满
        "duration_minutes": 480  # 游戏内8小时
    },
    "work": {
        "energy": -5,  # 每小时
        "money": "+hourly_rate",
        "duration_minutes": "until_off_work"
    },
    "talk": {
        "social": +15,
        "duration_minutes": "variable"  # 由对话系统控制
    },
    "rest": {
        "energy": +10,
        "happiness": +5,
        "duration_minutes": 60
    }
}
```

## 行为系统

### 行为类型

| 行为 | 描述 | 持续时间 | 效果 |
|------|------|----------|------|
| idle | 发呆/等待 | 即时 | 无 |
| walk_to | 走向某地 | 根据距离 | 能量-3/分钟 |
| talk_to | 和某人对话 | 1-5分钟 | 社交+15 |
| work | 工作 | 按职业 | 能量-5/小时，金钱+ |
| eat | 吃饭 | 30分钟 | 能量+30，金钱-30 |
| sleep | 睡觉 | 8小时 | 能量恢复满 |
| rest | 休息 | 不定 | 能量+10/小时 |
| read | 看书 | 不定 | 技能+0.1 |

### 移动系统

```python
# 智能体移动速度：每秒移动 5 像素（游戏内）
# 现实1秒 = 游戏内10秒，所以看起来像每秒50像素

MOVE_SPEED = 5  # 像素/游戏秒

def calculate_move_time(from_pos, to_pos):
    """计算移动所需时间（游戏内秒）"""
    distance = math.sqrt((to_pos.x - from_pos.x)**2 + (to_pos.y - from_pos.y)**2)
    return distance / MOVE_SPEED
```

## 初始智能体生成

### 生成策略

初始50个智能体按以下分布生成：

```python
INITIAL_AGENT_DISTRIBUTION = {
    "occupation": {
        "programmer": 10,
        "designer": 5,
        "waiter": 8,
        "teacher": 4,
        "artist": 3,
        "student": 8,
        "retired": 2,
        "other": 10
    },
    "age": {
        "18-25": 15,
        "26-35": 20,
        "36-50": 10,
        "51-65": 4,
        "66+": 1
    },
    "gender": {
        "male": 25,
        "female": 24,
        "other": 1
    }
}
```

### 智能体生成提示词

```python
AGENT_GENERATION_PROMPT = """
请为AI自治世界创造一个新角色。

## 约束条件
- 职业：{occupation}
- 年龄范围：{age_range}
- 性别：{gender}

## 当前社会情况
- 总人口：{total_population}人
- 职业分布：{occupation_stats}

## 请生成角色信息

请用JSON格式回答：
{{
  "name": "中文姓名（2-3字）",
  "age": 具体年龄,
  "personality": {{
    "openness": 0-100,
    "conscientiousness": 0-100,
    "extraversion": 0-100,
    "agreeableness": 0-100,
    "neuroticism": 0-100
  }},
  "skills": {{
    "技能名": 分数(0-100)
  }},
  "life_goal": "人生目标，一句话",
  "backstory": "背景故事，50-100字，要有趣"
}}

要求：
1. 性格要多样化，不要都是完美的
2. 可以有缺陷（如社恐、懒惰、暴脾气）
3. 背景故事要真实可信
4. 技能要和职业相关
"""
```

## 智能体淘汰/新增机制

### 自然增长

```python
# 每游戏内1天检查一次
# 条件：人口<100 且 社会需要

def check_population_growth():
    # 1. 检查职业缺口
    if cafe.customers > cafe.workers * 5:
        spawn_agent(occupation="waiter", reason="咖啡馆人手不足")
    
    # 2. 检查社交孤岛
    lonely_agents = find_agents_without_friends()
    if lonely_agents:
        spawn_compatible_friend(lonely_agents[0])
    
    # 3. 随机新移民（10%概率/天）
    if random.random() < 0.1:
        spawn_random_agent(reason="新居民搬入")
```

### 淘汰机制

```python
# 智能体不会真正"死亡"，但会"搬走"

def check_agent_departure():
    for agent in agents:
        # 条件1：破产且长期无法恢复
        if agent.money < -1000 and agent.days_in_debt > 30:
            depart_agent(agent, reason="经济困难搬走了")
        
        # 条件2：长期孤独且不开心
        if agent.happiness < 10 and agent.days_unhappy > 30:
            depart_agent(agent, reason="换个城市生活")
```

## 多模型配置

### 模型分配策略

```python
# 默认模型分配
# 重要：所有智能体默认使用 DeepSeek R1（推理模型）
# 可以针对单个智能体修改为其他模型
MODEL_ASSIGNMENT = {
    # 默认：所有智能体使用R1推理模型
    "default": "deepseek-reasoner",  # DeepSeek R1
    
    # 可选替代模型（用户可手动指定）
    "alternatives": [
        "deepseek-chat",      # DeepSeek Chat（便宜）
        "openai-gpt4o",       # GPT-4o
        "claude-sonnet",      # Claude 3.5 Sonnet
        "ollama-local"        # 本地模型（免费）
    ]
}

# 智能体创建时默认使用R1，后续可通过API修改
def assign_model(agent):
    # 默认使用 DeepSeek R1
    return "deepseek-reasoner"
    
# 支持运行时修改模型
async def change_agent_model(agent_id: str, new_model: str):
    """修改智能体使用的模型"""
    agent = get_agent(agent_id)
    if new_model in MODEL_ASSIGNMENT["alternatives"] + [MODEL_ASSIGNMENT["default"]]:
        agent.model_name = new_model
        return True
    return False
```

### 成本预算

```python
# 月度预算：$200 USD
MONTHLY_BUDGET = 200.0

# DeepSeek R1 定价（2024）
# 输入: $0.55/百万tokens
# 输出: $0.219/百万tokens（缓存命中）/ $2.19/百万tokens（无缓存）

# 预估每次决策token消耗
TOKENS_PER_DECISION = {
    "input": 1500,   # 提示词+上下文
    "output": 200    # 决策响应
}

# 50智能体，每10分钟决策1次
# 每小时: 50 * 6 = 300次决策
# 每天: 300 * 24 = 7200次决策
# 每月: 7200 * 30 = 216000次决策

# 月度token消耗估算
# 输入: 216000 * 1500 = 324M tokens → $178
# 输出: 216000 * 200 = 43.2M tokens → $9.5（缓存）/ $95（无缓存）
# 总计: $187-$273/月

# 成本控制策略
COST_CONTROL = {
    "enable_cache": True,           # 启用缓存
    "batch_decisions": True,        # 批量决策
    "reduce_frequency_if_over": 180 # 超过$180/月时降低决策频率
}
```
