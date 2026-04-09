"""
RAG 应用服务

实现Agentic RAG检索流程：
1. 查询分解
2. 知识库路由
3. 混合检索（向量+关键词）
4. RAG-Fusion
5. 重排序
6. 答案生成
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator

from langchain_openai import ChatOpenAI

from app.application.rag.dto import (
    RAGQueryRequest, 
    RAGQueryResponse,
    RagStreamEventDTO,
)
from app.config import get_llm_config
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.query import Query, SubQuery
from app.domain.rag.reranker import Reranker
from app.domain.rag.search_result import SearchResult, RankedResult
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.llm.llm_factory import LLMFactory
from app.prompts.rag import build_query_decomposition_prompt, build_answer_generation_prompt

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG 应用服务
    
    实现完整的Agentic RAG检索流程：
    1. 检索预处理：将问题分解为子问题
    2. 知识库路由：判断检索哪个知识库
    3. 混合检索：向量检索+关键词检索
    4. RAG-Fusion：结果融合
    5. 重排序：使用Reranker精排
    6. 答案生成：基于检索结果生成回答
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
        reranker: Reranker | None = None,
        llm: ChatOpenAI | None = None,
    ):
        """
        初始化RAG服务
        
        Args:
            vector_store: 向量存储
            keyword_index: 关键词索引
            reranker: 重排序器
            llm: LLM实例
        """
        self._vector_store = vector_store
        self._keyword_index = keyword_index
        self._reranker = reranker
        self._llm = llm or LLMFactory.create_llm()
        self._embedding = LLMFactory.create_embedding()
    
    async def query(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """
        执行RAG查询
        
        Args:
            request: 查询请求
            
        Returns:
            查询响应
        """
        logger.info(f"RAG查询: {request.query}")
        
        # 1. 查询分解和知识库路由
        query = await self._decompose_query(request)
        logger.debug(f"查询分解完成: {len(query.sub_queries)}个子查询")
        
        # 2. 并行检索
        search_results = await self._parallel_search(query)
        logger.debug(f"检索完成: {len(search_results)}条结果")
        
        # 3. RAG-Fusion去重
        fused_results = self._rag_fusion(search_results)
        logger.debug(f"RAG-Fusion后: {len(fused_results)}条结果")
        
        # 4. 重排序
        ranked_results = await self._rerank(request.query, fused_results, request.top_k)
        logger.debug(f"重排序完成: 前{len(ranked_results)}条")
        
        # 5. 答案生成
        answer = await self._generate_answer(request.query, ranked_results)
        
        # 构建响应
        response = RAGQueryResponse.from_ranked_results(answer, ranked_results)
        return response
    
    async def query_stream(
        self,
        request: RAGQueryRequest,
    ) -> AsyncGenerator[RagStreamEventDTO, None]:
        """
        执行RAG流式查询
        
        以流式方式返回处理流程的各个步骤和最终结果。
        
        Args:
            request: 查询请求
            
        Yields:
            流式事件：process, chunk, sources, complete, error
        """
        logger.info(f"RAG流式查询: {request.query}")
        
        # 初始化流程状态
        process_state = self._init_process_state(request.query)
        
        try:
            # 1. 查询分解
            yield self._update_process_step(process_state, "query_decomposition", "running")
            query = await self._decompose_query(request)
            process_state["query_decomposition"].update({
                "status": "completed",
                "original_query": request.query,
                "sub_queries": [sq.query for sq in query.sub_queries],
            })
            yield self._update_process_step(process_state, "query_decomposition", "completed")
            
            # 2. 向量检索
            yield self._update_process_step(process_state, "vector_retrieval", "running")
            all_vector_results = []
            total_chunks = 0
            
            for sub_query in query.sub_queries:
                query_embedding = await self._embedding.aembed_query(sub_query.query)
                vector_results = await self._vector_search(sub_query, query_embedding)
                all_vector_results.extend(vector_results)
                total_chunks += len(vector_results)
            
            process_state["vector_retrieval"].update({
                "status": "completed",
                "total_chunks": total_chunks,
                "retrieved_chunks": [
                    {
                        "chunk_id": r.chunk.chunk_id if hasattr(r.chunk, 'chunk_id') else str(i),
                        "document_id": r.document_id or "unknown",
                        "document_title": r.document_title or "未知文档",
                        "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        "score": r.score,
                    }
                    for i, r in enumerate(all_vector_results[:10])  # 只返回前10个
                ],
            })
            yield self._update_process_step(process_state, "vector_retrieval", "completed")
            
            # 3. 关键词检索
            yield self._update_process_step(process_state, "keyword_retrieval", "running")
            all_keyword_results = []
            all_keywords = []
            
            for sub_query in query.sub_queries:
                keyword_results = await self._keyword_search(sub_query)
                all_keyword_results.extend(keyword_results)
                # 提取关键词（简单处理：使用查询词作为关键词）
                all_keywords.extend(sub_query.query.split())
            
            process_state["keyword_retrieval"].update({
                "status": "completed",
                "keywords": list(set(all_keywords))[:10],  # 去重后取前10
                "matched_chunks": [
                    {
                        "chunk_id": r.chunk.chunk_id if hasattr(r.chunk, 'chunk_id') else str(i),
                        "document_id": r.document_id or "unknown",
                        "document_title": r.document_title or "未知文档",
                        "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        "score": r.score,
                    }
                    for i, r in enumerate(all_keyword_results[:5])
                ],
            })
            yield self._update_process_step(process_state, "keyword_retrieval", "completed")
            
            # 4. RAG-Fusion和重排序
            yield self._update_process_step(process_state, "reranking", "running")
            fused_results = self._rag_fusion(all_vector_results + all_keyword_results)
            ranked_results = await self._rerank(request.query, fused_results, request.top_k)
            
            process_state["reranking"].update({
                "status": "completed",
                "input_chunks": len(fused_results),
                "output_chunks": len(ranked_results),
                "ranked_chunks": [
                    {
                        "chunk_id": r.search_result.chunk.chunk_id if hasattr(r.search_result.chunk, 'chunk_id') else str(i),
                        "document_id": r.search_result.document_id or "unknown",
                        "document_title": r.search_result.document_title or "未知文档",
                        "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        "score": r.rerank_score,
                        "original_rank": i + 1,
                        "new_rank": r.rank,
                    }
                    for i, r in enumerate(ranked_results)
                ],
            })
            yield self._update_process_step(process_state, "reranking", "completed")
            
            # 5. 答案生成（流式）
            yield self._update_process_step(process_state, "answer_generation", "running")
            
            # 发送来源信息
            sources = [
                {
                    "document_id": r.search_result.document_id or "unknown",
                    "document_title": r.search_result.document_title or "未知文档",
                    "content": r.content[:500] + "..." if len(r.content) > 500 else r.content,
                    "score": r.rerank_score,
                }
                for r in ranked_results
            ]
            yield RagStreamEventDTO(type="sources", data=sources)
            
            # 流式生成答案
            answer = ""
            if ranked_results:
                context_parts = []
                for i, r in enumerate(ranked_results[:5], 1):
                    context_parts.append(f"[文档{i}] {r.content[:800]}")
                context = "\n\n".join(context_parts)
                prompt = build_answer_generation_prompt(request.query, context)
                
                # 尝试使用流式生成
                try:
                    async for chunk in self._llm.astream(prompt):
                        content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                        answer += content
                        yield RagStreamEventDTO(type="chunk", data=content)
                except Exception as e:
                    logger.warning(f"流式生成失败，使用非流式: {e}")
                    # 回退到非流式
                    response = await self._llm.ainvoke(prompt)
                    answer = response.content
                    yield RagStreamEventDTO(type="chunk", data=answer)
            else:
                answer = "抱歉，在知识库中没有找到相关信息。"
                yield RagStreamEventDTO(type="chunk", data=answer)
            
            process_state["answer_generation"].update({
                "status": "completed",
                "used_chunks": len(ranked_results),
                "tokens_generated": len(answer),
            })
            yield self._update_process_step(process_state, "answer_generation", "completed")
            
            # 完成
            final_response = RAGQueryResponse.from_ranked_results(answer, ranked_results)
            yield RagStreamEventDTO(
                type="complete",
                data={
                    "answer": answer,
                    "sources": [
                        {
                            "document_id": s.document_id,
                            "document_title": s.document_title,
                            "content": s.content,
                            "score": s.score,
                        }
                        for s in final_response.sources
                    ],
                }
            )
            
        except Exception as e:
            logger.error(f"RAG流式查询失败: {e}", exc_info=True)
            yield RagStreamEventDTO(
                type="error",
                data={"message": f"处理失败: {str(e)}"}
            )
    
    def _init_process_state(self, query: str) -> dict:
        """初始化流程状态"""
        now = datetime.now().isoformat()
        return {
            "query_decomposition": {
                "status": "pending",
                "original_query": query,
                "sub_queries": [],
                "start_time": now,
            },
            "vector_retrieval": {
                "status": "pending",
                "total_chunks": 0,
                "retrieved_chunks": [],
                "start_time": None,
            },
            "keyword_retrieval": {
                "status": "pending",
                "keywords": [],
                "matched_chunks": [],
                "start_time": None,
            },
            "reranking": {
                "status": "pending",
                "input_chunks": 0,
                "output_chunks": 0,
                "ranked_chunks": [],
                "start_time": None,
            },
            "answer_generation": {
                "status": "pending",
                "used_chunks": 0,
                "tokens_generated": 0,
                "start_time": None,
            },
        }
    
    def _update_process_step(
        self,
        state: dict,
        step: str,
        status: str,
    ) -> RagStreamEventDTO:
        """更新流程步骤状态"""
        state[step]["status"] = status
        if status in ("running", "completed"):
            state[step]["end_time" if status == "completed" else "start_time"] = datetime.now().isoformat()
        
        return RagStreamEventDTO(type="process", data=state.copy())
    
    async def _decompose_query(self, request: RAGQueryRequest) -> Query:
        """
        查询分解
        
        使用LLM将复杂问题分解为子问题，并判断知识库类型。
        
        Args:
            request: 查询请求
            
        Returns:
            分解后的查询对象
        """
        # 如果指定了知识库类型，不进行分解
        if request.kb_types:
            kb_types = [KnowledgeBaseType(t) for t in request.kb_types]
            sub_query = SubQuery(
                query=request.query,
                kb_types=kb_types,
            )
            return Query(
                original_query=request.query,
                sub_queries=[sub_query],
            )
        
        # 使用LLM分解查询
        prompt = build_query_decomposition_prompt(request.query)
        
        try:
            response = await self._llm.ainvoke(prompt)
            content = response.content
            
            # 解析响应（预期JSON格式）
            import json
            import re
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                sub_queries = []
                for sq in data.get("sub_queries", []):
                    kb_type_values = sq.get("kb_types", ["faq"])
                    kb_types = [KnowledgeBaseType.from_string(t) for t in kb_type_values]
                    
                    sub_queries.append(SubQuery(
                        query=sq["query"],
                        kb_types=kb_types,
                        weight=sq.get("weight", 1.0),
                    ))
                
                return Query(
                    original_query=request.query,
                    sub_queries=sub_queries,
                )
        
        except Exception as e:
            logger.warning(f"查询分解失败: {e}，使用原始查询")
        
        # 失败时使用原始查询，自动判断知识库
        return Query(
            original_query=request.query,
            sub_queries=[SubQuery(query=request.query, kb_types=list(KnowledgeBaseType))],
        )
    
    async def _parallel_search(self, query: Query) -> list[SearchResult]:
        """
        并行检索
        
        对每个子查询并行执行向量检索和关键词检索。
        
        Args:
            query: 查询对象
            
        Returns:
            检索结果列表
        """
        all_results = []
        
        # 对每个子查询执行检索
        for sub_query in query.sub_queries:
            # 生成查询向量
            query_embedding = await self._embedding.aembed_query(sub_query.query)
            
            # 并行执行向量检索和关键词检索
            vector_task = self._vector_search(sub_query, query_embedding)
            keyword_task = self._keyword_search(sub_query)
            
            vector_results, keyword_results = await asyncio.gather(
                vector_task, keyword_task
            )
            
            all_results.extend(vector_results)
            all_results.extend(keyword_results)
        
        return all_results
    
    async def _vector_search(
        self,
        sub_query: SubQuery,
        query_embedding: list[float],
    ) -> list[SearchResult]:
        """向量检索"""
        try:
            results = self._vector_store.similarity_search(
                query_embedding=query_embedding,
                kb_types=sub_query.kb_types,
                top_k=20,
            )
            
            search_results = []
            for chunk_id, score in results:
                # 获取分块内容
                chunk = self._vector_store.get_chunk_by_id(chunk_id)
                if chunk:
                    search_results.append(SearchResult(
                        chunk=chunk,
                        score=min(score / 100, 1.0),  # 归一化到0-1
                        source="vector",
                    ))
            
            return search_results
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    async def _keyword_search(self, sub_query: SubQuery) -> list[SearchResult]:
        """关键词检索"""
        try:
            results = self._keyword_index.search(
                query=sub_query.query,
                kb_types=sub_query.kb_types,
                top_k=20,
            )
            
            search_results = []
            for chunk_id, score in results:
                # 构造简化分块
                chunk = DocumentChunk(
                    content=f"[Keyword Result] {chunk_id}",
                    chunk_index=0,
                )
                search_results.append(SearchResult(
                    chunk=chunk,
                    score=min(score / 100, 1.0),
                    source="keyword",
                    metadata={"chunk_id": chunk_id},
                ))
            
            return search_results
        except Exception as e:
            logger.error(f"关键词检索失败: {e}")
            return []
    
    def _rag_fusion(self, results: list[SearchResult]) -> list[SearchResult]:
        """
        RAG-Fusion结果融合
        
        使用RRF (Reciprocal Rank Fusion) 算法融合多路召回结果。
        
        Args:
            results: 检索结果列表
            
        Returns:
            融合后的结果列表
        """
        # 按内容去重，保留最高分数
        seen_content = {}
        for r in results:
            content_hash = hash(r.content[:100])  # 使用前100字符哈希
            if content_hash not in seen_content:
                seen_content[content_hash] = r
            elif r.score > seen_content[content_hash].score:
                seen_content[content_hash] = r
        
        return list(seen_content.values())
    
    async def _rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[RankedResult]:
        """
        重排序
        
        Args:
            query: 原始查询
            results: 待排序结果
            top_k: 返回数量
            
        Returns:
            重排序后的结果
        """
        if not self._reranker or len(results) <= top_k:
            # 无reranker时按原始分数排序
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
            return [
                RankedResult(search_result=r, rerank_score=r.score, rank=i + 1)
                for i, r in enumerate(sorted_results[:top_k])
            ]
        
        return self._reranker.rerank(query, results, top_k)
    
    async def _generate_answer(self, query: str, results: list[RankedResult]) -> str:
        """
        生成答案
        
        Args:
            query: 用户查询
            results: 检索结果
            
        Returns:
            生成的答案
        """
        if not results:
            return "抱歉，在知识库中没有找到相关信息。"
        
        # 构建上下文
        context_parts = []
        for i, r in enumerate(results[:5], 1):
            context_parts.append(f"[文档{i}] {r.content[:800]}")
        
        context = "\n\n".join(context_parts)
        
        prompt = build_answer_generation_prompt(query, context)
        
        try:
            response = await self._llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return "抱歉，生成答案时出现错误。"


# 导入DocumentChunk用于类型提示
from app.domain.rag.document_chunk import DocumentChunk
