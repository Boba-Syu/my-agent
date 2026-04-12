"""
HTTP 请求/响应模型

Pydantic 模型定义，用于 API 的序列化和验证。
"""

from __future__ import annotations

from app.interfaces.http.schemas.agent_schemas import (
    ChatRequest,
    ChatResponse,
    ToolInfo,
    HealthResponse,
)
from app.interfaces.http.schemas.accounting_schemas import (
    AccountingChatRequest,
    AccountingChatResponse,
    TransactionRecord,
    CreateRecordRequest,
    UpdateRecordRequest,
    OperationResponse,
    StatsResponse,
)
from app.interfaces.http.schemas.rag_schemas import (
    RAGQueryRequestSchema,
    RAGQueryResponseSchema,
    SourceInfoSchema,
    DocumentUploadResponseSchema,
    DocumentListResponseSchema,
    CreateTextDocumentRequestSchema,
    CreateTextDocumentResponseSchema,
    KnowledgeBaseCreateRequestSchema,
    KnowledgeBaseUpdateRequestSchema,
    KnowledgeBaseResponseSchema,
    SuccessResponseSchema,
    HealthCheckResponseSchema,
)

__all__ = [
    # Agent schemas
    "ChatRequest",
    "ChatResponse",
    "ToolInfo",
    "HealthResponse",
    # Accounting schemas
    "AccountingChatRequest",
    "AccountingChatResponse",
    "TransactionRecord",
    "CreateRecordRequest",
    "UpdateRecordRequest",
    "OperationResponse",
    "StatsResponse",
    # RAG schemas
    "RAGQueryRequestSchema",
    "RAGQueryResponseSchema",
    "SourceInfoSchema",
    "DocumentUploadResponseSchema",
    "DocumentListResponseSchema",
    "CreateTextDocumentRequestSchema",
    "CreateTextDocumentResponseSchema",
    "KnowledgeBaseCreateRequestSchema",
    "KnowledgeBaseUpdateRequestSchema",
    "KnowledgeBaseResponseSchema",
    "SuccessResponseSchema",
    "HealthCheckResponseSchema",
]
