"""RAG API Schema

RAG相关的Pydantic模型定义，用于请求和响应数据验证。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ───────────────────────────────────────────────────────────
# RAG 查询相关 Schema
# ───────────────────────────────────────────────────────────

class RAGQueryRequestSchema(BaseModel):
    """RAG查询请求"""
    query: str
    kb_types: list[str] | None = None
    top_k: int = 10
    use_agentic: bool = Field(default=False, description="使用Agentic RAG模式（ReAct智能体）")
    session_id: str | None = Field(default=None, description="会话ID，用于保持上下文")


class SourceInfoSchema(BaseModel):
    """来源信息"""
    document_id: str
    document_title: str
    content: str
    score: float


class RAGQueryResponseSchema(BaseModel):
    """RAG查询响应"""
    answer: str
    sources: list[SourceInfoSchema]


# ───────────────────────────────────────────────────────────
# 文档相关 Schema
# ───────────────────────────────────────────────────────────

class DocumentUploadResponseSchema(BaseModel):
    """文档上传响应"""
    id: str
    title: str
    status: str
    chunkCount: int


class DocumentListResponseSchema(BaseModel):
    """文档列表响应"""
    id: str
    title: str
    docType: str
    kbType: str
    kbId: str
    status: str
    chunkCount: int
    createdAt: str


class CreateTextDocumentRequestSchema(BaseModel):
    """创建文本文档请求"""
    kbId: str
    title: str
    content: str
    chunkingStrategy: str = Field(default="none", description="分块策略: none/fixed_size/separator/paragraph")
    chunkSize: int = Field(default=500, description="分块大小（固定大小时使用）")
    chunkOverlap: int = Field(default=50, description="分块重叠大小")
    separator: str = Field(default="", description="分隔符（按分隔符分块时使用）")


class CreateTextDocumentResponseSchema(BaseModel):
    """创建文本文档响应"""
    id: str
    title: str
    docType: str
    kbId: str
    kbType: str
    chunkCount: int
    status: str


# ───────────────────────────────────────────────────────────
# 知识库相关 Schema
# ───────────────────────────────────────────────────────────

class KnowledgeBaseCreateRequestSchema(BaseModel):
    """创建知识库请求"""
    name: str
    description: str = ""
    kb_type: str = Field(default="faq", alias="kbType")

    class Config:
        populate_by_name = True


class KnowledgeBaseUpdateRequestSchema(BaseModel):
    """更新知识库请求"""
    name: str
    description: str = ""


class KnowledgeBaseResponseSchema(BaseModel):
    """知识库响应"""
    id: str
    name: str
    description: str
    kbType: str
    documentCount: int
    createdAt: str
    updatedAt: str


# ───────────────────────────────────────────────────────────
# 通用响应 Schema
# ───────────────────────────────────────────────────────────

class SuccessResponseSchema(BaseModel):
    """通用成功响应"""
    success: bool
    message: str


class HealthCheckResponseSchema(BaseModel):
    """健康检查响应"""
    status: str
    services: dict[str, str]
