"""
获取上下文工具

基于混合检索结果，使用Reranker精排获取最终上下文。
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.agent.agent_tool import AgentTool, ToolResult
from app.domain.rag.reranker import Reranker
from app.domain.rag.search_result import SearchResult, RankedResult

logger = logging.getLogger(__name__)


class GetContextTool(AgentTool):
    """
    获取上下文工具

    基于检索结果，使用Reranker进行精排序，返回高质量上下文。
    通常在hybrid_search之后调用，用于生成最终答案。

    Example:
        tool = GetContextTool(reranker=bailian_reranker)
        result = tool.execute(
            query="如何创建Bot",
            search_results=[...],
            top_k=5,
        )
    """

    def __init__(
        self,
        reranker: Reranker | None = None,
    ):
        """
        初始化获取上下文工具

        Args:
            reranker: 重排序器，None时不进行重排序
        """
        self._reranker = reranker

    @property
    def name(self) -> str:
        """工具名称"""
        return "get_context"

    @property
    def description(self) -> str:
        """工具描述"""
        return (
            "基于检索结果获取高质量上下文，使用Reranker进行精排序。\n"
            "适用于：已从hybrid_search获取候选结果，需要精选最佳上下文时\n"
            "参数：\n"
            "- query: 原始查询\n"
            "- search_results: 检索结果列表（来自hybrid_search）\n"
            "- top_k: 返回的上下文数量，默认5"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """参数Schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "原始用户查询",
                },
                "search_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "document_id": {"type": "string"},
                            "document_title": {"type": "string"},
                            "score": {"type": "number"},
                            "source": {"type": "string"},
                        },
                    },
                    "description": "检索结果列表",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的上下文数量",
                    "default": 5,
                },
            },
            "required": ["query", "search_results"],
        }

    def execute(
        self,
        query: str,
        search_results: list[dict],
        top_k: int = 5,
    ) -> ToolResult:
        """
        执行获取上下文

        Args:
            query: 原始查询
            search_results: 检索结果列表
            top_k: 返回数量

        Returns:
            工具执行结果
        """
        logger.info(f"[GetContext] 开始获取上下文 | query={query[:50]}... | 输入结果数={len(search_results)} | top_k={top_k}")

        try:
            if not search_results:
                logger.warning("[GetContext] 没有可用的检索结果")
                return ToolResult.success_result(
                    "没有可用的检索结果。",
                    context="",
                    result_count=0,
                )

            # 转换结果格式
            logger.debug("[GetContext] 解析检索结果...")
            results = self._parse_search_results(search_results)
            logger.debug(f"[GetContext] 解析完成: {len(results)}条")

            # 执行Rerank
            if self._reranker and len(results) > 1:
                logger.info(f"[GetContext] 使用Reranker精排 | 输入={len(results)} | 输出={top_k}")
                ranked_results = self._reranker.rerank(query, results, top_k)
                logger.info(f"[GetContext] Rerank完成 | 输出={len(ranked_results)}条")
                for i, r in enumerate(ranked_results[:3], 1):
                    logger.debug(f"  #{i}: score={r.rerank_score:.4f} | doc={r.document_title or 'unknown'}")
            else:
                logger.debug("[GetContext] 无Reranker，按原始分数排序")
                sorted_results = sorted(
                    results, key=lambda x: x.score, reverse=True
                )
                ranked_results = [
                    RankedResult(search_result=r, rerank_score=r.score, rank=i + 1)
                    for i, r in enumerate(sorted_results[:top_k])
                ]

            # 构建上下文
            logger.debug("[GetContext] 构建上下文字符串...")
            context = self._build_context(ranked_results)
            context_length = len(context)
            logger.info(f"[GetContext] 上下文构建完成 | 精选数={len(ranked_results)} | 字符数={context_length}")

            return ToolResult.success_result(
                f"已获取 {len(ranked_results)} 条精选上下文",
                context=context,
                sources=[
                    {
                        "document_id": r.search_result.document_id or "unknown",
                        "document_title": r.search_result.document_title or "未知文档",
                        "score": round(r.rerank_score, 4),
                        "rank": r.rank,
                    }
                    for r in ranked_results
                ],
                result_count=len(ranked_results),
            )

        except Exception as e:
            logger.error(f"[GetContext] 获取上下文失败: {e}", exc_info=True)
            return ToolResult.error_result(f"获取上下文失败: {str(e)}")

    def _parse_search_results(
        self,
        search_results: list[dict] | str | Any,
    ) -> list[SearchResult]:
        """
        解析检索结果

        Args:
            search_results: 原始检索结果，可能是列表、字符串或其他格式

        Returns:
            SearchResult列表
        """
        from app.domain.rag.document_chunk import DocumentChunk

        # 处理字符串情况（Agent可能直接传递了hybrid_search的字符串输出）
        if isinstance(search_results, str):
            logger.warning(f"[GetContext] search_results是字符串而非列表，尝试解析 | 内容长度={len(search_results)}")
            # 尝试从字符串中提取结构化数据
            return self._parse_search_results_from_string(search_results)

        # 处理非列表情况
        if not isinstance(search_results, list):
            logger.error(f"[GetContext] search_results类型不支持: {type(search_results)}")
            return []

        results = []
        for sr in search_results:
            # 处理每个结果项
            if isinstance(sr, str):
                # 如果列表项是字符串，尝试解析
                logger.debug(f"[GetContext] 列表项是字符串，尝试解析: {sr[:50]}...")
                parsed = self._try_parse_dict_from_string(sr)
                if parsed:
                    sr = parsed
                else:
                    # 无法解析，创建简化结果
                    chunk = DocumentChunk(
                        content=sr,
                        chunk_index=0,
                        metadata={"source": "unknown"},
                    )
                    results.append(SearchResult(
                        chunk=chunk,
                        score=0.5,
                        source="unknown",
                    ))
                    continue

            if not isinstance(sr, dict):
                logger.warning(f"[GetContext] 跳过非字典项: {type(sr)}")
                continue

            content = sr.get("content", "")
            doc_id = sr.get("document_id")
            doc_title = sr.get("document_title")
            score = sr.get("score", 0.5)
            source = sr.get("source", "unknown")

            chunk = DocumentChunk(
                content=content,
                chunk_index=0,
                metadata=sr,
            )

            results.append(SearchResult(
                chunk=chunk,
                score=score,
                source=source,
                document_id=doc_id,
                document_title=doc_title,
            ))

        return results

    def _parse_search_results_from_string(self, text: str) -> list[SearchResult]:
        """
        从hybrid_search的格式化字符串输出中解析检索结果

        Args:
            text: hybrid_search工具的格式化输出

        Returns:
            SearchResult列表
        """
        from app.domain.rag.document_chunk import DocumentChunk

        results = []
        lines = text.split("\n")
        current_title = None
        current_content = []
        current_score = 0.5

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配标题行格式: "[1] 文档标题 (相关度: 0.1234)"
            if line.startswith("[") and "]" in line and "相关度:" in line:
                # 保存之前的结果
                if current_title and current_content:
                    content = "\n".join(current_content).strip()
                    chunk = DocumentChunk(
                        content=content,
                        chunk_index=0,
                        metadata={"title": current_title},
                    )
                    results.append(SearchResult(
                        chunk=chunk,
                        score=current_score,
                        source="hybrid",
                        document_title=current_title,
                    ))

                # 解析新标题
                try:
                    title_part = line.split("]", 1)[1].split("(相关度:")[0].strip()
                    score_part = line.split("(相关度:")[1].rstrip(")").strip()
                    current_title = title_part
                    current_score = float(score_part) if score_part else 0.5
                    current_content = []
                except (IndexError, ValueError):
                    current_title = line
                    current_score = 0.5
                    current_content = []

            elif current_title is not None:
                # 内容行（缩进的）
                current_content.append(line.lstrip())

        # 保存最后一个结果
        if current_title and current_content:
            content = "\n".join(current_content).strip()
            chunk = DocumentChunk(
                content=content,
                chunk_index=0,
                metadata={"title": current_title},
            )
            results.append(SearchResult(
                chunk=chunk,
                score=current_score,
                source="hybrid",
                document_title=current_title,
            ))

        logger.info(f"[GetContext] 从字符串解析出 {len(results)} 条结果")
        return results

    def _try_parse_dict_from_string(self, text: str) -> dict | None:
        """
        尝试从字符串解析字典

        Args:
            text: 可能包含字典的字符串

        Returns:
            解析后的字典或None
        """
        import json
        try:
            # 尝试JSON解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试eval解析（仅用于简单字典）
        try:
            if text.strip().startswith("{") and text.strip().endswith("}"):
                result = eval(text, {"__builtins__": {}}, {})
                if isinstance(result, dict):
                    return result
        except Exception:
            pass

        return None

    def _build_context(self, ranked_results: list[RankedResult]) -> str:
        """
        构建上下文字符串

        Args:
            ranked_results: 重排序后的结果

        Returns:
            格式化的上下文
        """
        if not ranked_results:
            return ""

        context_parts = []
        for i, r in enumerate(ranked_results, 1):
            content = r.content
            title = r.document_title or "相关文档"

            context_parts.append(f"[文档{i}] {title}\n{content}")

        return "\n\n".join(context_parts)
