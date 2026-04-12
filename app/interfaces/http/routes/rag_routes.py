"""
RAG API 路由

提供RAG查询和文档管理的HTTP接口。
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from app.application.rag.dto import (
    RAGQueryRequest,
    DocumentUploadRequest,
    CreateKnowledgeBaseRequest,
)
from app.interfaces.http.dependencies import (
    RAGServiceDep,
    AgenticRAGServiceDep,
    DocumentServiceDep,
    KnowledgeBaseServiceDep,
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
    KnowledgeBaseResponseSchema,
    SuccessResponseSchema,
    HealthCheckResponseSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG知识库"])


# ───────────────────────────────────────────────────────────
# 知识库管理接口
# ───────────────────────────────────────────────────────────

@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponseSchema], summary="获取知识库列表")
async def list_knowledge_bases(
    service: KnowledgeBaseServiceDep,
    kb_type: str | None = Query(default=None, description="知识库类型过滤"),
) -> list[KnowledgeBaseResponseSchema]:
    """获取所有知识库"""
    try:
        kbs = service.list_knowledge_bases(kb_type=kb_type)
        return [
            KnowledgeBaseResponseSchema(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                kbType=kb.kb_type,
                documentCount=kb.document_count,
                createdAt=kb.created_at,
                updatedAt=kb.updated_at,
            )
            for kb in kbs
        ]
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponseSchema, summary="创建知识库")
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequestSchema,
    service: KnowledgeBaseServiceDep,
) -> KnowledgeBaseResponseSchema:
    """创建新知识库"""
    try:
        dto_request = CreateKnowledgeBaseRequest(
            name=request.name,
            description=request.description,
            kb_type=request.kb_type,
        )
        kb = service.create_knowledge_base(dto_request)
        return KnowledgeBaseResponseSchema(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            kbType=kb.kb_type,
            documentCount=kb.document_count,
            createdAt=kb.created_at,
            updatedAt=kb.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建知识库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponseSchema, summary="获取知识库详情")
async def get_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseServiceDep,
) -> KnowledgeBaseResponseSchema:
    """获取知识库详情"""
    try:
        kb = service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        return KnowledgeBaseResponseSchema(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            kbType=kb.kb_type,
            documentCount=kb.document_count,
            createdAt=kb.created_at,
            updatedAt=kb.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.put("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponseSchema, summary="更新知识库")
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseCreateRequestSchema,
    service: KnowledgeBaseServiceDep,
) -> KnowledgeBaseResponseSchema:
    """更新知识库"""
    try:
        kb = service.update_knowledge_base(
            id=kb_id,
            name=request.name,
            description=request.description,
        )
        return KnowledgeBaseResponseSchema(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            kbType=kb.kb_type,
            documentCount=kb.document_count,
            createdAt=kb.created_at,
            updatedAt=kb.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新知识库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/knowledge-bases/{kb_id}", response_model=SuccessResponseSchema, summary="删除知识库")
async def delete_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseServiceDep,
) -> SuccessResponseSchema:
    """删除知识库"""
    try:
        success = service.delete_knowledge_base(kb_id)
        if success:
            return SuccessResponseSchema(success=True, message="删除成功")
        else:
            raise HTTPException(status_code=404, detail="知识库不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ───────────────────────────────────────────────────────────
# RAG 查询接口
# ───────────────────────────────────────────────────────────

@router.post("/query", response_model=RAGQueryResponseSchema, summary="RAG知识库查询")
async def rag_query(
    request: RAGQueryRequestSchema,
    service: RAGServiceDep,
    agentic_service: AgenticRAGServiceDep,
) -> RAGQueryResponseSchema:
    """
    执行RAG检索查询

    支持两种模式：
    - 传统RAG：固定流程（查询分解→检索→重排序→生成）
    - Agentic RAG：ReAct模式，Agent自主决策是否检索

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

        # 根据use_agentic参数选择服务模式
        if getattr(request, 'use_agentic', False):
            logger.info("使用Agentic RAG模式")
            response = await agentic_service.query(dto_request)
        else:
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


