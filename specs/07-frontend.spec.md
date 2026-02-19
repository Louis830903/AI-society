# 前端界面规格说明

## 设计原则

- **观察为主**: 用户是观察者,不是玩家
- **信息丰富**: 一眼能看到世界在发生什么
- **流畅体验**: 60fps渲染,实时更新
- **简洁优雅**: 不花哨,让内容说话

就像观看纪录片：画面流畅,信息清晰,不喧宾夺主。

## 技术栈

```
框架: React 18 (函数组件 + Hooks)
构建: Vite 5
渲染: Pixi.js 8 (WebGL 2D渲染)
状态: Zustand (轻量状态管理)
样式: TailwindCSS 3
图表: Recharts
通信: 原生WebSocket
语言: TypeScript 5
```

## 页面布局

### 主界面结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Logo] AI Society 自治世界实验     [时间显示] Day 15 14:30     [控制] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────┐  ┌────────────────────────────┐ │
│  │                                  │  │  智能体面板                │ │
│  │                                  │  │  ┌──────────────────────┐  │ │
│  │                                  │  │  │ 🔍 搜索智能体...     │  │ │
│  │                                  │  │  ├──────────────────────┤  │ │
│  │        世界地图                  │  │  │ 🟢 李明 (程序员)     │  │ │
│  │        (Pixi.js Canvas)          │  │  │    📍 咖啡馆         │  │ │
│  │                                  │  │  │    💭 和朋友聊天     │  │ │
│  │        - 位置标注                │  │  ├──────────────────────┤  │ │
│  │        - 智能体精灵              │  │  │ 🟢 王芳 (设计师)     │  │ │
│  │        - 对话气泡                │  │  │    📍 咖啡馆         │  │ │
│  │        - 移动轨迹                │  │  │    💭 和朋友聊天     │  │ │
│  │                                  │  │  ├──────────────────────┤  │ │
│  │                                  │  │  │ 🟡 张华 (老师)       │  │ │
│  │                                  │  │  │    📍 学校           │  │ │
│  │                                  │  │  │    💭 上课中         │  │ │
│  │                                  │  │  └──────────────────────┘  │ │
│  └──────────────────────────────────┘  └────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  实时事件流                                                        │ │
│  │  14:30 李明 对 王芳 说: "最近项目忙吗?"                           │ │
│  │  14:29 王芳 走进了 时光咖啡馆                                     │ │
│  │  14:28 系统: 新居民 陈晨 搬入了小镇                               │ │
│  │  14:25 张华 开始 上课                                             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 响应式布局

```css
/* 大屏幕 (>1400px): 地图占60%,右侧面板40% */
/* 中屏幕 (1000-1400px): 地图占55%,右侧面板45% */
/* 小屏幕 (<1000px): 地图全宽,面板可折叠 */
```

## 组件设计

### 1. 顶部导航栏 (TopBar)

```typescript
interface TopBarProps {
  worldTime: Date;
  dayCount: number;
  status: 'running' | 'paused';
  onPause: () => void;
  onResume: () => void;
  onSpeedChange: (speed: number) => void;
}

// 功能:
// - 显示Logo和项目名称
// - 显示游戏内时间 (Day 15 14:30 下午)
// - 显示现实时间
// - 控制按钮: 暂停/继续, 加速(1x/2x/5x)
// - 全屏切换
// - 设置入口
```

### 2. 世界地图 (WorldMap)

```typescript
interface WorldMapProps {
  width: number;
  height: number;
  locations: Location[];
  agents: Agent[];
  conversations: ActiveConversation[];
  selectedAgentId?: string;
  onAgentClick: (agentId: string) => void;
  onLocationClick: (locationId: string) => void;
}

// 功能:
// - Pixi.js渲染2000x2000世界
// - 可缩放(滚轮)、可拖拽
// - 显示所有位置(建筑物)
// - 显示所有智能体(精灵图)
// - 显示对话气泡(正在对话的智能体头顶)
// - 点击智能体高亮并显示详情
// - 点击位置显示位置信息
// - 热力图模式(可选)

// Pixi.js图层:
// 1. 背景层: 地面、道路
// 2. 建筑层: 位置建筑物
// 3. 智能体层: 智能体精灵
// 4. 效果层: 对话气泡、选中高亮
// 5. UI层: 标签、指示器
```

