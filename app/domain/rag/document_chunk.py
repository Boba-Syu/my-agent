"""
文档分块值对象

表示文档的一个分块片段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.shared.value_object import ValueObject


@dataclass(frozen=True)
class DocumentChunk(ValueObject):
    """
    文档分块值对象
    
    表示文档的一个分块片段，包含内容、位置和元数据。
    
    Attributes:
        content: 分块文本内容
        chunk_index: 分块在文档中的索引位置
        metadata: 分块元数据（页码、段落等）
        embedding: 向量嵌入（可选，存储时生成）
    
    Example:
        chunk = DocumentChunk(
            content="这是文档的第一部分内容...",
            chunk_index=0,
            metadata={"page": 1, "paragraph": 1}
        )
    """
    
    content: str
    """分块文本内容"""
    
    chunk_index: int = 0
    """分块在文档中的索引位置"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """分块元数据（页码、段落、标题等位置信息）"""
    
    embedding: list[float] | None = None
    """向量嵌入（可选，存储时由基础设施层生成）"""
    
    def __post_init__(self):
        """初始化后验证"""
        if not self.content or not self.content.strip():
            raise ValueError("分块内容不能为空")
        if self.chunk_index < 0:
            raise ValueError("分块索引不能为负数")
    
    def with_embedding(self, embedding: list[float]) -> DocumentChunk:
        """
        创建带嵌入向量的新分块
        
        Args:
            embedding: 向量嵌入
            
        Returns:
            新的DocumentChunk实例
        """
        return DocumentChunk(
            content=self.content,
            chunk_index=self.chunk_index,
            metadata=self.metadata.copy(),
            embedding=embedding,
        )
    
    @property
    def has_embedding(self) -> bool:
        """检查是否已有嵌入向量"""
        return self.embedding is not None and len(self.embedding) > 0
    
    @property
    def char_count(self) -> int:
        """获取字符数"""
        return len(self.content)
    
    def get_text_preview(self, max_length: int = 100) -> str:
        """
        获取文本预览
        
        Args:
            max_length: 最大长度
            
        Returns:
            截断后的预览文本
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
