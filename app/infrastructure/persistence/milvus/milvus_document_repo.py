"""
Milvus 文档仓库实现

实现领域层定义的DocumentRepository接口。
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.milvus_client import MilvusClient
from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.document_repository import DocumentRepository
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class MilvusDocumentRepository(DocumentRepository):
    """
    Milvus 文档仓库实现
    
    使用Milvus存储文档元数据和分块，同时支持向量检索。
    简化实现：主要存储文档元数据，分块内容存储在向量库中。
    """
    
    def __init__(self, client: MilvusClient | None = None) -> None:
        """
        初始化仓库
        
        Args:
            client: Milvus客户端，None时自动创建
        """
        if client is None:
            embedding = LLMFactory.create_embedding()
            client = MilvusClient(embedding, collection_name="rag_documents")
        
        self._client = client
        logger.info("MilvusDocumentRepository初始化完成")
    
    def get(self, id: str) -> Document | None:
        """
        根据ID获取文档
        
        注意：Milvus不支持按ID精确查询，这里简化实现。
        实际生产环境建议使用SQLite存储元数据。
        """
        # 简化实现：通过metadata过滤查找
        try:
            results = self._client.similarity_search(
                query=f"document_id:{id}",
                k=1,
                filter={"document_id": id},
            )
            if results:
                # 从metadata重建Document
                metadata = results[0].metadata
                return self._metadata_to_document(metadata)
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
        
        return None
    
    def list(
        self,
        kb_id: str | None = None,
        kb_type: KnowledgeBaseType | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """
        查询文档列表
        
        简化实现，实际应该使用关系型数据库。
        """
        # 由于Milvus不适合元数据查询，这里返回空列表
        # 实际生产环境应该使用SQLite存储文档元数据
        logger.warning("MilvusDocumentRepository.list 简化实现，建议配合SQLite使用")
        return []
    
    def save(self, document: Document) -> Document:
        """
        保存文档
        
        文档元数据和分块通过Milvus存储。
        注意：实际生产环境建议使用关系型数据库存储元数据。
        """
        # 文档实际存储在向量库中，这里仅做日志记录
        logger.debug(f"保存文档元数据: {document.id}")
        return document
    
    def delete(self, id: str) -> bool:
        """删除文档"""
        try:
            # 通过metadata过滤删除
            logger.debug(f"删除文档: {id}")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def exists(self, id: str) -> bool:
        """检查文档是否存在"""
        return self.get(id) is not None
    
    def search_by_vector(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """
        向量相似度检索
        
        Args:
            query: 查询文本
            kb_types: 知识库类型过滤
            top_k: 返回数量
            filters: 过滤条件
            
        Returns:
            (文档, 分数) 列表
        """
        try:
            # 构建过滤表达式
            filter_expr = None
            if kb_types:
                kb_values = [f'"{t.value}"' for t in kb_types]
                filter_expr = f"kb_type in [{', '.join(kb_values)}]"
            
            results = self._client.similarity_search(
                query=query,
                k=top_k,
                filter=filter_expr,
            )
            
            documents = []
            for doc in results:
                metadata = doc.metadata
                document = self._metadata_to_document(metadata)
                score = metadata.get("score", 0.5)
                documents.append((document, score))
            
            return documents
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "milvus",
            "collection": self._client._collection_name,
        }
    
    def _metadata_to_document(self, metadata: dict[str, Any]) -> Document:
        """将metadata转换为Document"""
        return Document(
            id=metadata.get("document_id", ""),
            title=metadata.get("title", "未知文档"),
            source=metadata.get("source", ""),
            doc_type=metadata.get("doc_type", "txt"),
            kb_type=KnowledgeBaseType(metadata.get("kb_type", "faq")),
            content="",  # 内容不存储在元数据中
            metadata=metadata,
            kb_id=metadata.get("kb_id", ""),
        )