### 3. 智能体精灵 (AgentSprite)

```typescript
interface AgentSpriteProps {
  agent: Agent;
  isSelected: boolean;
  isTalking: boolean;
  onClick: () => void;
}

// 视觉设计:
// - 圆形头像(根据性别/职业生成)
// - 名字标签(鼠标悬停显示)
// - 状态指示器:
//   - 🟢 绿色边框: 正常活动
//   - 🟡 黄色边框: 工作中
//   - 🔵 蓝色边框: 正在对话
//   - 😴 灰色: 睡觉
// - 情绪图标(小表情)
// - 移动时显示轨迹线(淡出)
```

### 4. 对话气泡 (ChatBubble)

```typescript
interface ChatBubbleProps {
  speakerName: string;
  content: string;
  emotion: string;
  position: { x: number; y: number };
  duration?: number; // 显示时长,默认5秒
}

// 视觉设计:
// - 白色圆角矩形
// - 说话人名字(小字,灰色)
// - 对话内容(正文)
// - 左下角小三角指向说话人
// - 淡入淡出动画
// - 情绪对应背景色微调:
//   - happy: 淡黄
//   - sad: 淡蓝
//   - angry: 淡红
//   - neutral: 白色
```

### 5. 智能体列表面板 (AgentListPanel)

```typescript
interface AgentListPanelProps {
  agents: Agent[];
  selectedAgentId?: string;
  onSelectAgent: (agentId: string) => void;
  filter: AgentFilter;
  onFilterChange: (filter: AgentFilter) => void;
}

interface AgentFilter {
  search: string;
  occupation?: string;
  status?: 'all' | 'active' | 'talking' | 'working' | 'idle';
  sortBy: 'name' | 'activity' | 'wealth';
}

// 功能:
// - 搜索框(按名字搜索)
// - 筛选器(职业、状态)
// - 智能体列表(可滚动)
// - 每项显示:
//   - 头像
//   - 名字+职业
//   - 当前位置
//   - 当前状态/想法
//   - 状态指示器(颜色点)
// - 点击选中,地图跟随
```

### 6. 智能体详情面板 (AgentDetailPanel)

```typescript
interface AgentDetailPanelProps {
  agent: AgentDetail;
  onClose: () => void;
  onFollowToggle: () => void;
}

// 布局:
// ┌─────────────────────────────┐
// │ [头像]  李明, 28岁           │
// │         程序员               │
// │         💭 "在和朋友聊天"    │
// ├─────────────────────────────┤
// │ 性格                         │
// │ 外向 ████████░░ 80          │
// │ 友善 ██████░░░░ 65          │
// │ 尽责 ████████░░ 85          │
// ├─────────────────────────────┤
// │ 状态                         │
// │ ⚡ 能量: 75/100              │
// │ 💬 社交: 80/100              │
// │ 😊 幸福: 72/100              │
// │ 💰 余额: ¥5,230              │
// ├─────────────────────────────┤
// │ 社交关系                     │
// │ 👫 王芳 (朋友) ♥♥♥♥♡ 68     │
// │ 👥 张华 (认识) ♥♥♡♡♡ 35     │
// ├─────────────────────────────┤
// │ 最近记忆                     │
// │ • 14:20 在咖啡馆遇到王芳    │
// │ • 12:00 在餐厅吃午饭        │
// │ • 09:00 开始工作            │
// └─────────────────────────────┘
```

### 7. 实时事件流 (EventStream)

```typescript
interface EventStreamProps {
  events: WorldEvent[];
  maxDisplay?: number; // 默认显示最近20条
  filter: EventFilter;
  onFilterChange: (filter: EventFilter) => void;
}

interface EventFilter {
  types: ('conversation' | 'move' | 'relationship' | 'system')[];
  agentId?: string; // 只看某智能体的事件
}

// 事件格式:
// [14:30] 李明 对 王芳 说: "最近项目忙吗?"
// [14:29] 王芳 走进了 时光咖啡馆
// [14:28] 系统: 新居民 陈晨 搬入了小镇
// [14:27] 李明 ↔ 王芳 关系提升 (+3)

// 功能:
// - 实时滚动(新事件自动滚到顶部)
// - 点击事件跳转到相关智能体/位置
// - 按类型筛选
// - 暂停滚动(鼠标悬停时)
```

