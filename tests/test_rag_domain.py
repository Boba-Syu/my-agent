"""
RAG领域层单元测试

测试文档、分块、查询等核心领域模型
"""

from __future__ import annotations

import pytest
from datetime import datetime

from app.domain.rag.document import Document, DocumentStatus
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.query import Query, SubQuery
from app.domain.rag.search_result import SearchResult, RankedResult


class TestDocumentChunk:
    """文档分块值对象测试"""
    
    def test_create_chunk_success(self):
        """成功创建分块"""
        chunk = DocumentChunk(
            content="这是测试内容",
            chunk_index=0,
            metadata={"page": 1}
        )
        
        assert chunk.content == "这是测试内容"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {"page": 1}
        assert not chunk.has_embedding
    
    def test_create_chunk_empty_content_raises(self):
        """空内容创建分块应抛出异常"""
        with pytest.raises(ValueError, match="分块内容不能为空"):
            DocumentChunk(content="", chunk_index=0)
        
        with pytest.raises(ValueError, match="分块内容不能为空"):
            DocumentChunk(content="   ", chunk_index=0)
    
    def test_create_chunk_negative_index_raises(self):
        """负索引创建分块应抛出异常"""
        with pytest.raises(ValueError, match="分块索引不能为负数"):
            DocumentChunk(content="内容", chunk_index=-1)
    
    def test_chunk_with_embedding(self):
        """添加嵌入向量"""
        chunk = DocumentChunk(content="测试", chunk_index=0)
        embedding = [0.1, 0.2, 0.3, 0.4]
        
        new_chunk = chunk.with_embedding(embedding)
        
        assert new_chunk.has_embedding
        assert new_chunk.embedding == embedding
        assert new_chunk.content == chunk.content  # 不变性
    
    def test_char_count(self):
        """字符数统计"""
        chunk = DocumentChunk(content="Hello World", chunk_index=0)
        assert chunk.char_count == 11
    
    def test_text_preview(self):
        """文本预览"""
        long_content = "a" * 200
        chunk = DocumentChunk(content=long_content, chunk_index=0)
        
        preview = chunk.get_text_preview(100)
        assert len(preview) == 103  # 100 + "..."
        assert preview.endswith("...")
        
        short_preview = chunk.get_text_preview(250)
        assert short_preview == long_content  # 未截断


class TestDocument:
    """文档聚合根测试"""
    
    @pytest.fixture
    def sample_document(self) -> Document:
        """示例文档"""
        return Document(
            id="doc-001",
            title="测试文档",
            source="/path/to/doc.pdf",
            doc_type="pdf",
            kb_type=KnowledgeBaseType.FAQ,
            content="这是文档的原始内容",
            metadata={"author": "test"}
        )
    
    def test_create_document_success(self, sample_document: Document):
        """成功创建文档"""
        assert sample_document.id == "doc-001"
        assert sample_document.title == "测试文档"
        assert sample_document.source == "/path/to/doc.pdf"
        assert sample_document.doc_type == "pdf"
        assert sample_document.kb_type == KnowledgeBaseType.FAQ
        assert sample_document.content == "这是文档的原始内容"
        assert sample_document.status == DocumentStatus.PENDING
        assert sample_document.metadata == {"author": "test"}
        assert sample_document.char_count == 9  # "这是文档的原始内容"
        assert sample_document.chunk_count == 0
        assert not sample_document.is_processed
    
    def test_create_document_empty_title_raises(self):
        """空标题创建文档应抛出异常"""
        with pytest.raises(ValueError, match="文档标题不能为空"):
            Document(
                id=None,
                title="",
                source="/path/test.pdf",
                doc_type="pdf",
                kb_type=KnowledgeBaseType.FAQ,
                content="内容"
            )
    
    def test_create_document_empty_source_raises(self):
        """空来源创建文档应抛出异常"""
        with pytest.raises(ValueError, match="文档来源不能为空"):
            Document(
                id=None,
                title="标题",
                source="",
                doc_type="pdf",
                kb_type=KnowledgeBaseType.FAQ,
                content="内容"
            )
    
    def test_create_document_empty_content_raises(self):
        """空内容创建文档应抛出异常"""
        with pytest.raises(ValueError, match="文档内容不能为空"):
            Document(
                id=None,
                title="标题",
                source="/path/test.pdf",
                doc_type="pdf",
                kb_type=KnowledgeBaseType.FAQ,
                content=""
            )
    
    def test_split_into_chunks(self, sample_document: Document):
        """设置分块"""
        chunks = [
            DocumentChunk(content="第一部分", chunk_index=0),
            DocumentChunk(content="第二部分", chunk_index=1),
        ]
        
        sample_document.split_into_chunks(chunks)
        
        assert sample_document.chunk_count == 2
        assert sample_document.is_processed
        assert sample_document.status == DocumentStatus.PROCESSED
    
    def test_split_into_chunks_empty_raises(self, sample_document: Document):
        """空分块列表应抛出异常"""
        with pytest.raises(ValueError, match="分块列表不能为空"):
            sample_document.split_into_chunks([])
    
    def test_mark_processing(self, sample_document: Document):
        """标记处理中"""
        sample_document.mark_processing()
        
        assert sample_document.status == DocumentStatus.PROCESSING
        assert sample_document.error_message is None
    
    def test_mark_failed(self, sample_document: Document):
        """标记失败"""
        error_msg = "解析PDF失败"
        sample_document.mark_failed(error_msg)
        
        assert sample_document.status == DocumentStatus.FAILED
        assert sample_document.error_message == error_msg
    
    def test_update_metadata(self, sample_document: Document):
        """更新元数据"""
        sample_document.update_metadata({"category": "重要"})
        
        assert sample_document.metadata["category"] == "重要"
        assert sample_document.metadata["author"] == "test"  # 保留原有
    
    def test_get_chunk_by_index(self, sample_document: Document):
        """根据索引获取分块"""
        chunks = [
            DocumentChunk(content="第一部分", chunk_index=0),
            DocumentChunk(content="第二部分", chunk_index=1),
        ]
        sample_document.split_into_chunks(chunks)
        
        chunk = sample_document.get_chunk_by_index(1)
        assert chunk is not None
        assert chunk.content == "第二部分"
        
        not_found = sample_document.get_chunk_by_index(999)
        assert not_found is None
    
    def test_to_snapshot(self, sample_document: Document):
        """生成快照"""
        snapshot = sample_document.to_snapshot()
        
        assert snapshot["id"] == "doc-001"
        assert snapshot["title"] == "测试文档"
        assert snapshot["kb_type"] == "faq"
        assert snapshot["status"] == "pending"
        assert "created_at" in snapshot
        assert "version" in snapshot


