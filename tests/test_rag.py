"""
RAG系统单元测试入口

运行所有RAG相关测试:
    py -m pytest tests/test_rag.py -v
"""

from __future__ import annotations

import pytest

# 导入所有测试类
from tests.test_rag_domain import (
    TestDocumentChunk,
    TestDocument,
    TestKnowledgeBaseType,
    TestQuery,
    TestSubQuery,
    TestSearchResult,
    TestRankedResult,
)

from tests.test_rag_processors import (
    TestTextProcessor,
    TestProcessorFactory,
    TestDocumentProcessorInterface,
    TestDocumentChunkCreation,
)

from tests.test_rag_service import (
    TestRAGDTOs,
    TestQueryDecomposition,
    TestSearchResultScoring,
    TestKnowledgeBaseRouting,
    TestRAGRetrievalFlow,
    TestDocumentProcessingFlow,
    TestRAGFusion,
)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
