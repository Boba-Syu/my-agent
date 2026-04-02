"""
向量存储接口

定义向量存储的领域层契约。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """
    向量存储接口
    
    定义向量存储的领域层契约，由基础设施层实现。
    
    特性：
    - 存储文档分块的向量嵌入
    - 支持语义相似度检索
    - 支持元数据过滤
    
    Example:
        class MilvusVectorStore(VectorStore):
            def add_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]):
                # Milvus实现
                pass
    """
    
    @abstractmethod
    def add_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        kb_type: KnowledgeBaseType,
    ) -> list[str]:
        """
        添加文档分块及其向量
        
        Args:
            document_id: 文档ID
            chunks: 文档分块列表
            embeddings: 对应的向量嵌入列表
            kb_type: 知识库类型
            
        Returns:
            存储的记录ID列表
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self,
        query_embedding: list[float],
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """
        向量相似度检索
        
        Args:
            query_embedding: 查询向量
            kb_types: 知识库类型过滤
            top_k: 返回结果数量
            filters: 元数据过滤条件
            
        Returns:
            (分块ID, 相似度分数) 列表，按分数降序
        """
        pass
    
    @abstractmethod
    def delete_by_document(self, document_id: str) -> bool:
        """
        删除文档的所有分块
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk | None:
        """
        根据ID获取分块
        
        Args:
            chunk_id: 分块ID
            
        Returns:
            分块，不存在返回None
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否可用
        """
        pass