class TestKnowledgeBaseType:
    """知识库类型枚举测试"""
    
    def test_enum_values(self):
        """枚举值测试"""
        assert KnowledgeBaseType.FAQ.value == "faq"
        assert KnowledgeBaseType.REGULATION.value == "regulation"
    
    def test_enum_comparison(self):
        """枚举比较"""
        kb_type = KnowledgeBaseType.FAQ
        assert kb_type == KnowledgeBaseType.FAQ
        assert kb_type != KnowledgeBaseType.REGULATION


class TestQuery:
    """查询值对象测试"""
    
    def test_create_query(self):
        """创建查询"""
        query = Query(
            original_query="公司年假政策是什么？",
            top_k=5
        )
        
        assert query.original_query == "公司年假政策是什么？"
        assert query.top_k == 5
        assert query.sub_queries == []
        assert query.filters == {}
    
    def test_create_query_defaults(self):
        """创建查询使用默认值"""
        query = Query(original_query="测试")
        
        assert query.top_k == 10
        assert query.sub_queries == []
        assert query.filters == {}
    
    def test_create_query_empty_raises(self):
        """空查询应抛出异常"""
        with pytest.raises(ValueError, match="原始查询不能为空"):
            Query(original_query="")
        
        with pytest.raises(ValueError, match="原始查询不能为空"):
            Query(original_query="   ")
    
    def test_create_query_invalid_top_k(self):
        """无效的top_k应抛出异常"""
        with pytest.raises(ValueError, match="top_k必须大于0"):
            Query(original_query="测试", top_k=0)
        
        with pytest.raises(ValueError, match="top_k必须大于0"):
            Query(original_query="测试", top_k=-1)
    
    def test_has_sub_queries(self):
        """检查是否有子查询"""
        query_without = Query(original_query="测试")
        assert not query_without.has_sub_queries
        
        query_with = Query(
            original_query="测试",
            sub_queries=[SubQuery(query="子查询")]
        )
        assert query_with.has_sub_queries
    
    def test_all_kb_types(self):
        """获取所有知识库类型"""
        query = Query(
            original_query="测试",
            sub_queries=[
                SubQuery(query="Q1", kb_types=[KnowledgeBaseType.FAQ]),
                SubQuery(query="Q2", kb_types=[KnowledgeBaseType.FAQ, KnowledgeBaseType.REGULATION]),
            ]
        )
        
        types = query.all_kb_types
        assert len(types) == 2
        assert KnowledgeBaseType.FAQ in types
        assert KnowledgeBaseType.REGULATION in types
    
    def test_get_queries_for_kb(self):
        """获取指定知识库的查询"""
        query = Query(
            original_query="原始问题",
            sub_queries=[
                SubQuery(query="FAQ问题", kb_types=[KnowledgeBaseType.FAQ]),
                SubQuery(query="规章问题", kb_types=[KnowledgeBaseType.REGULATION]),
            ]
        )
        
        faq_queries = query.get_queries_for_kb(KnowledgeBaseType.FAQ)
        assert faq_queries == ["FAQ问题"]
        
        reg_queries = query.get_queries_for_kb(KnowledgeBaseType.REGULATION)
        assert reg_queries == ["规章问题"]


