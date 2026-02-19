"""
AI Society 后端主入口
=====================
FastAPI 应用程序入口点

运行方式：
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.events import event_bus
from app.core.world import world_clock
from app.core.locations import location_manager
from app.agents import decision_scheduler, agent_manager
from app.agents.models import AgentState, ActionType
from app.conversations.handlers import setup_conversation_handlers
from app.routes import world as world_routes
from app.routes import agents as agent_routes
from app.routes import conversations as conversation_routes
from app.routes import locations as location_routes
from app.routes import llm as llm_routes
from app.routes import data as data_routes
from app.routes import expansion as expansion_routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    应用生命周期管理
    
    启动时：初始化服务
    关闭时：清理资源
    """
    # ========== 启动 ==========
    logger.info("=" * 50)
    logger.info("AI Society 后端启动中...")
    logger.info(f"应用名称: {settings.app_name}")
    logger.info(f"调试模式: {settings.debug}")
    logger.info(f"时间缩放: 1:{settings.time_scale}")
    logger.info(f"默认模型: {settings.default_model}")
    logger.info(f"月度预算: ${settings.monthly_budget}")
    logger.info(f"初始智能体数: {settings.initial_agent_count}")
    logger.info("=" * 50)
    
    # 加载地点配置
    location_count = location_manager.load_from_file()
    logger.info(f"加载地点配置: {location_count} 个地点")
    
    # 启动世界时钟（后台任务）
    clock_task = asyncio.create_task(world_clock.start())
    
    # 设置对话事件处理器
    await setup_conversation_handlers()
    
    # 清理智能体状态不一致（重启后残留的 in_conversation 状态）
    from app.conversations.manager import conversation_manager
    for agent in agent_manager.agents.values():
        if agent.state.value == "in_conversation":
            if not conversation_manager.is_in_conversation(agent.id):
                logger.warning(f"清理残留状态: [{agent.name}] in_conversation -> active")
                agent._state = AgentState.ACTIVE
                agent.current_action._type = ActionType.IDLE
    
    # 启动智能体决策调度器（后台任务）
    # 只有当有智能体时才会实际运行决策
    decision_task = asyncio.create_task(decision_scheduler.start())
    logger.info(f"智能体决策调度器已启动，当前智能体数: {agent_manager.count()}")
    
    logger.info("AI Society 后端启动完成")
    logger.info("API文档: http://localhost:8000/api/docs")
    
    yield  # 应用运行中
    
    # ========== 关闭 ==========
    logger.info("AI Society 后端关闭中...")
    
    # 停止世界时钟
    world_clock.stop()
    clock_task.cancel()
    try:
        await clock_task
    except asyncio.CancelledError:
        pass
    
    # 清理事件历史
    event_bus.clear_history()
    
    logger.info("AI Society 后端已关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        配置好的 FastAPI 应用
    """
    app = FastAPI(
        title="AI Society",
        description="""
## 自治智能体社会实验平台 API

AI Society 是一个开源的多智能体仿真平台，观察AI智能体在虚拟社会中自由生活、交流、发展。

### 主要功能
- **世界系统**: 时间管理、地点管理
- **智能体系统**: 全AI决策、需求系统、经济系统
- **对话系统**: 智能体自然对话、关系影响

### 核心特点
- 默认使用 DeepSeek R1 推理模型
- 所有智能体行为由AI决定，无规则引擎
- 时间缩放：现实1分钟 = 游戏内10分钟
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(world_routes.router, prefix="/api/world", tags=["世界"])
    app.include_router(location_routes.router, prefix="/api/locations", tags=["地点"])
    app.include_router(agent_routes.router, prefix="/api/agents", tags=["智能体"])
    app.include_router(conversation_routes.router, prefix="/api/conversations", tags=["对话"])
    app.include_router(llm_routes.router, tags=["LLM"])
    app.include_router(data_routes.router, prefix="/api", tags=["数据管理"])
    app.include_router(expansion_routes.router, prefix="/api", tags=["自动扩展"])
    
    # 根路由
    @app.get("/", tags=["系统"])
    async def root():
        """API根路径"""
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs": "/api/docs",
            "status": "running",
        }
    
    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy", 
            "version": "0.1.0",
            "world_clock": {
                "is_running": world_clock.is_running,
                "is_paused": world_clock.is_paused,
            },
            "locations_loaded": len(location_manager.locations),
        }
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
