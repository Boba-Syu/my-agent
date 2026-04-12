"""
验证实际代码中是否存在asyncio.run() Bug的测试

运行方式：
    cd c:/Users/19148/PycharmProjects/my-agent
    uv run python -m pytest tests/test_check_actual_bug.py -v
"""

from __future__ import annotations

import pytest
import asyncio
import inspect
from unittest.mock import Mock, patch


class TestActualCodeBug:
    """
    检查实际代码中是否存在asyncio.run() Bug
    """
    
    def test_answer_generation_tool_source_code(self):
        """
        测试：检查AnswerGenerationTool的源代码中是否包含asyncio.run()
        
        如果存在asyncio.run()，说明Bug还未修复
        """
        from app.infrastructure.tools.rag.answer_generation_tool import AnswerGenerationTool
        
        # 获取execute方法的源代码
        source = inspect.getsource(AnswerGenerationTool.execute)
        
        print(f"\n[AnswerGenerationTool源代码检查]")
        print(f"  execute方法源代码长度: {len(source)} 字符")
        
        # 检查是否包含asyncio.run
        has_asyncio_run = "asyncio.run" in source
        
        if has_asyncio_run:
            print(f"  警告: 代码中仍包含 'asyncio.run'，Bug未修复！")
            # 找到包含asyncio.run的行
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                if "asyncio.run" in line:
                    print(f"    第{i}行: {line.strip()}")
        else:
            print(f"  通过: 代码中不包含 'asyncio.run'，Bug已修复")
        
        # 检查是否使用了同步invoke方法
        has_sync_invoke = "self._llm.invoke" in source and "self._llm.ainvoke" not in source
        
        if has_sync_invoke:
            print(f"  通过: 代码使用同步的 self._llm.invoke()")
        
        # 断言：修复后的代码不应该包含asyncio.run
        assert not has_asyncio_run, "Bug未修复：代码中仍包含asyncio.run()"
        assert has_sync_invoke, "修复不完整：应该使用同步的self._llm.invoke()"
    
    def test_hybrid_search_tool_source_code(self):
        """
        测试：检查HybridSearchTool的源代码中是否包含asyncio.run()
        
        这个工具比较复杂，因为它内部有异步方法，
        需要在同步的execute方法中调用异步方法
        """
        from app.infrastructure.tools.rag.hybrid_search_tool import HybridSearchTool
        
        source = inspect.getsource(HybridSearchTool.execute)
        
        print(f"\n[HybridSearchTool源代码检查]")
        print(f"  execute方法源代码长度: {len(source)} 字符")
        
        has_asyncio_run = "asyncio.run" in source
        has_thread_pool = "ThreadPoolExecutor" in source
        
        if has_asyncio_run:
            if has_thread_pool:
                print(f"  注意: 代码包含asyncio.run，但也使用了ThreadPoolExecutor")
                print(f"  这是修复后的代码，在新线程中运行asyncio.run")
            else:
                print(f"  警告: 代码包含asyncio.run但没有ThreadPoolExecutor，Bug未修复！")
                lines = source.split('\n')
                for i, line in enumerate(lines, 1):
                    if "asyncio.run" in line:
                        print(f"    第{i}行: {line.strip()}")
        else:
            print(f"  通过: 代码中不包含 'asyncio.run'")
        
        # 对于HybridSearchTool，使用ThreadPoolExecutor是预期的修复方式
        if has_asyncio_run:
            assert has_thread_pool, "Bug未修复：使用asyncio.run但没有ThreadPoolExecutor"
            print(f"  通过: 使用ThreadPoolExecutor在新线程中运行asyncio.run")
    
    @pytest.mark.asyncio
    async def test_answer_generation_tool_execution(self):
        """
        测试：在实际事件循环中调用AnswerGenerationTool
        
        这是真正的Bug复现测试
        """
        from app.infrastructure.tools.rag.answer_generation_tool import AnswerGenerationTool
        from app.domain.agent.agent_tool import ToolResult
        
        print(f"\n[AnswerGenerationTool执行测试]")
        
        # 创建Mock LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value=Mock(content="这是测试答案"))
        
        tool = AnswerGenerationTool(llm=mock_llm)
        
        async def run_in_event_loop():
            """在事件循环中调用工具"""
            # 工具execute是同步方法，直接调用
            result = tool.execute(
                query="测试问题",
                context="这是上下文"
            )
            return result
        
        try:
            result = await run_in_event_loop()
            
            print(f"  结果类型: {type(result).__name__}")
            print(f"  成功: {result.success}")
            print(f"  内容: {result.content}")
            
            # 验证结果
            assert isinstance(result, ToolResult), "应该返回ToolResult"
            assert result.success, f"工具应该成功执行，但失败: {result.error_message}"
            assert result.content == "这是测试答案", f"答案不匹配: {result.content}"
            
            print(f"  [PASS] 工具在事件循环中正常执行")
            
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                pytest.fail(f"Bug仍存在：asyncio.run在事件循环中调用失败: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_hybrid_search_tool_execution(self):
        """
        测试：在实际事件循环中调用HybridSearchTool
        """
        from app.infrastructure.tools.rag.hybrid_search_tool import HybridSearchTool
        from app.domain.agent.agent_tool import ToolResult
        
        print(f"\n[HybridSearchTool执行测试]")
        
        # 创建Mock依赖
        mock_vector_store = Mock()
        mock_vector_store.similarity_search = Mock(return_value=[("chunk_1", 0.9)])
        mock_vector_store.get_chunk_by_id = Mock(return_value=Mock(
            content="测试内容",
            metadata={"document_id": "doc_1", "title": "测试文档"}
        ))
        
        mock_keyword_index = Mock()
        mock_keyword_index.search = Mock(return_value=[("chunk_1", 0.8)])
        
        mock_embedding = Mock()
        mock_embedding.aembed_query = Mock()
        mock_embedding.aembed_query.return_value = asyncio.Future()
        mock_embedding.aembed_query.return_value.set_result([0.1] * 768)
        
        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )
        tool._embedding = mock_embedding
        
        async def run_in_event_loop():
            """在事件循环中调用工具"""
            result = tool.execute(
                query="测试查询",
                kb_types=["faq"],
                top_k=5
            )
            return result
        
        try:
            result = await run_in_event_loop()
            
            print(f"  结果类型: {type(result).__name__}")
            print(f"  成功: {result.success}")
            
            assert isinstance(result, ToolResult), "应该返回ToolResult"
            # 可能成功也可能失败（取决于Mock），但不应该抛出RuntimeError
            
            print(f"  [PASS] 工具在事件循环中执行未抛出RuntimeError")
            
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                pytest.fail(f"Bug仍存在：asyncio.run在事件循环中调用失败: {e}")
            else:
                raise


