"""
Agentic RAG 应用服务

基于ReAct模式的智能RAG服务，Agent自主决策是否检索、如何检索。
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Any

from app.application.agent.agent_factory import AgentFactory
from app.application.rag.dto import (
    RAGQueryRequest,
    RAGQueryResponse,
    SourceInfo,
    RagStreamEventDTO,
)
from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_response import ChunkType
from app.domain.agent.agent_tool import AgentTool
from app.domain.rag.reranker import Reranker
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.infrastructure.tools.rag import (
    HybridSearchTool,
    GetContextTool,
    AnswerGenerationTool,
)
from app.prompts.rag import build_agentic_rag_prompt

logger = logging.getLogger(__name__)


class AgenticRAGService:
    """
    Agentic RAG 应用服务

    使用ReAct模式智能体实现自主决策的RAG流程：
    1. 智能体分析用户问题，决定是否检索
    2. 如需检索，调用混合检索工具获取候选结果
    3. 使用Reranker精排序，获取高质量上下文
    4. 基于上下文生成最终答案

    智能体人设：Coze客服助手

    Example:
        service = AgenticRAGService(
            agent_factory=AgentFactory(),
            vector_store=ChromaVectorStore(),
            keyword_index=WhooshKeywordIndex(),
            reranker=BailianReranker(),
        )

        # 查询
        response = await service.query(
            RAGQueryRequest(query="如何创建Bot")
        )

        # 流式查询
        async for event in service.query_stream(request):
            print(event.type, event.data)
    """

    def __init__(
        self,
        agent_factory: AgentFactory,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
        reranker: Reranker | None = None,
    ):
        """
        初始化Agentic RAG服务

        Args:
            agent_factory: Agent工厂
            vector_store: 向量存储
            keyword_index: 关键词索引
            reranker: 重排序器，可选
        """
        self._agent_factory = agent_factory
        self._vector_store = vector_store
        self._keyword_index = keyword_index
        self._reranker = reranker

        # 缓存Agent实例（按配置）
        self._agent_cache: dict[str, AbstractAgent] = {}

        logger.info(
            f"AgenticRAGService初始化完成，"
            f"reranker={reranker.name if reranker else 'None'}"
        )

    async def query(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """
        执行Agentic RAG查询

        Args:
            request: 查询请求

        Returns:
            查询响应
        """
        logger.info(f"[AgenticRAG] 开始查询 | query={request.query[:50]}... | session_id={request.session_id}")
        logger.debug(f"[AgenticRAG] 查询参数 | kb_types={request.kb_types} | top_k={request.top_k} | model={request.model}")

        # 获取或创建Agent
        logger.debug("[AgenticRAG] 获取或创建Agent...")
        agent = self._get_or_create_agent(
            model=request.model or "deepseek-v3",
            kb_types=request.kb_types,
        )

        # 调用Agent
        logger.info("[AgenticRAG] Agent开始推理...")
        response = await agent.ainvoke(
            message=request.query,
            thread_id=request.session_id or "default",
        )

        # 解析响应
        answer = response.content
        logger.info(f"[AgenticRAG] Agent推理完成 | answer长度={len(answer)}")

        # 提取来源信息（从metadata中）
        logger.debug("[AgenticRAG] 提取来源信息...")
        sources = self._extract_sources_from_response(response)
        logger.info(f"[AgenticRAG] 来源数量: {len(sources)}")

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            sub_queries=[],  # Agentic模式下可能无法直接获取
        )

    async def query_stream(
        self,
        request: RAGQueryRequest,
    ) -> AsyncGenerator[RagStreamEventDTO, None]:
        """
        执行Agentic RAG流式查询

        以流式方式返回Agent的思考过程和最终答案。

        Args:
            request: 查询请求

        Yields:
            流式事件：thought, action, observation, chunk, complete, error
        """
        logger.info(f"[AgenticRAG] 开始流式查询 | query={request.query[:50]}... | session_id={request.session_id}")

        # 发送开始事件
        yield RagStreamEventDTO(
            type="start",
            data={"query": request.query, "mode": "agentic"},
        )

        try:
            # 获取Agent
            logger.debug("[AgenticRAG] 获取或创建Agent...")
            agent = self._get_or_create_agent(
                model=request.model or "deepseek-v3",
                kb_types=request.kb_types,
            )

            # 流式调用
            logger.info("[AgenticRAG] Agent开始流式推理...")
            full_answer = ""
            chunk_count = 0
            tool_call_count = 0

            async for chunk in agent.astream(
                message=request.query,
                thread_id=request.session_id or "default",
            ):
                if chunk.type == ChunkType.CONTENT:
                    chunk_count += 1
                    full_answer += chunk.content
                    yield RagStreamEventDTO(
                        type="chunk",
                        data={"content": chunk.content},
                    )
                elif chunk.type == ChunkType.TOOL_CALL:
                    tool_call_count += 1
                    tool_name = chunk.tool_call.name if chunk.tool_call else "unknown"
                    tool_args = chunk.tool_call.arguments if chunk.tool_call else {}
                    logger.info(f"[AgenticRAG] 工具调用 #{tool_call_count} | {tool_name} | args={tool_args}")
                    yield RagStreamEventDTO(
                        type="action",
                        data={
                            "tool": tool_name,
                            "arguments": tool_args,
                        },
                    )
                elif chunk.type == ChunkType.ERROR:
                    logger.error(f"[AgenticRAG] 流式推理出错: {chunk.content}")
                    yield RagStreamEventDTO(
                        type="error",
                        data={"message": chunk.content},
                    )
                    return

            # 完成
            logger.info(f"[AgenticRAG] 流式推理完成 | chunks={chunk_count} | tools={tool_call_count} | answer长度={len(full_answer)}")
            yield RagStreamEventDTO(
                type="complete",
                data={
                    "answer": full_answer,
                    "sources": [],  # Agentic模式下需要额外解析
                    "stats": {
                        "chunk_count": chunk_count,
                        "tool_call_count": tool_call_count,
                    },
                },
            )

        except Exception as e:
            logger.error(f"[AgenticRAG] 流式查询失败: {e}", exc_info=True)
            yield RagStreamEventDTO(
                type="error",
                data={"message": f"查询失败: {str(e)}"},
            )

    def _get_or_create_agent(
        self,
        model: str,
        kb_types: list[str] | None = None,
    ) -> AbstractAgent:
        """
        获取或创建Agent实例

        Args:
            model: 模型名称
            kb_types: 知识库类型

        Returns:
            Agent实例
        """
        # 构建缓存key
        cache_key = f"{model}_{'-'.join(kb_types or ['auto'])}"

        if cache_key not in self._agent_cache:
            logger.info(f"[AgenticRAG] 创建新Agent | cache_key={cache_key} | model={model}")

            # 创建系统提示词
            logger.debug("[AgenticRAG] 构建系统提示词...")
            system_prompt = build_agentic_rag_prompt()

            # 创建RAG工具
            logger.debug("[AgenticRAG] 创建RAG工具...")
            tools = self._create_rag_tools(kb_types)
            logger.info(f"[AgenticRAG] 工具列表: {[t.name for t in tools]}")

            # 通过工厂创建Agent
            logger.debug("[AgenticRAG] 调用Agent工厂创建Agent...")
            agent = self._agent_factory.create_agent(
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                implementation="langgraph",  # 使用LangGraph实现ReAct
                max_iterations=10,
            )

            self._agent_cache[cache_key] = agent
            logger.info(f"[AgenticRAG] Agent创建完成 | cache_size={len(self._agent_cache)}")

        return self._agent_cache[cache_key]

    def _create_rag_tools(
        self,
        kb_types: list[str] | None = None,
    ) -> list[AgentTool]:
        """
        创建RAG工具列表

        Args:
            kb_types: 知识库类型

        Returns:
            工具列表
        """
        tools: list[AgentTool] = [
            # 混合检索工具
            HybridSearchTool(
                vector_store=self._vector_store,
                keyword_index=self._keyword_index,
            ),
            # 获取上下文工具（含Rerank）
            GetContextTool(reranker=self._reranker),
            # 答案生成工具
            AnswerGenerationTool(),
        ]

        return tools

    def _extract_sources_from_response(
        self,
        response: Any,
    ) -> list[SourceInfo]:
        """
        从Agent响应中提取来源信息

        Args:
            response: Agent响应

        Returns:
            来源信息列表
        """
        sources = []

        # 从metadata中提取来源信息
        metadata = getattr(response, "metadata", {}) or {}
        tool_calls = getattr(response, "tool_calls", []) or []

        # 尝试从工具调用结果中提取来源
        for tc in tool_calls:
            if tc.name in ("hybrid_search", "get_context"):
                # 这里需要更复杂的解析逻辑
                # 简化处理：返回空列表
                pass

        return sources

    def clear_agent_cache(self) -> None:
        """清除Agent缓存"""
        cache_size = len(self._agent_cache)
        self._agent_cache.clear()
        logger.info(f"[AgenticRAG] Agent缓存已清除 | 清除数量={cache_size}")
