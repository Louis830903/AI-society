"""
数据库连接模块
=============
配置SQLAlchemy异步引擎和会话
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from loguru import logger


# ===================
# 异步引擎
# ===================

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,  # 适合多进程环境
)


# ===================
# 会话工厂
# ===================

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ===================
# 依赖注入
# ===================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    
    用于FastAPI依赖注入
    
    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（上下文管理器版本）
    
    用于非FastAPI代码中获取数据库会话
    
    Example:
        async with get_async_session() as db:
            result = await db.execute(query)
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ===================
# 初始化
# ===================

async def init_db() -> None:
    """
    初始化数据库
    
    创建所有表（仅在开发环境使用）
    生产环境应使用Alembic迁移
    """
    from app.database.models import Base
    
    logger.info("正在初始化数据库...")
    
    async with engine.begin() as conn:
        # 开发环境可以使用create_all
        # 生产环境应该使用Alembic
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("数据库初始化完成")


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")
