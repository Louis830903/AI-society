# 世界与地图系统规格说明

## 设计原则

世界地图是智能体生活的舞台，需要：
- 有真实感的空间布局
- 不同功能区域满足不同需求
- 支持智能体自主导航

就像一个真实的小镇：有住宅区、商业区、办公区、休闲区。

## 世界配置

```python
WORLD_CONFIG = {
    "size": {
        "width": 2000,   # 像素
        "height": 2000
    },
    "time": {
        "scale": 10,           # 现实1分钟 = 游戏内10分钟
        "day_start": "06:00",  # 白天开始
        "day_end": "22:00"     # 夜晚开始
    },
    "grid_size": 20,           # 寻路网格大小
    "max_agents": 200          # 最大智能体数量
}
```

## 地图布局

### 区域划分

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌────────────────────┐     ┌────────────────────────┐   │
│    │                    │     │                        │   │
│    │    住宅区 (NW)     │     │     商业区 (NE)        │   │
│    │    Residential     │     │     Commercial         │   │
│    │                    │     │                        │   │
│    │  - 公寓楼 ×5       │     │  - 咖啡馆             │   │
│    │  - 住宅 ×20        │     │  - 餐厅              │   │
│    │                    │     │  - 商场              │   │
│    │                    │     │  - 便利店            │   │
│    └────────────────────┘     └────────────────────────┘   │
│                                                             │
│                    ┌──────────────────┐                     │
│                    │                  │                     │
│                    │   中心广场 (C)   │                     │
│                    │   Central Plaza  │                     │
│                    │                  │                     │
│                    │   - 喷泉         │                     │
│                    │   - 长椅 ×10     │                     │
│                    │   - 公告板       │                     │
│                    │                  │                     │
│                    └──────────────────┘                     │
│                                                             │
│    ┌────────────────────┐     ┌────────────────────────┐   │
│    │                    │     │                        │   │
│    │    休闲区 (SW)     │     │     工作区 (SE)        │   │
│    │    Leisure         │     │     Business           │   │
│    │                    │     │                        │   │
│    │  - 公园            │     │  - 科技公司           │   │
│    │  - 图书馆          │     │  - 设计工作室         │   │
│    │  - 电影院          │     │  - 学校              │   │
│    │  - 健身房          │     │  - 艺术工作室         │   │
│    │                    │     │                        │   │
│    └────────────────────┘     └────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 位置详细配置

