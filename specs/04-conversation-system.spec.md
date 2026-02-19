# 对话与社交系统规格说明

## 设计原则

对话系统是观察智能体的核心窗口——我们主要观察智能体之间聊了什么。

就像偷听隔壁桌聊天：
- 他们说了什么？
- 关系变化了吗？
- 有什么有趣的事情发生？

## 对话触发机制

### 触发条件

```python
CONVERSATION_TRIGGERS = {
    # 1. 近距离遇见（最常见）
    "proximity": {
        "distance": 50,  # 像素距离
        "duration": 30,  # 停留超过30秒
        "base_probability": 0.3,  # 基础概率30%
        "modifiers": {
            "stranger": 0.1,      # 陌生人只有3%
            "acquaintance": 0.5,  # 认识的人15%
            "friend": 1.0,        # 朋友30%
            "close_friend": 1.5   # 好友45%
        }
    },
    
    # 2. 主动搭讪（社交需求高时）
    "active_approach": {
        "condition": "social_need > 70",
        "target_preference": "friend > acquaintance > stranger"
    },
    
    # 3. 工作互动（服务场景）
    "work_interaction": {
        "waiter_customer": True,  # 服务员必须招呼客人
        "teacher_student": True,
        "salesperson_customer": True
    },
    
    # 4. 约定见面（记忆触发）
    "scheduled_meeting": {
        "check_memory": "昨天说好今天见面",
        "reliability": "based_on_conscientiousness"  # 受尽责性影响
    }
}
```

### 对话开启逻辑

```python
async def check_conversation_opportunity(world_state):
    """检查是否有对话机会"""
    conversations_to_start = []
    
    for agent in world_state.agents:
        nearby = get_nearby_agents(agent, distance=50)
        
        for other in nearby:
            if should_start_conversation(agent, other):
                conversations_to_start.append((agent, other))
    
    return conversations_to_start

def should_start_conversation(agent_a, agent_b) -> bool:
    """判断是否应该开始对话"""
    # 1. 检查是否正在对话中
    if agent_a.current_action == "talking" or agent_b.current_action == "talking":
        return False
    
    # 2. 检查最近是否刚聊过
    last_chat = get_last_conversation_time(agent_a, agent_b)
    if last_chat and (world_time - last_chat) < timedelta(hours=1):
        return False  # 1小时内聊过就不再聊
    
    # 3. 计算开启概率
    relationship = get_relationship(agent_a, agent_b)
    base_prob = 0.3
    
    # 关系修正
    rel_modifier = RELATIONSHIP_MODIFIERS.get(relationship.type, 0.5)
    
    # 外向性修正（两人外向性平均值）
    avg_extraversion = (agent_a.personality.extraversion + agent_b.personality.extraversion) / 2
    ext_modifier = avg_extraversion / 50  # 50为基准
    
    # 社交需求修正
    social_modifier = max(agent_a.needs.social, agent_b.needs.social) / 50
    
    final_prob = base_prob * rel_modifier * ext_modifier * social_modifier
    
    return random.random() < final_prob
```

## 对话生成

### 对话提示词

```python
CONVERSATION_START_PROMPT = """
你是{speaker.name}，准备和{listener.name}打招呼。

## 你的背景
- 职业：{speaker.occupation}
- 性格：外向{speaker.personality.extraversion}/100，友善{speaker.personality.agreeableness}/100
- 当前心情：{speaker.current_emotion}

## 你们的关系
- 关系类型：{relationship.type}（{relationship_description}）
- 认识多久：{relationship.duration}
- 上次见面：{last_meeting}
- 你对TA的印象：{relationship.impression}

## 当前场景
- 地点：{location.name}
- 时间：{world_time}（{time_period}）
- 你在做什么：{speaker.current_action}
- TA在做什么：{listener.current_action}

## 最近记忆
{relevant_memories}

## 请生成一句开场白

要求：
1. 符合你的性格和当前心情
2. 考虑你们的关系亲疏
3. 结合当前场景
4. 自然真实，像真人说话
5. 15-40个字

直接输出对话内容，不要加任何标签或解释。
"""

CONVERSATION_REPLY_PROMPT = """
你是{listener.name}，{speaker.name}对你说："{last_message}"

## 你的背景
- 职业：{listener.occupation}
- 性格：外向{listener.personality.extraversion}/100，友善{listener.personality.agreeableness}/100
- 当前心情：{listener.current_emotion}

## 你们的关系
- 关系类型：{relationship.type}
- 你对TA的印象：{relationship.impression}

## 对话历史
{conversation_history}

## 请回复

要求：
1. 符合你的性格
2. 自然接话，可以：
   - 回答问题
   - 表达感受
   - 提新话题
   - 结束对话（如果想离开）
3. 15-50个字

直接输出回复内容。如果想结束对话，在回复后加 [END]
"""
```