class TestSubQuery:
    """子查询值对象测试"""
    
    def test_create_sub_query(self):
        """创建子查询"""
        sub = SubQuery(query="子问题")
        
        assert sub.query == "子问题"
        assert sub.kb_types == []
        assert sub.weight == 1.0
    
    def test_create_sub_query_full(self):
        """完整创建子查询"""
        sub = SubQuery(
            query="子问题",
            kb_types=[KnowledgeBaseType.FAQ],
            weight=1.5
        )
        
        assert sub.query == "子问题"
        assert sub.kb_types == [KnowledgeBaseType.FAQ]
        assert sub.weight == 1.5
    
    def test_create_sub_query_empty_raises(self):
        """空子查询应抛出异常"""
        with pytest.raises(ValueError, match="子查询不能为空"):
            SubQuery(query="")
        
        with pytest.raises(ValueError, match="子查询不能为空"):
            SubQuery(query="   ")
    
    def test_create_sub_query_invalid_weight(self):
        """无效权重应抛出异常"""
        with pytest.raises(ValueError, match="权重必须大于0"):
            SubQuery(query="测试", weight=0)
        
        with pytest.raises(ValueError, match="权重必须大于0"):
            SubQuery(query="测试", weight=-1)


class TestSearchResult:
    """搜索结果值对象测试"""
    
    def test_create_search_result(self):
        """创建搜索结果"""
        chunk = DocumentChunk(content="相关内容", chunk_index=0)
        result = SearchResult(
            chunk=chunk,
            score=0.85,
            source="vector",
            document_id="doc-001",
            document_title="测试文档"
        )
        
        assert result.chunk == chunk
        assert result.score == 0.85
        assert result.source == "vector"
        assert result.document_id == "doc-001"
        assert result.document_title == "测试文档"
    
    def test_search_result_content_property(self):
        """内容属性"""
        chunk = DocumentChunk(content="结果内容", chunk_index=0)
        result = SearchResult(
            chunk=chunk,
            score=0.9,
            source="keyword"
        )
        
        assert result.content == "结果内容"
        assert result.char_count == 4
    
    def test_search_result_invalid_score(self):
        """无效分数应抛出异常"""
        chunk = DocumentChunk(content="内容", chunk_index=0)
        
        with pytest.raises(ValueError, match="分数必须在0-1之间"):
            SearchResult(chunk=chunk, score=1.5, source="vector")
        
        with pytest.raises(ValueError, match="分数必须在0-1之间"):
            SearchResult(chunk=chunk, score=-0.1, source="vector")


class TestRankedResult:
    """重排序结果值对象测试"""
    
    def test_create_ranked_result(self):
        """创建重排序结果"""
        chunk = DocumentChunk(content="内容", chunk_index=0)
        search_result = SearchResult(
            chunk=chunk,
            score=0.8,
            source="hybrid",
            document_title="原文档"
        )
        
        ranked = RankedResult(
            search_result=search_result,
            rerank_score=0.92,
            rank=1
        )
        
        assert ranked.search_result == search_result
        assert ranked.rerank_score == 0.92
        assert ranked.rank == 1
        assert ranked.content == "内容"
        assert ranked.document_title == "原文档"
        assert ranked.original_score == 0.8
    
    def test_ranked_result_invalid_rank(self):
        """无效排序位次应抛出异常"""
        chunk = DocumentChunk(content="内容", chunk_index=0)
        search_result = SearchResult(chunk=chunk, score=0.8, source="vector")
        
        with pytest.raises(ValueError, match="排序位次必须从1开始"):
            RankedResult(search_result=search_result, rerank_score=0.9, rank=0)
        
        with pytest.raises(ValueError, match="排序位次必须从1开始"):
            RankedResult(search_result=search_result, rerank_score=0.9, rank=-1)
    
    def test_ranked_result_invalid_score(self):
        """无效重排序分数应抛出异常"""
        chunk = DocumentChunk(content="内容", chunk_index=0)
        search_result = SearchResult(chunk=chunk, score=0.8, source="vector")
        
        with pytest.raises(ValueError, match="重排序分数不能为负数"):
            RankedResult(search_result=search_result, rerank_score=-0.1, rank=1)


# 标记测试类型
pytestmark = [
    pytest.mark.unit,
]
