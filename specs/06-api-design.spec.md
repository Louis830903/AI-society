# API与通信协议规格说明

## 设计原则

- RESTful API用于查询和控制操作
- WebSocket用于实时事件推送
- 统一的响应格式
- 中文友好的错误信息

## API基础信息

```
Base URL: /api
Version: v1
Content-Type: application/json
```

## REST API

### 世界相关

#### 获取世界状态

```http
GET /api/world/status

Response:
{
  "success": true,
  "data": {
    "world_time": "2024-01-15 14:30:00",
    "real_time": "2024-01-01 10:00:00",
    "time_scale": 10,
    "time_period": "下午",
    "is_daytime": true,
    "day_count": 15,
    "agent_count": 52,
    "active_conversations": 8,
    "status": "running"  // running / paused
  }
}
```

#### 控制世界运行

```http
POST /api/world/control

Request:
{
  "action": "pause" | "resume" | "speed_up" | "slow_down" | "reset"
}

Response:
{
  "success": true,
  "message": "世界已暂停"
}
```

#### 获取位置列表

```http
GET /api/world/locations

Response:
{
  "success": true,
  "data": [
    {
      "id": "cafe_1",
      "name": "时光咖啡馆",
      "type": "cafe",
      "zone": "commercial",
      "position": {"x": 1200, "y": 200},
      "size": {"width": 100, "height": 80},
      "capacity": 15,
      "current_occupants": 8,
      "is_open": true,
      "heat": 65.5
    }
  ]
}
```

#### 获取位置详情

```http
GET /api/world/locations/{location_id}

Response:
{
  "success": true,
  "data": {
    "id": "cafe_1",
    "name": "时光咖啡馆",
    "type": "cafe",
    "current_occupants": [
      {"id": "agent_1", "name": "李明"},
      {"id": "agent_2", "name": "王芳"}
    ],
    "recent_events": [
      {"type": "conversation", "participants": ["李明", "王芳"], "time": "14:25"}
    ],
    "heat_history": [50, 55, 60, 65, 65.5]  // 最近5个时间点
  }
}
```

### 智能体相关

#### 获取所有智能体

```http
GET /api/agents?page=1&limit=20&occupation=programmer&sort=name

Response:
{
  "success": true,
  "data": {
    "total": 52,
    "page": 1,
    "limit": 20,
    "agents": [
      {
        "id": "agent_1",
        "name": "李明",
        "age": 28,
        "gender": "male",
        "occupation": "programmer",
        "position": {"x": 1250, "y": 220},
        "current_location": "时光咖啡馆",
        "current_action": "talking",
        "current_emotion": "happy",
        "economic_status": "stable"
      }
    ]
  }
}
```

#### 获取智能体详情

```http
GET /api/agents/{agent_id}

Response:
{
  "success": true,
  "data": {
    "profile": {
      "id": "agent_1",
      "name": "李明",
      "age": 28,
      "gender": "male",
      "occupation": "programmer",
      "personality": {
        "openness": 70,
        "conscientiousness": 80,
        "extraversion": 45,
        "agreeableness": 65,
        "neuroticism": 30
      },
      "skills": {
        "programming": 85,
        "social": 60,
        "design": 40
      },
      "life_goal": "成为技术专家，开发改变世界的产品",
      "backstory": "从小对电脑感兴趣，大学学了计算机...",
      "model_name": "deepseek-chat"
    },
    "state": {
      "position": {"x": 1250, "y": 220},
      "current_location": "时光咖啡馆",
      "current_action": "talking",
      "current_target": "王芳",
      "current_thinking": "好久没和朋友聊天了，感觉很开心",
      "current_emotion": "happy",
      "needs": {
        "energy": 75,
        "social": 80,
        "happiness": 72
      },
      "economy": {
        "money": 5230.50,
        "status": "stable",
        "income_today": 1200,
        "expense_today": 185
      }
    },
    "relationships": [
      {
        "agent_id": "agent_2",
        "agent_name": "王芳",
        "type": "friend",
        "strength": 68,
        "last_interaction": "2024-01-15 14:25:00"
      }
    ],
    "recent_memories": [
      {
        "content": "在咖啡馆和王芳聊了工作的事",
        "time": "14:25",
        "importance": 45
      }
    ]
  }
}
```

#### 获取智能体轨迹

