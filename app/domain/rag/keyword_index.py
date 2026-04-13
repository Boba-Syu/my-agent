"""
关键词索引接口

定义关键词检索的领域层契约。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class KeywordIndex(ABC):
    """
    关键词索引接口
    
    定义关键词检索（BM25/倒排索引）的领域层契约，
    用于与向量检索结合实现混合检索。
    
    Example:
        class WhooshKeywordIndex(KeywordIndex):
            def add_document(self, document_id, chunks, kb_type):
                # Whoosh实现
                pass
    """
    
    @abstractmethod
    def add_document(
        self,
        document_id: str,
        chunks: list,
        kb_type: KnowledgeBaseType,
    ) -> None:
        """
        添加文档到索引
        
        Args:
            document_id: 文档ID
            chunks: 文档分块列表
            kb_type: 知识库类型
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """
        关键词检索
        
        Args:
            query: 查询文本
            kb_types: 知识库类型过滤
            top_k: 返回结果数量
            
        Returns:
            (分块ID, 分数) 列表，按分数降序
        """
        pass
    
    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档的所有索引
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def optimize(self) -> None:
        """优化索引（合并段、清理等）"""
        pass

    @abstractmethod
    def get_chunk_content(self, chunk_id: str) -> str | None:
        """
        根据chunk_id获取分块内容

        用于关键词检索后获取实际的分块内容。

        Args:
            chunk_id: 分块ID (格式: {document_id}_{chunk_index})

        Returns:
            分块内容，不存在返回None
        """
        pass
