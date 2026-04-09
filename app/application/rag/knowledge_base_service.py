"""
知识库应用服务

协调知识库领域对象完成用户用例。
"""

from __future__ import annotations

import logging
from typing import Any

from app.application.rag.dto import KnowledgeBaseDTO, CreateKnowledgeBaseRequest
from app.domain.rag.knowledge_base import KnowledgeBase
from app.domain.rag.knowledge_base_repository import KnowledgeBaseRepository
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    知识库应用服务
    
    提供知识库的CRUD操作，协调领域层完成业务逻辑。
    """
    
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
    ):
        """
        初始化服务
        
        Args:
            repository: 知识库仓库
        """
        self._repository = repository
    
    def create_knowledge_base(
        self,
        request: CreateKnowledgeBaseRequest,
    ) -> KnowledgeBaseDTO:
        """
        创建知识库
        
        Args:
            request: 创建请求
            
        Returns:
            创建后的知识库DTO
            
        Raises:
            ValueError: 名称已存在
        """
        # 检查名称是否已存在
        existing = self._repository.get_by_name(request.name)
        if existing:
            raise ValueError(f"知识库名称 '{request.name}' 已存在")
        
        # 创建知识库实体
        kb_type = KnowledgeBaseType.from_string(request.kb_type)
        
        knowledge_base = KnowledgeBase(
            name=request.name,
            description=request.description or "",
            kb_type=kb_type,
        )
        
        # 保存
        saved = self._repository.save(knowledge_base)
        logger.info(f"创建知识库: {saved.id} - {saved.name}")
        
        return KnowledgeBaseDTO.from_entity(saved)
    
    def get_knowledge_base(self, id: str) -> KnowledgeBaseDTO | None:
        """
        获取知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            知识库DTO，不存在返回None
        """
        knowledge_base = self._repository.get(id)
        if knowledge_base:
            return KnowledgeBaseDTO.from_entity(knowledge_base)
        return None
    
    def list_knowledge_bases(
        self,
        kb_type: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeBaseDTO]:
        """
        获取知识库列表
        
        Args:
            kb_type: 按类型过滤
            limit: 返回数量限制
            
        Returns:
            知识库DTO列表
        """
        if kb_type:
            kb_type_enum = KnowledgeBaseType.from_string(kb_type)
            knowledge_bases = self._repository.list_by_type(kb_type_enum, limit)
        else:
            knowledge_bases = self._repository.list_all(limit)
        
        return [KnowledgeBaseDTO.from_entity(kb) for kb in knowledge_bases]
    
    def update_knowledge_base(
        self,
        id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBaseDTO:
        """
        更新知识库
        
        Args:
            id: 知识库ID
            name: 新名称
            description: 新描述
            
        Returns:
            更新后的知识库DTO
            
        Raises:
            ValueError: 知识库不存在或名称已存在
        """
        knowledge_base = self._repository.get(id)
        if not knowledge_base:
            raise ValueError(f"知识库不存在: {id}")
        
        # 如果修改名称，检查是否已存在
        if name and name != knowledge_base.name:
            existing = self._repository.get_by_name(name)
            if existing and existing.id != id:
                raise ValueError(f"知识库名称 '{name}' 已存在")
        
        # 更新
        knowledge_base.update(name=name, description=description)
        saved = self._repository.save(knowledge_base)
        
        logger.info(f"更新知识库: {saved.id}")
        return KnowledgeBaseDTO.from_entity(saved)
    
    def delete_knowledge_base(self, id: str) -> bool:
        """
        删除知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            是否成功删除
            
        Note:
            删除知识库不会删除关联的文档，需要额外处理
        """
        success = self._repository.delete(id)
        if success:
            logger.info(f"删除知识库: {id}")
        return success
