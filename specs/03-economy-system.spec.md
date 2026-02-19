# 经济系统规格说明

## 设计原则

经济系统与现实世界对齐，让智能体体验真实的经济压力：
- 工作才能赚钱
- 生活需要开销
- 没钱会影响行为和情绪

就像真实生活：你需要上班赚钱，然后用钱吃饭、交房租、买东西。

## 货币单位

使用"元"作为货币单位，参考中国一线城市生活水平。

## 收入系统

### 工资收入

| 职业 | 时薪(元) | 日薪(8小时) | 月薪(22天) | 说明 |
|------|----------|-------------|------------|------|
| 程序员 | 150 | 1200 | 26400 | 高薪技术岗 |
| 设计师 | 120 | 960 | 21120 | 创意技术岗 |
| 教师 | 100 | 800 | 17600 | 稳定职业 |
| 销售 | 60+提成 | 480+提成 | 10560+ | 底薪+业绩 |
| 服务员 | 40 | 320 | 7040 | 基础服务 |
| 学生 | 0 | 补贴200 | 4400 | 生活费/奖学金 |
| 退休 | 0 | 退休金100 | 2200 | 养老金 |
| 自由职业 | 不固定 | 不固定 | 看作品 | 画家、作家等 |

### 收入计算逻辑

```python
def calculate_income(agent, hours_worked):
    """计算智能体工作收入"""
    base_rate = OCCUPATION_RATES[agent.occupation]["hourly"]
    
    # 技能加成：主要技能每10点加5%收入
    primary_skill = get_primary_skill(agent.occupation)
    skill_level = agent.skills.get(primary_skill, 50)
    skill_bonus = 1 + (skill_level - 50) * 0.005  # 50分为基准
    
    # 心情影响：不开心时效率降低
    mood_modifier = 1.0 if agent.happiness > 50 else 0.8
    
    income = base_rate * hours_worked * skill_bonus * mood_modifier
    return round(income, 2)
```

### 被动收入

```python
PASSIVE_INCOME = {
    "student": {
        "type": "daily_allowance",
        "amount": 200,
        "description": "生活费/奖学金"
    },
    "retired": {
        "type": "daily_pension",
        "amount": 100,
        "description": "退休金"
    }
}
```

## 支出系统

### 必要支出（每日自动扣除）

| 支出项 | 日均费用(元) | 说明 |
|--------|--------------|------|
| 房租 | 100 | 月租3000，平摊每天 |
| 基础餐饮 | 60 | 三餐基础消费 |
| 交通 | 20 | 上班通勤等 |
| 通讯 | 5 | 手机费平摊 |
| **日均最低开销** | **185** | 维持基本生存 |

### 可选支出（行为触发）

| 消费项 | 费用(元) | 触发条件 | 效果 |
|--------|----------|----------|------|
| 咖啡 | 30 | 去咖啡馆 | 社交+5 |
| 外出聚餐 | 80 | 和朋友吃饭 | 社交+15, 幸福+5 |
| 看电影 | 60 | 去娱乐场所 | 幸福+10 |
| 购物 | 100-500 | 去商场 | 幸福+10-30 |
| 旅行 | 500/天 | 请假旅行 | 幸福+50 |

### 支出计算逻辑

```python
# 每游戏内1天结算一次（现实2.4小时）

def daily_settlement(agent):
    """每日经济结算"""
    # 1. 扣除固定支出
    fixed_cost = DAILY_FIXED_COST[agent.living_standard]  # 185元
    agent.money -= fixed_cost
    
    # 2. 结算当日可选消费（已在行为时扣除）
    # 无需额外处理
    
    # 3. 发放被动收入
    if agent.occupation in PASSIVE_INCOME:
        agent.money += PASSIVE_INCOME[agent.occupation]["amount"]
    
    # 4. 检查经济状态
    update_economic_status(agent)
```

## 经济状态

### 状态分级

