"""
混合检索修复测试

验证以下修复点：
1. 向量检索返回正确的Chroma ID
2. 关键词检索返回实际内容而非占位符
3. RRF融合使用正确的去重key
"""

from __future__ import annotations

import unittest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.search_result import SearchResult
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.infrastructure.tools.rag.hybrid_search_tool import HybridSearchTool


@dataclass
class MockChromaResult:
    """模拟Chroma查询结果"""
    ids: list
    documents: list
    metadatas: list
    distances: list


class TestChromaVectorStoreFix(unittest.TestCase):
    """测试ChromaVectorStore修复"""

    def test_similarity_search_returns_chroma_ids(self):
        """
        测试: similarity_search 应该返回 Chroma 实际记录ID，而不是 chunk_index
        """
        from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore

        # 创建mock
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["chroma-id-1", "chroma-id-2"]],
            "documents": [["content1", "content2"]],
            "metadatas": [[{"chunk_index": 0}, {"chunk_index": 1}]],
            "distances": [[0.1, 0.2]],
        }

        store = ChromaVectorStore()
        store._store = Mock()
        store._store._collection = mock_collection

        # 执行搜索
        results = store.similarity_search(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=2
        )

        # 验证返回的是 Chroma ID，而不是 chunk_index
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "chroma-id-1")  # 应该是 Chroma ID
        self.assertEqual(results[1][0], "chroma-id-2")
        self.assertNotEqual(results[0][0], "0")  # 不应该是 "0"
        self.assertNotEqual(results[1][0], "1")  # 不应该是 "1"

    def test_get_chunk_by_id_logic(self):
        """
        测试: 验证 get_chunk_by_id 方法逻辑使用 Chroma ID 查询
        """
        from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore

        # 验证源代码中使用的是 ids=[chunk_id] 而不是 where={"chunk_index": int(chunk_id)}
        import inspect
        source = inspect.getsource(ChromaVectorStore.get_chunk_by_id)

        # 验证使用了 ids 参数
        self.assertIn('ids=[chunk_id]', source)
        # 验证没有使用旧的查询方式
        self.assertNotIn('"chunk_index": int(chunk_id)', source)


class TestKeywordSearchFix(unittest.TestCase):
    """测试关键词检索修复"""

    def test_keyword_search_returns_actual_content(self):
        """
        测试: 关键词检索应该返回实际内容，而不是占位符
        """
        # 创建mock
        mock_vector_store = Mock()
        mock_keyword_index = Mock()

        # 设置mock返回值
        mock_keyword_index.search.return_value = [
            ("doc-1_0", 15.5),  # (chunk_id, score)
            ("doc-1_1", 12.3),
        ]
        mock_keyword_index.get_chunk_content.side_effect = [
            "这是实际的文档内容第一段",
            "这是实际的文档内容第二段",
        ]

        # 创建工具实例
        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )

        # 执行关键词检索（通过 execute 方法间接调用）
        import asyncio

        async def run_test():
            return await tool._keyword_search(
                query="测试查询",
                kb_types=None,
                top_k=10,
            )

        results = asyncio.run(run_test())

        # 验证返回的是实际内容
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].content, "这是实际的文档内容第一段")
        self.assertEqual(results[1].content, "这是实际的文档内容第二段")

        # 验证调用了 get_chunk_content
        mock_keyword_index.get_chunk_content.assert_called()

    def test_keyword_search_not_placeholder(self):
        """
        测试: 关键词检索结果不应该包含占位符文本
        """
        mock_vector_store = Mock()
        mock_keyword_index = Mock()

        mock_keyword_index.search.return_value = [
            ("doc-1_0", 15.5),
        ]
        mock_keyword_index.get_chunk_content.return_value = "实际内容"

        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )

        import asyncio

        async def run_test():
            return await tool._keyword_search(
                query="测试查询",
                kb_types=None,
                top_k=10,
            )

        results = asyncio.run(run_test())

        # 验证不包含占位符
        self.assertNotIn("[Keyword匹配]", results[0].content)
        self.assertNotIn("文档片段", results[0].content)