### 8. 统计面板 (StatsPanel)

```typescript
interface StatsPanelProps {
  stats: WorldStats;
}

// 显示内容:
// - 人口统计: 52人
// - 职业分布饼图
// - 活跃对话数: 8
// - 今日对话总数: 89
// - 热门地点: 咖啡馆(12人)
// - 经济指标: 平均财富 ¥5,481
```

### 9. 社交网络图 (SocialNetworkGraph)

```typescript
interface SocialNetworkGraphProps {
  agents: Agent[];
  relationships: Relationship[];
  highlightAgentId?: string;
}

// 力导向图:
// - 节点: 智能体(大小=社交连接数)
// - 边: 关系(粗细=关系强度,颜色=关系类型)
// - 可拖拽、可缩放
// - 悬停显示关系详情
// - 点击节点选中智能体
```

## 状态管理

### Zustand Store结构

```typescript
// stores/worldStore.ts
interface WorldStore {
  // 状态
  worldTime: Date;
  dayCount: number;
  status: 'running' | 'paused';
  timeScale: number;
  
  // 动作
  setWorldTime: (time: Date) => void;
  pause: () => void;
  resume: () => void;
  setTimeScale: (scale: number) => void;
}

// stores/agentStore.ts
interface AgentStore {
  // 状态
  agents: Map<string, Agent>;
  selectedAgentId: string | null;
  followingAgentId: string | null;
  
  // 动作
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  selectAgent: (id: string | null) => void;
  followAgent: (id: string | null) => void;
  addAgent: (agent: Agent) => void;
  removeAgent: (id: string) => void;
}

// stores/eventStore.ts
interface EventStore {
  // 状态
  events: WorldEvent[];
  maxEvents: number;
  
  // 动作
  addEvent: (event: WorldEvent) => void;
  clearEvents: () => void;
}

// stores/conversationStore.ts
interface ConversationStore {
  // 状态
  activeConversations: Map<string, Conversation>;
  
  // 动作
  startConversation: (conv: Conversation) => void;
  addMessage: (convId: string, message: Message) => void;
  endConversation: (convId: string) => void;
}
```

## WebSocket集成

```typescript
// hooks/useWebSocket.ts
export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  
  const agentStore = useAgentStore();
  const eventStore = useEventStore();
  const conversationStore = useConversationStore();
  
  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setIsConnected(true);
      ws.send(JSON.stringify({ type: 'subscribe', channels: ['all'] }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'agent_move':
          agentStore.updateAgent(data.data.agent_id, {
            x: data.data.to.x,
            y: data.data.to.y
          });
          break;
          
        case 'conversation_message':
          conversationStore.addMessage(data.data.conversation_id, data.data);
          eventStore.addEvent(data);
          break;
          
        // ... 其他事件类型
      }
    };
    
    wsRef.current = ws;
    
    return () => ws.close();
  }, [url]);
  
  return { isConnected };
}
```

## 动画与交互

### Pixi.js动画

```typescript
// 智能体移动动画
function animateAgentMove(sprite: PIXI.Sprite, from: Point, to: Point, duration: number) {
  const startTime = performance.now();
  
  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // 缓动函数(ease-out)
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    
    sprite.x = from.x + (to.x - from.x) * easeProgress;
    sprite.y = from.y + (to.y - from.y) * easeProgress;
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };
  
  requestAnimationFrame(animate);
}

// 对话气泡淡入淡出
function animateBubble(bubble: PIXI.Container, fadeIn: boolean, duration: number = 300) {
  const startAlpha = fadeIn ? 0 : 1;
  const endAlpha = fadeIn ? 1 : 0;
  
  bubble.alpha = startAlpha;
  
  const animate = (progress: number) => {
    bubble.alpha = startAlpha + (endAlpha - startAlpha) * progress;
  };
  
  // 使用PIXI.Ticker或requestAnimationFrame
}
```

### 交互响应

```typescript
// 地图缩放
function handleWheel(event: WheelEvent) {
  const scaleDelta = event.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.max(0.5, Math.min(2, currentScale * scaleDelta));
  setScale(newScale);
}

// 地图拖拽
function handleDrag(event: MouseEvent) {
  if (!isDragging) return;
  
  const dx = event.clientX - lastMousePosition.x;
  const dy = event.clientY - lastMousePosition.y;
  
  setViewport({
    x: viewport.x + dx,
    y: viewport.y + dy
  });
}

// 智能体选中
function handleAgentClick(agentId: string) {
  selectAgent(agentId);
  
  // 如果开启了跟随模式,地图跟随智能体
  if (isFollowing) {
    centerOnAgent(agentId);
  }
}
```

