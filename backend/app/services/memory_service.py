"""
记忆服务
========
整合数据库存储和向量检索的记忆管理服务

功能：
- 记忆创建与存储（同时写入PG和Qdrant）
- 语义检索
- 记忆重要性衰减
- 记忆反思生成
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud import MemoryCRUD
from app.database.models import MemoryModel
from app.services.vector_store import VectorStoreService, get_vector_store
from app.services.embedding import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class MemoryService:
    """记忆服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        vector_store: Optional[VectorStoreService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        初始化记忆服务
        
        Args:
            db: 数据库会话
            vector_store: 向量存储服务
            embedding_service: 嵌入服务
        """
        self.db = db
        self._vector_store = vector_store
        self._embedding_service = embedding_service
    
    @property
    def vector_store(self) -> VectorStoreService:
        """获取向量存储服务"""
        if self._vector_store is None:
            from app.services.vector_store import vector_store
            self._vector_store = vector_store
        return self._vector_store
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """获取嵌入服务"""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    # ===================
    # 创建记忆
    # ===================
    
    async def create_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "event",
        importance: float = 5.0,
        keywords: Optional[List[str]] = None,
        related_agents: Optional[List[str]] = None,
        location: Optional[str] = None,
        game_time: Optional[datetime] = None,
    ) -> MemoryModel:
        """
        创建记忆（同时存储到数据库和向量库）
        
        Args:
            agent_id: 智能体ID
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性
            keywords: 关键词
            related_agents: 相关智能体
            location: 地点
            game_time: 游戏时间
            
        Returns:
            创建的记忆记录
        """
        # 1. 生成嵌入向量
        embedding = await self.embedding_service.embed_text(content)
        
        # 2. 存储到数据库
        db_memory = await MemoryCRUD.create(
            db=self.db,
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            keywords=keywords,
            related_agents=related_agents,
            location=location,
            game_time=game_time,
        )
        
        # 3. 存储到向量库
        try:
            vector_id = await self.vector_store.upsert_memory(
                memory_id=db_memory.id,
                agent_id=agent_id,
                content=content,
                embedding=embedding,
                memory_type=memory_type,
                importance=importance,
                keywords=keywords,
                related_agents=related_agents,
                location=location,
                game_time=game_time,
            )
            
            # 4. 更新数据库中的vector_id
            await MemoryCRUD.update_vector_id(self.db, db_memory.id, vector_id)
            db_memory.vector_id = vector_id
            
        except Exception as e:
            logger.error(f"Failed to store memory in vector db: {e}")
            # 继续执行，记忆至少存储在数据库中
        
        logger.info(f"Created memory {db_memory.id} for agent {agent_id}")
        return db_memory
    
    async def create_memories_batch(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[MemoryModel]:
        """
        批量创建记忆
        
        Args:
            memories: 记忆数据列表
            
        Returns:
            创建的记忆记录列表
        """
        if not memories:
            return []
        
        # 1. 批量生成嵌入
        contents = [m["content"] for m in memories]
        embeddings = await self.embedding_service.embed_texts(contents)
        
        # 2. 批量存储到数据库
        db_memories = await MemoryCRUD.create_batch(self.db, memories)
        
        # 3. 批量存储到向量库
        try:
            vector_memories = []
            for i, (mem, db_mem, embedding) in enumerate(zip(memories, db_memories, embeddings)):
                vector_memories.append({
                    "memory_id": db_mem.id,
                    "agent_id": mem["agent_id"],
                    "content": mem["content"],
                    "embedding": embedding,
                    "memory_type": mem.get("memory_type", "event"),
                    "importance": mem.get("importance", 5.0),
                    "keywords": mem.get("keywords"),
                    "related_agents": mem.get("related_agents"),
                    "location": mem.get("location"),
                    "game_time": mem.get("game_time"),
                })
            
            await self.vector_store.upsert_memories_batch(vector_memories)
            
        except Exception as e:
            logger.error(f"Failed to batch store memories in vector db: {e}")
        
        return db_memories
    
    # ===================
    # 检索记忆
    # ===================
    
    async def search_memories(
        self,
        query: str,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        语义检索记忆
        
        Args:
            query: 查询文本
            agent_id: 过滤特定智能体
            memory_type: 过滤记忆类型
            min_importance: 最小重要性
            limit: 返回数量
            
        Returns:
            检索结果列表
        """
        # 1. 生成查询向量
        query_embedding = await self.embedding_service.embed_text(query)
        
        # 2. 向量检索
        results = await self.vector_store.search_similar(
            query_embedding=query_embedding,
            agent_id=agent_id,
            memory_type=memory_type,
            min_importance=min_importance,
            limit=limit,
        )
        
        # 3. 更新访问次数
        for result in results:
            memory_id = result.get("memory_id")
            if memory_id:
                await MemoryCRUD.increment_access(self.db, memory_id)
        
        return results
    
    async def retrieve_relevant_memories(
        self,
        agent_id: str,
        context: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索与当前上下文相关的记忆
        
        用于智能体决策时获取相关记忆
        
        Args:
            agent_id: 智能体ID
            context: 当前上下文（如：当前位置、时间、周围人物等）
            limit: 返回数量
            
        Returns:
            相关记忆列表
        """
        return await self.search_memories(
            query=context,
            agent_id=agent_id,
            limit=limit,
        )
    
    async def retrieve_memories_about_agent(
        self,
        observer_id: str,
        target_id: str,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索关于特定智能体的记忆
        
        Args:
            observer_id: 观察者智能体ID
            target_id: 目标智能体ID
            query: 额外的查询条件
            limit: 返回数量
            
        Returns:
            相关记忆列表
        """
        search_query = f"关于智能体 {target_id} 的记忆"
        if query:
            search_query = f"{query} {search_query}"
        
        query_embedding = await self.embedding_service.embed_text(search_query)
        
        return await self.vector_store.search_about_agent(
            query_embedding=query_embedding,
            target_agent_id=target_id,
            observer_agent_id=observer_id,
            limit=limit,
        )
    
    # ===================
    # 记忆管理
    # ===================
    
    async def get_recent_memories(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[MemoryModel]:
        """获取最近的记忆"""
        return await MemoryCRUD.get_recent_memories(self.db, agent_id, limit)
    
    async def get_important_memories(
        self,
        agent_id: str,
        min_importance: float = 7.0,
        limit: int = 20,
    ) -> List[MemoryModel]:
        """获取重要记忆"""
        return await MemoryCRUD.get_important_memories(
            self.db, agent_id, min_importance, limit
        )
    
    async def delete_memory(
        self,
        memory_id: str,
    ) -> bool:
        """
        删除记忆
        
        同时从数据库和向量库删除
        """
        # 1. 从向量库删除
        try:
            await self.vector_store.delete_memory(memory_id)
        except Exception as e:
            logger.error(f"Failed to delete memory from vector db: {e}")
        
        # 2. 从数据库删除
        return await MemoryCRUD.delete(self.db, memory_id)
    
    async def cleanup_old_memories(
        self,
        agent_id: str,
        keep_count: int = 100,
        min_importance: float = 5.0,
    ) -> int:
        """
        清理旧的低重要性记忆
        
        Args:
            agent_id: 智能体ID
            keep_count: 保留的记忆数量
            min_importance: 始终保留的最小重要性
            
        Returns:
            删除的记忆数量
        """
        return await MemoryCRUD.delete_old_memories(
            self.db, agent_id, keep_count, min_importance
        )
    
    # ===================
    # 记忆反思
    # ===================
    
    async def create_reflection(
        self,
        agent_id: str,
        reflection_content: str,
        source_memories: List[str],
        importance: float = 7.0,
    ) -> MemoryModel:
        """
        创建反思记忆
        
        反思是基于多个记忆生成的高层次总结
        
        Args:
            agent_id: 智能体ID
            reflection_content: 反思内容
            source_memories: 源记忆ID列表
            importance: 重要性（反思通常较重要）
            
        Returns:
            创建的反思记忆
        """
        return await self.create_memory(
            agent_id=agent_id,
            content=reflection_content,
            memory_type="reflection",
            importance=importance,
            keywords=["reflection", "思考", "总结"],
            related_agents=source_memories,  # 存储源记忆ID
        )
    
    async def create_plan_memory(
        self,
        agent_id: str,
        plan_content: str,
        importance: float = 6.0,
    ) -> MemoryModel:
        """创建计划记忆"""
        return await self.create_memory(
            agent_id=agent_id,
            content=plan_content,
            memory_type="plan",
            importance=importance,
            keywords=["plan", "计划", "目标"],
        )
    
    # ===================
    # 统计
    # ===================
    
    async def get_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """获取记忆统计"""
        db_stats = await MemoryCRUD.get_memory_stats(self.db, agent_id)
        
        try:
            vector_count = await self.vector_store.count_agent_memories(agent_id)
            db_stats["vector_count"] = vector_count
        except Exception:
            db_stats["vector_count"] = None
        
        return db_stats


# ===================
# 工厂函数
# ===================

async def create_memory_service(db: AsyncSession) -> MemoryService:
    """创建记忆服务实例"""
    vector_store = await get_vector_store()
    return MemoryService(
        db=db,
        vector_store=vector_store,
        embedding_service=get_embedding_service(),
    )
