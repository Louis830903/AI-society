# 数据库Schema设计

<cite>
**本文档引用的文件**
- [backend/app/core/agent.py](file://backend/app/core/agent.py)
- [backend/app/core/world.py](file://backend/app/core/world.py)
- [backend/app/core/config.py](file://backend/app/core/config.py)
- [specs/03-economy-system.spec.md](file://specs/03-economy-system.spec.md)
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md)
- [specs/05-world-map.spec.md](file://specs/05-world-map.spec.md)
- [specs/06-api-design.spec.md](file://specs/06-api-design.spec.md)
- [specs/08-implementation-plan.spec.md](file://specs/08-implementation-plan.spec.md)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本文件面向从内存存储方案迁移到数据库存储的完整路径，涵盖数据库Schema设计、字段映射关系、索引策略与约束定义。重点阐述智能体表、世界状态表、事件表、关系表等核心数据表的结构设计，明确主键、外键关系与参照完整性约束，并给出数据类型选择、字符集配置、排序规则设置及性能优化策略。同时提供数据迁移脚本、版本升级策略与备份恢复方案，以及数据库连接配置、事务管理策略与并发控制机制。

## 项目结构
项目采用后端Python + 前端React的双端架构，数据库采用PostgreSQL，结合Redis与Qdrant向量数据库。后端核心模块包括配置管理、世界时钟、智能体状态与事件系统；前端负责可视化展示与实时事件推送。

```mermaid
graph TB
subgraph "后端"
Config["配置管理<br/>settings.database_url"]
WorldClock["世界时钟<br/>时间系统"]
AgentState["智能体状态<br/>AgentState"]
Events["事件系统<br/>EventBus"]
API["API层<br/>FastAPI"]
WS["WebSocket<br/>实时推送"]
end
subgraph "数据库"
PG["PostgreSQL"]
Redis["Redis"]
Qdrant["Qdrant 向量库"]
end
subgraph "前端"
ReactUI["React + Vite"]
PixiJS["地图渲染"]
end
Config --> PG
WorldClock --> Events
AgentState --> Events
Events --> API
API --> WS
API --> PG
API --> Redis
API --> Qdrant
WS --> ReactUI
ReactUI --> PixiJS
```

**图表来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L84-L87)
- [backend/app/core/world.py](file://backend/app/core/world.py#L73-L292)
- [specs/06-api-design.spec.md](file://specs/06-api-design.spec.md#L1-L655)

**章节来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L1-L175)
- [specs/06-api-design.spec.md](file://specs/06-api-design.spec.md#L1-L655)

## 核心组件
- 配置管理：集中管理数据库连接URL、Redis与Qdrant配置，支持环境变量覆盖。
- 世界时钟：提供游戏内时间、昼夜判断与定时事件发布，支撑世界状态持久化。
- 智能体状态：包含身份信息、位置坐标、需求与经济状态、近期记忆索引等。
- 事件系统：统一发布/订阅机制，支撑实时事件推送与数据库持久化。

**章节来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L82-L107)
- [backend/app/core/world.py](file://backend/app/core/world.py#L45-L292)
- [backend/app/core/agent.py](file://backend/app/core/agent.py#L25-L92)

## 架构概览
数据库层采用PostgreSQL作为主存储，Redis用于缓存热点数据，Qdrant用于向量化记忆检索。迁移路径遵循“先设计Schema，再实现模型与迁移，最后集成业务”的步骤。

```mermaid
graph TB
subgraph "迁移路径"
Design["设计Schema"]
Model["实现SQLAlchemy模型"]
Alembic["实现Alembic迁移"]
CRUD["实现智能体CRUD"]
ConvStore["实现对话存储"]
RelStore["实现关系存储"]
Vector["集成Qdrant向量库"]
MemStore["实现记忆向量化存储"]
MemSearch["实现记忆检索"]
StateSave["实现世界状态保存/恢复"]
Export["实现数据导出API"]
end
Design --> Model --> Alembic --> CRUD --> ConvStore --> RelStore --> Vector --> MemStore --> MemSearch --> StateSave --> Export
```

**图表来源**
- [specs/08-implementation-plan.spec.md](file://specs/08-implementation-plan.spec.md#L331-L341)

**章节来源**
- [specs/08-implementation-plan.spec.md](file://specs/08-implementation-plan.spec.md#L327-L352)

## 详细组件分析

### 智能体表（agents）
智能体表用于持久化AgentState的所有核心字段，包括身份信息、位置坐标、需求与经济状态、近期记忆索引以及模型配置。

- 主键：id（UUID或字符串）
- 字段映射：
  - 身份信息：name、age、gender、occupation、personality（JSON）、skills（JSON）
  - 状态：x、y、current_action、current_thinking、current_emotion、created_at、last_updated
  - 需求与经济：needs（JSON）、economy（JSON）
  - 记忆索引：recent_memory_ids（JSON数组）
  - 模型配置：model_name
- 约束：
  - 主键约束：id
  - 非空约束：name、age、gender、occupation、personality、skills、x、y、created_at、last_updated
  - 性别与职业枚举约束：通过应用层校验或数据库check约束
- 索引策略：
  - 唯一索引：id
  - 复合索引：(x, y) 用于快速查找邻近智能体
  - JSON字段索引：personality、skills、needs、economy、recent_memory_ids（视查询需求而定）

```mermaid
erDiagram
AGENTS {
uuid id PK
string name
int age
enum gender
enum occupation
json personality
json skills
float x
float y
string current_action
string current_thinking
string current_emotion
json needs
json economy
json recent_memory_ids
string model_name
datetime created_at
datetime last_updated
}
```

**图表来源**
- [backend/app/core/agent.py](file://backend/app/core/agent.py#L48-L76)

**章节来源**
- [backend/app/core/agent.py](file://backend/app/core/agent.py#L25-L92)

### 世界状态表（world_states）
世界状态表用于持久化世界时钟与世界状态的关键信息，支撑世界状态的保存与恢复。

- 主键：id（自增）
- 字段映射：
  - 世界时间：datetime、day、time_of_day、is_daytime
  - 时钟状态：time_scale、is_running、is_paused、start_world_time、start_real_time
  - 事件：last_tick_time_of_day（用于时间段变化检测）
- 约束：
  - 主键约束：id
  - 非空约束：datetime、day、time_of_day、is_daytime、time_scale、start_world_time、start_real_time
- 索引策略：
  - 唯一索引：id
  - 时间相关索引：datetime、day

```mermaid
erDiagram
WORLD_STATES {
int id PK
datetime datetime
int day
enum time_of_day
boolean is_daytime
int time_scale
boolean is_running
boolean is_paused
datetime start_world_time
datetime start_real_time
enum last_tick_time_of_day
}
```

**图表来源**
- [backend/app/core/world.py](file://backend/app/core/world.py#L46-L118)

**章节来源**
- [backend/app/core/world.py](file://backend/app/core/world.py#L45-L166)

### 事件表（events）
事件表用于持久化系统产生的各类事件，支持事件查询与回放。

- 主键：id（自增）
- 字段映射：
  - 事件类型：event_type（枚举）
  - 数据：data（JSON）
  - 源：source（字符串）
  - 时间戳：timestamp
- 约束：
  - 主键约束：id
  - 非空约束：event_type、timestamp
- 索引策略：
  - 唯一索引：id
  - 复合索引：(event_type, timestamp) 用于事件筛选与排序
  - JSON字段索引：data（视查询需求而定）

```mermaid
erDiagram
EVENTS {
int id PK
enum event_type
json data
string source
datetime timestamp
}
```

**图表来源**
- [backend/app/core/world.py](file://backend/app/core/world.py#L254-L264)

**章节来源**
- [backend/app/core/world.py](file://backend/app/core/world.py#L254-L273)

### 对话表（conversations）与消息表（messages）
对话表与消息表用于持久化智能体间的对话过程，支持对话查询、消息检索与关系变化记录。

- 对话表（conversations）：
  - 主键：id（UUID）
  - 字段映射：conversation_type、participants（JSON数组）、location、topic、started_at、ended_at、world_time_start、world_time_end、message_count、sentiment_summary
  - 约束：主键约束、非空约束（如started_at、world_time_start）
  - 索引：唯一索引（id）、索引（topic、location、started_at、ended_at）

- 消息表（messages）：
  - 主键：id（UUID）
  - 外键：conversation_id → conversations(id)
  - 字段映射：speaker_id、content、emotion、mentioned_ids（JSON数组）、timestamp、world_time、sequence
  - 约束：主键约束、外键约束、非空约束（如timestamp、world_time）
  - 索引：唯一索引（id）、索引（conversation_id、sequence、timestamp）

```mermaid
erDiagram
CONVERSATIONS {
uuid id PK
string conversation_type
json participants
string location
string topic
datetime started_at
datetime ended_at
datetime world_time_start
datetime world_time_end
int message_count
string sentiment_summary
}
MESSAGES {
uuid id PK
uuid conversation_id FK
string speaker_id
string content
string emotion
json mentioned_ids
datetime timestamp
datetime world_time
int sequence
}
CONVERSATIONS ||--o{ MESSAGES : "包含"
```

**图表来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L509-L536)

**章节来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L506-L536)

### 关系表（relationships）
关系表用于持久化智能体间的关系强度、类型与交互历史，支撑关系变化事件与社交网络分析。

- 主键：id（UUID）
- 字段映射：agent_a_id、agent_b_id、strength、relationship_type、last_interaction、interaction_count、created_at、updated_at
- 约束：
  - 主键约束：id
  - 外键约束：agent_a_id、agent_b_id → agents(id)
  - 非空约束：strength、last_interaction、interaction_count、created_at、updated_at
  - 唯一约束：(agent_a_id, agent_b_id) 保证每对智能体关系唯一
- 索引：
  - 唯一索引：(agent_a_id, agent_b_id)
  - 复合索引：(strength, last_interaction) 用于社交网络分析

```mermaid
erDiagram
RELATIONSHIPS {
uuid id PK
uuid agent_a_id FK
uuid agent_b_id FK
int strength
enum relationship_type
datetime last_interaction
int interaction_count
datetime created_at
datetime updated_at
}
AGENTS ||--o{ RELATIONSHIPS : "关联A"
AGENTS ||--o{ RELATIONSHIPS : "关联B"
```

**图表来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L331-L374)

**章节来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L328-L374)

### 经济交易表（transactions）与债务表（debts）
经济交易表与债务表用于持久化智能体的经济活动与债务关系，支撑经济统计与风险评估。

- 经济交易表（transactions）：
  - 主键：id（UUID）
  - 字段映射：agent_id → agents(id)、transaction_type、category、amount、balance_after、description、counterparty_id、timestamp、world_time
  - 约束：主键约束、外键约束、非空约束
  - 索引：索引（agent_id、timestamp、category）

- 债务表（debts）：
  - 主键：id（UUID）
  - 字段映射：borrower_id → agents(id)、lender_id → agents(id)、original_amount、remaining_amount、created_at、due_date、status
  - 约束：主键约束、外键约束、非空约束
  - 索引：索引（borrower_id、lender_id、status）

```mermaid
erDiagram
TRANSACTIONS {
uuid id PK
uuid agent_id FK
string transaction_type
string category
float amount
float balance_after
string description
uuid counterparty_id
datetime timestamp
datetime world_time
}
DEBTS {
uuid id PK
uuid borrower_id FK
uuid lender_id FK
float original_amount
float remaining_amount
datetime created_at
datetime due_date
string status
}
AGENTS ||--o{ TRANSACTIONS : "交易"
AGENTS ||--o{ DEBTS : "借贷(借入)"
AGENTS ||--o{ DEBTS : "借贷(贷出)"
```

**图表来源**
- [specs/03-economy-system.spec.md](file://specs/03-economy-system.spec.md#L315-L342)

**章节来源**
- [specs/03-economy-system.spec.md](file://specs/03-economy-system.spec.md#L312-L342)

### 记忆表（memories）
记忆表用于持久化智能体的记忆内容与向量化表示，支撑记忆检索与相似度分析。

- 主键：id（UUID）
- 字段映射：agent_id → agents(id)、memory_type、content、importance、world_time、related_agent_id、topic、vector（向量）
- 约束：主键约束、外键约束、非空约束
- 索引：索引（agent_id、topic、importance、world_time）

```mermaid
erDiagram
MEMORIES {
uuid id PK
uuid agent_id FK
enum memory_type
text content
int importance
datetime world_time
uuid related_agent_id
string topic
vector vector
}
AGENTS ||--o{ MEMORIES : "拥有"
```

**图表来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L380-L409)

**章节来源**
- [specs/04-conversation-system.spec.md](file://specs/04-conversation-system.spec.md#L376-L439)

## 依赖分析
- 模块耦合：
  - world.py 依赖 config.py 的配置项，确保数据库URL与时间系统配置一致。
  - agent.py 的 AgentState 与 world.py 的 WorldTime 通过事件总线进行解耦。
- 外部依赖：
  - PostgreSQL：主存储，支持JSON、向量类型与全文检索。
  - Redis：缓存热点智能体状态与对话元数据。
  - Qdrant：向量化检索，支持高维向量相似度查询。

```mermaid
graph LR
Config["配置管理"] --> DB["PostgreSQL"]
Config --> Redis["Redis"]
Config --> Qdrant["Qdrant"]
WorldClock["世界时钟"] --> Events["事件系统"]
AgentState["智能体状态"] --> Events
Events --> API["API层"]
API --> DB
API --> Redis
API --> Qdrant
```

**图表来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L82-L107)
- [backend/app/core/world.py](file://backend/app/core/world.py#L31-L32)

**章节来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L82-L107)
- [backend/app/core/world.py](file://backend/app/core/world.py#L31-L32)

## 性能考虑
- 数据类型选择：
  - UUID：用于分布式场景下的唯一标识，避免序列竞争。
  - JSON/JSONB：存储灵活结构化数据，支持索引与查询。
  - 向量：使用专用向量类型（如PostgreSQL向量扩展）提升相似度检索性能。
- 索引策略：
  - 对高频查询字段建立复合索引，如(conversation_id, sequence)、(agent_id, timestamp)。
  - 对枚举字段建立部分索引，如(status='active')。
- 查询优化：
  - 使用LIMIT与分页，避免全表扫描。
  - 对时间范围查询使用索引覆盖。
- 缓存策略：
  - Redis缓存热点智能体状态与对话列表，降低数据库压力。
- 并发控制：
  - 使用数据库事务保证一致性，必要时使用SELECT FOR UPDATE锁定。
  - 对高并发写入场景采用批量插入与队列化处理。

## 故障排除指南
- 连接失败：
  - 检查DATABASE_URL格式与可达性，确认PostgreSQL服务运行正常。
  - 校验SSL配置与证书链。
- 索引失效：
  - 使用EXPLAIN ANALYZE分析慢查询，重建或调整索引。
  - 对JSON字段使用GIN索引以提升查询性能。
- 数据不一致：
  - 检查事务边界与隔离级别，确保关键操作在单事务中完成。
  - 对外键约束冲突进行捕获与重试。
- 性能下降：
  - 监控慢查询日志，识别热点表与索引缺失。
  - 调整缓存命中率与批量写入策略。

**章节来源**
- [backend/app/core/config.py](file://backend/app/core/config.py#L84-L87)

## 结论
本文档提供了从内存存储到数据库存储的完整迁移路径，明确了核心数据表的Schema设计、字段映射关系、索引策略与约束定义。通过合理的数据类型选择、索引设计与缓存策略，可在保证数据一致性的同时提升系统性能。建议在实施过程中严格遵循迁移脚本与版本升级策略，确保平滑过渡与可恢复性。

## 附录

### 数据迁移脚本（示例流程）
- 步骤1：创建数据库与用户
  - 创建数据库 aisociety
  - 创建用户 aisociety_user，授予读写权限
- 步骤2：初始化Schema
  - 执行 Alembic 迁移，创建 agents、world_states、events、conversations、messages、relationships、transactions、debts、memories 表
- 步骤3：数据迁移
  - 从内存状态导出为JSON/CSV
  - 使用批量插入脚本导入到对应表
  - 验证数据完整性与一致性
- 步骤4：切换流量
  - 更新配置文件 DATABASE_URL 指向新数据库
  - 逐步切换API请求到新存储
  - 监控性能指标与错误率

### 版本升级策略
- 语义化版本：v1.0.0 → v1.x.x（功能演进），v2.0.0（破坏性变更）
- 迁移脚本：每个版本对应一组 Alembic 迁移，支持向上/向下升级
- 回滚策略：保留上一个版本的迁移脚本，出现问题时回滚至上一版本

### 备份与恢复方案
- 备份策略：
  - 全量备份：每周一次
  - 增量备份：每日一次
  - WAL归档：开启WAL日志，支持时间点恢复
- 恢复策略：
  - RTO/RPO：根据SLA设定恢复目标
  - 多地域备份：跨区域容灾
  - 自动化演练：定期进行恢复演练

### 数据库连接配置
- 连接参数：
  - 连接池大小：根据并发请求调整
  - 超时设置：连接超时、查询超时
  - SSL：生产环境启用SSL
- 连接字符串格式：
  - postgresql+asyncpg://user:password@host:port/dbname

### 事务管理与并发控制
- 事务策略：
  - 读写分离：查询走只读副本
  - 乐观锁：对更新操作使用版本号或时间戳
  - 悲观锁：对关键资源使用行级锁
- 并发控制：
  - 分布式锁：Redis实现全局互斥
  - 限流与熔断：防止雪崩效应
  - 重试机制：指数退避重试