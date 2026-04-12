"""
Agentic RAG无输出问题诊断测试

测试目标：验证Agentic RAG工具在事件循环中调用时不会失败
问题根因：工具使用了asyncio.run()，在已有事件循环中调用会抛出RuntimeError
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


class TestAsyncioRunBug:
    """
    测试asyncio.run()在已有事件循环中的问题
    
    这是Agentic RAG无输出的根本原因：
    当Agent在事件循环中调用工具时，如果工具内部使用asyncio.run()，
    会抛出 RuntimeError: asyncio.run() cannot be called from a running event loop
    """
    
    def test_asyncio_run_in_event_loop_should_fail(self):
        """
        测试：在已有事件循环中调用asyncio.run()应该失败
        
        这个测试验证了问题的根本原因
        """
        async def inner_async():
            return "inner result"
        
        async def test_in_event_loop():
            """模拟在事件循环中调用asyncio.run()"""
            try:
                # 这会失败，因为我们已经在事件循环中
                result = asyncio.run(inner_async())
                return f"unexpected success: {result}"
            except RuntimeError as e:
                return f"expected error: {e}"
        
        # 在事件循环中运行测试
        result = asyncio.run(test_in_event_loop())
        
        print(f"\n[asyncio.run()冲突测试]")
        print(f"  结果: {result}")
        
        # 验证确实抛出了RuntimeError
        assert "cannot be called from a running event loop" in result, \
            "应该在已有事件循环中调用asyncio.run()时失败"
        
        print("  [PASS] 确认asyncio.run()在事件循环中会失败")
    
    def test_answer_generation_tool_with_bug(self):
        """
        测试：修复前的AnswerGenerationTool会在事件循环中失败
        
        模拟修复前的代码行为：
        response = asyncio.run(self._llm.ainvoke(prompt))
        """
        async def mock_ainvoke(prompt):
            await asyncio.sleep(0.01)  # 模拟异步操作
            return Mock(content="生成的答案")
        
        def buggy_execute(query: str, context: str):
            """模拟修复前的工具execute方法"""
            # 这是修复前的代码
            response = asyncio.run(mock_ainvoke("prompt"))
            return response.content
        
        async def test_in_event_loop():
            """模拟Agent在事件循环中调用工具"""
            try:
                result = buggy_execute("问题", "上下文")
                return f"success: {result}"
            except RuntimeError as e:
                return f"error: {e}"
        
        result = asyncio.run(test_in_event_loop())
        
        print(f"\n[修复前工具行为测试]")
        print(f"  结果: {result}")
        
        # 验证修复前的代码会失败
        assert "cannot be called from a running event loop" in result, \
            "修复前的代码应该在事件循环中调用时失败"
        
        print("  [PASS] 确认修复前的工具代码会在事件循环中失败")
    
    def test_answer_generation_tool_fixed(self):
        """
        测试：修复后的AnswerGenerationTool应该在事件循环中正常工作
        
        修复方案：使用同步方法代替asyncio.run()
        response = self._llm.invoke(prompt)  # 同步调用
        """
        def fixed_execute(query: str, context: str):
            """模拟修复后的工具execute方法"""
            # 这是修复后的代码 - 使用同步方法
            mock_llm = Mock()
            mock_llm.invoke = Mock(return_value=Mock(content="生成的答案"))
            response = mock_llm.invoke("prompt")
            return response.content
        
        async def test_in_event_loop():
            """模拟Agent在事件循环中调用工具"""
            try:
                result = fixed_execute("问题", "上下文")
                return f"success: {result}"
            except RuntimeError as e:
                return f"error: {e}"
        
        result = asyncio.run(test_in_event_loop())
        
        print(f"\n[修复后工具行为测试]")
        print(f"  结果: {result}")
        
        # 验证修复后的代码能正常工作
        assert result == "success: 生成的答案", \
            f"修复后的代码应该正常工作，但得到: {result}"
        
        print("  [PASS] 确认修复后的工具代码在事件循环中正常工作")


class TestHybridSearchToolBug:
    """
    测试HybridSearchTool的问题
    """
    
    def test_hybrid_search_async_methods(self):
        """
        测试：HybridSearchTool的异步方法在事件循环中调用
        
        HybridSearchTool内部有异步方法（_async_hybrid_search, _vector_search等），
        需要通过某种方式在同步的execute方法中调用它们
        """
        async def mock_async_search():
            await asyncio.sleep(0.01)
            return ["result1", "result2"]
        
        def execute_with_asyncio_run():
            """使用asyncio.run调用异步方法（修复前）"""
            return asyncio.run(mock_async_search())
        
        def execute_with_threadpool():
            """使用ThreadPoolExecutor调用异步方法（修复后）"""
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, mock_async_search())
                return future.result()
        
        # 测试1：在事件循环中使用asyncio.run()会失败
        async def test_asyncio_run():
            try:
                result = execute_with_asyncio_run()
                return f"success: {result}"
            except RuntimeError as e:
                return f"error: {e}"
        
        result1 = asyncio.run(test_asyncio_run())
        print(f"\n[HybridSearch asyncio.run测试]")
        print(f"  结果: {result1}")
        assert "cannot be called from a running event loop" in result1
        print("  [PASS] asyncio.run在事件循环中会失败")
        
        # 测试2：使用ThreadPoolExecutor可以正常工作
        async def test_threadpool():
            try:
                result = execute_with_threadpool()
                return f"success: {result}"
            except Exception as e:
                return f"error: {e}"
        
        result2 = asyncio.run(test_threadpool())
        print(f"\n[HybridSearch ThreadPoolExecutor测试]")
        print(f"  结果: {result2}")
        assert result2 == "success: ['result1', 'result2']"
        print("  [PASS] ThreadPoolExecutor在事件循环中正常工作")


class TestToolIntegration:
    """
    集成测试：模拟完整的Agentic RAG调用链路
    """
    
    @pytest.mark.asyncio
    async def test_agentic_rag_tool_chain(self):
        """
        测试：模拟完整的Agent工具调用链
        
        流程：
        1. Agent在事件循环中运行
        2. Agent调用HybridSearchTool.execute()（同步）
        3. HybridSearchTool内部调用异步方法获取结果
        4. Agent调用AnswerGenerationTool.execute()（同步）
        5. AnswerGenerationTool生成答案
        """
        print(f"\n[Agentic RAG工具链测试]")
        
        async def mock_embedding():
            return [0.1] * 768
        
        async def mock_vector_search():
            await asyncio.sleep(0.01)
            return [("chunk_1", 0.9)]
        
        async def mock_keyword_search():
            await asyncio.sleep(0.01)
            return [("chunk_1", 0.8)]
        
        def hybrid_search_execute():
            """模拟HybridSearchTool.execute()"""
            # 修复后的方式：使用ThreadPoolExecutor
            import concurrent.futures
            
            async def async_search():
                # 并行执行向量检索和关键词检索
                vector_results, keyword_results = await asyncio.gather(
                    mock_vector_search(),
                    mock_keyword_search()
                )
                return vector_results + keyword_results
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_search())
                return future.result()
        
        def answer_generation_execute(context: str):
            """模拟AnswerGenerationTool.execute()"""
            # 修复后的方式：使用同步方法
            mock_llm = Mock()
            mock_llm.invoke = Mock(return_value=Mock(content=f"基于{context}的答案"))
            response = mock_llm.invoke("prompt")
            return response.content
        
        # 在事件循环中执行完整的工具链
        async def run_tool_chain():
            # 步骤1：检索
            search_results = hybrid_search_execute()
            print(f"  1. 检索结果: {search_results}")
            
            # 步骤2：生成答案
            answer = answer_generation_execute(str(search_results))
            print(f"  2. 生成答案: {answer}")
            
            return answer
        
        result = await run_tool_chain()
        
        assert "答案" in result, f"应该生成答案，但得到: {result}"
        print("  [PASS] Agentic RAG工具链正常工作")


# 运行测试的简单方式
if __name__ == "__main__":
    print("=" * 60)
    print("Agentic RAG无输出问题诊断测试")
    print("=" * 60)
    
    test = TestAsyncioRunBug()
    test.test_asyncio_run_in_event_loop_should_fail()
    test.test_answer_generation_tool_with_bug()
    test.test_answer_generation_tool_fixed()
    
    test2 = TestHybridSearchToolBug()
    test2.test_hybrid_search_async_methods()
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
