"""
文档聚合根

RAG系统的核心领域模型，代表一份文档及其分块。
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class DocumentStatus(Enum):
    """文档处理状态"""
    
    PENDING = "pending"
    """待处理"""
    
    PROCESSING = "processing"
    """处理中"""
    
    PROCESSED = "processed"
    """已处理完成"""
    
    FAILED = "failed"
    """处理失败"""


class Document(AggregateRoot):
    """
    文档聚合根
    
    表示一份文档及其所有分块，是RAG系统的核心领域模型。
    
    聚合边界包含：
    - 文档基本信息（标题、来源、类型）
    - 知识库类型分类
    - 文档分块列表
    - 处理状态
    
    业务规则：
    - 文档必须有标题和内容
    - 分块后不能修改原始内容
    - 删除文档会级联删除所有分块
    
    Example:
        doc = Document(
            id=None,
            title="产品使用手册",
            source="docs/manual.pdf",
            doc_type="pdf",
            kb_type=KnowledgeBaseType.FAQ,
            content="...原始内容..."
        )
        
        # 分块处理
        doc.split_into_chunks(chunk_size=500, overlap=50)
    """
    
    def __init__(
        self,
        id: str | None,
        title: str,
        source: str,
        doc_type: str,
        kb_type: KnowledgeBaseType,
        content: str,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ):
        """
        初始化文档聚合根
        
        Args:
            id: 文档ID，None表示新文档
            title: 文档标题
            source: 文档来源（文件路径或URL）
            doc_type: 文档类型（pdf/word/txt/md）
            kb_type: 知识库类型
            content: 文档原始内容
            metadata: 文档元数据
            created_at: 创建时间
            
        Raises:
            ValueError: 参数验证失败
        """
        super().__init__(id)
        
        # 验证必填字段
        if not title or not title.strip():
            raise ValueError("文档标题不能为空")
        if not source or not source.strip():
            raise ValueError("文档来源不能为空")
        if not content:
            raise ValueError("文档内容不能为空")
        
        self._id = id
        self._title = title.strip()
        self._source = source
        self._doc_type = doc_type.lower()
        self._kb_type = kb_type
        self._content = content
        self._metadata = metadata or {}
        self._chunks: list[DocumentChunk] = []
        self._status = DocumentStatus.PENDING
        self._error_message: str | None = None
        self._created_at = created_at or datetime.now()
        self._updated_at = self._created_at
        
        logger.debug(f"创建文档: {self}")
    
    # -------------------------------------------------------------------------
    # 属性
    # -------------------------------------------------------------------------
    
    @property
    def title(self) -> str:
        """文档标题"""
        return self._title
    
    @property
    def source(self) -> str:
        """文档来源"""
        return self._source
    
    @property
    def doc_type(self) -> str:
        """文档类型"""
        return self._doc_type
    
    @property
    def kb_type(self) -> KnowledgeBaseType:
        """知识库类型"""
        return self._kb_type
    
    @property
    def content(self) -> str:
        """文档原始内容"""
        return self._content
    
    @property
    def metadata(self) -> dict[str, Any]:
        """文档元数据"""
        return self._metadata.copy()
    
    @property
    def chunks(self) -> list[DocumentChunk]:
        """文档分块列表"""
        return self._chunks.copy()
    
    @property
    def status(self) -> DocumentStatus:
        """处理状态"""
        return self._status
    
    @property
    def error_message(self) -> str | None:
        """错误信息（处理失败时）"""
        return self._error_message
    
    @property
    def created_at(self) -> datetime:
        """创建时间"""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """更新时间"""
        return self._updated_at
    
    @property
    def char_count(self) -> int:
        """字符数"""
        return len(self._content)
    
    @property
    def chunk_count(self) -> int:
        """分块数量"""
        return len(self._chunks)
    
    @property
    def is_processed(self) -> bool:
        """是否已处理完成"""
        return self._status == DocumentStatus.PROCESSED
    
    # -------------------------------------------------------------------------
    # 业务方法
    # -------------------------------------------------------------------------
    
    def split_into_chunks(
        self,
        chunks: list[DocumentChunk],
    ) -> None:
        """
        设置文档分块
        
        由文档处理器调用，将分块结果保存到聚合根。
        
        Args:
            chunks: 分块列表
        """
        if not chunks:
            raise ValueError("分块列表不能为空")
        
        self._chunks = chunks
        self._status = DocumentStatus.PROCESSED
        self._updated_at = datetime.now()
        self._increment_version()
        
        logger.debug(f"文档分块完成: {self._title}, 共 {len(chunks)} 个分块")
    
    def mark_processing(self) -> None:
        """标记为处理中"""
        self._status = DocumentStatus.PROCESSING
        self._error_message = None
        self._updated_at = datetime.now()
        self._increment_version()
    
    def mark_failed(self, error_message: str) -> None:
        """
        标记为处理失败
        
        Args:
            error_message: 错误信息
        """
        self._status = DocumentStatus.FAILED
        self._error_message = error_message
        self._updated_at = datetime.now()
        self._increment_version()
        
        logger.error(f"文档处理失败: {self._title}, 错误: {error_message}")
    
    def update_metadata(self, metadata: dict[str, Any]) -> None:
        """
        更新元数据
        
        Args:
            metadata: 新元数据（会合并到现有元数据）
        """
        self._metadata.update(metadata)
        self._updated_at = datetime.now()
        self._increment_version()
    
    def get_chunk_by_index(self, index: int) -> DocumentChunk | None:
        """
        根据索引获取分块
        
        Args:
            index: 分块索引
            
        Returns:
            分块，不存在返回None
        """
        for chunk in self._chunks:
            if chunk.chunk_index == index:
                return chunk
        return None
    
    def to_snapshot(self) -> dict[str, Any]:
        """
        生成快照
        
        Returns:
            文档的字典表示
        """
        return {
            "id": self._id,
            "title": self._title,
            "source": self._source,
            "doc_type": self._doc_type,
            "kb_type": self._kb_type.value,
            "metadata": self._metadata,
            "status": self._status.value,
            "chunk_count": self.chunk_count,
            "char_count": self.char_count,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "version": self._version,
        }
    
    def __repr__(self) -> str:
        return (
            f"Document("
            f"id={self._id!r}, "
            f"title={self._title!r}, "
            f"type={self._doc_type}, "
            f"kb={self._kb_type.value}, "
            f"chunks={self.chunk_count}"
            f")"
        )
