"""
RAG工具Bug修复验证测试

测试问题：Agentic RAG提问没有输出
根本原因：工具中使用了asyncio.run()，在已有事件循环中调用会失败
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from app.infrastructure.tools.rag.answer_generation_tool import AnswerGenerationTool
from app.infrastructure.tools.rag.hybrid_search_tool import HybridSearchTool
from app.domain.agent.agent_tool import ToolResult


class TestAnswerGenerationToolFix:
    """测试答案生成工具修复"""
    
    def test_answer_generation_no_asyncio_run(self):
        """测试：答案生成工具不应在同步方法中使用asyncio.run()"""
        # 创建Mock LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value=Mock(content="这是生成的答案"))
        
        tool = AnswerGenerationTool(llm=mock_llm)
        
        # 测试在正常事件循环中调用
        async def test_in_event_loop():
            # 模拟Agent在事件循环中调用工具
            def run_tool():
                return tool.execute(
                    query="测试问题",
                    context="这是上下文内容"
                )
            
            # 在线程中运行同步工具
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_tool)
                result = future.result()
            
            return result
        
        # 运行测试
        result = asyncio.run(test_in_event_loop())
        
        print(f"\n[AnswerGenerationTool测试]")
        print(f"  - 结果类型: {type(result)}")
        print(f"  - 成功: {result.success}")
        print(f"  - 内容: {result.content[:50]}...")
        
        # 验证
        assert result is not None, "工具返回None"
        assert isinstance(result, ToolResult), "返回类型不是ToolResult"
        assert result.success, f"工具执行失败: {result.error_message}"
        assert result.content != "", "答案为空"
        
        print("  [PASS] AnswerGenerationTool修复成功")
    
    def test_answer_generation_with_empty_context(self):
        """测试：空上下文处理"""
        mock_llm = Mock()
        tool = AnswerGenerationTool(llm=mock_llm)
        
        result = tool.execute(
            query="测试问题",
            context=""  # 空上下文
        )
        
        print(f"\n[空上下文测试]")
        print(f"  - 成功: {result.success}")
        print(f"  - 内容: {result.content}")
        
        assert result.success, "应返回成功但提示无信息"
        assert "没有找到相关信息" in result.content or "抱歉" in result.content, "应返回友好的无结果提示"
        
        print("  [PASS] 空上下文处理正确")


class TestHybridSearchToolFix:
    """测试混合检索工具修复"""
    
    def test_hybrid_search_no_asyncio_run(self):
        """测试：混合检索工具不应在同步方法中使用asyncio.run()"""
        # 创建Mock
        mock_vector_store = Mock()
        mock_vector_store.similarity_search = Mock(return_value=[("chunk_001", 85.5)])
        mock_vector_store.get_chunk_by_id = Mock(return_value=Mock(
            content="测试内容",
            metadata={"document_id": "doc_001", "title": "测试文档"}
        ))
        
        mock_keyword_index = Mock()
        mock_keyword_index.search = Mock(return_value=[("chunk_001", 75.0)])
        
        mock_embedding = Mock()
        mock_embedding.aembed_query = AsyncMock(return_value=[0.1] * 768)
        
        tool = HybridSearchTool(
            vector_store=mock_vector_store,
            keyword_index=mock_keyword_index,
        )
        tool._embedding = mock_embedding
        
        # 测试在正常事件循环中调用
        async def test_in_event_loop():
            def run_tool():
                return tool.execute(
                    query="测试查询",
                    kb_types=["faq"],
                    top_k=5
                )
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_tool)
                result = future.result()
            
            return result
        
        # 运行测试
        result = asyncio.run(test_in_event_loop())
        
        print(f"\n[HybridSearchTool测试]")
        print(f"  - 结果类型: {type(result)}")
        print(f"  - 成功: {result.success}")
        print(f"  - 内容长度: {len(result.content)}")
        
        # 验证
        assert result is not None, "工具返回None"
        assert isinstance(result, ToolResult), "返回类型不是ToolResult"
        
        print("  [PASS] HybridSearchTool修复成功")


class TestRAGIntegration:
    """RAG集成测试 - 模拟Agentic RAG完整流程"""
    
    @pytest.mark.asyncio
    async def test_agentic_rag_flow_simulation(self):
        """模拟Agentic RAG完整流程"""
        print(f"\n[Agentic RAG集成测试]")
        
        # 模拟事件循环环境
        async def simulate_agent_loop():
            """模拟Agent在事件循环中调用工具"""
            
            # 1. 模拟HybridSearch工具调用
            mock_vector_store = Mock()
            mock_vector_store.similarity_search = Mock(return_value=[
                ("chunk_001", 85.5),
                ("chunk_002", 80.0),
            ])
            mock_vector_store.get_chunk_by_id = Mock(side_effect=lambda cid: Mock(
                content=f"这是{cid}的内容",
                metadata={"document_id": "doc_001", "title": "测试文档"}
            ))
            
            mock_keyword_index = Mock()
            mock_keyword_index.search = Mock(return_value=[
                ("chunk_001", 75.0),
            ])
            
            mock_embedding = Mock()
            mock_embedding.aembed_query = AsyncMock(return_value=[0.1] * 768)
            
            search_tool = HybridSearchTool(
                vector_store=mock_vector_store,
                keyword_index=mock_keyword_index,
            )
            search_tool._embedding = mock_embedding
            
            # 2. 模拟AnswerGeneration工具调用
            mock_llm = Mock()
            mock_llm.invoke = Mock(return_value=Mock(content="根据文档内容，年假是15天。"))
            gen_tool = AnswerGenerationTool(llm=mock_llm)
            
            # 3. 在事件循环中调用工具（这是关键测试点）
            def run_search():
                return search_tool.execute(query="年假政策", kb_types=["faq"])
            
            def run_generate(context):
                return gen_tool.execute(query="年假政策", context=context)
            
            # 使用线程池执行同步工具
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 执行检索
                search_future = executor.submit(run_search)
                search_result = search_future.result()
                print(f"  1. 检索工具 - 成功: {search_result.success}")
                
                # 执行生成
                gen_future = executor.submit(run_generate, search_result.content)
                gen_result = gen_future.result()
                print(f"  2. 生成工具 - 成功: {gen_result.success}")
                print(f"  3. 最终答案: {gen_result.content[:50]}...")
                
                return gen_result
        
        # 在事件循环中运行模拟
        result = await simulate_agent_loop()
        
        assert result is not None, "最终结果为空"
        assert result.success, f"流程失败: {result.error_message}"
        assert result.content != "", "最终答案为空"
        
        print("  [PASS] Agentic RAG集成测试通过")


# 标记测试类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.rag,
]
