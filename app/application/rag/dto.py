"""
RAG 应用层 DTO

数据传输对象，用于应用层与接口层之间的数据交换。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.rag.document import Document
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.search_result import RankedResult


@dataclass(frozen=True)
class RAGQueryRequest:
    """RAG查询请求 DTO"""

    query: str
    """用户查询"""

    kb_types: list[str] | None = None
    """指定检索的知识库类型，None表示自动判断"""

    top_k: int = 10
    """返回结果数量"""

    use_rerank: bool = True
    """是否使用重排序"""

    model: str | None = None
    """使用模型，None时使用默认配置"""

    session_id: str | None = None
    """会话ID，用于保持上下文"""

    use_agentic: bool = False
    """是否使用Agentic RAG模式"""


@dataclass(frozen=True)
class SourceInfo:
    """来源信息 DTO"""
    
    document_id: str
    """文档ID"""
    
    document_title: str
    """文档标题"""
    
    content: str
    """引用内容"""
    
    score: float
    """相关度分数"""


@dataclass(frozen=True)
class RAGQueryResponse:
    """RAG查询响应 DTO"""
    
    answer: str
    """生成的答案"""
    
    sources: list[SourceInfo]
    """答案来源"""
    
    sub_queries: list[str]
    """分解的子查询"""
    
    @classmethod
    def from_ranked_results(
        cls,
        answer: str,
        results: list[RankedResult],
    ) -> RAGQueryResponse:
        """从重排序结果创建响应"""
        sources = []
        for r in results:
            sources.append(SourceInfo(
                document_id=r.search_result.document_id or "unknown",
                document_title=r.search_result.document_title or "未知文档",
                content=r.content[:500] + "..." if len(r.content) > 500 else r.content,
                score=r.rerank_score,
            ))
        
        return cls(
            answer=answer,
            sources=sources,
            sub_queries=[],
        )


@dataclass(frozen=True)
class DocumentUploadRequest:
    """文档上传请求 DTO"""
    
    file_path: str
    """文件路径"""
    
    title: str | None = None
    """文档标题，None时使用文件名"""
    
    kb_type: str = "faq"
    """知识库类型"""
    
    kb_id: str = ""
    """知识库ID"""
    
    metadata: dict[str, Any] | None = None
    """额外元数据"""
    
    chunking_strategy: str = "fixed_size"
    """分块策略: none/fixed_size/separator/paragraph"""
    
    chunk_size: int = 500
    """分块大小（固定大小时使用）"""
    
    chunk_overlap: int = 50
    """分块重叠大小"""
    
    separator: str = ""
    """分隔符（按分隔符分块时使用）"""


@dataclass(frozen=True)
class DocumentDTO:
    """文档数据 DTO"""
    
    id: str
    """文档ID"""
    
    title: str
    """标题"""
    
    source: str
    """来源"""
    
    doc_type: str
    """文档类型"""
    
    kb_type: str
    """知识库类型"""
    
    status: str
    """处理状态"""
    
    chunk_count: int
    """分块数量"""
    
    char_count: int
    """字符数"""
    
    kb_id: str = ""
    """知识库ID"""
    
    created_at: str = ""
    """创建时间"""
    
    updated_at: str = ""
    """更新时间"""
    
    @classmethod
    def from_entity(cls, entity: Document) -> DocumentDTO:
        """从领域实体创建 DTO"""
        created_at = getattr(entity, 'created_at', None)
        updated_at = getattr(entity, 'updated_at', None)
        # 使用属性访问器获取 kb_id（不是 _kb_id）
        kb_id = entity.kb_id if hasattr(entity, 'kb_id') else ''
        return cls(
            id=entity.id or "",
            title=entity.title,
            source=entity.source,
            doc_type=entity.doc_type,
            kb_type=entity.kb_type.value,
            kb_id=kb_id,
            status=entity.status.value,
            chunk_count=entity.chunk_count,
            char_count=entity.char_count,
            created_at=created_at.isoformat() if created_at else "",
            updated_at=updated_at.isoformat() if updated_at else "",
        )


@dataclass(frozen=True)
class KnowledgeBaseDTO:
    """知识库数据 DTO"""
    
    id: str
    """知识库ID"""
    
    name: str
    """名称"""
    
    description: str
    """描述"""
    
    kb_type: str
    """类型"""
    
    document_count: int
    """文档数量"""
    
    created_at: str
    """创建时间"""
    
    updated_at: str
    """更新时间"""
    
    @classmethod
    def from_entity(cls, entity: Any) -> KnowledgeBaseDTO:
        """从领域实体创建 DTO"""
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            kb_type=entity.kb_type.value,
            document_count=entity.document_count,
            created_at=entity.created_at.isoformat() if entity.created_at else "",
            updated_at=entity.updated_at.isoformat() if entity.updated_at else "",
        )


@dataclass(frozen=True)
class CreateKnowledgeBaseRequest:
    """创建知识库请求 DTO"""
    
    name: str
    """名称"""
    
    description: str = ""
    """描述"""
    
    kb_type: str = "faq"
    """类型"""


@dataclass(frozen=True)
class CreateTextDocumentRequest:
    """创建文本文档请求 DTO"""
    
    kb_id: str
    """知识库ID"""
    
    title: str
    """标题"""
    
    content: str
    """内容"""
    
    kb_type: str = "faq"
    """知识库类型"""


@dataclass(frozen=True)
class RagProcessStepDTO:
    """RAG处理步骤 DTO"""
    
    status: str
    """状态"""
    
    start_time: str | None = None
    """开始时间"""
    
    end_time: str | None = None
    """结束时间"""
    
    details: dict[str, Any] | None = None
    """详情"""


@dataclass(frozen=True)
class RagProcessDTO:
    """RAG处理流程 DTO"""
    
    query_decomposition: dict[str, Any]
    """查询分解"""
    
    vector_retrieval: dict[str, Any]
    """向量检索"""
    
    keyword_retrieval: dict[str, Any]
    """关键词检索"""
    
    reranking: dict[str, Any]
    """重排序"""
    
    answer_generation: dict[str, Any]
    """答案生成"""


@dataclass(frozen=True)
class RagStreamEventDTO:
    """RAG流式事件 DTO"""
    
    type: str
    """事件类型: process, chunk, sources, complete, error"""
    
    data: Any
    """事件数据"""