### 对话轮次控制

```python
CONVERSATION_CONFIG = {
    "min_turns": 2,           # 最少2轮
    "max_turns": 10,          # 最多10轮
    "turn_interval": 5,       # 每轮间隔5秒（游戏内）
    
    # 结束条件
    "end_conditions": {
        "natural_end": True,       # AI主动说再见
        "timeout": 300,            # 5分钟无响应
        "interruption": True,      # 第三方打断
        "need_urgent": True        # 紧急需求（能量<10）
    },
    
    # 话题持续性
    "topic_memory": True,          # 记住话题
    "reference_previous": True     # 可引用之前的对话
}
```

### 对话状态机

```python
class ConversationState(Enum):
    INIT = "init"           # 开始
    GREETING = "greeting"   # 打招呼
    ACTIVE = "active"       # 正常对话中
    CLOSING = "closing"     # 准备结束
    ENDED = "ended"         # 已结束

class Conversation:
    """对话会话管理"""
    id: str
    participants: List[str]  # 参与者ID列表
    location: str
    state: ConversationState
    messages: List[Message]
    topic: str              # 当前话题
    started_at: datetime
    ended_at: Optional[datetime]
    
    async def process_turn(self, speaker_id: str) -> Message:
        """处理一轮对话"""
        speaker = get_agent(speaker_id)
        listener = get_agent(self.get_other_participant(speaker_id))
        
        # 构建提示词
        if len(self.messages) == 0:
            prompt = build_greeting_prompt(speaker, listener)
        else:
            prompt = build_reply_prompt(speaker, listener, self.messages)
        
        # 调用LLM
        response = await llm_router.generate(speaker.model_name, prompt)
        
        # 解析响应
        message = Message(
            speaker_id=speaker_id,
            content=response.strip("[END]").strip(),
            timestamp=world_clock.now(),
            emotion=detect_emotion(response)
        )
        
        self.messages.append(message)
        
        # 检查是否结束
        if "[END]" in response or len(self.messages) >= CONVERSATION_CONFIG["max_turns"]:
            self.state = ConversationState.CLOSING
        
        return message
```

## 对话内容分析

### 情绪检测

```python
EMOTION_KEYWORDS = {
    "happy": ["哈哈", "太好了", "开心", "高兴", "棒", "！"],
    "sad": ["唉", "可惜", "难过", "遗憾", "伤心"],
    "angry": ["气死", "烦", "讨厌", "什么鬼", "！！"],
    "curious": ["真的吗", "为什么", "怎么", "？"],
    "neutral": []
}

def detect_emotion(message: str) -> str:
    """检测消息情绪"""
    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message:
                scores[emotion] += 1
    
    if max(scores.values()) == 0:
        return "neutral"
    
    return max(scores, key=scores.get)
```

### 话题提取