```http
GET /api/agents/{agent_id}/trajectory?hours=24

Response:
{
  "success": true,
  "data": {
    "agent_id": "agent_1",
    "trajectory": [
      {"time": "06:00", "location": "阳光公寓", "action": "sleeping"},
      {"time": "08:00", "location": "阳光公寓", "action": "waking_up"},
      {"time": "09:00", "location": "创新科技公司", "action": "working"},
      {"time": "12:00", "location": "家常菜馆", "action": "eating"},
      {"time": "13:00", "location": "创新科技公司", "action": "working"},
      {"time": "18:30", "location": "时光咖啡馆", "action": "social"}
    ]
  }
}
```

### 对话相关

#### 获取实时对话列表

```http
GET /api/conversations/active

Response:
{
  "success": true,
  "data": [
    {
      "id": "conv_123",
      "participants": [
        {"id": "agent_1", "name": "李明"},
        {"id": "agent_2", "name": "王芳"}
      ],
      "location": "时光咖啡馆",
      "started_at": "14:20",
      "message_count": 5,
      "topic": "work",
      "latest_message": {
        "speaker": "王芳",
        "content": "最近项目太忙了",
        "time": "14:28"
      }
    }
  ]
}
```

#### 获取对话详情

```http
GET /api/conversations/{conversation_id}

Response:
{
  "success": true,
  "data": {
    "id": "conv_123",
    "participants": ["李明", "王芳"],
    "location": "时光咖啡馆",
    "started_at": "2024-01-15 14:20:00",
    "ended_at": null,
    "topic": "work",
    "messages": [
      {"speaker": "李明", "content": "嗨，好久不见！", "emotion": "happy", "time": "14:20"},
      {"speaker": "王芳", "content": "是啊，最近太忙了", "emotion": "neutral", "time": "14:21"},
      {"speaker": "李明", "content": "我也是，项目快上线了", "emotion": "neutral", "time": "14:22"}
    ],
    "relationship_change": {
      "before": 65,
      "after": 68,
      "reason": "愉快的对话"
    }
  }
}
```

#### 获取历史对话

```http
GET /api/conversations/history?agent_id=agent_1&start_date=2024-01-01&end_date=2024-01-15&page=1&limit=20

Response:
{
  "success": true,
  "data": {
    "total": 156,
    "conversations": [...]
  }
}
```

### 统计相关

#### 获取社会统计

```http
GET /api/stats/society

Response:
{
  "success": true,
  "data": {
    "population": {
      "total": 52,
      "by_occupation": {
        "programmer": 12,
        "designer": 6,
        "waiter": 8,
        "teacher": 4,
        "student": 10,
        "other": 12
      },
      "by_age_group": {
        "18-25": 15,
        "26-35": 22,
        "36-50": 12,
        "51+": 3
      },
      "by_gender": {
        "male": 26,
        "female": 25,
        "other": 1
      }
    },
    "economy": {
      "total_wealth": 285000,
      "average_wealth": 5481,
      "gini_coefficient": 0.32,
      "unemployment_rate": 0.04,
      "wealth_distribution": {
        "wealthy": 5,
        "stable": 30,
        "tight": 14,
        "struggling": 2,
        "in_debt": 1
      }
    },
    "social": {
      "total_relationships": 312,
      "average_friends_per_agent": 6,
      "most_connected_agent": {"id": "agent_5", "name": "张华", "connections": 18},
      "conversations_today": 89,
      "average_daily_conversations": 75
    }
  }
}
```

#### 获取热门地点

```http
GET /api/stats/hot-locations

Response:
{
  "success": true,
  "data": [
    {"id": "cafe_1", "name": "时光咖啡馆", "heat": 85, "current_count": 12},
    {"id": "central_plaza", "name": "中心广场", "heat": 72, "current_count": 15},
    {"id": "park_1", "name": "绿荫公园", "heat": 60, "current_count": 8}
  ]
}
```

### 数据导出

#### 导出对话数据

```http
GET /api/export/conversations?format=csv&start_date=2024-01-01&end_date=2024-01-15

Response: CSV文件下载
时间,对话ID,说话人,对象,内容,地点,情绪
2024-01-15 14:20:00,conv_123,李明,王芳,"嗨，好久不见！",时光咖啡馆,happy
...
```

#### 导出智能体数据

```http
GET /api/export/agents?format=json

Response: JSON文件下载
```

#### 导出社交网络

```http
GET /api/export/social-network?format=graphml

Response: GraphML文件下载（可用Gephi分析）
```

## WebSocket 协议

### 连接

```javascript
const ws = new WebSocket('ws://host/api/stream');

// 连接成功后发送订阅消息
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['all']  // 或 ['agents', 'conversations', 'world']
  }));
};
```

