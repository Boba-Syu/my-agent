"""
RAG应用服务单元测试

测试RAG服务、查询分解、检索流程等
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.query import Query, SubQuery
from app.domain.rag.search_result import SearchResult, RankedResult
from app.domain.rag.reranker import Reranker
from app.application.rag.dto import (
    DocumentUploadRequest,
    DocumentDTO,
    RAGQueryRequest,
    RAGQueryResponse,
    SourceInfo,
)


class TestRAGDTOs:
    """RAG数据传输对象测试"""
    
    def test_document_upload_request(self):
        """文档上传请求DTO"""
        request = DocumentUploadRequest(
            file_path="/path/to/doc.pdf",
            title="测试文档",
            kb_type="faq",
            metadata={"author": "test"}
        )
        
        assert request.file_path == "/path/to/doc.pdf"
        assert request.title == "测试文档"
        assert request.kb_type == "faq"
        assert request.metadata["author"] == "test"
    
    def test_document_upload_request_defaults(self):
        """文档上传请求默认值"""
        request = DocumentUploadRequest(file_path="/path/to/doc.pdf")
        
        assert request.title is None
        assert request.kb_type == "faq"
        assert request.metadata is None
    
    def test_document_dto(self):
        """文档响应DTO"""
        doc = DocumentDTO(
            id="doc-001",
            title="测试文档",
            doc_type="pdf",
            kb_type="faq",
            source="/path/to/doc.pdf",
            status="processed",
            chunk_count=5,
            char_count=100
        )
        
        assert doc.id == "doc-001"
        assert doc.title == "测试文档"
        assert doc.chunk_count == 5
        assert doc.char_count == 100
    
    def test_document_dto_from_entity(self):
        """从领域实体创建DTO"""
        entity = Document(
            id="doc-001",
            title="测试文档",
            source="/path/to/doc.pdf",
            doc_type="pdf",
            kb_type=KnowledgeBaseType.FAQ,
            content="文档内容"
        )
        
        dto = DocumentDTO.from_entity(entity)
        
        assert dto.id == "doc-001"
        assert dto.title == "测试文档"
        assert dto.kb_type == "faq"
        assert dto.status == "pending"
    
    def test_rag_query_request(self):
        """RAG查询请求DTO"""
        request = RAGQueryRequest(
            query="什么是年假政策？",
            kb_types=["regulation"],
            top_k=5,
            use_rerank=True
        )
        
        assert request.query == "什么是年假政策？"
        assert request.kb_types == ["regulation"]
        assert request.top_k == 5
        assert request.use_rerank
    
    def test_rag_query_request_defaults(self):
        """RAG查询请求默认值"""
        request = RAGQueryRequest(query="问题")
        
        assert request.kb_types is None
        assert request.top_k == 10
        assert request.use_rerank
    
    def test_source_info(self):
        """来源信息DTO"""
        source = SourceInfo(
            document_id="doc-001",
            document_title="员工手册",
            content="相关内容",
            score=0.95
        )
        
        assert source.document_id == "doc-001"
        assert source.document_title == "员工手册"
        assert source.score == 0.95
    
    def test_rag_query_response(self):
        """RAG查询响应DTO"""
        sources = [
            SourceInfo(
                document_id="c1",
                document_title="员工手册",
                content="答案内容",
                score=0.95
            )
        ]
        response = RAGQueryResponse(
            answer="年假是每年15天",
            sources=sources,
            sub_queries=["年假政策"]
        )
        
        assert response.answer == "年假是每年15天"
        assert len(response.sources) == 1
        assert response.sub_queries == ["年假政策"]
    
    def test_rag_query_response_from_ranked_results(self):
        """从重排序结果创建响应"""
        chunk = DocumentChunk(content="答案内容在这里", chunk_index=0)
        search_result = SearchResult(
            chunk=chunk,
            score=0.9,
            source="hybrid",
            document_id="doc-001",
            document_title="员工手册"
        )
        ranked = RankedResult(
            search_result=search_result,
            rerank_score=0.95,
            rank=1
        )
        
        response = RAGQueryResponse.from_ranked_results(
            answer="生成的答案",
            results=[ranked]
        )
        
        assert response.answer == "生成的答案"
        assert len(response.sources) == 1
        assert response.sources[0].score == 0.95


class TestQueryDecomposition:
    """查询分解测试"""
    
    @pytest.fixture
    def sample_query(self) -> Query:
        """示例查询"""
        return Query(
            original_query="公司的年假和病假政策是什么？",
            top_k=10
        )
    
    def test_query_creation(self, sample_query: Query):
        """查询对象创建"""
        assert sample_query.original_query == "公司的年假和病假政策是什么？"
        assert sample_query.top_k == 10
    
    def test_sub_query_creation(self):
        """子查询创建"""
        sub = SubQuery(
            query="年假政策是什么？",
            kb_types=[KnowledgeBaseType.REGULATION],
            weight=1.0
        )
        
        assert sub.query == "年假政策是什么？"
        assert sub.kb_types == [KnowledgeBaseType.REGULATION]
    
    def test_query_with_sub_queries(self, sample_query: Query):
        """添加子查询到查询"""
        new_query = Query(
            original_query=sample_query.original_query,
            sub_queries=[
                SubQuery(query="年假政策是什么？", kb_types=[KnowledgeBaseType.REGULATION]),
                SubQuery(query="病假政策是什么？", kb_types=[KnowledgeBaseType.REGULATION]),
            ]
        )
        
        assert new_query.sub_queries is not None
        assert len(new_query.sub_queries) == 2
        assert new_query.has_sub_queries


class TestSearchResultScoring:
    """搜索结果评分测试"""
    
    def test_search_result_score_comparison(self):
        """搜索结果分数比较"""
        chunk1 = DocumentChunk(content="内容1", chunk_index=0)
        chunk2 = DocumentChunk(content="内容2", chunk_index=1)
        chunk3 = DocumentChunk(content="内容3", chunk_index=2)
        
        results = [
            SearchResult(chunk=chunk1, score=0.9, source="vector"),
            SearchResult(chunk=chunk2, score=0.7, source="keyword"),
            SearchResult(chunk=chunk3, score=0.95, source="hybrid"),
        ]
        
        # 按分数排序
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        
        assert sorted_results[0].score == 0.95
        assert sorted_results[1].score == 0.9
        assert sorted_results[2].score == 0.7
    
    def test_ranked_result_final_score(self):
        """重排序结果最终分数"""
        chunk = DocumentChunk(content="内容", chunk_index=0)
        search_result = SearchResult(
            chunk=chunk,
            score=0.8,
            source="vector"
        )
        
        ranked = RankedResult(
            search_result=search_result,
            rerank_score=0.92,
            rank=1
        )
        
        assert ranked.rerank_score == 0.92
        assert ranked.rank == 1


class TestKnowledgeBaseRouting:
    """知识库路由测试"""
    
    def test_faq_kb_type(self):
        """FAQ知识库类型"""
        kb_type = KnowledgeBaseType.FAQ
        
        assert kb_type.value == "faq"
        assert kb_type == KnowledgeBaseType.FAQ
    
    def test_regulation_kb_type(self):
        """规章制度知识库类型"""
        kb_type = KnowledgeBaseType.REGULATION
        
        assert kb_type.value == "regulation"
        assert kb_type == KnowledgeBaseType.REGULATION
    
    def test_kb_type_from_string(self):
        """从字符串获取知识库类型"""
        kb_type = KnowledgeBaseType("faq")
        
        assert kb_type == KnowledgeBaseType.FAQ


class TestRAGRetrievalFlow:
    """RAG检索流程测试（Mock）"""
    
    @pytest.fixture
    def mock_document_repo(self) -> Mock:
        """Mock文档仓库"""
        repo = Mock()
        repo.search_by_vector = AsyncMock(return_value=[])
        repo.get_by_id = AsyncMock(return_value=None)
        return repo
    
    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock向量存储"""
        store = Mock()
        store.similarity_search = AsyncMock(return_value=[])
        return store
    
    @pytest.fixture
    def mock_keyword_index(self) -> Mock:
        """Mock关键词索引"""
        index = Mock()
        index.search = AsyncMock(return_value=[])
        return index
    
    @pytest.fixture
    def mock_reranker(self) -> Mock:
        """Mock重排序器"""
        reranker = Mock(spec=Reranker)
        reranker.rerank = AsyncMock(return_value=[])
        return reranker
    
    def test_retrieval_components_exist(self):
        """检索组件存在性验证"""
        # 验证所有必要的组件可以被导入
        from app.domain.rag.document_repository import DocumentRepository
        from app.domain.rag.vector_store import VectorStore
        from app.domain.rag.keyword_index import KeywordIndex
        from app.domain.rag.reranker import Reranker
        
        # 验证都是抽象基类
        assert hasattr(DocumentRepository, '__abstractmethods__')
        assert hasattr(VectorStore, '__abstractmethods__')
        assert hasattr(KeywordIndex, '__abstractmethods__')
        assert hasattr(Reranker, '__abstractmethods__')


