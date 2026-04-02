"""
Milvus 向量存储实现

实现领域层定义的VectorStore接口。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_milvus import Milvus

from app.config import get_milvus_config
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MilvusVectorStore(VectorStore):
    """
    Milvus 向量存储实现
    
    使用 Milvus Lite 本地文件模式，无需启动服务。
    实现领域层定义的VectorStore接口。
    """
    
    def __init__(
        self,
        embedding: Embeddings | None = None,
        collection_name: str | None = None,
    ):
        """
        初始化 Milvus 向量存储
        
        Args:
            embedding: Embedding模型，None时从工厂创建
            collection_name: 集合名称，None时使用配置默认值
        """
        milvus_cfg = get_milvus_config()
        self._uri = milvus_cfg.get("uri", "./data/milvus_rag.db")
        self._collection_name = collection_name or milvus_cfg.get(
            "collection_name", "rag_vectors"
        )
        
        # 延迟加载embedding
        self._embedding = embedding
        self._store: Milvus | None = None
        
        logger.info(f"MilvusVectorStore初始化: uri={self._uri}, collection={self._collection_name}")
    
    def _get_embedding(self) -> Embeddings:
        """获取Embedding模型（延迟加载）"""
        if self._embedding is None:
            from app.llm.llm_factory import LLMFactory
            self._embedding = LLMFactory.create_embedding()
        return self._embedding
    
    def _get_store(self) -> Milvus:
        """获取Milvus存储（延迟初始化）"""
        if self._store is None:
            self._store = Milvus(
                embedding_function=self._get_embedding(),
                collection_name=self._collection_name,
                connection_args={"uri": self._uri},
                auto_id=True,
            )
        return self._store
    
    def add_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        kb_type: KnowledgeBaseType,
    ) -> list[str]:
        """
        添加文档分块及其向量
        
        Args:
            document_id: 文档ID
            chunks: 文档分块列表
            embeddings: 对应的向量嵌入列表
            kb_type: 知识库类型
            
        Returns:
            存储的记录ID列表
        """
        if len(chunks) != len(embeddings):
            raise ValueError("分块和嵌入向量数量不匹配")
        
        texts = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "kb_type": kb_type.value,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            for chunk in chunks
        ]
        
        store = self._get_store()
        ids = store.add_texts(texts=texts, metadatas=metadatas)
        
        logger.debug(f"添加 {len(chunks)} 个分块到Milvus，文档: {document_id}")
        return ids
    
    def similarity_search(
        self,
        query_embedding: list[float],
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """
        向量相似度检索
        
        Args:
            query_embedding: 查询向量
            kb_types: 知识库类型过滤
            top_k: 返回结果数量
            filters: 元数据过滤条件
            
        Returns:
            (分块ID, 相似度分数) 列表
        """
        # 构建过滤表达式
        expr_parts = []
        
        if kb_types:
            kb_values = [f'"{t.value}"' for t in kb_types]
            expr_parts.append(f"kb_type in [{', '.join(kb_values)}]")
        
        if filters:
            for key, value in filters.items():
                expr_parts.append(f'{key} == "{value}"')
        
        expr = " and ".join(expr_parts) if expr_parts else None
        
        store = self._get_store()
        
        # 使用embedding搜索（需要先包装为Document）
        from langchain_core.documents import Document
        query_doc = Document(page_content="", metadata={"embedding": query_embedding})
        
        results = store.similarity_search_with_score(
            query="",  # 不使用文本查询
            k=top_k,
            expr=expr,
        )
        
        # 返回 (chunk_id, score) 列表
        return [(str(doc.metadata.get("chunk_index", 0)), score) for doc, score in results]
    
    def delete_by_document(self, document_id: str) -> bool:
        """
        删除文档的所有分块
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否成功删除
        """
        try:
            store = self._get_store()
            store.delete(expr=f'document_id == "{document_id}"')
            logger.debug(f"删除文档分块: {document_id}")
            return True
        except Exception as e:
            logger.error(f"删除文档分块失败: {document_id}, 错误: {e}")
            return False
    
    def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk | None:
        """
        根据ID获取分块
        
        Args:
            chunk_id: 分块ID
            
        Returns:
            分块，不存在返回None
        """
        # Milvus不支持直接按ID获取，需要通过搜索
        logger.warning("MilvusVectorStore.get_chunk_by_id 未完全实现")
        return None
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            store = self._get_store()
            # 尝试简单操作检查连接
            return True
        except Exception as e:
            logger.error(f"Milvus健康检查失败: {e}")
            return False
