"""
领域层 (Domain Layer)

核心业务逻辑层，独立于框架、UI 和数据库。
包含实体、值对象、聚合根、领域服务和仓库接口。
"""

from __future__ import annotations

from app.domain.shared.entity import Entity
from app.domain.shared.value_object import ValueObject
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.repository import Repository

from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_message import AgentMessage, MessageRole
from app.domain.agent.agent_tool import AgentTool
from app.domain.agent.agent_response import AgentResponse, AgentChunk, ToolResult, ToolCall

from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.accounting.money import Money
from app.domain.accounting.transaction_category import TransactionCategory
from app.domain.accounting.transaction_repository import TransactionRepository
from app.domain.accounting.transaction_statistics import TransactionStatistics

__all__ = [
    # Shared
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "Repository",
    # Agent
    "AbstractAgent",
    "AgentMessage",
    "MessageRole",
    "AgentTool",
    "AgentResponse",
    "AgentChunk",
    "ToolResult",
    "ToolCall",
    # Accounting
    "Transaction",
    "TransactionType",
    "Money",
    "TransactionCategory",
    "TransactionRepository",
    "TransactionStatistics",
]
