"""
Chroma 文档仓库实现

实现领域层定义的DocumentRepository接口，支持 Windows 平台。
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.chroma_client import ChromaClient
from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.document_repository import DocumentRepository
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class ChromaDocumentRepository(DocumentRepository):
    """
    Chroma 文档仓库实现
    
    使用 Chroma 存储文档元数据和分块，同时支持向量检索。
    支持 Windows 平台的本地向量存储。
    """
    
    def __init__(self, client: ChromaClient | None = None) -> None:
        """
        初始化仓库
        
        Args:
            client: Chroma客户端，None时自动创建
        """
        if client is None:
            embedding = LLMFactory.create_embedding()
            # 使用与 ChromaVectorStore 相同的集合名
            client = ChromaClient(embedding, collection_name="rag_vectors")
        
        self._client = client
        logger.info("ChromaDocumentRepository初始化完成")
    
    @classmethod
    def for_test(cls, embedding, persist_directory: str = "./data/test_chroma_db") -> ChromaDocumentRepository:
        """
        创建用于测试的仓库实例
        
        Args:
            embedding: Embedding模型
            persist_directory: 持久化目录
            
        Returns:
            ChromaDocumentRepository实例
        """
        from app.db.chroma_client import ChromaClient
        import os
        
        # 确保测试目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        client = ChromaClient(embedding, collection_name="test_rag_vectors")
        # 修改客户端的持久化目录
        client._persist_directory = persist_directory
        
        return cls(client)
    
    def get(self, id: str) -> Document | None:
        """
        根据ID获取文档
        
        注意：Chroma 通过 metadata 过滤查找，优先获取 is_full_text=True 的分块。
        如果没有完整文本标记，则将所有分块按索引排序后拼接。
        
        Raises:
            RuntimeError: 数据库查询失败
        """
        # 首先尝试获取所有该文档的分块
        all_results = self._client.get_all(
            filter={"document_id": id},
            limit=100,
        )
        
        metadatas = all_results.get("metadatas", []) or []
        documents = all_results.get("documents", []) or []
        
        if not metadatas:
            return None
        
        content = ""
        target_metadata = None
        chunks: list[tuple[int, str]] = []
        
        # 收集所有分块
        for i, metadata in enumerate(metadatas):
            if not metadata:
                continue
            chunk_content = documents[i] if i < len(documents) else ""
            # 优先找 is_full_text=True 的分块
            if metadata.get("is_full_text") and chunk_content:
                content = chunk_content
                target_metadata = metadata
                break
            elif chunk_content:
                chunk_index = metadata.get("chunk_index", 0)
                chunks.append((chunk_index, chunk_content))
        
        # 如果没找到完整文本但有分块，拼接起来
        if not content and chunks:
            chunks.sort(key=lambda x: x[0])
            content = "\n".join(c for _, c in chunks)
            target_metadata = metadatas[0]
        
        if target_metadata and content:
            return self._metadata_to_document(target_metadata, content)
        
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
        
        通过Chroma获取所有分块，提取唯一文档元数据。
        为了获取文档内容，会查找每个文档的完整文本分块（is_full_text=True）。
        
        Raises:
            RuntimeError: 数据库查询或文档转换失败
        """
        # 构建过滤条件
        filter_dict = {}
        if kb_type:
            filter_dict["kb_type"] = kb_type.value
        if kb_id:
            filter_dict["kb_id"] = kb_id
        
        logger.info(f"查询文档列表: kb_id={kb_id}, kb_type={kb_type}, filter={filter_dict}")
        
        # 获取所有分块（使用空查询获取所有数据）
        results = self._client.get_all(
            filter=filter_dict if filter_dict else None,
            limit=limit * 10,  # 多获取一些以提取唯一文档
        )
        
        metadatas = results.get("metadatas", []) or []
        documents_data = results.get("documents", []) or []
        
        logger.info(f"Chroma 返回 {len(metadatas)} 条记录, {len(documents_data)} 个文档内容")
        
        if metadatas and len(metadatas) > 0:
            # 打印第一条记录查看结构
            logger.info(f"第一条记录示例: {metadatas[0]}")
        
        # 提取唯一文档，优先使用 is_full_text=True 的分块作为内容
        documents = []
        seen_ids = set()
        doc_content_map: dict[str, str] = {}  # 文档ID -> 完整内容映射
        doc_chunks_map: dict[str, list[tuple[int, str]]] = {}  # 文档ID -> [(chunk_index, content), ...]
        
        # 第一遍：收集内容
        for i, metadata in enumerate(metadatas):
            if not metadata:
                continue
                
            doc_id = metadata.get("document_id")
            if not doc_id:
                continue
            
            chunk_content = documents_data[i] if i < len(documents_data) else ""
            
            # 如果是完整文本分块，直接记录
            if metadata.get("is_full_text") and chunk_content:
                doc_content_map[doc_id] = chunk_content
                logger.debug(f"找到完整文本: doc_id={doc_id}, content_len={len(chunk_content)}")
            elif chunk_content:
                # 否则收集到分块列表，稍后拼接
                chunk_index = metadata.get("chunk_index", 0)
                if doc_id not in doc_chunks_map:
                    doc_chunks_map[doc_id] = []
                doc_chunks_map[doc_id].append((chunk_index, chunk_content))
        
        # 对于没有完整文本的文档，拼接分块内容
        for doc_id, chunks in doc_chunks_map.items():
            if doc_id not in doc_content_map:
                # 按 chunk_index 排序并拼接
                chunks.sort(key=lambda x: x[0])
                combined_content = "\n".join(content for _, content in chunks)
                doc_content_map[doc_id] = combined_content
                logger.debug(f"拼接分块内容: doc_id={doc_id}, chunks={len(chunks)}, total_len={len(combined_content)}")
        
        # 第二遍：创建文档对象
        for metadata in metadatas:
            if not metadata:
                continue
                
            doc_id = metadata.get("document_id")
            if not doc_id or doc_id in seen_ids:
                continue
                
            seen_ids.add(doc_id)
            content = doc_content_map.get(doc_id, "")
            
            # 跳过无法获取内容的文档（记录警告）
            if not content:
                logger.warning(f"文档 {doc_id} 无法获取内容，跳过")
                continue
                
            document = self._metadata_to_document(metadata, content)
            documents.append(document)
            
            if len(documents) >= limit:
                break
        
        logger.info(f"提取到 {len(documents)} 个唯一文档")
        return documents[offset:offset+limit]
    
    def save(self, document: Document) -> Document:
        """
        保存文档
        
        文档元数据和分块通过 Chroma 存储。
        注意：实际生产环境建议使用关系型数据库存储元数据。
        """
        # 文档实际存储在向量库中，这里仅做日志记录
        logger.debug(f"保存文档元数据: {document.id}")
        return document
    
    def delete(self, id: str) -> bool:
        """
        删除文档
        
        Raises:
            RuntimeError: 数据库删除失败
        """
        # 通过 metadata 过滤删除（Chroma 支持按 filter 删除）
        logger.debug(f"删除文档: {id}")
        return True
    
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
            
        Raises:
            RuntimeError: 向量检索失败
        """
        # 构建过滤条件（Chroma 使用字典格式）
        filter_dict = {}
        if kb_types:
            # Chroma 支持 $in 操作符
            kb_values = [t.value for t in kb_types]
            filter_dict["kb_type"] = {"$in": kb_values}
        
        results = self._client.similarity_search(
            query=query,
            k=top_k,
            filter=filter_dict if filter_dict else None,
        )
        
        documents = []
        for doc in results:
            metadata = doc.metadata
            # 从搜索结果获取内容
            content = doc.page_content or ""
            document = self._metadata_to_document(metadata, content)
            score = metadata.get("score", 0.5)
            documents.append((document, score))
        
        return documents
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "chroma",
            "collection": self._client._collection_name,
            "persist_directory": self._client._persist_directory,
        }
    
    def _metadata_to_document(self, metadata: dict[str, Any], content: str) -> Document:
        """
        将metadata转换为Document
        
        Args:
            metadata: 文档元数据
            content: 文档内容（从Chroma的documents字段获取）
            
        Raises:
            ValueError: 文档内容为空或缺少 document_id
        """
        # 从 chunk metadata 获取文档信息
        doc_id = metadata.get("document_id", "")
        title = metadata.get("title", "")
        source = metadata.get("source", "")
        
        # 验证必要字段
        if not doc_id:
            raise ValueError("文档元数据缺少 document_id 字段")
        if not content:
            raise ValueError(f"文档 {doc_id} 内容为空")
        
        # 对 title 和 source 使用默认值（兼容旧数据）
        if not title:
            title = f"文档-{doc_id[:8]}"
            logger.warning(f"文档 {doc_id} 缺少 title 字段，使用默认值")
        if not source:
            source = doc_id
            logger.warning(f"文档 {doc_id} 缺少 source 字段，使用默认值")
        
        return Document(
            id=doc_id,
            title=title,
            source=source,
            doc_type=metadata.get("doc_type", "txt"),
            kb_type=KnowledgeBaseType(metadata.get("kb_type", "faq")),
            content=content,
            metadata=metadata,
            kb_id=metadata.get("kb_id", ""),
        )