```python
TOPIC_PATTERNS = {
    "work": ["工作", "项目", "老板", "同事", "加班", "公司"],
    "life": ["生活", "房子", "吃", "玩", "周末"],
    "relationship": ["朋友", "男/女朋友", "家人", "约会"],
    "hobby": ["游戏", "电影", "书", "运动", "音乐"],
    "gossip": ["听说", "你知道吗", "据说", "有人说"],
    "plan": ["打算", "计划", "想要", "准备", "未来"]
}

def extract_topic(messages: List[Message]) -> str:
    """提取对话话题"""
    full_text = " ".join([m.content for m in messages])
    
    topic_scores = {topic: 0 for topic in TOPIC_PATTERNS}
    for topic, keywords in TOPIC_PATTERNS.items():
        for keyword in keywords:
            if keyword in full_text:
                topic_scores[topic] += 1
    
    if max(topic_scores.values()) == 0:
        return "casual"  # 闲聊
    
    return max(topic_scores, key=topic_scores.get)
```

## 关系变化

### 关系影响因子

```python
RELATIONSHIP_EFFECTS = {
    # 对话本身的影响
    "conversation": {
        "base_increase": 2,           # 每次对话基础+2
        "long_conversation_bonus": 5,  # 超过5轮额外+5
        "emotional_resonance": 3,      # 情绪共鸣+3
        "argument_penalty": -10        # 争吵-10
    },
    
    # 话题影响
    "topic_effects": {
        "deep_talk": 5,    # 深度交流+5
        "gossip": 2,       # 八卦+2
        "help_offered": 8, # 提供帮助+8
        "complaint": -2    # 抱怨-2
    },
    
    # 性格兼容性
    "personality_compatibility": {
        "similar_extraversion": 1.2,    # 外向性相近加成
        "opposite_agreeableness": 0.8   # 宜人性相反惩罚
    }
}
```

### 关系更新逻辑

```python
def update_relationship_after_conversation(conv: Conversation):
    """对话结束后更新关系"""
    agent_a, agent_b = conv.participants
    relationship = get_relationship(agent_a, agent_b)
    
    # 基础增加
    delta = RELATIONSHIP_EFFECTS["conversation"]["base_increase"]
    
    # 对话长度加成
    if len(conv.messages) >= 5:
        delta += RELATIONSHIP_EFFECTS["conversation"]["long_conversation_bonus"]
    
    # 情绪分析
    emotions = [m.emotion for m in conv.messages]
    if emotions.count("happy") >= 2:
        delta += RELATIONSHIP_EFFECTS["conversation"]["emotional_resonance"]
    if emotions.count("angry") >= 1:
        delta += RELATIONSHIP_EFFECTS["conversation"]["argument_penalty"]
    
    # 话题影响
    topic = extract_topic(conv.messages)
    if topic in RELATIONSHIP_EFFECTS["topic_effects"]:
        delta += RELATIONSHIP_EFFECTS["topic_effects"][topic]
    
    # 更新关系
    old_strength = relationship.strength
    relationship.strength = max(0, min(100, relationship.strength + delta))
    relationship.last_interaction = conv.ended_at
    relationship.interaction_count += 1
    
    # 检查关系类型升级
    update_relationship_type(relationship)
    
    # 广播事件
    if relationship.strength != old_strength:
        broadcast_event({
            "type": "relationship_change",
            "agent_a": agent_a,
            "agent_b": agent_b,
            "old_strength": old_strength,
            "new_strength": relationship.strength,
            "reason": f"进行了一次{get_conversation_quality(conv)}的对话"
        })
```

## 记忆存储

### 对话记忆

```python
def store_conversation_memory(conv: Conversation, agent_id: str):
    """将对话存入智能体记忆"""
    agent = get_agent(agent_id)
    other = get_agent(conv.get_other_participant(agent_id))
    
    # 生成记忆摘要
    summary_prompt = f"""
    总结这段对话的要点（从{agent.name}的视角）：
    
    {format_conversation(conv)}
    
    请用一句话总结（30字以内）：
    """
    
    summary = await llm_router.generate(agent.model_name, summary_prompt)
    
    # 存储到记忆系统
    memory = Memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"和{other.name}聊天：{summary}",
        importance=calculate_importance(conv),
        world_time=conv.ended_at,
        related_agent_id=other.id,
        topic=conv.topic
    )
    
    await memory_engine.store(memory)
```

### 重要对话标记