class TestRAGServiceIntegration:
    """
    集成测试：测试RAGService的完整流程
    """
    
    @pytest.mark.asyncio
    async def test_rag_service_query(self):
        """
        测试：RAGService.query()方法
        
        这是一个更高级别的集成测试
        """
        from app.application.rag.rag_service import RAGService
        from app.application.rag.dto import RAGQueryRequest
        
        print(f"\n[RAGService集成测试]")
        
        # 创建Mock依赖
        mock_vector_store = Mock()
        mock_vector_store.similarity_search = Mock(return_value=[("chunk_1", 90.0)])
        mock_vector_store.get_chunk_by_id = Mock(return_value=Mock(
            content="年假每年15天",
            metadata={"document_id": "doc_1", "title": "员工手册"}
        ))
        
        mock_keyword_index = Mock()
        mock_keyword_index.search = Mock(return_value=[])
        
        mock_llm = Mock()
        mock_llm.ainvoke = Mock()
        mock_llm.ainvoke.return_value = asyncio.Future()
        mock_llm.ainvoke.return_value.set_result(Mock(content='{"sub_queries": [{"query": "年假政策", "kb_types": ["faq"]}]}'))
        
        mock_embedding = Mock()
        mock_embedding.aembed_query = Mock()
        mock_embedding.aembed_query.return_value = asyncio.Future()
        mock_embedding.aembed_query.return_value.set_result([0.1] * 768)
        
        # 创建RAGService
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
            
            # 创建请求
            request = RAGQueryRequest(
                query="年假政策是什么？",
                kb_types=["faq"],
                top_k=5
            )
            
            try:
                # 执行查询
                response = await service.query(request)
                
                print(f"  响应类型: {type(response).__name__}")
                print(f"  答案: {response.answer[:50] if response.answer else 'None'}...")
                
                print(f"  [PASS] RAGService.query()执行成功")
                
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    pytest.fail(f"Bug仍存在：在RAGService中调用asyncio.run失败: {e}")
                else:
                    raise


# 标记测试类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.rag,
]


if __name__ == "__main__":
    # 简单的自测
    print("=" * 60)
    print("检查实际代码中的Bug")
    print("=" * 60)
    
    test = TestActualCodeBug()
    test.test_answer_generation_tool_source_code()
    test.test_hybrid_search_tool_source_code()
    
    print("\n" + "=" * 60)
    print("源代码检查完成")
    print("=" * 60)
