"""
RAG 领域层

包含文档管理、检索、向量存储等核心业务逻辑。
"""

from __future__ import annotations

from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.query import Query, SubQuery
from app.domain.rag.search_result import SearchResult, RankedResult
from app.domain.rag.document_repository import DocumentRepository
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.domain.rag.reranker import Reranker
from app.domain.rag.document_processor import DocumentProcessor

__all__ = [
    # 枚举
    "KnowledgeBaseType",
    # 实体和值对象
    "Document",
    "DocumentChunk",
    "Query",
    "SubQuery",
    "SearchResult",
    "RankedResult",
    # 接口
    "DocumentRepository",
    "VectorStore",
    "KeywordIndex",
    "Reranker",
    "DocumentProcessor",
]
