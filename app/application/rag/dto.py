"""
RAG 应用层 DTO

数据传输对象，用于应用层与接口层之间的数据交换。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.rag.document import Document
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.search_result import RankedResult


@dataclass(frozen=True)
class RAGQueryRequest:
    """RAG查询请求 DTO"""
    
    query: str
    """用户查询"""
    
    kb_types: list[str] | None = None
    """指定检索的知识库类型，None表示自动判断"""
    
    top_k: int = 10
    """返回结果数量"""
    
    use_rerank: bool = True
    """是否使用重排序"""


@dataclass(frozen=True)
class SourceInfo:
    """来源信息 DTO"""
    
    document_id: str
    """文档ID"""
    
    document_title: str
    """文档标题"""
    
    content: str
    """引用内容"""
    
    score: float
    """相关度分数"""


@dataclass(frozen=True)
class RAGQueryResponse:
    """RAG查询响应 DTO"""
    
    answer: str
    """生成的答案"""
    
    sources: list[SourceInfo]
    """答案来源"""
    
    sub_queries: list[str]
    """分解的子查询"""
    
    @classmethod
    def from_ranked_results(
        cls,
        answer: str,
        results: list[RankedResult],
    ) -> RAGQueryResponse:
        """从重排序结果创建响应"""
        sources = []
        for r in results:
            sources.append(SourceInfo(
                document_id=r.search_result.document_id or "unknown",
                document_title=r.search_result.document_title or "未知文档",
                content=r.content[:500] + "..." if len(r.content) > 500 else r.content,
                score=r.rerank_score,
            ))
        
        return cls(
            answer=answer,
            sources=sources,
            sub_queries=[],
        )


@dataclass(frozen=True)
class DocumentUploadRequest:
    """文档上传请求 DTO"""
    
    file_path: str
    """文件路径"""
    
    title: str | None = None
    """文档标题，None时使用文件名"""
    
    kb_type: str = "faq"
    """知识库类型"""
    
    metadata: dict[str, Any] | None = None
    """额外元数据"""


@dataclass(frozen=True)
class DocumentDTO:
    """文档数据 DTO"""
    
    id: str
    """文档ID"""
    
    title: str
    """标题"""
    
    source: str
    """来源"""
    
    doc_type: str
    """文档类型"""
    
    kb_type: str
    """知识库类型"""
    
    status: str
    """处理状态"""
    
    chunk_count: int
    """分块数量"""
    
    char_count: int
    """字符数"""
    
    @classmethod
    def from_entity(cls, entity: Document) -> DocumentDTO:
        """从领域实体创建 DTO"""
        return cls(
            id=entity.id or "",
            title=entity.title,
            source=entity.source,
            doc_type=entity.doc_type,
            kb_type=entity.kb_type.value,
            status=entity.status.value,
            chunk_count=entity.chunk_count,
            char_count=entity.char_count,
        )