```python
class EconomicStatus(Enum):
    WEALTHY = "wealthy"       # 富裕：余额 > 月均支出*3 (>15000)
    STABLE = "stable"         # 稳定：余额 > 月均支出*1 (>5000)
    TIGHT = "tight"           # 紧张：余额 > 周均支出 (>1300)
    STRUGGLING = "struggling" # 拮据：余额 > 0
    IN_DEBT = "in_debt"       # 负债：余额 < 0
```

### 经济状态对行为的影响

```python
ECONOMIC_BEHAVIOR_MODIFIERS = {
    "wealthy": {
        "consumption_willingness": 1.5,  # 更愿意消费
        "work_motivation": 0.8,          # 工作动力降低
        "stress_level": 0.5              # 压力小
    },
    "stable": {
        "consumption_willingness": 1.0,
        "work_motivation": 1.0,
        "stress_level": 0.7
    },
    "tight": {
        "consumption_willingness": 0.5,  # 消费谨慎
        "work_motivation": 1.2,          # 更努力工作
        "stress_level": 1.0
    },
    "struggling": {
        "consumption_willingness": 0.2,  # 基本不消费
        "work_motivation": 1.5,          # 拼命工作
        "stress_level": 1.5,
        "happiness_penalty": -10         # 幸福感惩罚
    },
    "in_debt": {
        "consumption_willingness": 0,    # 停止消费
        "work_motivation": 2.0,          # 疯狂工作
        "stress_level": 2.0,
        "happiness_penalty": -30,
        "social_penalty": -20            # 不好意思见人
    }
}
```

## 经济事件

### 随机经济事件

```python
ECONOMIC_EVENTS = [
    {
        "name": "bonus",
        "probability": 0.02,  # 每天2%概率
        "condition": "employed",
        "effect": {"money": "+2000"},
        "message": "{agent.name}获得了公司奖金"
    },
    {
        "name": "medical_expense",
        "probability": 0.01,
        "condition": "any",
        "effect": {"money": "-500"},
        "message": "{agent.name}生病了，花了医药费"
    },
    {
        "name": "lucky_money",
        "probability": 0.005,
        "condition": "any",
        "effect": {"money": "+888"},
        "message": "{agent.name}收到了一个大红包"
    },
    {
        "name": "phone_broken",
        "probability": 0.005,
        "condition": "any",
        "effect": {"money": "-2000"},
        "message": "{agent.name}的手机坏了，换了新手机"
    }
]
```

### 社交经济互动

```python
# 朋友之间可以借钱
def borrow_money(borrower, lender, amount):
    """借钱逻辑"""
    # 检查关系强度
    relationship = get_relationship(borrower, lender)
    if relationship.strength < 60:
        return False, "关系不够好，不好意思借"
    
    # 检查出借人经济状况
    if lender.money < amount * 2:
        return False, "对方也不宽裕"
    
    # 执行借款
    lender.money -= amount
    borrower.money += amount
    
    # 记录债务关系
    create_debt(borrower, lender, amount)
    
    return True, f"{borrower.name}向{lender.name}借了{amount}元"

# 请客吃饭
def treat_meal(host, guests, location):
    """请客逻辑"""
    cost = MEAL_COST[location] * (1 + len(guests))
    host.money -= cost
    
    # 提升关系
    for guest in guests:
        improve_relationship(host, guest, 10)
    
    return f"{host.name}请{', '.join([g.name for g in guests])}吃了饭"
```

## 职业变动

### 失业

```python
def check_employment(agent):
    """检查是否失业"""
    # 条件1：公司裁员（随机事件）
    if random.random() < 0.001:  # 每天0.1%概率
        fire_agent(agent, reason="公司裁员")
        return
    
    # 条件2：长期表现差
    if agent.work_performance < 30 and agent.performance_warning_count >= 3:
        fire_agent(agent, reason="工作表现不佳")
        return

def fire_agent(agent, reason):
    """处理失业"""
    agent.occupation = "unemployed"
    agent.money += SEVERANCE_PAY  # 遣散费
    agent.happiness -= 30
    
    broadcast_event({
        "type": "unemployment",
        "agent": agent.id,
        "reason": reason,
        "message": f"{agent.name}失业了：{reason}"
    })
```

