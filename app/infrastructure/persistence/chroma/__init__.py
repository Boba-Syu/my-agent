"""Chroma 持久化模块

提供向量存储和文档仓库的Chroma实现，支持 Windows 平台。
"""

from __future__ import annotations

from .chroma_vector_store import ChromaVectorStore
from .chroma_document_repo import ChromaDocumentRepository

__all__ = [
    "ChromaVectorStore",
    "ChromaDocumentRepository",
]