class TestRRFFusionFix(unittest.TestCase):
    """测试RRF融合修复"""

    def test_fusion_uses_document_key_for_deduplication(self):
        """
        测试: RRF融合应该使用 document_id + chunk_index 作为去重key
        """
        mock_vector_store = Mock()
        mock_keyword_index = Mock()

        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )

        # 创建模拟结果 - 向量检索和关键词检索返回相同文档的不同内容
        chunk1 = DocumentChunk(content="向量检索内容A", chunk_index=0, metadata={"document_id": "doc-1"})
        chunk2 = DocumentChunk(content="关键词检索内容A", chunk_index=0, metadata={"document_id": "doc-1"})
        chunk3 = DocumentChunk(content="内容B", chunk_index=1, metadata={"document_id": "doc-1"})

        vector_results = [
            SearchResult(chunk=chunk1, score=0.9, source="vector", document_id="doc-1"),
            SearchResult(chunk=chunk3, score=0.8, source="vector", document_id="doc-1"),
        ]

        keyword_results = [
            SearchResult(chunk=chunk2, score=0.85, source="keyword", document_id="doc-1"),
        ]

        # 执行融合
        fused = tool._fuse_results(vector_results, keyword_results)

        # 验证去重正确 - doc-1_0 应该只出现一次（融合结果）
        doc_0_results = [r for r in fused if r.chunk.chunk_index == 0]
        self.assertEqual(len(doc_0_results), 1)

        # 验证融合后的结果有更高的分数（因为两个检索都命中）
        self.assertGreater(doc_0_results[0].score, 0.015)  # RRF分数应该大于单一检索

    def test_get_result_key_method(self):
        """
        测试: _get_result_key 方法生成正确的key
        """
        mock_vector_store = Mock()
        mock_keyword_index = Mock()

        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )

        chunk = DocumentChunk(content="test", chunk_index=5, metadata={})
        result = SearchResult(chunk=chunk, score=0.9, source="vector", document_id="doc-123")

        key = tool._get_result_key(result)

        self.assertEqual(key, "doc-123_5")


class TestWhooshKeywordIndexFix(unittest.TestCase):
    """测试WhooshKeywordIndex修复"""

    def test_get_chunk_content_returns_actual_content(self):
        """
        测试: get_chunk_content 应该返回实际存储的内容
        """
        from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

        # 设置mock
        mock_searcher = Mock()
        mock_searcher.search.return_value = [{"content": "存储的实际内容"}]

        mock_qp = Mock()
        mock_qp.parse.return_value = Mock()

        mock_index = Mock()
        mock_index.schema = Mock()
        mock_index.searcher.return_value.__enter__ = Mock(return_value=mock_searcher)
        mock_index.searcher.return_value.__exit__ = Mock(return_value=False)

        # 创建实例并mock _index
        with patch.object(WhooshKeywordIndex, '_get_index', return_value=mock_index):
            with patch('whoosh.qparser.QueryParser', return_value=mock_qp):
                index = WhooshKeywordIndex(index_dir="/tmp/test_index")

                # 执行查询
                content = index.get_chunk_content("doc-1_0")

                # 验证返回实际内容
                self.assertEqual(content, "存储的实际内容")

    def test_get_chunk_content_returns_none_for_missing(self):
        """
        测试: get_chunk_content 对不存在的chunk_id返回None
        """
        from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

        # 设置mock - 空结果
        mock_searcher = Mock()
        mock_searcher.search.return_value = []

        mock_qp = Mock()
        mock_qp.parse.return_value = Mock()

        mock_index = Mock()
        mock_index.schema = Mock()
        mock_index.searcher.return_value.__enter__ = Mock(return_value=mock_searcher)
        mock_index.searcher.return_value.__exit__ = Mock(return_value=False)

        # 创建实例并mock _index
        with patch.object(WhooshKeywordIndex, '_get_index', return_value=mock_index):
            with patch('whoosh.qparser.QueryParser', return_value=mock_qp):
                index = WhooshKeywordIndex(index_dir="/tmp/test_index")

                # 执行查询
                content = index.get_chunk_content("non-existent-id")

                # 验证返回None
                self.assertIsNone(content)


class TestIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""

    def test_end_to_end_hybrid_search_flow(self):
        """
        测试: 完整的混合检索流程
        """
        mock_vector_store = Mock()
        mock_keyword_index = Mock()

        # 设置向量检索mock
        chunk_v = DocumentChunk(content="向量检索内容", chunk_index=0, metadata={"document_id": "doc-1"})
        mock_vector_store.get_chunk_by_id.return_value = chunk_v

        # 设置关键词检索mock
        mock_keyword_index.search.return_value = [("doc-1_0", 10.0)]
        mock_keyword_index.get_chunk_content.return_value = "关键词检索内容"

        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )

        # Mock embedding
        with patch.object(tool, '_vector_search') as mock_vector_search, \
             patch.object(tool, '_keyword_search') as mock_keyword_search:

            # 设置返回结果 - 模拟同一文档被两种检索都命中
            chunk1 = DocumentChunk(content="向量内容", chunk_index=0, metadata={})
            chunk2 = DocumentChunk(content="关键词内容", chunk_index=0, metadata={})

            mock_vector_search.return_value = [
                SearchResult(chunk=chunk1, score=0.9, source="vector", document_id="doc-1"),
            ]
            mock_keyword_search.return_value = [
                SearchResult(chunk=chunk2, score=0.8, source="keyword", document_id="doc-1"),
            ]

            import asyncio

            async def run_test():
                return await tool._async_hybrid_search(
                    query="测试",
                    kb_types=None,
                    top_k=5,
                    embedding=Mock(),
                )

            results = asyncio.run(run_test())

            # 验证融合后的结果
            self.assertEqual(len(results), 1)  # 去重后只有一个结果
            self.assertEqual(results[0].source, "hybrid")  # 来源标记为hybrid
            self.assertGreater(results[0].score, 0.03)  # RRF融合分数应该较高


if __name__ == "__main__":
    unittest.main(verbosity=2)
