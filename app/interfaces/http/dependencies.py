"""
HTTP 依赖注入

FastAPI 依赖注入配置，用于获取应用服务实例。

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.application.accounting.accounting_agent_service import AccountingAgentService
from app.application.agent.agent_factory import AgentFactory
from app.application.agent.agent_service import AgentService
from app.application.accounting.transaction_service import TransactionService
from app.application.rag.rag_service import RAGService
from app.application.rag.agentic_rag_service import AgenticRAGService
from app.application.rag.document_service import DocumentService
from app.application.rag.knowledge_base_service import KnowledgeBaseService
from app.domain.accounting.transaction_repository import TransactionRepository
from app.domain.rag.document_repository import DocumentRepository
from app.domain.rag.knowledge_base_repository import KnowledgeBaseRepository
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.domain.rag.reranker import Reranker
from app.infrastructure.agent.cache.agent_cache import AgentCache, InMemoryAgentCache
from app.infrastructure.llm.llm_provider import LLMProvider
from app.infrastructure.persistence.chroma import ChromaVectorStore, ChromaDocumentRepository
from app.infrastructure.persistence.sqlite import SQLiteKnowledgeBaseRepository
from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository
from app.infrastructure.persistence.whoosh import WhooshKeywordIndex
from app.infrastructure.rag.reranker.bailian_reranker import BailianReranker
from app.infrastructure.tools.accounting import (
    AddTransactionTool,
    CalculatorTool,
    GetCategoriesTool,
    GetCurrentDatetimeTool,
    QueryAccountingTool,
    StatsByPeriodTool,
)
from app.infrastructure.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Repository 依赖
# ────────────────────────────────────────────────────────────

@lru_cache()
def get_transaction_repository() -> TransactionRepository:
    """
    获取交易仓库（单例）
    
    Returns:
        TransactionRepository 实例
    """
    return SQLiteTransactionRepository()


# ────────────────────────────────────────────────────────────
# Agent 相关依赖
# ────────────────────────────────────────────────────────────

@lru_cache()
def get_agent_factory() -> AgentFactory:
    """
    获取 Agent 工厂（单例）
    
    Returns:
        AgentFactory 实例
    """
    return AgentFactory()


@lru_cache()
def get_agent_cache() -> AgentCache:
    """
    获取 Agent 缓存（单例）
    
    Returns:
        AgentCache 接口实例（InMemoryAgentCache 实现）
    """
    return InMemoryAgentCache()


@lru_cache()
def get_tool_registry() -> ToolRegistry:
    """
    获取工具注册表（单例）
    
    Returns:
        ToolRegistry 实例
    """
    return ToolRegistry()


@lru_cache()
def get_llm_provider() -> LLMProvider:
    """
    获取 LLM 提供器（单例）
    
    Returns:
        LLMProvider 实例
    """
    return LLMProvider()


@lru_cache()
def get_accounting_tools() -> list:
    """
    获取记账工具列表（单例）
    
    工具通过 Repository 依赖注入，符合 DDD 原则。
    
    Returns:
        记账工具列表
    """
    repository = get_transaction_repository()
    
    return [
        AddTransactionTool(repository=repository),
        QueryAccountingTool(repository=repository),
        StatsByPeriodTool(repository=repository),
        GetCategoriesTool(),
        GetCurrentDatetimeTool(),
        CalculatorTool(),
    ]


# ────────────────────────────────────────────────────────────
# 应用服务依赖
# ────────────────────────────────────────────────────────────

@lru_cache()
def get_agent_service() -> AgentService:
    """
    获取 Agent 应用服务（单例）
    
    注入领域层接口的具体实现：
    - AgentCache -> InMemoryAgentCache
    - ToolRegistry -> ToolRegistry
    
    Returns:
        AgentService 实例
    """
    return AgentService(
        agent_cache=get_agent_cache(),
        tool_registry=get_tool_registry(),
        agent_factory=get_agent_factory(),
    )


@lru_cache()
def get_accounting_agent_service() -> AccountingAgentService:
    """
    获取记账 Agent 应用服务（单例）
    
    通过依赖注入获取工具列表和工厂，符合 DDD 原则。
    
    Returns:
        AccountingAgentService 实例
    """
    return AccountingAgentService(
        agent_cache=get_agent_cache(),
        agent_factory=get_agent_factory(),
        accounting_tools=get_accounting_tools(),
    )


@lru_cache()
def get_transaction_service() -> TransactionService:
    """
    获取交易应用服务（单例）
    
    Returns:
        TransactionService 实例
    """
    repository = get_transaction_repository()
    return TransactionService(repository=repository)


# ────────────────────────────────────────────────────────────
# RAG 相关依赖
# ────────────────────────────────────────────────────────────

@lru_cache()
def get_document_repository() -> DocumentRepository:
    """
    获取文档仓库（单例）
    
    Returns:
        DocumentRepository 接口实例（ChromaDocumentRepository 实现）
    """
    return ChromaDocumentRepository()


@lru_cache()
def get_knowledge_base_repository() -> KnowledgeBaseRepository:
    """
    获取知识库仓库（单例）
    
    Returns:
        KnowledgeBaseRepository 接口实例（SQLiteKnowledgeBaseRepository 实现）
    """
    return SQLiteKnowledgeBaseRepository()


@lru_cache()
def get_vector_store() -> VectorStore:
    """
    获取向量存储（单例）
    
    Returns:
        VectorStore 接口实例（ChromaVectorStore 实现）
    """
    return ChromaVectorStore()


@lru_cache()
def get_keyword_index() -> KeywordIndex:
    """
    获取关键词索引（单例）
    
    Returns:
        KeywordIndex 接口实例（WhooshKeywordIndex 实现）
    """
    return WhooshKeywordIndex()


@lru_cache()
def get_reranker() -> Reranker | None:
    """
    获取重排序器（单例）
    
    Returns:
        Reranker 接口实例（BailianReranker 实现），如果配置不可用则返回 None
    """
    try:
        return BailianReranker()
    except Exception as e:
        logger.warning(f"重排序器初始化失败: {e}，将不使用重排序")
        return None


@lru_cache()
def get_rag_service() -> RAGService:
    """
    获取 RAG 应用服务（单例）

    注入领域层接口的具体实现：
    - VectorStore -> ChromaVectorStore
    - KeywordIndex -> WhooshKeywordIndex
    - Reranker -> BailianReranker

    Returns:
        RAGService 实例
    """
    return RAGService(
        vector_store=get_vector_store(),
        keyword_index=get_keyword_index(),
        reranker=get_reranker(),
    )


@lru_cache()
def get_agentic_rag_service() -> AgenticRAGService:
    """
    获取 Agentic RAG 应用服务（单例）

    基于ReAct模式的智能RAG服务，Agent自主决策检索策略。
    注入领域层接口的具体实现。

    Returns:
        AgenticRAGService 实例
    """
    return AgenticRAGService(
        agent_factory=get_agent_factory(),
        vector_store=get_vector_store(),
        keyword_index=get_keyword_index(),
        reranker=get_reranker(),
    )


@lru_cache()
def get_document_service() -> DocumentService:
    """
    获取文档应用服务（单例）
    
    注入领域层接口的具体实现：
    - DocumentRepository -> ChromaDocumentRepository
    - VectorStore -> ChromaVectorStore
    - KeywordIndex -> WhooshKeywordIndex
    
    Returns:
        DocumentService 实例
    """
    return DocumentService(
        document_repository=get_document_repository(),
        vector_store=get_vector_store(),
        keyword_index=get_keyword_index(),
    )


@lru_cache()
def get_knowledge_base_service() -> KnowledgeBaseService:
    """
    获取知识库应用服务（单例）
    
    注入领域层接口的具体实现：
    - KnowledgeBaseRepository -> SQLiteKnowledgeBaseRepository
    
    Returns:
        KnowledgeBaseService 实例
    """
    return KnowledgeBaseService(
        repository=get_knowledge_base_repository(),
    )


# ────────────────────────────────────────────────────────────
# FastAPI 依赖类型
# ────────────────────────────────────────────────────────────

AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
AccountingAgentServiceDep = Annotated[AccountingAgentService, Depends(get_accounting_agent_service)]
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
AgenticRAGServiceDep = Annotated[AgenticRAGService, Depends(get_agentic_rag_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
KnowledgeBaseServiceDep = Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
