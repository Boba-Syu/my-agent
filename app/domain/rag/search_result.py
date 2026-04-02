"""
检索结果值对象

表示RAG检索的结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.shared.value_object import ValueObject
from app.domain.rag.document_chunk import DocumentChunk


@dataclass(frozen=True)
class SearchResult(ValueObject):
    """
    检索结果值对象
    
    表示从知识库中检索到的一个结果。
    
    Example:
        result = SearchResult(
            chunk=chunk,
            score=0.85,
            source="vector",
            metadata={"doc_id": "doc-001"}
        )
    """
    
    chunk: DocumentChunk
    """匹配的文档分块"""
    
    score: float
    """匹配分数（0-1之间）"""
    
    source: str
    """检索来源（vector/keyword/hybrid）"""
    
    document_id: str | None = None
    """所属文档ID"""
    
    document_title: str | None = None
    """所属文档标题"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """额外元数据"""
    
    def __post_init__(self):
        """初始化后验证"""
        if not 0 <= self.score <= 1:
            raise ValueError("分数必须在0-1之间")
    
    @property
    def content(self) -> str:
        """获取内容文本"""
        return self.chunk.content
    
    @property
    def char_count(self) -> int:
        """获取字符数"""
        return self.chunk.char_count


@dataclass(frozen=True)
class RankedResult(ValueObject):
    """
    重排序后的结果值对象
    
    经过Reranker重排序后的检索结果。
    
    Example:
        ranked = RankedResult(
            search_result=result,
            rerank_score=0.92,
            rank=1
        )
    """
    
    search_result: SearchResult
    """原始检索结果"""
    
    rerank_score: float
    """重排序分数"""
    
    rank: int
    """排序位次（从1开始）"""
    
    def __post_init__(self):
        """初始化后验证"""
        if self.rerank_score < 0:
            raise ValueError("重排序分数不能为负数")
        if self.rank < 1:
            raise ValueError("排序位次必须从1开始")
    
    @property
    def content(self) -> str:
        """获取内容文本"""
        return self.search_result.content
    
    @property
    def document_title(self) -> str | None:
        """获取文档标题"""
        return self.search_result.document_title
    
    @property
    def original_score(self) -> float:
        """获取原始分数"""
        return self.search_result.score