@router.get("/query/stream", summary="RAG流式查询(SSE)")
async def rag_query_stream(
    query: str = Query(..., description="查询内容"),
    kb_id: str = Query(default="", description="知识库ID"),
    kb_type: str | None = Query(default=None, description="知识库类型"),
    top_k: int = Query(default=10, description="返回结果数量"),
    use_agentic: bool = Query(default=True, description="使用Agentic RAG模式"),
    service: RAGServiceDep = None,
    agentic_service: AgenticRAGServiceDep = None,
):
    """
    执行RAG流式检索查询（SSE）

    以Server-Sent Events方式流式返回：
    1. 处理流程状态（query_decomposition, vector_retrieval等）
    2. 答案片段（chunk）
    3. 来源文档（sources）
    4. 完成事件（complete）或错误事件（error）

    支持Agentic RAG模式，可观察Agent思考过程。
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            dto_request = RAGQueryRequest(
                query=query,
                kb_types=[kb_type] if kb_type else None,
                top_k=top_k,
            )

            # 根据模式选择服务
            stream_service = agentic_service if use_agentic else service

            async for event in stream_service.query_stream(dto_request):
                # 将事件转换为SSE格式
                data = json.dumps({
                    "type": event.type,
                    "data": event.data,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
        except Exception as e:
            logger.error(f"RAG流式查询失败: {e}", exc_info=True)
            error_data = json.dumps({
                "type": "error",
                "data": {"message": f"流式查询失败: {str(e)}"},
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )


# ───────────────────────────────────────────────────────────
# 文档管理接口
# ───────────────────────────────────────────────────────────

@router.get("/documents", response_model=list[DocumentListResponseSchema], summary="列示文档")
async def list_documents(
    kbId: str | None = Query(default=None, description="知识库ID过滤"),
    kb_type: str | None = Query(default=None, description="知识库类型过滤"),
    service: DocumentServiceDep = None,
) -> list[DocumentListResponseSchema]:
    """列示已上传的文档"""
    try:
        logger.info(f"API: 查询文档列表, kbId={kbId}, kb_type={kb_type}")
        documents = service.list_documents(kb_id=kbId, kb_type=kb_type)
        logger.info(f"API: 查询完成, 返回 {len(documents)} 个文档")
        for d in documents:
            logger.info(f"  - {d.id}: {d.title}, kb_id={d.kb_id}")
        return [
            DocumentListResponseSchema(
                id=d.id,
                title=d.title,
                docType=d.doc_type,
                kbType=d.kb_type,
                kbId=d.kb_id,
                status=d.status,
                chunkCount=d.chunk_count,
                createdAt=d.created_at,
            )
            for d in documents
        ]
    except Exception as e:
        logger.error(f"列示文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列示失败: {str(e)}")


@router.post("/documents/upload", response_model=DocumentUploadResponseSchema, summary="上传文档")
async def upload_document(
    file: UploadFile = File(..., description="文档文件"),
    kbId: str = Query(default="", description="知识库ID"),
    kb_type: str = Query(default="faq", description="知识库类型: faq/regulation"),
    title: str | None = Query(default=None, description="文档标题"),
    chunking_strategy: str = Query(default="fixed_size", description="分块策略: none/fixed_size/separator/paragraph"),
    chunk_size: int = Query(default=500, description="分块大小（固定大小时使用）"),
    chunk_overlap: int = Query(default=50, description="分块重叠大小"),
    separator: str = Query(default="", description="分隔符（按分隔符分块时使用）"),
    service: DocumentServiceDep = None,
) -> DocumentUploadResponseSchema:
    """
    上传文档到知识库
    
    支持格式：PDF、Word(.docx)、TXT、Markdown
    
    分块策略：
    - none: 不分块，完整保存
    - fixed_size: 固定大小分块（默认500字符）
    - separator: 按指定分隔符分块
    - paragraph: 按段落分块（双换行）
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
            kb_id=kbId,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator,
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
            chunkCount=result.chunk_count,
        )
        
    except Exception as e:
        logger.error(f"上传文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/documents/text", response_model=CreateTextDocumentResponseSchema, summary="创建文本文档")
