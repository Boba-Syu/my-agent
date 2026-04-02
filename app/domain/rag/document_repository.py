"""
文档仓库接口

定义文档聚合根的持久化契约。
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from app.domain.shared.repository import Repository
from app.domain.rag.document import Document
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class DocumentRepository(Repository[Document]):
    """
    文档仓库接口
    
    定义文档聚合根的持久化契约，由基础设施层实现。
    
    实现类：
    - MilvusDocumentRepository: Milvus向量数据库实现
    
    Example:
        class MilvusDocumentRepository(DocumentRepository):
            def get(self, id: str) -> Document | None:
                # Milvus实现
                pass
    """
    
    @abstractmethod
    def get(self, id: str) -> Document | None:
        """
        根据ID获取文档
        
        Args:
            id: 文档ID
            
        Returns:
            文档聚合根，不存在则返回None
        """
        pass
    
    @abstractmethod
    def list(
        self,
        kb_type: KnowledgeBaseType | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """
        查询文档列表
        
        Args:
            kb_type: 按知识库类型过滤
            status: 按处理状态过滤
            limit: 返回条数限制
            offset: 偏移量
            
        Returns:
            文档列表
        """
        pass
    
    @abstractmethod
    def save(self, document: Document) -> Document:
        """
        保存文档
        
        如果文档已有ID则更新，否则创建。
        
        Args:
            document: 文档聚合根
            
        Returns:
            保存后的文档（可能包含生成的ID）
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除文档
        
        Args:
            id: 文档ID
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查文档是否存在
        
        Args:
            id: 文档ID
            
        Returns:
            是否存在
        """
        pass
    
    @abstractmethod
    def search_by_vector(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """
        向量相似度检索
        
        Args:
            query: 查询文本
            kb_types: 知识库类型过滤
            top_k: 返回结果数量
            filters: 元数据过滤条件
            
        Returns:
            (文档, 相似度分数) 列表，按分数降序
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        pass
