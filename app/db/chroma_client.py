"""
Chroma 本地向量数据库客户端模块
基于 langchain-chroma，使用本地文件模式（无需启动服务）
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.config import get_config

logger = logging.getLogger(__name__)


class ChromaClient:
    """
    Chroma 本地向量数据库客户端

    使用本地文件模式，无需安装和启动 Chroma 服务，
    直接将向量数据持久化到本地目录。

    使用示例:
        from app.llm.llm_factory import LLMFactory

        embedding = LLMFactory.create_embedding()
        client = ChromaClient(embedding)

        # 添加文本
        ids = client.add_texts(["你好，世界", "AI 很有趣"], [{"source": "demo"}] * 2)

        # 相似度检索
        docs = client.similarity_search("人工智能", k=3)
        for doc in docs:
            print(doc.page_content, doc.metadata)
    """

    def __init__(self, embedding: Embeddings, collection_name: str | None = None) -> None:
        """
        初始化 Chroma 客户端

        Args:
            embedding:       LangChain Embeddings 实例（用于向量化文本）
            collection_name: 集合名称，为 None 时使用配置文件中的默认值
        """
        config = get_config()
        # 使用 Chroma 本地存储路径
        self._persist_directory = config.get("chroma", {}).get("persist_directory", "./data/chroma_db")
        self._collection_name = collection_name or config.get("chroma", {}).get(
            "collection_name", "agent_vectors"
        )
        self._embedding = embedding

        # 初始化 Chroma 向量存储（本地文件模式）
        self._store = Chroma(
            embedding_function=embedding,
            collection_name=self._collection_name,
            persist_directory=self._persist_directory,
        )
        logger.info(
            f"Chroma 本地存储已连接：persist_directory={self._persist_directory}, collection={self._collection_name}"
        )

    def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
    ) -> list[str]:
        """
        向集合中添加文本（自动向量化并存储）

        Args:
            texts:     文本列表
            metadatas: 每条文本对应的元数据字典列表（可选）

        Returns:
            插入记录的 ID 列表
        """
        ids = self._store.add_texts(texts=texts, metadatas=metadatas)
        logger.debug(f"添加 {len(texts)} 条文本到 Chroma，集合：{self._collection_name}")
        return ids

    def add_documents(self, documents: list[Document]) -> list[str]:
        """
        向集合中添加 LangChain Document 对象

        Args:
            documents: Document 列表

        Returns:
            插入记录的 ID 列表
        """
        ids = self._store.add_documents(documents)
        logger.debug(f"添加 {len(documents)} 条 Document 到 Chroma")
        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """
        基于语义相似度检索最相关的文档

        Args:
            query:  查询文本
            k:      返回结果数量
            filter: 元数据过滤条件（可选）

        Returns:
            相似度最高的 Document 列表
        """
        kwargs: dict[str, Any] = {}
        if filter:
            kwargs["filter"] = filter

        results = self._store.similarity_search(query=query, k=k, **kwargs)
        logger.debug(f"向量检索：query='{query}', k={k}, 命中={len(results)}")
        return results

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> list[tuple[Document, float]]:
        """
        带相似度分数的语义检索

        Args:
            query: 查询文本
            k:     返回结果数量

        Returns:
            [(Document, score), ...] 按分数降序
        """
        return self._store.similarity_search_with_score(query=query, k=k)

    def as_retriever(self, search_kwargs: dict | None = None):
        """
        将 Chroma 存储转换为 LangChain Retriever，可直接用于 RAG 链

        Args:
            search_kwargs: 检索参数，如 {"k": 3}

        Returns:
            VectorStoreRetriever 实例
        """
        return self._store.as_retriever(search_kwargs=search_kwargs or {"k": 4})
    
    def delete_collection(self) -> bool:
        """
        删除当前集合
        
        Returns:
            是否删除成功
        """
        try:
            self._store.delete_collection()
            logger.info(f"Chroma 集合已删除：{self._collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除 Chroma 集合失败: {e}")
            return False
    
    def get_all(
        self,
        filter: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """
        获取集合中的所有数据
        
        Args:
            filter: 元数据过滤条件（可选）
            limit: 返回结果数量限制
            
        Returns:
            包含 ids, documents, metadatas 的字典
        """
        try:
            kwargs: dict[str, Any] = {
                "limit": limit,
                "include": ["metadatas", "documents"],
            }
            if filter:
                kwargs["where"] = filter
            
            results = self._store.get(**kwargs)
            logger.info(f"Chroma get_all: filter={filter}, limit={limit}, 返回={len(results.get('ids', []))} 条")
            return results
        except Exception as e:
            logger.error(f"获取所有数据失败: {e}", exc_info=True)
            return {"ids": [], "documents": [], "metadatas": []}
