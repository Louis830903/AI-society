"""
嵌入服务
========
文本向量化服务，支持多种嵌入模型

支持的模型：
- DeepSeek 嵌入（通过API）
- OpenAI text-embedding-3-small（通过API）
- 本地 sentence-transformers 模型
"""

import hashlib
from typing import List, Optional, Dict
import logging
from functools import lru_cache

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ===================
# 嵌入缓存
# ===================

_embedding_cache: Dict[str, List[float]] = {}
MAX_CACHE_SIZE = 10000


def _get_cache_key(text: str, model: str) -> str:
    """生成缓存键"""
    return hashlib.md5(f"{model}:{text}".encode()).hexdigest()


def _get_cached_embedding(text: str, model: str) -> Optional[List[float]]:
    """获取缓存的嵌入"""
    key = _get_cache_key(text, model)
    return _embedding_cache.get(key)


def _cache_embedding(text: str, model: str, embedding: List[float]):
    """缓存嵌入"""
    if len(_embedding_cache) >= MAX_CACHE_SIZE:
        # 简单的缓存淘汰：清空一半
        keys = list(_embedding_cache.keys())
        for key in keys[:len(keys)//2]:
            del _embedding_cache[key]
    
    key = _get_cache_key(text, model)
    _embedding_cache[key] = embedding


# ===================
# 嵌入服务类
# ===================

class EmbeddingService:
    """嵌入服务"""
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        初始化嵌入服务
        
        Args:
            model: 嵌入模型名称
            api_key: API密钥
            base_url: API基础URL
        """
        self.model = model
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or "https://api.openai.com/v1"  # OpenAI兼容接口
        self._client: Optional[httpx.AsyncClient] = None
        
        # 模型维度映射
        self._dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
    
    @property
    def dimension(self) -> int:
        """获取嵌入维度"""
        return self._dimensions.get(self.model, 1536)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._client
    
    async def embed_text(
        self,
        text: str,
        use_cache: bool = True,
    ) -> List[float]:
        """
        生成单个文本的嵌入向量
        
        Args:
            text: 输入文本
            use_cache: 是否使用缓存
            
        Returns:
            嵌入向量
        """
        # 检查缓存
        if use_cache:
            cached = _get_cached_embedding(text, self.model)
            if cached:
                return cached
        
        # 调用API
        embedding = await self._call_embedding_api([text])
        result = embedding[0]
        
        # 缓存结果
        if use_cache:
            _cache_embedding(text, self.model, result)
        
        return result
    
    async def embed_texts(
        self,
        texts: List[str],
        use_cache: bool = True,
    ) -> List[List[float]]:
        """
        批量生成文本嵌入
        
        Args:
            texts: 文本列表
            use_cache: 是否使用缓存
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        # 检查缓存
        for i, text in enumerate(texts):
            if use_cache:
                cached = _get_cached_embedding(text, self.model)
                if cached:
                    results[i] = cached
                    continue
            
            texts_to_embed.append(text)
            indices_to_embed.append(i)
        
        # 批量调用API
        if texts_to_embed:
            embeddings = await self._call_embedding_api(texts_to_embed)
            
            for i, embedding in zip(indices_to_embed, embeddings):
                results[i] = embedding
                if use_cache:
                    _cache_embedding(texts[i], self.model, embedding)
        
        return results
    
    async def _call_embedding_api(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        调用嵌入API
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json={
                    "model": self.model,
                    "input": texts,
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 按索引排序结果
            embeddings = [None] * len(texts)
            for item in data["data"]:
                embeddings[item["index"]] = item["embedding"]
            
            logger.debug(f"Generated {len(texts)} embeddings with {self.model}")
            return embeddings
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ===================
# 本地嵌入服务（可选）
# ===================

class LocalEmbeddingService:
    """
    本地嵌入服务
    
    使用 sentence-transformers 进行本地向量化
    需要安装：pip install sentence-transformers
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化本地嵌入服务
        
        Args:
            model_name: 模型名称
        """
        self.model_name = model_name
        self._model = None
    
    @property
    def dimension(self) -> int:
        """获取嵌入维度"""
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
        }
        return dimensions.get(self.model_name, 384)
    
    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded local embedding model: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model
    
    async def embed_text(self, text: str) -> List[float]:
        """生成单个文本的嵌入"""
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本嵌入"""
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    async def close(self):
        """释放模型"""
        self._model = None


# ===================
# 全局实例
# ===================

# 默认使用API嵌入服务
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取嵌入服务单例"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            model="text-embedding-3-small",
        )
    
    return _embedding_service


async def embed_text(text: str) -> List[float]:
    """便捷函数：生成文本嵌入"""
    service = get_embedding_service()
    return await service.embed_text(text)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """便捷函数：批量生成文本嵌入"""
    service = get_embedding_service()
    return await service.embed_texts(texts)
