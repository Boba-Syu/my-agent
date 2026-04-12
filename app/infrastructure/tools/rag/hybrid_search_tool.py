"""
混合检索工具

实现混合检索（向量+关键词）的AgentTool，供ReAct Agent调用。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.domain.agent.agent_tool import AgentTool, ToolResult
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.domain.rag.search_result import SearchResult
from app.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class HybridSearchTool(AgentTool):
    """
    混合检索工具

    执行向量检索和关键词检索，返回融合的候选结果。
    供ReAct Agent在需要检索时调用。

    Example:
        tool = HybridSearchTool(
            vector_store=chroma_store,
            keyword_index=whoosh_index,
        )
        result = tool.execute(
            query="如何创建Bot",
            kb_types=["faq"],
            top_k=10,
        )
    """

    def __init__(
        self,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
    ):
        """
        初始化混合检索工具

        Args:
            vector_store: 向量存储实现
            keyword_index: 关键词索引实现
        """
        self._vector_store = vector_store
        self._keyword_index = keyword_index
        # 注意：不在init中创建embedding实例，避免httpx客户端被复用导致Event loop is closed错误
        # 每次执行时在run_async_search中创建新实例

    @property
    def name(self) -> str:
        """工具名称"""
        return "hybrid_search"

    @property
    def description(self) -> str:
        """工具描述"""
        return (
            "执行混合检索（向量+关键词），从知识库中检索相关文档。\n"
            "适用于：需要查找知识库信息来回答用户问题时\n"
            "参数：\n"
            "- query: 检索查询词\n"
            "- kb_types: 知识库类型列表，可选值：faq（常见问题）、regulation（规章制度）\n"
            "- top_k: 返回结果数量，默认10"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """参数Schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索查询词，用于从知识库中查找相关信息",
                },
                "kb_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "知识库类型列表，如['faq', 'regulation']",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 10,
                },
            },
            "required": ["query"],
        }

    def execute(
        self,
        query: str,
        kb_types: list[str] | None = None,
        top_k: int = 10,
    ) -> ToolResult:
        """
        执行混合检索

        Args:
            query: 检索查询词
            kb_types: 知识库类型列表
            top_k: 返回结果数量

        Returns:
            工具执行结果
        """
        logger.info(f"[HybridSearch] 开始混合检索 | query={query[:50]}... | top_k={top_k}")
        logger.debug(f"[HybridSearch] 知识库类型: {kb_types}")

        try:
            # 解析知识库类型
            kb_type_enums = None
            if kb_types:
                kb_type_enums = [
                    KnowledgeBaseType(t) for t in kb_types
                    if t in [kt.value for kt in KnowledgeBaseType]
                ]
                logger.debug(f"[HybridSearch] 解析后的知识库类型: {[k.value for k in kb_type_enums]}")

            # 执行检索 - 在新线程中运行异步搜索
            logger.debug("[HybridSearch] 开始混合检索...")
            import concurrent.futures

            def run_async_search():
                """在新线程中运行异步搜索"""
                # 每次执行时创建新的embedding实例，避免httpx客户端被复用
                embedding = LLMFactory.create_embedding()
                # 手动管理事件循环，避免 asyncio.run() 关闭循环后资源清理问题
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self._async_hybrid_search(query, kb_type_enums, top_k, embedding)
                    )
                finally:
                    # 确保所有异步资源都被正确清理
                    try:
                        # 取消所有待处理的任务
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            for task in pending:
                                task.cancel()
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        # 关闭循环
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    finally:
                        loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_search)
                results = future.result()

            if not results:
                logger.warning(f"[HybridSearch] 未找到相关文档 | query={query[:50]}...")
                return ToolResult.success_result(
                    "未找到相关文档。",
                    result_count=0,
                )

            logger.info(f"[HybridSearch] 检索完成 | 结果数={len(results)} | 前5条分数={[round(r.score, 4) for r in results[:5]]}")

            # 格式化结果
            formatted_results = self._format_results(results)

            return ToolResult.success_result(
                formatted_results,
                result_count=len(results),
                sources=[
                    {
                        "document_id": r.document_id or "unknown",
                        "document_title": r.document_title or "未知文档",
                        "score": round(r.score, 4),
                        "source": r.source,
                    }
                    for r in results[:5]  # 只返回前5个的元数据
                ],
            )

        except Exception as e:
            logger.error(f"[HybridSearch] 混合检索失败: {e}", exc_info=True)
            return ToolResult.error_result(f"检索失败: {str(e)}")

    async def _async_hybrid_search(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None,
        top_k: int,
        embedding: Any,
    ) -> list[SearchResult]:
        """
        异步执行混合检索

        Args:
            query: 查询词
            kb_types: 知识库类型
            top_k: 返回数量
            embedding: embedding实例（每次执行时创建的新实例）

        Returns:
            检索结果列表
        """
        # 并行执行向量检索和关键词检索
        vector_task = self._vector_search(query, kb_types, top_k * 2, embedding)
        keyword_task = self._keyword_search(query, kb_types, top_k * 2)

        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task
        )

        # 融合结果
        fused_results = self._fuse_results(vector_results, keyword_results)

        # 返回前top_k个
        return fused_results[:top_k]

    async def _vector_search(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None,
        top_k: int,
        embedding: Any,
    ) -> list[SearchResult]:
        """向量检索"""
        try:
            # 生成查询向量
            query_embedding = await embedding.aembed_query(query)

            # 执行检索
            results = self._vector_store.similarity_search(
                query_embedding=query_embedding,
                kb_types=kb_types,
                top_k=top_k,
            )

            search_results = []
            for chunk_id, score in results:
                # 获取分块内容
                chunk = self._vector_store.get_chunk_by_id(chunk_id)
                if chunk:
                    # 获取元数据
                    metadata = chunk.metadata or {}
                    search_results.append(SearchResult(
                        chunk=chunk,
                        score=min(score, 1.0),
                        source="vector",
                        document_id=metadata.get("document_id"),
                        document_title=metadata.get("title"),
                    ))

            logger.debug(f"[HybridSearch] 向量检索完成: {len(search_results)}条结果")
            return search_results

        except Exception as e:
            logger.error(f"[HybridSearch] 向量检索失败: {e}")
            raise

    async def _keyword_search(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """关键词检索"""
        try:
            results = self._keyword_index.search(
                query=query,
                kb_types=kb_types,
                top_k=top_k,
            )

            search_results = []
            for chunk_id, score in results:
                # 从chunk_id解析信息
                # chunk_id格式: {document_id}_{chunk_index}
                if "_" in chunk_id:
                    doc_id, idx = chunk_id.rsplit("_", 1)
                else:
                    doc_id, idx = chunk_id, "0"

                # 构造简化分块（实际项目中应查询完整内容）
                from app.domain.rag.document_chunk import DocumentChunk
                chunk = DocumentChunk(
                    content=f"[Keyword匹配] 文档片段",
                    chunk_index=int(idx) if idx.isdigit() else 0,
                    metadata={"chunk_id": chunk_id, "document_id": doc_id},
                )

                search_results.append(SearchResult(
                    chunk=chunk,
                    score=min(score / 100, 1.0),
                    source="keyword",
                    document_id=doc_id,
                ))

            logger.debug(f"[HybridSearch] 关键词检索完成: {len(search_results)}条结果")
            return search_results

        except Exception as e:
            logger.error(f"[HybridSearch] 关键词检索失败: {e}")
            raise

    def _fuse_results(
        self,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        融合向量检索和关键词检索结果

        使用RRF (Reciprocal Rank Fusion) 算法融合结果。

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果

        Returns:
            融合后的结果
        """
        # RRF常数
        k = 60

        # 构建内容到结果的映射
        all_results = {}

        # 处理向量结果
        for rank, result in enumerate(vector_results, 1):
            content_key = result.content[:100]  # 使用前100字符作为key
            if content_key not in all_results:
                all_results[content_key] = {
                    "result": result,
                    "vector_rank": rank,
                    "keyword_rank": None,
                }

        # 处理关键词结果
        for rank, result in enumerate(keyword_results, 1):
            content_key = result.content[:100]
            if content_key in all_results:
                all_results[content_key]["keyword_rank"] = rank
            else:
                all_results[content_key] = {
                    "result": result,
                    "vector_rank": None,
                    "keyword_rank": rank,
                }

        # 计算RRF分数
        scored_results = []
        for data in all_results.values():
            rrf_score = 0.0
            if data["vector_rank"]:
                rrf_score += 1.0 / (k + data["vector_rank"])
            if data["keyword_rank"]:
                rrf_score += 1.0 / (k + data["keyword_rank"])

            # 更新分数
            result = data["result"]
            # 创建新的SearchResult，使用融合后的分数
            from dataclasses import replace
            fused_result = replace(result, score=rrf_score, source="hybrid")
            scored_results.append((fused_result, rrf_score))

        # 按分数降序排序
        scored_results.sort(key=lambda x: x[1], reverse=True)

        return [r[0] for r in scored_results]

    def _format_results(self, results: list[SearchResult]) -> str:
        """
        格式化检索结果

        Args:
            results: 检索结果列表

        Returns:
            格式化后的字符串
        """
        if not results:
            return "未找到相关文档。"

        lines = [f"检索到 {len(results)} 条相关文档：", ""]

        for i, result in enumerate(results[:10], 1):  # 最多显示10条
            title = result.document_title or "未知文档"
            content = result.content[:300]  # 截断内容
            if len(result.content) > 300:
                content += "..."

            lines.append(f"[{i}] {title} (相关度: {result.score:.4f})")
            lines.append(f"    {content}")
            lines.append("")

        return "\n".join(lines)