### 事件类型

#### 智能体移动

```json
{
  "type": "agent_move",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "agent_id": "agent_1",
    "agent_name": "李明",
    "from": {"x": 1200, "y": 200},
    "to": {"x": 1250, "y": 220},
    "location": "时光咖啡馆"
  }
}
```

#### 智能体状态变化

```json
{
  "type": "agent_state_change",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "agent_id": "agent_1",
    "changes": {
      "current_action": {"old": "walking", "new": "idle"},
      "current_thinking": "到了咖啡馆，看看有没有朋友",
      "energy": {"old": 78, "new": 75}
    }
  }
}
```

#### 对话开始

```json
{
  "type": "conversation_start",
  "timestamp": "2024-01-15T14:20:00Z",
  "data": {
    "conversation_id": "conv_123",
    "participants": [
      {"id": "agent_1", "name": "李明"},
      {"id": "agent_2", "name": "王芳"}
    ],
    "location": "时光咖啡馆"
  }
}
```

#### 新消息

```json
{
  "type": "conversation_message",
  "timestamp": "2024-01-15T14:21:00Z",
  "data": {
    "conversation_id": "conv_123",
    "speaker_id": "agent_1",
    "speaker_name": "李明",
    "content": "嗨，好久不见！",
    "emotion": "happy"
  }
}
```

#### 对话结束

```json
{
  "type": "conversation_end",
  "timestamp": "2024-01-15T14:35:00Z",
  "data": {
    "conversation_id": "conv_123",
    "duration_minutes": 15,
    "message_count": 12,
    "topic": "work",
    "relationship_change": {
      "agent_a": "agent_1",
      "agent_b": "agent_2",
      "delta": 3
    }
  }
}
```

#### 关系变化

```json
{
  "type": "relationship_change",
  "timestamp": "2024-01-15T14:35:00Z",
  "data": {
    "agent_a": {"id": "agent_1", "name": "李明"},
    "agent_b": {"id": "agent_2", "name": "王芳"},
    "old_strength": 65,
    "new_strength": 68,
    "old_type": "friend",
    "new_type": "friend",
    "reason": "进行了一次愉快的对话"
  }
}
```

#### 新智能体创建

```json
{
  "type": "agent_created",
  "timestamp": "2024-01-15T15:00:00Z",
  "data": {
    "agent_id": "agent_53",
    "name": "陈晨",
    "age": 24,
    "occupation": "student",
    "reason": "新居民搬入",
    "initial_location": "阳光公寓"
  }
}
```

#### 智能体离开

```json
{
  "type": "agent_departed",
  "timestamp": "2024-01-15T16:00:00Z",
  "data": {
    "agent_id": "agent_10",
    "name": "周强",
    "reason": "经济困难搬走了",
    "days_lived": 45
  }
}
```

#### 世界事件

```json
{
  "type": "world_event",
  "timestamp": "2024-01-15T18:00:00Z",
  "data": {
    "event": "sunset",
    "message": "夜幕降临",
    "world_time": "22:00"
  }
}
```

#### 经济事件

```json
{
  "type": "economic_event",
  "timestamp": "2024-01-15T00:00:00Z",
  "data": {
    "event": "daily_settlement",
    "summary": {
      "total_income": 45000,
      "total_expense": 9620,
      "bankruptcies": 0,
      "new_jobs": 1
    }
  }
}
```

### 订阅管理

```javascript
// 订阅特定频道
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['conversations']  // 只接收对话相关事件
}));

// 订阅特定智能体
ws.send(JSON.stringify({
  type: 'subscribe_agent',
  agent_id: 'agent_1'  // 只接收该智能体的事件
}));

// 取消订阅
ws.send(JSON.stringify({
  type: 'unsubscribe',
  channels: ['conversations']
}));
```

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "找不到指定的智能体",
    "details": {
      "agent_id": "agent_999"
    }
  }
}
```

### 错误码表

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| AGENT_NOT_FOUND | 404 | 智能体不存在 |
| LOCATION_NOT_FOUND | 404 | 位置不存在 |
| CONVERSATION_NOT_FOUND | 404 | 对话不存在 |
| INVALID_PARAMETER | 400 | 参数错误 |
| WORLD_PAUSED | 409 | 世界已暂停，无法执行操作 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

## 速率限制

```
REST API: 100次/分钟
WebSocket: 无限制（服务器推送）
导出API: 10次/小时
```