async def create_text_document(
    request: CreateTextDocumentRequestSchema,
    service: DocumentServiceDep,
) -> CreateTextDocumentResponseSchema:
    """
    创建纯文本文档
    
    直接在知识库中创建文本内容，无需上传文件。
    
    分块策略：
    - none: 不分块，完整保存（默认）
    - fixed_size: 固定大小分块
    - separator: 按指定分隔符分块
    - paragraph: 按段落分块（双换行）
    """
    import tempfile
    import os
    
    logger.info(f"API: 创建文本文档, kbId={request.kbId}, title={request.title}, strategy={request.chunkingStrategy}")
    
    try:
        # 创建临时文件保存文本内容
        suffix = ".txt"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix, encoding='utf-8') as tmp:
            tmp.write(request.content)
            tmp_path = tmp.name
        
        # 创建上传请求，传递分块策略
        dto_request = DocumentUploadRequest(
            file_path=tmp_path,
            title=request.title,
            kb_type="faq",  # 可以从知识库获取
            kb_id=request.kbId,
            chunking_strategy=request.chunkingStrategy,
            chunk_size=request.chunkSize,
            chunk_overlap=request.chunkOverlap,
            separator=request.separator,
        )
        
        result = await service.upload_document(dto_request)
        logger.info(f"API: 文档创建成功, id={result.id}, kb_id={result.kb_id}, chunks={result.chunk_count}")
        
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return CreateTextDocumentResponseSchema(
            id=result.id,
            title=result.title,
            docType="text",
            kbId=result.kb_id,
            kbType=result.kb_type,
            chunkCount=result.chunk_count,
            status=result.status,
        )
        
    except Exception as e:
        logger.error(f"创建文本文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.delete("/documents/{document_id}", response_model=SuccessResponseSchema, summary="删除文档")
async def delete_document(
    document_id: str,
    service: DocumentServiceDep,
) -> SuccessResponseSchema:
    """删除指定文档及其所有分块"""
    try:
        success = service.delete_document(document_id)
        if success:
            return SuccessResponseSchema(success=True, message="删除成功")
        else:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ───────────────────────────────────────────────────────────
# Agentic RAG 专用接口
# ───────────────────────────────────────────────────────────

@router.post("/query/agentic", response_model=RAGQueryResponseSchema, summary="Agentic RAG查询")
async def agentic_rag_query(
    request: RAGQueryRequestSchema,
    service: AgenticRAGServiceDep,
) -> RAGQueryResponseSchema:
    """
    执行Agentic RAG查询（ReAct模式）

    智能体自主决策：
    - 判断是否需要检索知识库
    - 决定检索策略（知识库类型、关键词）
    - 基于检索结果生成答案或进一步检索

    人设：Coze客服助手，专业、热情、耐心
    """
    try:
        from app.application.rag.dto import RAGQueryRequest

        dto_request = RAGQueryRequest(
            query=request.query,
            kb_types=request.kb_types,
            top_k=request.top_k,
            session_id=request.session_id,
            use_agentic=True,
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
        logger.error(f"Agentic RAG查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/query/agentic/stream", summary="Agentic RAG流式查询(SSE)")
async def agentic_rag_query_stream(
    query: str = Query(..., description="查询内容"),
    kb_type: str | None = Query(default=None, description="知识库类型"),
    top_k: int = Query(default=10, description="返回结果数量"),
    session_id: str | None = Query(default=None, description="会话ID"),
    service: AgenticRAGServiceDep = None,
):
    """
    执行Agentic RAG流式检索查询（SSE）

    以Server-Sent Events方式流式返回：
    1. 开始事件（start）
    2. Agent思考过程（thought）
    3. 工具调用（action）
    4. 答案片段（chunk）
    5. 完成事件（complete）或错误事件（error）
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            from app.application.rag.dto import RAGQueryRequest

            dto_request = RAGQueryRequest(
                query=query,
                kb_types=[kb_type] if kb_type else None,
                top_k=top_k,
                session_id=session_id,
                use_agentic=True,
            )

            async for event in service.query_stream(dto_request):
                # 将事件转换为SSE格式
                data = json.dumps({
                    "type": event.type,
                    "data": event.data,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"

        except Exception as e:
            logger.error(f"Agentic RAG流式查询失败: {e}", exc_info=True)
            error_data = json.dumps({
                "type": "error",
                "data": {"message": f"流式查询失败: {str(e)}"},
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ───────────────────────────────────────────────────────────
# 健康检查
# ───────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthCheckResponseSchema, summary="RAG服务健康检查")
async def health_check() -> HealthCheckResponseSchema:
    """检查RAG服务状态"""
    return HealthCheckResponseSchema(
        status="ok",
        services={
            "vector_store": "connected",
            "keyword_index": "connected",
        },
    )