```json
{
  "locations": [
    {
      "id": "residential_apartment_1",
      "name": "阳光公寓",
      "type": "apartment",
      "zone": "residential",
      "position": {"x": 200, "y": 200},
      "size": {"width": 150, "height": 200},
      "capacity": 20,
      "functions": ["sleep", "rest"],
      "open_hours": "24h"
    },
    {
      "id": "cafe_1",
      "name": "时光咖啡馆",
      "type": "cafe",
      "zone": "commercial",
      "position": {"x": 1200, "y": 200},
      "size": {"width": 100, "height": 80},
      "capacity": 15,
      "functions": ["eat", "social", "work_casual"],
      "open_hours": "07:00-23:00",
      "consumption": {"coffee": 30, "meal": 50}
    },
    {
      "id": "tech_company_1",
      "name": "创新科技公司",
      "type": "office",
      "zone": "business",
      "position": {"x": 1300, "y": 1300},
      "size": {"width": 200, "height": 150},
      "capacity": 30,
      "functions": ["work"],
      "work_hours": "09:00-18:00",
      "occupations": ["programmer", "designer"]
    },
    {
      "id": "central_plaza",
      "name": "中心广场",
      "type": "plaza",
      "zone": "center",
      "position": {"x": 900, "y": 900},
      "size": {"width": 200, "height": 200},
      "capacity": 50,
      "functions": ["social", "rest", "event"],
      "open_hours": "24h"
    },
    {
      "id": "park_1",
      "name": "绿荫公园",
      "type": "park",
      "zone": "leisure",
      "position": {"x": 200, "y": 1300},
      "size": {"width": 250, "height": 200},
      "capacity": 40,
      "functions": ["rest", "social", "exercise"],
      "open_hours": "06:00-22:00"
    },
    {
      "id": "library_1",
      "name": "市立图书馆",
      "type": "library",
      "zone": "leisure",
      "position": {"x": 300, "y": 1550},
      "size": {"width": 120, "height": 100},
      "capacity": 25,
      "functions": ["read", "study", "work_quiet"],
      "open_hours": "09:00-21:00"
    },
    {
      "id": "school_1",
      "name": "社区学校",
      "type": "school",
      "zone": "business",
      "position": {"x": 1500, "y": 1500},
      "size": {"width": 180, "height": 150},
      "capacity": 40,
      "functions": ["study", "teach"],
      "work_hours": "08:00-16:00",
      "occupations": ["teacher", "student"]
    },
    {
      "id": "restaurant_1",
      "name": "家常菜馆",
      "type": "restaurant",
      "zone": "commercial",
      "position": {"x": 1400, "y": 300},
      "size": {"width": 100, "height": 80},
      "capacity": 20,
      "functions": ["eat", "social"],
      "open_hours": "10:00-22:00",
      "consumption": {"meal_basic": 30, "meal_nice": 80}
    },
    {
      "id": "convenience_store_1",
      "name": "24小时便利店",
      "type": "store",
      "zone": "commercial",
      "position": {"x": 1500, "y": 100},
      "size": {"width": 60, "height": 50},
      "capacity": 8,
      "functions": ["buy", "eat_quick"],
      "open_hours": "24h",
      "consumption": {"snack": 15, "drink": 10}
    },
    {
      "id": "art_studio_1",
      "name": "创意工作室",
      "type": "studio",
      "zone": "business",
      "position": {"x": 1600, "y": 1300},
      "size": {"width": 80, "height": 70},
      "capacity": 8,
      "functions": ["work", "create"],
      "open_hours": "flexible",
      "occupations": ["artist"]
    }
  ]
}
```

## 位置类型

### 位置功能表

| 位置类型 | 功能 | 典型消费 | 典型人群 |
|----------|------|----------|----------|
| apartment | 睡觉、休息 | 房租 | 所有人 |
| cafe | 社交、工作、吃喝 | 30-50 | 社交型、自由职业 |
| restaurant | 吃饭、社交 | 30-80 | 所有人 |
| office | 工作 | 无 | 上班族 |
| school | 学习、教学 | 无 | 学生、教师 |
| park | 休息、运动、社交 | 无 | 休闲人群 |
| library | 阅读、学习 | 无 | 学习型 |
| plaza | 社交、休息 | 无 | 所有人 |
| store | 购物 | 10-500 | 所有人 |
| studio | 创作、工作 | 无 | 艺术家 |

### 位置状态

```python
@dataclass
class LocationState:
    """位置实时状态"""
    id: str
    current_occupants: List[str]  # 当前在此位置的智能体ID
    is_open: bool                  # 是否营业
    
    @property
    def is_crowded(self) -> bool:
        """是否拥挤"""
        location = get_location(self.id)
        return len(self.current_occupants) > location.capacity * 0.8
    
    @property
    def is_empty(self) -> bool:
        """是否空旷"""
        return len(self.current_occupants) == 0
```

## 时间系统

### 时间缩放

```python
class WorldClock:
    """
    现实1分钟 = 游戏内10分钟
    现实1小时 = 游戏内10小时
    现实2.4小时 = 游戏内1天
    现实约10天 = 游戏内1年
    """
    
    TIME_SCALE = 10
    
    def __init__(self):
        self.start_real_time = datetime.now(timezone.utc)
        self.start_world_time = datetime(2024, 1, 1, 6, 0, 0)  # 游戏从早上6点开始
    
    def now(self) -> datetime:
        """返回当前游戏内时间"""
        real_elapsed = datetime.now(timezone.utc) - self.start_real_time
        world_elapsed = real_elapsed * self.TIME_SCALE
        return self.start_world_time + world_elapsed
    
    @property
    def hour(self) -> int:
        return self.now().hour
    
    @property
    def is_daytime(self) -> bool:
        return 6 <= self.hour < 22
    
    @property
    def time_period(self) -> str:
        hour = self.hour
        if 6 <= hour < 9:
            return "早晨"
        elif 9 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "傍晚"
        else:
            return "深夜"
```