class TestDocumentProcessingFlow:
    """文档处理流程测试"""
    
    @pytest.fixture
    def sample_document(self) -> Document:
        """示例文档"""
        return Document(
            id="doc-001",
            title="员工手册",
            source="/docs/handbook.pdf",
            doc_type="pdf",
            kb_type=KnowledgeBaseType.REGULATION,
            content="第一章：公司介绍...\n第二章：规章制度..."
        )
    
    def test_document_status_lifecycle(self, sample_document: Document):
        """文档状态生命周期"""
        # 初始状态
        assert sample_document.status.value == "pending"
        
        # 标记处理中
        sample_document.mark_processing()
        assert sample_document.status.value == "processing"
        
        # 完成分块
        chunks = [
            DocumentChunk(content="第一章内容", chunk_index=0),
            DocumentChunk(content="第二章内容", chunk_index=1),
        ]
        sample_document.split_into_chunks(chunks)
        assert sample_document.status.value == "processed"
        assert sample_document.is_processed
    
    def test_document_status_failed(self, sample_document: Document):
        """文档处理失败状态"""
        sample_document.mark_failed("PDF解析错误")
        
        assert sample_document.status.value == "failed"
        assert sample_document.error_message == "PDF解析错误"


class TestRAGFusion:
    """RAG-Fusion测试"""
    
    def test_fusion_deduplication(self):
        """融合去重"""
        chunk1 = DocumentChunk(content="相关内容A", chunk_index=0)
        chunk2 = DocumentChunk(content="相关内容B", chunk_index=1)
        chunk3 = DocumentChunk(content="相关内容C", chunk_index=2)
        
        # 模拟来自不同子查询的重复结果
        results_from_q1 = [
            SearchResult(
                chunk=chunk1,
                score=0.9,
                source="hybrid",
                document_id="doc-001"
            ),
            SearchResult(
                chunk=chunk2,
                score=0.8,
                source="vector",
                document_id="doc-001"
            ),
        ]
        
        results_from_q2 = [
            SearchResult(
                chunk=chunk1,  # 相同chunk
                score=0.85,
                source="keyword",
                document_id="doc-001"
            ),
            SearchResult(
                chunk=chunk3,
                score=0.75,
                source="hybrid",
                document_id="doc-002"
            ),
        ]
        
        # 合并并按chunk去重（保留最高分）
        all_results = results_from_q1 + results_from_q2
        seen_chunks: dict[int, SearchResult] = {}
        
        for result in all_results:
            chunk_idx = result.chunk.chunk_index
            if chunk_idx not in seen_chunks:
                seen_chunks[chunk_idx] = result
            elif result.score > seen_chunks[chunk_idx].score:
                seen_chunks[chunk_idx] = result
        
        deduplicated = list(seen_chunks.values())
        
        # 验证去重结果
        assert len(deduplicated) == 3
        
        # 验证chunk1(索引0)保留最高分0.9
        chunk_0_result = seen_chunks[0]
        assert chunk_0_result.score == 0.9


# 标记测试类型
pytestmark = [
    pytest.mark.unit,
]
