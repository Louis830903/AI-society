# AI Society 🏘️

**DeepSeek 驱动的智能体模拟世界** | A DeepSeek-powered Agent Simulation World

观察 AI 居民在虚拟小镇中生活、工作、社交、聊天。每个居民都由大语言模型驱动，拥有独特的性格、记忆和社交关系。

Watch AI residents live, work, socialize and chat in a virtual town. Each resident is powered by LLM, with unique personality, memory and social relationships.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/react-18+-61dafb.svg)

---

## ✨ 特性 Features

- 🧠 **全 AI 决策** - 智能体的每个行为都由 DeepSeek 大模型决策，无规则引擎
- 💬 **自然对话** - 智能体之间可以自由交谈，对话内容由 AI 生成
- 🎭 **独特人格** - 每个智能体都有基于大五人格的性格特点
- 🏠 **虚拟小镇** - 包含住宅、商店、餐厅、公园等场所
- 📊 **实时观察** - 观察智能体的状态、行为、对话和社交关系
- ⏱️ **时间系统** - 游戏时间可调速，1分钟现实时间 = 10分钟游戏时间

---

## 🚀 快速开始 Quick Start

### 1. 克隆项目
```bash
git clone https://github.com/Louis830903/AI-society.git
cd AI-society
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env
cp backend/.env.example backend/.env

# 编辑 backend/.env，填入你的 DeepSeek API Key
# DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 启动后端
```bash
cd backend
pip install -r requirements.txt  # 或使用 poetry install
python -m uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 5. 访问
打开浏览器访问 http://localhost:5173

---

## 🏗️ 技术栈 Tech Stack

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| 前端 | React 18, TypeScript, Vite, Pixi.js, TailwindCSS |
| AI | DeepSeek R1 / DeepSeek Chat |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 实时通信 | WebSocket |

---

## 📁 项目结构 Project Structure

```
AI-society/
├── backend/           # 后端服务
│   ├── app/
│   │   ├── agents/    # 智能体系统（决策、记忆、性格）
│   │   ├── conversations/  # 对话系统
│   │   ├── core/      # 核心模块（世界、事件、配置）
│   │   ├── llm/       # LLM 抽象层（适配器、缓存、路由）
│   │   └── routes/    # API 路由
│   └── tests/         # 测试
├── frontend/          # 前端应用
│   ├── src/
│   │   ├── components/  # React 组件
│   │   ├── game/        # Pixi.js 游戏渲染
│   │   └── store/       # Zustand 状态管理
└── specs/             # 设计文档
```

---

## 🎮 功能演示 Demo

### 智能体决策
每个智能体根据自己的：
- 性格特点（开朗/内向/友善/挑剔...）
- 当前需求（饥饿、疲劳、社交、娱乐）
- 周围环境（谁在附近、现在几点）
- 记忆（之前发生过什么）

由 AI 决定下一步行动：去餐厅吃饭、去公园散步、找朋友聊天...

### 对话生成
当两个智能体相遇并决定聊天时：
- AI 会根据双方性格、关系、话题生成自然对话
- 对话结束后，双方会记住这次交流
- 关系亲密度会根据对话内容变化

---

## ⚙️ 配置 Configuration

主要配置在 `backend/.env`：

```env
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key

# 默认模型（deepseek-reasoner 或 deepseek-chat）
DEFAULT_MODEL=deepseek-reasoner

# 月度预算限制
MONTHLY_BUDGET=200

# 时间缩放（1分钟现实 = 10分钟游戏）
TIME_SCALE=10
```

---

## 📄 许可证 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢 Acknowledgments

- [DeepSeek](https://www.deepseek.com/) - 提供强大的 AI 模型
- [Generative Agents](https://arxiv.org/abs/2304.03442) - 斯坦福大学的研究启发

---

**Made with ❤️ by Louis**