```python
def calculate_importance(conv: Conversation) -> int:
    """计算对话重要性（0-100）"""
    importance = 30  # 基础重要性
    
    # 对话长度
    if len(conv.messages) >= 8:
        importance += 20
    elif len(conv.messages) >= 5:
        importance += 10
    
    # 情感强度
    emotions = [m.emotion for m in conv.messages]
    if "happy" in emotions or "angry" in emotions or "sad" in emotions:
        importance += 15
    
    # 关系变化
    relationship_delta = get_relationship_change(conv)
    if abs(relationship_delta) >= 5:
        importance += 20
    
    # 话题重要性
    if conv.topic in ["plan", "relationship", "deep_talk"]:
        importance += 15
    
    return min(100, importance)
```

## 群体对话（3人以上）

### 群聊触发

```python
def check_group_conversation():
    """检查是否有群聊机会"""
    # 找到3人以上聚集的地点
    gatherings = find_gatherings(min_size=3, max_distance=30)
    
    for gathering in gatherings:
        # 检查是否有人正在1v1聊天
        chatting_pairs = find_chatting_pairs(gathering)
        
        if chatting_pairs:
            # 第三人有概率加入
            bystanders = [a for a in gathering if a not in chatting_pairs]
            for bystander in bystanders:
                if should_join_conversation(bystander, chatting_pairs):
                    # 转为群聊
                    convert_to_group_chat(chatting_pairs, bystander)
```

### 群聊轮流发言

```python
async def group_conversation_turn(conv: GroupConversation):
    """群聊轮次处理"""
    # 选择下一个发言者
    next_speaker = select_next_speaker(conv)
    
    # 构建群聊提示词
    prompt = build_group_chat_prompt(conv, next_speaker)
    
    # 生成回复
    response = await llm_router.generate(next_speaker.model_name, prompt)
    
    # 可以@某人
    mentioned = extract_mentions(response)  # 提取被@的人
    
    message = GroupMessage(
        speaker_id=next_speaker.id,
        content=response,
        mentioned_ids=mentioned
    )
    
    return message

def select_next_speaker(conv: GroupConversation) -> Agent:
    """选择下一个发言者"""
    # 优先级：
    # 1. 被@的人
    # 2. 外向性高的人
    # 3. 最久没说话的人
    
    if conv.last_message.mentioned_ids:
        return get_agent(conv.last_message.mentioned_ids[0])
    
    candidates = [a for a in conv.participants if a.id != conv.last_message.speaker_id]
    
    # 按外向性加权随机
    weights = [a.personality.extraversion for a in candidates]
    return random.choices(candidates, weights=weights)[0]
```

## 数据库模型

```python
class Conversation(Base):
    __tablename__ = "conversations"
    
    id: str
    conversation_type: str  # "one_on_one" / "group"
    participants: JSON      # [agent_id, ...]
    location: str
    topic: str
    started_at: datetime
    ended_at: datetime
    world_time_start: datetime
    world_time_end: datetime
    message_count: int
    sentiment_summary: str  # positive/negative/neutral

class Message(Base):
    __tablename__ = "messages"
    
    id: str
    conversation_id: str
    speaker_id: str
    content: str
    emotion: str
    mentioned_ids: JSON     # 群聊中@的人
    timestamp: datetime
    world_time: datetime
    sequence: int           # 在对话中的顺序
```

## 前端展示

### 对话气泡

```typescript
interface ChatBubble {
  agentId: string;
  agentName: string;
  content: string;
  emotion: string;
  position: { x: number; y: number };
  timestamp: Date;
}

// 在地图上显示对话气泡
// 气泡存在5秒后消失
// 点击气泡可以查看完整对话历史
```

### 实时对话流

```typescript
interface ConversationEvent {
  type: "conversation_start" | "message" | "conversation_end";
  conversationId: string;
  participants: string[];
  location: string;
  message?: {
    speakerId: string;
    speakerName: string;
    content: string;
    emotion: string;
  };
  relationshipChange?: {
    agentA: string;
    agentB: string;
    delta: number;
  };
}

// WebSocket推送给前端
// 前端在事件流面板实时显示
```