### 定时事件

```python
SCHEDULED_EVENTS = [
    {
        "name": "sunrise",
        "time": "06:00",
        "action": "broadcast_event",
        "data": {"type": "world", "event": "日出了，新的一天开始"}
    },
    {
        "name": "work_start",
        "time": "09:00",
        "action": "trigger_work",
        "data": {"message": "上班时间到"}
    },
    {
        "name": "lunch_break",
        "time": "12:00",
        "action": "trigger_lunch",
        "data": {"message": "午餐时间"}
    },
    {
        "name": "work_end",
        "time": "18:00",
        "action": "trigger_off_work",
        "data": {"message": "下班时间到"}
    },
    {
        "name": "sunset",
        "time": "22:00",
        "action": "broadcast_event",
        "data": {"type": "world", "event": "夜幕降临"}
    },
    {
        "name": "daily_settlement",
        "time": "00:00",
        "action": "economic_settlement",
        "data": {"message": "每日经济结算"}
    }
]
```

## 导航系统

### 寻路算法

```python
# 使用A*算法寻路
# 地图被分成20x20像素的网格

import heapq

def find_path(start: Point, end: Point, world_state) -> List[Point]:
    """A*寻路算法"""
    grid_size = WORLD_CONFIG["grid_size"]
    
    # 转换为网格坐标
    start_grid = (start.x // grid_size, start.y // grid_size)
    end_grid = (end.x // grid_size, end.y // grid_size)
    
    # A*算法
    open_set = [(0, start_grid)]
    came_from = {}
    g_score = {start_grid: 0}
    f_score = {start_grid: heuristic(start_grid, end_grid)}
    
    while open_set:
        current = heapq.heappop(open_set)[1]
        
        if current == end_grid:
            return reconstruct_path(came_from, current, grid_size)
        
        for neighbor in get_neighbors(current, world_state):
            tentative_g = g_score[current] + 1
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, end_grid)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    
    return []  # 无法到达

def heuristic(a, b):
    """曼哈顿距离启发函数"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
```

### 移动执行

```python
MOVE_SPEED = 5  # 像素/游戏秒

async def move_agent(agent: AgentState, destination: Point):
    """移动智能体到目标位置"""
    path = find_path(Point(agent.x, agent.y), destination, world_state)
    
    if not path:
        return False, "无法到达目标位置"
    
    agent.current_action = "walking"
    
    for point in path:
        # 计算移动时间
        distance = math.sqrt((point.x - agent.x)**2 + (point.y - agent.y)**2)
        travel_time = distance / MOVE_SPEED  # 游戏秒
        real_time = travel_time / WORLD_CONFIG["time"]["scale"]  # 现实秒
        
        # 等待（异步）
        await asyncio.sleep(real_time)
        
        # 更新位置
        agent.x = point.x
        agent.y = point.y
        agent.last_updated = datetime.utcnow()
        
        # 广播移动事件
        broadcast_event({
            "type": "agent_move",
            "agent_id": agent.id,
            "position": {"x": agent.x, "y": agent.y}
        })
        
        # 消耗能量
        agent.needs.energy -= 0.1
    
    agent.current_action = "idle"
    agent.current_location = get_location_at(agent.x, agent.y)
    
    return True, "到达目的地"
```

## 世界事件

### 事件类型

```python
class WorldEventType(Enum):
    # 时间事件
    SUNRISE = "sunrise"
    SUNSET = "sunset"
    NEW_DAY = "new_day"
    
    # 天气事件（可选扩展）
    WEATHER_CHANGE = "weather_change"
    
    # 社会事件
    AGENT_CREATED = "agent_created"
    AGENT_DEPARTED = "agent_departed"
    
    # 经济事件
    DAILY_SETTLEMENT = "daily_settlement"
    
    # 特殊事件
    RANDOM_EVENT = "random_event"
```

