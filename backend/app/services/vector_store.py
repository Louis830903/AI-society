"""
向量存储服务
============
基于 Qdrant 的向量数据库操作

功能：
- 记忆向量化存储
- 语义相似度检索
- 集合管理
"""

import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


# ===================
# 嵌入模型配置
# ===================

# 使用 text-embedding-3-small 维度
EMBEDDING_DIM = 1536

# 或者使用本地模型如 all-MiniLM-L6-v2
# EMBEDDING_DIM = 384


class VectorStoreService:
    """向量存储服务"""
    
    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._collection_name = settings.qdrant_collection
        self._initialized = False
    
    @property
    def client(self) -> QdrantClient:
        """获取Qdrant客户端（懒加载）"""
        if self._client is None:
            self._client = QdrantClient(url=settings.qdrant_url)
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
        return self._client
    
    async def initialize(self):
        """初始化向量存储"""
        if self._initialized:
            return
        
        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self._collection_name not in collection_names:
                await self._create_collection()
                logger.info(f"Created collection: {self._collection_name}")
            else:
                logger.info(f"Collection exists: {self._collection_name}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def _create_collection(self):
        """创建记忆集合"""
        self.client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
            # 定义payload索引以加速过滤
            on_disk_payload=True,
        )
        
        # 创建payload索引
        self.client.create_payload_index(
            collection_name=self._collection_name,
            field_name="agent_id",
            field_schema="keyword",
        )
        self.client.create_payload_index(
            collection_name=self._collection_name,
            field_name="memory_type",
            field_schema="keyword",
        )
        self.client.create_payload_index(
            collection_name=self._collection_name,
            field_name="importance",
            field_schema="float",
        )
    
    def _generate_point_id(self, memory_id: str) -> str:
        """
        生成点ID
        
        Qdrant需要UUID或整数ID，我们使用哈希生成
        """
        return hashlib.md5(memory_id.encode()).hexdigest()
    
    # ===================
    # 向量操作
    # ===================
    
    async def upsert_memory(
        self,
        memory_id: str,
        agent_id: str,
        content: str,
        embedding: List[float],
        memory_type: str = "event",
        importance: float = 5.0,
        keywords: Optional[List[str]] = None,
        related_agents: Optional[List[str]] = None,
        location: Optional[str] = None,
        game_time: Optional[datetime] = None,
    ) -> str:
        """
        存储或更新记忆向量
        
        Args:
            memory_id: 记忆ID
            agent_id: 智能体ID
            content: 记忆内容
            embedding: 向量嵌入
            memory_type: 记忆类型
            importance: 重要性
            keywords: 关键词
            related_agents: 相关智能体
            location: 地点
            game_time: 游戏时间
            
        Returns:
            点ID
        """
        point_id = self._generate_point_id(memory_id)
        
        payload = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "keywords": keywords or [],
            "related_agents": related_agents or [],
            "location": location,
            "created_at": datetime.now().isoformat(),
        }
        
        if game_time:
            payload["game_time"] = game_time.isoformat()
        
        self.client.upsert(
            collection_name=self._collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ]
        )
        
        logger.debug(f"Upserted memory {memory_id} as point {point_id}")
        return point_id
    
    async def upsert_memories_batch(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[str]:
        """
        批量存储记忆向量
        
        Args:
            memories: 记忆数据列表，每个元素包含:
                - memory_id
                - agent_id
                - content
                - embedding
                - memory_type (可选)
                - importance (可选)
                - keywords (可选)
                - related_agents (可选)
                - location (可选)
                - game_time (可选)
                
        Returns:
            点ID列表
        """
        points = []
        point_ids = []
        
        for mem in memories:
            point_id = self._generate_point_id(mem["memory_id"])
            point_ids.append(point_id)
            
            payload = {
                "memory_id": mem["memory_id"],
                "agent_id": mem["agent_id"],
                "content": mem["content"],
                "memory_type": mem.get("memory_type", "event"),
                "importance": mem.get("importance", 5.0),
                "keywords": mem.get("keywords", []),
                "related_agents": mem.get("related_agents", []),
                "location": mem.get("location"),
                "created_at": datetime.now().isoformat(),
            }
            
            if mem.get("game_time"):
                payload["game_time"] = mem["game_time"].isoformat()
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=mem["embedding"],
                    payload=payload,
                )
            )
        
        self.client.upsert(
            collection_name=self._collection_name,
            points=points,
        )
        
        logger.info(f"Batch upserted {len(points)} memories")
        return point_ids
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆向量"""
        point_id = self._generate_point_id(memory_id)
        
        self.client.delete(
            collection_name=self._collection_name,
            points_selector=models.PointIdsList(
                points=[point_id],
            ),
        )
        
        logger.debug(f"Deleted memory {memory_id}")
        return True
    
    async def delete_agent_memories(self, agent_id: str) -> int:
        """删除智能体的所有记忆向量"""
        result = self.client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=agent_id),
                        )
                    ]
                )
            ),
        )
        
        logger.info(f"Deleted memories for agent {agent_id}")
        return 1  # Qdrant不返回删除数量
    
    # ===================
    # 检索操作
    # ===================
    
    async def search_similar(
        self,
        query_embedding: List[float],
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        语义相似度检索
        
        Args:
            query_embedding: 查询向量
            agent_id: 过滤特定智能体
            memory_type: 过滤记忆类型
            min_importance: 最小重要性
            limit: 返回数量
            score_threshold: 最小相似度阈值
            
        Returns:
            检索结果列表
        """
        # 构建过滤条件
        must_conditions = []
        
        if agent_id:
            must_conditions.append(
                FieldCondition(
                    key="agent_id",
                    match=MatchValue(value=agent_id),
                )
            )
        
        if memory_type:
            must_conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchValue(value=memory_type),
                )
            )
        
        if min_importance is not None:
            must_conditions.append(
                FieldCondition(
                    key="importance",
                    range=models.Range(gte=min_importance),
                )
            )
        
        query_filter = None
        if must_conditions:
            query_filter = Filter(must=must_conditions)
        
        # 执行搜索
        results = self.client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            search_params=SearchParams(
                exact=False,  # 使用近似搜索加速
                hnsw_ef=128,
            ),
        )
        
        # 格式化结果
        memories = []
        for hit in results:
            memories.append({
                "memory_id": hit.payload.get("memory_id"),
                "agent_id": hit.payload.get("agent_id"),
                "content": hit.payload.get("content"),
                "memory_type": hit.payload.get("memory_type"),
                "importance": hit.payload.get("importance"),
                "keywords": hit.payload.get("keywords"),
                "related_agents": hit.payload.get("related_agents"),
                "location": hit.payload.get("location"),
                "score": hit.score,
            })
        
        return memories
    
    async def search_by_agent(
        self,
        query_embedding: List[float],
        agent_id: str,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """检索特定智能体的相关记忆"""
        return await self.search_similar(
            query_embedding=query_embedding,
            agent_id=agent_id,
            limit=limit,
            score_threshold=score_threshold,
        )
    
    async def search_about_agent(
        self,
        query_embedding: List[float],
        target_agent_id: str,
        observer_agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        检索关于特定智能体的记忆
        
        Args:
            query_embedding: 查询向量
            target_agent_id: 被查询的智能体ID
            observer_agent_id: 观察者智能体ID（可选）
            limit: 返回数量
        """
        must_conditions = [
            FieldCondition(
                key="related_agents",
                match=MatchValue(value=target_agent_id),
            )
        ]
        
        if observer_agent_id:
            must_conditions.append(
                FieldCondition(
                    key="agent_id",
                    match=MatchValue(value=observer_agent_id),
                )
            )
        
        results = self.client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            query_filter=Filter(must=must_conditions),
            limit=limit,
        )
        
        return [
            {
                "memory_id": hit.payload.get("memory_id"),
                "agent_id": hit.payload.get("agent_id"),
                "content": hit.payload.get("content"),
                "score": hit.score,
            }
            for hit in results
        ]
    
    async def search_by_location(
        self,
        query_embedding: List[float],
        location: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索特定地点的记忆"""
        must_conditions = [
            FieldCondition(
                key="location",
                match=MatchValue(value=location),
            )
        ]
        
        if agent_id:
            must_conditions.append(
                FieldCondition(
                    key="agent_id",
                    match=MatchValue(value=agent_id),
                )
            )
        
        results = self.client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            query_filter=Filter(must=must_conditions),
            limit=limit,
        )
        
        return [
            {
                "memory_id": hit.payload.get("memory_id"),
                "content": hit.payload.get("content"),
                "score": hit.score,
            }
            for hit in results
        ]
    
    # ===================
    # 统计操作
    # ===================
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        info = self.client.get_collection(self._collection_name)
        
        return {
            "name": self._collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
            "optimizer_status": info.optimizer_status,
        }
    
    async def count_agent_memories(self, agent_id: str) -> int:
        """计算智能体的记忆数量"""
        result = self.client.count(
            collection_name=self._collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id),
                    )
                ]
            ),
            exact=True,
        )
        return result.count
    
    # ===================
    # 维护操作
    # ===================
    
    async def recreate_collection(self):
        """重建集合（清空所有数据）"""
        try:
            self.client.delete_collection(self._collection_name)
            logger.warning(f"Deleted collection: {self._collection_name}")
        except Exception:
            pass
        
        await self._create_collection()
        logger.info(f"Recreated collection: {self._collection_name}")
    
    async def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._initialized = False
            logger.info("Closed Qdrant connection")


# ===================
# 全局实例
# ===================

vector_store = VectorStoreService()


async def get_vector_store() -> VectorStoreService:
    """获取向量存储服务（依赖注入）"""
    if not vector_store._initialized:
        await vector_store.initialize()
    return vector_store