### 求职

```python
def job_search(agent):
    """求职逻辑"""
    if agent.occupation != "unemployed":
        return None
    
    # 根据技能匹配职位
    available_jobs = get_available_jobs()
    suitable_jobs = []
    
    for job in available_jobs:
        required_skill = job["required_skill"]
        if agent.skills.get(required_skill, 0) >= job["min_level"]:
            suitable_jobs.append(job)
    
    if suitable_jobs:
        # 选择最好的offer
        best_job = max(suitable_jobs, key=lambda j: j["salary"])
        return best_job
    
    return None
```

### 创业（高级功能）

```python
# 预留：智能体可以尝试创业
def start_business(agent, business_type):
    """创业逻辑"""
    startup_cost = BUSINESS_COSTS[business_type]
    
    if agent.money < startup_cost:
        return False, "资金不足"
    
    if agent.skills.get("business", 0) < 50:
        return False, "商业能力不足"
    
    agent.money -= startup_cost
    agent.occupation = f"owner_{business_type}"
    
    # 创业成功率受技能影响
    success_rate = agent.skills.get("business", 50) / 100
    
    return True, f"{agent.name}开始创业了"
```

## 数据库模型

```python
# 经济交易记录
class Transaction(Base):
    __tablename__ = "transactions"
    
    id: str                    # UUID
    agent_id: str              # 智能体ID
    transaction_type: str      # income/expense/transfer
    category: str              # salary/rent/food/entertainment/gift
    amount: float              # 金额（正数收入，负数支出）
    balance_after: float       # 交易后余额
    description: str           # 描述
    counterparty_id: str       # 交易对手（如借钱、请客）
    timestamp: datetime
    world_time: datetime       # 游戏内时间

# 债务关系
class Debt(Base):
    __tablename__ = "debts"
    
    id: str
    borrower_id: str
    lender_id: str
    original_amount: float
    remaining_amount: float
    created_at: datetime
    due_date: datetime         # 预期还款日
    status: str                # active/paid/defaulted
```

## 经济统计面板

### 前端展示数据

```python
# 个人经济面板
{
    "agent_id": "xxx",
    "current_balance": 5230.50,
    "economic_status": "stable",
    "income_today": 1200,
    "expense_today": 215,
    "income_this_month": 18500,
    "expense_this_month": 5800,
    "net_worth_trend": [5000, 5100, 5230, ...]  # 最近7天
}

# 社会经济面板
{
    "total_gdp": 2500000,           # 社会总财富
    "average_income": 800,          # 平均日收入
    "gini_coefficient": 0.35,       # 基尼系数（贫富差距）
    "unemployment_rate": 0.04,      # 失业率
    "wealth_distribution": {
        "wealthy": 5,
        "stable": 25,
        "tight": 15,
        "struggling": 4,
        "in_debt": 1
    }
}
```

## 配置文件示例

```json
// data/economy_config.json
{
  "currency": "元",
  "time_scale": 10,
  
  "daily_fixed_costs": {
    "rent": 100,
    "food_basic": 60,
    "transport": 20,
    "utilities": 5
  },
  
  "occupation_wages": {
    "programmer": {"hourly": 150, "work_hours": 8},
    "designer": {"hourly": 120, "work_hours": 8},
    "teacher": {"hourly": 100, "work_hours": 8},
    "waiter": {"hourly": 40, "work_hours": 8},
    "student": {"daily_allowance": 200},
    "retired": {"daily_pension": 100}
  },
  
  "consumption_prices": {
    "coffee": 30,
    "meal_basic": 30,
    "meal_nice": 80,
    "movie": 60,
    "shopping_basic": 100,
    "shopping_luxury": 500
  },
  
  "economic_thresholds": {
    "wealthy": 15000,
    "stable": 5000,
    "tight": 1300,
    "struggling": 0
  }
}
```