### 随机世界事件

```python
RANDOM_WORLD_EVENTS = [
    {
        "name": "free_coffee",
        "probability": 0.01,  # 每游戏天1%概率
        "location": "cafe_1",
        "message": "时光咖啡馆今天免费请大家喝咖啡！",
        "effect": "attract_agents_to_location"
    },
    {
        "name": "park_event",
        "probability": 0.02,
        "location": "park_1",
        "message": "公园举办周末集市",
        "effect": "attract_agents_to_location"
    },
    {
        "name": "company_outing",
        "probability": 0.01,
        "location": "park_1",
        "message": "创新科技公司组织团建",
        "effect": "move_occupation_agents"
    }
]
```

## 位置热度系统

### 热度计算

```python
def calculate_location_heat(location_id: str) -> float:
    """计算位置热度（0-100）"""
    location = get_location(location_id)
    state = get_location_state(location_id)
    
    # 基础热度：当前人数/容量
    occupancy_ratio = len(state.current_occupants) / location.capacity
    base_heat = occupancy_ratio * 50
    
    # 时间修正
    time_modifier = get_time_modifier(location.type, world_clock.hour)
    
    # 最近活动修正
    recent_conversations = get_recent_conversations(location_id, minutes=30)
    activity_modifier = min(len(recent_conversations) * 5, 30)
    
    return min(100, base_heat * time_modifier + activity_modifier)

def get_time_modifier(location_type: str, hour: int) -> float:
    """不同类型位置在不同时间的热度修正"""
    modifiers = {
        "cafe": {
            range(6, 10): 1.5,   # 早高峰
            range(10, 14): 1.2,
            range(14, 18): 1.0,
            range(18, 22): 1.3,  # 晚间
            range(22, 24): 0.5,
            range(0, 6): 0.1
        },
        "office": {
            range(9, 12): 1.5,
            range(12, 13): 0.5,  # 午休
            range(13, 18): 1.5,
            range(18, 24): 0.2,
            range(0, 9): 0.1
        },
        "park": {
            range(6, 9): 1.0,    # 晨练
            range(9, 17): 0.8,
            range(17, 21): 1.3,  # 傍晚散步
            range(21, 24): 0.3,
            range(0, 6): 0.1
        }
    }
    
    for time_range, modifier in modifiers.get(location_type, {}).items():
        if hour in time_range:
            return modifier
    
    return 1.0
```

## 前端地图渲染

### 图层结构

```typescript
// Pixi.js图层结构
const mapLayers = {
  background: new PIXI.Container(),  // 背景（地面、道路）
  buildings: new PIXI.Container(),   // 建筑物
  agents: new PIXI.Container(),      // 智能体
  effects: new PIXI.Container(),     // 特效（气泡、指示器）
  ui: new PIXI.Container()           // UI覆盖层
};

// 图层顺序：background < buildings < agents < effects < ui
```

### 位置渲染

```typescript
interface LocationSprite {
  id: string;
  sprite: PIXI.Sprite;
  nameLabel: PIXI.Text;
  heatIndicator: PIXI.Graphics;  // 热度指示器
  occupantCount: PIXI.Text;      // 当前人数显示
}

function renderLocation(location: Location): LocationSprite {
  const sprite = new PIXI.Sprite(getLocationTexture(location.type));
  sprite.position.set(location.position.x, location.position.y);
  sprite.width = location.size.width;
  sprite.height = location.size.height;
  
  // 名称标签
  const nameLabel = new PIXI.Text(location.name, {
    fontSize: 12,
    fill: 0xffffff
  });
  
  // 热度指示器（圆圈，颜色随热度变化）
  const heatIndicator = new PIXI.Graphics();
  
  return { id: location.id, sprite, nameLabel, heatIndicator };
}
```