## 性能优化

### 渲染优化

```typescript
// 1. 只渲染可见区域内的智能体
function getVisibleAgents(agents: Agent[], viewport: Rect, padding: number = 100) {
  return agents.filter(agent => 
    agent.x >= viewport.x - padding &&
    agent.x <= viewport.x + viewport.width + padding &&
    agent.y >= viewport.y - padding &&
    agent.y <= viewport.y + viewport.height + padding
  );
}

// 2. 使用对象池复用精灵
const spritePool: PIXI.Sprite[] = [];

function getSprite(): PIXI.Sprite {
  return spritePool.pop() || new PIXI.Sprite();
}

function releaseSprite(sprite: PIXI.Sprite) {
  sprite.visible = false;
  spritePool.push(sprite);
}

// 3. 批量更新状态
function batchUpdateAgents(updates: AgentUpdate[]) {
  // 使用 requestAnimationFrame 合并更新
  requestAnimationFrame(() => {
    updates.forEach(update => {
      agentStore.updateAgent(update.id, update.changes);
    });
  });
}
```

### 内存优化

```typescript
// 限制事件历史
const MAX_EVENTS = 500;

function addEvent(event: WorldEvent) {
  events.push(event);
  if (events.length > MAX_EVENTS) {
    events.shift(); // 移除最旧的
  }
}

// 限制对话气泡显示数量
const MAX_VISIBLE_BUBBLES = 10;
```

## 素材资源

### 精灵图规格

```
/public/assets/
├── agents/
│   ├── male_programmer.png     (64x64)
│   ├── female_designer.png     (64x64)
│   ├── male_waiter.png         (64x64)
│   └── ...
├── locations/
│   ├── cafe.png                (100x80)
│   ├── office.png              (200x150)
│   ├── park.png                (250x200)
│   └── ...
├── ui/
│   ├── bubble.9.png            (9-patch气泡)
│   ├── icons.png               (图标精灵图)
│   └── ...
└── map/
    ├── ground.png              (地面纹理)
    └── road.png                (道路纹理)
```

### 颜色规范

```css
:root {
  /* 主色 */
  --primary: #3B82F6;        /* 蓝色 */
  --secondary: #10B981;      /* 绿色 */
  
  /* 状态色 */
  --success: #22C55E;
  --warning: #F59E0B;
  --danger: #EF4444;
  --info: #06B6D4;
  
  /* 中性色 */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F3F4F6;
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --border: #E5E7EB;
  
  /* 情绪色 */
  --emotion-happy: #FEF3C7;
  --emotion-sad: #DBEAFE;
  --emotion-angry: #FEE2E2;
  --emotion-neutral: #FFFFFF;
}
```

## 目录结构

```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopBar.tsx
│   │   │   ├── MainLayout.tsx
│   │   │   └── SidePanel.tsx
│   │   ├── world/
│   │   │   ├── WorldMap.tsx
│   │   │   ├── AgentSprite.tsx
│   │   │   ├── LocationSprite.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   └── PathLine.tsx
│   │   ├── panels/
│   │   │   ├── AgentListPanel.tsx
│   │   │   ├── AgentDetailPanel.tsx
│   │   │   ├── EventStream.tsx
│   │   │   ├── StatsPanel.tsx
│   │   │   └── SocialGraph.tsx
│   │   └── ui/
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Badge.tsx
│   │       └── ProgressBar.tsx
│   ├── stores/
│   │   ├── worldStore.ts
│   │   ├── agentStore.ts
│   │   ├── eventStore.ts
│   │   └── conversationStore.ts
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── usePixiApp.ts
│   │   └── useViewport.ts
│   ├── utils/
│   │   ├── format.ts
│   │   ├── animation.ts
│   │   └── pathfinding.ts
│   ├── types/
│   │   ├── agent.ts
│   │   ├── world.ts
│   │   └── event.ts
│   └── api/
│       └── client.ts
├── public/
│   └── assets/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```
