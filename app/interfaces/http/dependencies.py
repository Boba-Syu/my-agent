"""
HTTP 依赖注入

FastAPI 依赖注入配置，用于获取应用服务实例。
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.application.agent.agent_service import AgentService
from app.application.accounting.accounting_agent_service import AccountingAgentService
from app.application.accounting.transaction_service import TransactionService
from app.infrastructure.agent.cache.agent_cache import InMemoryAgentCache
from app.infrastructure.llm.llm_provider import LLMProvider
from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository
from app.infrastructure.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@lru_cache()
def get_agent_service() -> AgentService:
    """
    获取 Agent 应用服务（单例）
    
    Returns:
        AgentService 实例
    """
    return AgentService(
        agent_cache=InMemoryAgentCache(),
        tool_registry=ToolRegistry(),
        llm_provider=LLMProvider(),
    )


@lru_cache()
def get_accounting_agent_service() -> AccountingAgentService:
    """
    获取记账 Agent 应用服务（单例）
    
    Returns:
        AccountingAgentService 实例
    """
    return AccountingAgentService(
        agent_cache=InMemoryAgentCache(),
        llm_provider=LLMProvider(),
    )


@lru_cache()
def get_transaction_service() -> TransactionService:
    """
    获取交易应用服务（单例）
    
    Returns:
        TransactionService 实例
    """
    repository = SQLiteTransactionRepository()
    return TransactionService(repository=repository)


# FastAPI 依赖类型
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
AccountingAgentServiceDep = Annotated[AccountingAgentService, Depends(get_accounting_agent_service)]
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
