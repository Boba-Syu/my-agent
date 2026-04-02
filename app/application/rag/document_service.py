"""
文档应用服务

协调文档领域对象完成用户用例。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.application.rag.dto import DocumentUploadRequest, DocumentDTO
from app.domain.rag.document import Document
from app.domain.rag.document_repository import DocumentRepository
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.keyword_index import KeywordIndex
from app.infrastructure.rag.processors.processor_factory import ProcessorFactory
from app.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class DocumentService:
    """
    文档应用服务
    
    协调文档处理管道：
    1. 文档解析
    2. 文本分块
    3. 向量化
    4. 存储到向量库和关键词索引
    """
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_store: VectorStore,
        keyword_index: KeywordIndex,
        processor_factory: ProcessorFactory | None = None,
    ):
        """
        初始化服务
        
        Args:
            document_repository: 文档仓库
            vector_store: 向量存储
            keyword_index: 关键词索引
            processor_factory: 处理器工厂
        """
        self._repository = document_repository
        self._vector_store = vector_store
        self._keyword_index = keyword_index
        self._processor_factory = processor_factory or ProcessorFactory()
        self._embedding = LLMFactory.create_embedding()
    
    async def upload_document(self, request: DocumentUploadRequest) -> DocumentDTO:
        """
        上传并处理文档
        
        Args:
            request: 上传请求
            
        Returns:
            文档DTO
        """
        logger.info(f"上传文档: {request.file_path}")
        
        # 确定标题
        title = request.title
        if not title:
            import os
            title = os.path.basename(request.file_path)
        
        # 创建文档聚合根
        kb_type = KnowledgeBaseType.from_string(request.kb_type)
        
        # 先提取文本内容
        processor = self._processor_factory.get_processor(request.file_path)
        content, chunks = processor.process(request.file_path)
        
        document = Document(
            id=str(uuid.uuid4()),
            title=title,
            source=request.file_path,
            doc_type=request.file_path.split(".")[-1].lower(),
            kb_type=kb_type,
            content=content,
            metadata=request.metadata or {},
        )
        
        # 标记处理中
        document.mark_processing()
        
        try:
            # 保存分块到聚合根
            document.split_into_chunks(chunks)
            
            # 生成嵌入向量
            texts = [chunk.content for chunk in chunks]
            embeddings = await self._embedding.aembed_documents(texts)
            
            # 存储到向量库
            self._vector_store.add_chunks(
                document_id=document.id,
                chunks=chunks,
                embeddings=embeddings,
                kb_type=kb_type,
            )
            
            # 存储到关键词索引
            self._keyword_index.add_document(
                document_id=document.id,
                chunks=chunks,
                kb_type=kb_type,
            )
            
            # 保存文档元数据
            saved = self._repository.save(document)
            
            logger.info(f"文档处理完成: {saved.id}, {len(chunks)}个分块")
            return DocumentDTO.from_entity(saved)
            
        except Exception as e:
            document.mark_failed(str(e))
            self._repository.save(document)
            logger.error(f"文档处理失败: {e}")
            raise
    
    def list_documents(
        self,
        kb_type: str | None = None,
        limit: int = 100,
    ) -> list[DocumentDTO]:
        """
        列示文档
        
        Args:
            kb_type: 知识库类型过滤
            limit: 返回数量限制
            
        Returns:
            文档DTO列表
        """
        kb_type_enum = KnowledgeBaseType(kb_type) if kb_type else None
        documents = self._repository.list(kb_type=kb_type_enum, limit=limit)
        return [DocumentDTO.from_entity(d) for d in documents]
    
    def get_document(self, document_id: str) -> DocumentDTO | None:
        """
        获取文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档DTO，不存在返回None
        """
        document = self._repository.get(document_id)
        if document:
            return DocumentDTO.from_entity(document)
        return None
    
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否成功删除
        """
        try:
            # 删除向量库数据
            self._vector_store.delete_by_document(document_id)
            
            # 删除关键词索引
            self._keyword_index.delete_document(document_id)
            
            # 删除文档记录
            return self._repository.delete(document_id)
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
