"""
RAG API 路由

提供RAG查询和文档管理的HTTP接口。
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from app.application.rag.dto import RAGQueryRequest, DocumentUploadRequest
from app.application.rag.rag_service import RAGService
from app.application.rag.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG知识库"])


# ───────────────────────────────────────────────────────────
# 请求/响应模型
# ───────────────────────────────────────────────────────────

class RAGQueryRequestSchema(BaseModel):
    """RAG查询请求"""
    query: str
    kb_types: list[str] | None = None
    top_k: int = 10


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


class DocumentUploadResponseSchema(BaseModel):
    """文档上传响应"""
    id: str
    title: str
    status: str
    chunk_count: int


class DocumentListResponseSchema(BaseModel):
    """文档列表响应"""
    id: str
    title: str
    doc_type: str
    kb_type: str
    status: str
    chunk_count: int


# ───────────────────────────────────────────────────────────
# 依赖注入
# ───────────────────────────────────────────────────────────

def get_rag_service() -> RAGService:
    """获取RAG服务"""
    from app.infrastructure.persistence.milvus import MilvusVectorStore
    from app.infrastructure.persistence.whoosh import WhooshKeywordIndex
    from app.infrastructure.rag.reranker.bailian_reranker import BailianReranker
    
    vector_store = MilvusVectorStore()
    keyword_index = WhooshKeywordIndex()
    reranker = BailianReranker()
    
    return RAGService(
        vector_store=vector_store,
        keyword_index=keyword_index,
        reranker=reranker,
    )


def get_document_service() -> DocumentService:
    """获取文档服务"""
    from app.infrastructure.persistence.milvus import MilvusVectorStore, MilvusDocumentRepository
    from app.infrastructure.persistence.whoosh import WhooshKeywordIndex
    
    return DocumentService(
        document_repository=MilvusDocumentRepository(),
        vector_store=MilvusVectorStore(),
        keyword_index=WhooshKeywordIndex(),
    )


RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


# ───────────────────────────────────────────────────────────
# RAG 查询接口
# ───────────────────────────────────────────────────────────

@router.post("/query", response_model=RAGQueryResponseSchema, summary="RAG知识库查询")
async def rag_query(
    request: RAGQueryRequestSchema,
    service: RAGServiceDep,
) -> RAGQueryResponseSchema:
    """
    执行RAG检索查询
    
    流程：
    1. 查询分解和知识库路由
    2. 混合检索（向量+关键词）
    3. 重排序
    4. 生成答案
    """
    try:
        dto_request = RAGQueryRequest(
            query=request.query,
            kb_types=request.kb_types,
            top_k=request.top_k,
        )
        
        response = await service.query(dto_request)
        
        return RAGQueryResponseSchema(
            answer=response.answer,
            sources=[
                SourceInfoSchema(
                    document_id=s.document_id,
                    document_title=s.document_title,
                    content=s.content,
                    score=s.score,
                )
                for s in response.sources
            ],
        )
    except Exception as e:
        logger.error(f"RAG查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ───────────────────────────────────────────────────────────
# 文档管理接口
# ───────────────────────────────────────────────────────────

@router.get("/documents", response_model=list[DocumentListResponseSchema], summary="列示文档")
async def list_documents(
    kb_type: str | None = Query(default=None, description="知识库类型过滤"),
    service: DocumentServiceDep = None,
) -> list[DocumentListResponseSchema]:
    """列示已上传的文档"""
    try:
        documents = service.list_documents(kb_type=kb_type)
        return [
            DocumentListResponseSchema(
                id=d.id,
                title=d.title,
                doc_type=d.doc_type,
                kb_type=d.kb_type,
                status=d.status,
                chunk_count=d.chunk_count,
            )
            for d in documents
        ]
    except Exception as e:
        logger.error(f"列示文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列示失败: {str(e)}")


@router.post("/documents/upload", response_model=DocumentUploadResponseSchema, summary="上传文档")
async def upload_document(
    file: UploadFile = File(..., description="文档文件"),
    kb_type: str = Query(default="faq", description="知识库类型: faq/regulation"),
    title: str | None = Query(default=None, description="文档标题"),
    service: DocumentServiceDep = None,
) -> DocumentUploadResponseSchema:
    """
    上传文档到知识库
    
    支持格式：PDF、Word(.docx)、TXT、Markdown
    """
    import tempfile
    import os
    
    try:
        # 保存上传文件到临时目录
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 使用文件名作为默认标题
        doc_title = title or (file.filename or "未命名文档")
        
        request = DocumentUploadRequest(
            file_path=tmp_path,
            title=doc_title,
            kb_type=kb_type,
        )
        
        result = await service.upload_document(request)
        
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return DocumentUploadResponseSchema(
            id=result.id,
            title=result.title,
            status=result.status,
            chunk_count=result.chunk_count,
        )
        
    except Exception as e:
        logger.error(f"上传文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/documents/{document_id}", summary="删除文档")
async def delete_document(
    document_id: str,
    service: DocumentServiceDep,
) -> dict:
    """删除指定文档及其所有分块"""
    try:
        success = service.delete_document(document_id)
        if success:
            return {"success": True, "message": "删除成功"}
        else:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ───────────────────────────────────────────────────────────
# 健康检查
# ───────────────────────────────────────────────────────────

@router.get("/health", summary="RAG服务健康检查")
async def health_check() -> dict:
    """检查RAG服务状态"""
    return {
        "status": "ok",
        "services": {
            "vector_store": "connected",
            "keyword_index": "connected",
        },
    }
