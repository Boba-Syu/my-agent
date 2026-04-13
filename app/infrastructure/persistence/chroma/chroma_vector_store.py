"""
Chroma 向量存储实现

实现领域层定义的VectorStore接口，支持 Windows 平台。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma

from app.config import get_config
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStore):
    """
    Chroma 向量存储实现
    
    使用 Chroma 本地文件模式，支持 Windows 平台。
    实现领域层定义的VectorStore接口。
    """
    
    def __init__(
        self,
        embedding: Embeddings | None = None,
        collection_name: str | None = None,
    ):
        """
        初始化 Chroma 向量存储
        
        Args:
            embedding: Embedding模型，None时从工厂创建
            collection_name: 集合名称，None时使用配置默认值
        """
        config = get_config()
        chroma_cfg = config.get("chroma", {})
        self._persist_directory = chroma_cfg.get("persist_directory", "./data/chroma_db")
        self._collection_name = collection_name or chroma_cfg.get(
            "collection_name", "rag_vectors"
        )
        
        # 延迟加载embedding
        self._embedding = embedding
        self._store: Chroma | None = None
        
        logger.info(f"ChromaVectorStore初始化: persist_directory={self._persist_directory}, collection={self._collection_name}")
    
    def _get_embedding(self) -> Embeddings:
        """获取Embedding模型（延迟加载）"""
        if self._embedding is None:
            from app.llm.llm_factory import LLMFactory
            self._embedding = LLMFactory.create_embedding()
        return self._embedding
    
    def _get_store(self) -> Chroma:
        """获取Chroma存储（延迟初始化）"""
        if self._store is None:
            self._store = Chroma(
                embedding_function=self._get_embedding(),
                collection_name=self._collection_name,
                persist_directory=self._persist_directory,
            )
        return self._store
    
    def add_chunks(
        self,
        document_id: str,
        title: str,
        source: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        kb_type: KnowledgeBaseType,
        kb_id: str = "",
    ) -> list[str]:
        """
        添加文档分块及其向量
        
        Args:
            document_id: 文档ID
            title: 文档标题
            source: 文档来源
            chunks: 文档分块列表
            embeddings: 对应的向量嵌入列表
            kb_type: 知识库类型
            kb_id: 知识库ID
            
        Returns:
            存储的记录ID列表
        """
        if len(chunks) != len(embeddings):
            raise ValueError("分块和嵌入向量数量不匹配")
        
        texts = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "title": title,
                "source": source,
                "kb_type": kb_type.value,
                "kb_id": kb_id,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            for chunk in chunks
        ]
        
        store = self._get_store()
        ids = store.add_texts(texts=texts, metadatas=metadatas)
        
        logger.debug(f"添加 {len(chunks)} 个分块到Chroma，文档: {document_id}")
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
            (Chroma记录ID, 相似度分数) 列表
        """
        # 构建过滤条件（Chroma 使用字典格式）
        filter_dict: dict[str, Any] = {}

        if kb_types:
            kb_values = [t.value for t in kb_types]
            filter_dict["kb_type"] = {"$in": kb_values}

        if filters:
            filter_dict.update(filters)

        store = self._get_store()

        # 使用 Chroma 底层 API 进行向量搜索
        # 通过 _collection 直接访问 chromadb 的 query 方法
        try:
            where_filter = filter_dict if filter_dict else None
            results = store._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["metadatas", "distances"],
            )

            # 返回 (chroma_id, score) 列表
            # 注意：Chroma 返回的是距离，需要转换为相似度分数
            chunks = []
            if results and results["ids"] and results["ids"][0]:
                for chroma_id, distance in zip(results["ids"][0], results["distances"][0]):
                    # 将距离转换为相似度分数（Chroma使用余弦距离的变种）
                    # 距离越小表示越相似
                    score = 1.0 - min(distance, 1.0)
                    chunks.append((chroma_id, score))
            return chunks

        except Exception as e:
            logger.error(f"向量检索失败: {e}", exc_info=True)
            return []
    
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
            # Chroma 使用 where 参数过滤
            store.delete(where={"document_id": document_id})
            logger.debug(f"删除文档分块: {document_id}")
            return True
        except Exception as e:
            logger.error(f"删除文档分块失败: {document_id}, 错误: {e}")
            return False
    
    def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk | None:
        """
        根据ID获取分块

        Args:
            chunk_id: Chroma记录ID

        Returns:
            分块，不存在返回None
        """
        # 使用 Chroma ID 直接获取
        try:
            store = self._get_store()
            results = store.get(ids=[chunk_id])
            if results and results["documents"] and len(results["documents"]) > 0:
                metadata = results["metadatas"][0] if results["metadatas"] else {}
                return DocumentChunk(
                    content=results["documents"][0],
                    chunk_index=metadata.get("chunk_index", 0),
                    metadata=metadata,
                )
        except Exception as e:
            logger.error(f"获取分块失败: {chunk_id}, 错误: {e}")
        return None
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            store = self._get_store()
            # 尝试简单操作检查连接
            return True
        except Exception as e:
            logger.error(f"Chroma健康检查失败: {e}")
            return False
