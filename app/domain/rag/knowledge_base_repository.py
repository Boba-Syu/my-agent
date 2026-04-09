"""
知识库仓库接口

领域层定义的仓库接口，基础设施层负责实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.rag.knowledge_base import KnowledgeBase
from app.domain.rag.knowledge_base_type import KnowledgeBaseType


class KnowledgeBaseRepository(ABC):
    """
    知识库仓库接口
    
    提供知识库的CRUD操作。
    """
    
    @abstractmethod
    def save(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """
        保存知识库
        
        Args:
            knowledge_base: 知识库实体
            
        Returns:
            保存后的知识库
        """
        pass
    
    @abstractmethod
    def get(self, id: str) -> KnowledgeBase | None:
        """
        根据ID获取知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            知识库实体，不存在返回None
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> KnowledgeBase | None:
        """
        根据名称获取知识库
        
        Args:
            name: 知识库名称
            
        Returns:
            知识库实体，不存在返回None
        """
        pass
    
    @abstractmethod
    def list_all(self, limit: int = 100) -> list[KnowledgeBase]:
        """
        获取所有知识库
        
        Args:
            limit: 返回数量限制
            
        Returns:
            知识库列表
        """
        pass
    
    @abstractmethod
    def list_by_type(
        self,
        kb_type: KnowledgeBaseType,
        limit: int = 100,
    ) -> list[KnowledgeBase]:
        """
        根据类型获取知识库
        
        Args:
            kb_type: 知识库类型
            limit: 返回数量限制
            
        Returns:
            知识库列表
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查知识库是否存在
        
        Args:
            id: 知识库ID
            
        Returns:
            是否存在
        """
        pass
