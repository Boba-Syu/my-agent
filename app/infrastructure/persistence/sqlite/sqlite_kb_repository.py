"""
SQLite 知识库仓库实现

实现领域层的 KnowledgeBaseRepository 接口。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.db.sqlite_client import SQLiteClient
from app.domain.rag.knowledge_base import KnowledgeBase
from app.domain.rag.knowledge_base_repository import KnowledgeBaseRepository
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class SQLiteKnowledgeBaseRepository(KnowledgeBaseRepository):
    """
    SQLite 知识库仓库实现
    
    实现领域层的 KnowledgeBaseRepository 接口，
    提供知识库的持久化功能。
    """
    
    def __init__(self, client: SQLiteClient | None = None):
        """
        初始化仓库
        
        Args:
            client: SQLite 客户端，None 时自动创建
        """
        self._client = client or SQLiteClient()
        self._ensure_table()
    
    def _ensure_table(self) -> None:
        """确保表结构存在"""
        self._client.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                kb_type TEXT NOT NULL,
                document_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
    
    def save(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """
        保存知识库
        
        Args:
            knowledge_base: 知识库实体
            
        Returns:
            保存后的知识库
        """
        data = knowledge_base.to_dict()
        
        # 检查是否已存在
        existing = self.get(knowledge_base.id)
        
        if existing:
            # 更新
            self._client.execute(
                """
                UPDATE knowledge_bases
                SET name = :name,
                    description = :description,
                    kb_type = :kb_type,
                    document_count = :document_count,
                    updated_at = :updated_at,
                    metadata = :metadata
                WHERE id = :id
                """,
                {
                    "id": data["id"],
                    "name": data["name"],
                    "description": data["description"],
                    "kb_type": data["kb_type"],
                    "document_count": data["document_count"],
                    "updated_at": data["updated_at"],
                    "metadata": json.dumps(data["metadata"]),
                },
            )
        else:
            # 插入
            self._client.execute(
                """
                INSERT INTO knowledge_bases
                (id, name, description, kb_type, document_count, created_at, updated_at, metadata)
                VALUES (:id, :name, :description, :kb_type, :document_count, :created_at, :updated_at, :metadata)
                """,
                {
                    "id": data["id"],
                    "name": data["name"],
                    "description": data["description"],
                    "kb_type": data["kb_type"],
                    "document_count": data["document_count"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "metadata": json.dumps(data["metadata"]),
                },
            )
        
        return knowledge_base
    
    def get(self, id: str) -> KnowledgeBase | None:
        """
        根据ID获取知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            知识库实体，不存在返回None
        """
        rows = self._client.query(
            "SELECT * FROM knowledge_bases WHERE id = :id",
            {"id": id},
        )
        if not rows:
            return None
        return self._row_to_entity(rows[0])
    
    def get_by_name(self, name: str) -> KnowledgeBase | None:
        """
        根据名称获取知识库
        
        Args:
            name: 知识库名称
            
        Returns:
            知识库实体，不存在返回None
        """
        rows = self._client.query(
            "SELECT * FROM knowledge_bases WHERE name = :name",
            {"name": name},
        )
        if not rows:
            return None
        return self._row_to_entity(rows[0])
    
    def list_all(self, limit: int = 100) -> list[KnowledgeBase]:
        """
        获取所有知识库
        
        Args:
            limit: 返回数量限制
            
        Returns:
            知识库列表
        """
        rows = self._client.query(
            """
            SELECT * FROM knowledge_bases
            ORDER BY updated_at DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )
        return [self._row_to_entity(row) for row in rows]
    
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
        rows = self._client.query(
            """
            SELECT * FROM knowledge_bases
            WHERE kb_type = :kb_type
            ORDER BY updated_at DESC
            LIMIT :limit
            """,
            {"kb_type": kb_type.value, "limit": limit},
        )
        return [self._row_to_entity(row) for row in rows]
    
    def delete(self, id: str) -> bool:
        """
        删除知识库
        
        Args:
            id: 知识库ID
            
        Returns:
            是否成功删除
        """
        result = self._client.execute(
            "DELETE FROM knowledge_bases WHERE id = :id",
            {"id": id},
        )
        return result.rowcount > 0
    
    def exists(self, id: str) -> bool:
        """
        检查知识库是否存在
        
        Args:
            id: 知识库ID
            
        Returns:
            是否存在
        """
        rows = self._client.query(
            "SELECT 1 FROM knowledge_bases WHERE id = :id LIMIT 1",
            {"id": id},
        )
        return len(rows) > 0
    
    def update_document_count(self, id: str, delta: int) -> bool:
        """
        更新文档计数
        
        Args:
            id: 知识库ID
            delta: 变化量（正数增加，负数减少）
            
        Returns:
            是否成功更新
        """
        result = self._client.execute(
            """
            UPDATE knowledge_bases
            SET document_count = MAX(0, document_count + :delta),
                updated_at = :updated_at
            WHERE id = :id
            """,
            {
                "id": id,
                "delta": delta,
                "updated_at": datetime.now().isoformat(),
            },
        )
        return result.rowcount > 0
    
    def _row_to_entity(self, row: dict) -> KnowledgeBase:
        """
        将数据库行转换为领域实体
        
        Args:
            row: 数据库行字典
            
        Returns:
            知识库实体
        """
        metadata = {}
        if row.get("metadata"):
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                pass
        
        return KnowledgeBase(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            kb_type=KnowledgeBaseType(row["kb_type"]),
            document_count=row.get("document_count", 0),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
            metadata=metadata,
        )
