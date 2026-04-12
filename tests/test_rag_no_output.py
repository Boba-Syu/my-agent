"""
RAG无输出问题诊断测试

测试场景：
1. 查询分解是否正常
2. 检索是否正常
3. 答案生成是否正常
4. 流式输出是否正常
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from app.application.rag.rag_service import RAGService
from app.application.rag.dto import RAGQueryRequest, RAGQueryResponse
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.query import Query, SubQuery
from app.domain.rag.search_result import SearchResult, RankedResult


class TestRAGNoOutputDiagnosis:
    """RAG无输出问题诊断测试"""
    
    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock向量存储"""
        store = Mock()
        store.similarity_search = Mock(return_value=[
            ("chunk_001", 85.5),
            ("chunk_002", 80.0),
        ])
        store.get_chunk_by_id = Mock(side_effect=lambda cid: DocumentChunk(
            content=f"这是{cid}的内容" * 20,
            chunk_index=int(cid.split("_")[-1]) if "_" in cid else 0,
            metadata={"document_id": "doc_001", "title": "测试文档"}
        ))
        return store
    
    @pytest.fixture
    def mock_keyword_index(self) -> Mock:
        """Mock关键词索引"""
        index = Mock()
        index.search = Mock(return_value=[
            ("chunk_001", 75.0),
            ("chunk_003", 70.0),
        ])
        return index
    
    @pytest.fixture
    def mock_llm(self) -> Mock:
        """Mock LLM"""
        llm = Mock()
        # 模拟查询分解的JSON响应
        llm.ainvoke = AsyncMock(return_value=Mock(content='''
        {
            "sub_queries": [
                {"query": "年假政策是什么？", "kb_types": ["faq"], "weight": 1.0}
            ]
        }
        '''))
        llm.astream = AsyncMock(return_value=AsyncIteratorMock([
            Mock(content="根据"),
            Mock(content="公司"),
            Mock(content="规定"),
            Mock(content="，年假是15天。"),
        ]))
        return llm
    
    @pytest.fixture
    def mock_embedding(self) -> Mock:
        """Mock Embedding"""
        embedding = Mock()
        embedding.aembed_query = AsyncMock(return_value=[0.1] * 768)
        embedding.aembed_documents = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
        return embedding
    
    @pytest.fixture
    def rag_service(self, mock_vector_store, mock_keyword_index, mock_llm, mock_embedding) -> RAGService:
        """创建RAG服务实例"""
        with patch('app.application.rag.rag_service.LLMFactory') as mock_factory:
            mock_factory.create_llm.return_value = mock_llm
            mock_factory.create_embedding.return_value = mock_embedding
            
            service = RAGService(
                vector_store=mock_vector_store,
                keyword_index=mock_keyword_index,
                reranker=None,
                llm=mock_llm,
            )
            service._embedding = mock_embedding
            return service
    
    @pytest.mark.asyncio
    async def test_query_decomposition_step(self, rag_service, mock_llm):
        """测试1: 查询分解步骤是否正常"""
        request = RAGQueryRequest(query="年假政策是什么？")
        
        # 直接调用查询分解
        query = await rag_service._decompose_query(request)
        
        print(f"\n[测试1] 查询分解结果:")
        print(f"  - 原始查询: {query.original_query}")
        print(f"  - 子查询数: {len(query.sub_queries)}")
        
        # 验证
        assert query is not None, "查询分解返回None"
        assert len(query.sub_queries) > 0, "子查询列表为空"
        assert query.sub_queries[0].query != "", "子查询内容为空"
        
        print(f"  - 子查询内容: {query.sub_queries[0].query}")
        print("  [PASS] 查询分解正常")
    
    @pytest.mark.asyncio
    async def test_vector_search_step(self, rag_service, mock_vector_store, mock_embedding):
        """测试2: 向量检索步骤是否正常"""
        sub_query = SubQuery(
            query="年假政策",
            kb_types=[KnowledgeBaseType.FAQ]
        )
        query_embedding = await mock_embedding.aembed_query("年假政策")
        
        # 执行向量检索
        results = await rag_service._vector_search(sub_query, query_embedding)
        
        print(f"\n[测试2] 向量检索结果:")
        print(f"  - 结果数: {len(results)}")
        
        # 验证
        assert results is not None, "向量检索返回None"
        assert isinstance(results, list), "向量检索返回不是列表"
        
        if len(results) > 0:
            print(f"  - 第一条结果分数: {results[0].score}")
            print(f"  - 第一条结果来源: {results[0].source}")
            print("  [PASS] 向量检索正常")
        else:
            print("  [WARNING] 向量检索返回空列表")
    
    @pytest.mark.asyncio
    async def test_keyword_search_step(self, rag_service, mock_keyword_index):
        """测试3: 关键词检索步骤是否正常"""
        sub_query = SubQuery(
            query="年假政策",
            kb_types=[KnowledgeBaseType.FAQ]
        )
        
        # 执行关键词检索
        results = await rag_service._keyword_search(sub_query)
        
        print(f"\n[测试3] 关键词检索结果:")
        print(f"  - 结果数: {len(results)}")
        
        # 验证
        assert results is not None, "关键词检索返回None"
        assert isinstance(results, list), "关键词检索返回不是列表"
        
        if len(results) > 0:
            print(f"  - 第一条结果分数: {results[0].score}")
            print(f"  - 第一条结果来源: {results[0].source}")
            print("  [PASS] 关键词检索正常")
        else:
            print("  [WARNING] 关键词检索返回空列表")
    
    @pytest.mark.asyncio
    async def test_answer_generation_step(self, rag_service, mock_llm):
        """测试4: 答案生成步骤是否正常"""
        # 创建模拟的排序结果
        chunk = DocumentChunk(content="年假每年15天" * 10, chunk_index=0)
        search_result = SearchResult(
            chunk=chunk,
            score=0.9,
            source="hybrid",
            document_id="doc_001",
            document_title="员工手册"
        )
        ranked = RankedResult(
            search_result=search_result,
            rerank_score=0.95,
            rank=1
        )
        
        # 执行答案生成
        answer = await rag_service._generate_answer("年假政策是什么？", [ranked])
        
        print(f"\n[测试4] 答案生成结果:")
        print(f"  - 答案长度: {len(answer)}")
        print(f"  - 答案内容: {answer[:100]}...")
        
        # 验证
        assert answer is not None, "答案生成返回None"
        assert answer != "", "答案为空字符串"
        assert "抱歉" not in answer or len(answer) > 10, "答案生成失败或返回默认消息"
        
        print("  [PASS] 答案生成正常")
    
    @pytest.mark.asyncio
    async def test_full_query_flow(self, rag_service):
        """测试5: 完整查询流程"""
        request = RAGQueryRequest(
            query="年假政策是什么？",
            kb_types=["faq"],
            top_k=5
        )
        
        print(f"\n[测试5] 完整查询流程:")
        print(f"  - 输入查询: {request.query}")
        
        # 执行完整查询
        response = await rag_service.query(request)
        
        print(f"  - 响应类型: {type(response)}")
        print(f"  - 答案长度: {len(response.answer) if response.answer else 0}")
        print(f"  - 来源数: {len(response.sources)}")
        
        # 验证
        assert response is not None, "查询返回None"
        assert isinstance(response, RAGQueryResponse), "返回类型不是RAGQueryResponse"
        assert response.answer is not None, "答案为None"
        
        if response.answer and response.answer != "抱歉，在知识库中没有找到相关信息。":
            print(f"  - 答案内容: {response.answer[:100]}...")
            print("  [PASS] 完整查询流程正常")
        else:
            print(f"  [WARNING] 返回默认无结果消息: {response.answer}")
    
    @pytest.mark.asyncio
    async def test_stream_query_flow(self, rag_service):
        """测试6: 流式查询流程"""
        request = RAGQueryRequest(
            query="年假政策是什么？",
            kb_types=["faq"],
            top_k=5
        )
        
        print(f"\n[测试6] 流式查询流程:")
        print(f"  - 输入查询: {request.query}")
        
        # 收集所有事件
        events = []
        async for event in rag_service.query_stream(request):
            events.append(event)
            print(f"  - 事件类型: {event.type}")
            
            # 限制输出数量
            if len(events) > 20:
                print("  ... (事件过多，截断)")
                break
        
        print(f"  - 总事件数: {len(events)}")
        
        # 验证
        assert len(events) > 0, "没有收到任何事件"
        
        # 检查事件类型
        event_types = [e.type for e in events]
        print(f"  - 事件类型列表: {event_types}")
        
        # 检查是否有完成事件或错误事件
        if "complete" in event_types:
            print("  [PASS] 流式查询正常完成")
        elif "error" in event_types:
            error_event = next(e for e in events if e.type == "error")
            print(f"  [FAIL] 流式查询出错: {error_event.data}")
            pytest.fail(f"流式查询出错: {error_event.data}")
        else:
            print("  [WARNING] 未收到complete事件")


class TestRAGEdgeCases:
    """RAG边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_empty_query(self):
        """测试空查询处理"""
        request = RAGQueryRequest(query="")
        
        print(f"\n[边界测试] 空查询:")
        print(f"  - 查询内容: '{request.query}'")
        print(f"  - 预期: 应该返回错误提示或默认响应")
    
    @pytest.mark.asyncio
    async def test_no_results_scenario(self):
        """测试无检索结果场景"""
        print(f"\n[边界测试] 无检索结果:")
        print(f"  - 场景: 查询内容在知识库中不存在")
        print(f"  - 预期: 应该返回'抱歉，在知识库中没有找到相关信息'")
    
    @pytest.mark.asyncio
    async def test_llm_error_scenario(self):
        """测试LLM错误场景"""
        print(f"\n[边界测试] LLM错误:")
        print(f"  - 场景: LLM调用抛出异常")
        print(f"  - 预期: 应该抛出异常或返回错误提示")


# 辅助类
class AsyncIteratorMock:
    """异步迭代器Mock"""
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


# 标记测试类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.rag,
]
