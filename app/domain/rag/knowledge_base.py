"""
知识库领域实体

知识库是RAG系统的核心概念，用于组织和管理相关文档。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.domain.rag.knowledge_base_type import KnowledgeBaseType


class KnowledgeBase:
    """
    知识库实体
    
    属性:
        id: 唯一标识
        name: 知识库名称
        description: 知识库描述
        kb_type: 知识库类型 (faq/regulation/other)
        document_count: 文档数量
        created_at: 创建时间
        updated_at: 更新时间
        metadata: 元数据
    """
    
    def __init__(
        self,
        id: str | None = None,
        name: str = "",
        description: str = "",
        kb_type: KnowledgeBaseType | None = None,
        document_count: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self._id = id or str(uuid.uuid4())
        self._name = name
        self._description = description
        self._kb_type = kb_type or KnowledgeBaseType.FAQ
        self._document_count = document_count
        self._created_at = created_at or datetime.now()
        self._updated_at = updated_at or datetime.now()
        self._metadata = metadata or {}
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._updated_at = datetime.now()
    
    @property
    def description(self) -> str:
        return self._description
    
    @description.setter
    def description(self, value: str) -> None:
        self._description = value
        self._updated_at = datetime.now()
    
    @property
    def kb_type(self) -> KnowledgeBaseType:
        return self._kb_type
    
    @kb_type.setter
    def kb_type(self, value: KnowledgeBaseType) -> None:
        self._kb_type = value
        self._updated_at = datetime.now()
    
    @property
    def document_count(self) -> int:
        return self._document_count
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        return self._updated_at
    
    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata.copy()
    
    def increment_document_count(self) -> None:
        """增加文档计数"""
        self._document_count += 1
        self._updated_at = datetime.now()
    
    def decrement_document_count(self) -> None:
        """减少文档计数"""
        if self._document_count > 0:
            self._document_count -= 1
        self._updated_at = datetime.now()
    
    def update(self, name: str | None = None, description: str | None = None) -> None:
        """更新知识库信息"""
        if name is not None:
            self._name = name
        if description is not None:
            self._description = description
        self._updated_at = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "kb_type": self._kb_type.value,
            "document_count": self._document_count,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "metadata": self._metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeBase:
        """从字典创建"""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            kb_type=KnowledgeBaseType(data.get("kb_type", "faq")),
            document_count=data.get("document_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            metadata=data.get("metadata", {}),
        )
