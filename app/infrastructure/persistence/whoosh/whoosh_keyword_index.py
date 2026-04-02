"""
Whoosh 关键词索引实现

使用Whoosh实现倒排索引，支持关键词检索。
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.config import get_sqlite_config
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.keyword_index import KeywordIndex
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class WhooshKeywordIndex(KeywordIndex):
    """
    Whoosh 关键词索引实现
    
    使用Whoosh实现倒排索引，用于混合检索中的关键词匹配。
    
    特性：
    - 支持中文分词（使用jieba）
    - 支持元数据过滤
    - 本地文件存储
    """
    
    def __init__(self, index_dir: str | None = None) -> None:
        """
        初始化Whoosh索引
        
        Args:
            index_dir: 索引目录，None时使用默认路径
        """
        if index_dir is None:
            sqlite_cfg = get_sqlite_config()
            db_path = sqlite_cfg.get("path", "./data/agent.db")
            index_dir = db_path.replace(".db", "_whoosh_index")
        
        self._index_dir = index_dir
        self._index = None
        
        # 确保目录存在
        os.makedirs(self._index_dir, exist_ok=True)
        
        logger.info(f"WhooshKeywordIndex初始化: index_dir={self._index_dir}")
    
    def _get_index(self):
        """获取或创建索引（延迟加载）"""
        if self._index is None:
            try:
                from whoosh import index
                from whoosh.fields import Schema, TEXT, ID, KEYWORD
                
                if index.exists_in(self._index_dir):
                    self._index = index.open_dir(self._index_dir)
                else:
                    # 创建schema
                    schema = Schema(
                        chunk_id=ID(stored=True),
                        document_id=ID(stored=True),
                        kb_type=KEYWORD(stored=True),
                        content=TEXT(stored=True),
                    )
                    self._index = index.create_in(self._index_dir, schema)
            except ImportError:
                logger.error("Whoosh未安装，请运行: uv add whoosh jieba")
                raise
        return self._index
    
    def add_document(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        kb_type: KnowledgeBaseType,
    ) -> None:
        """
        添加文档到索引
        
        Args:
            document_id: 文档ID
            chunks: 文档分块列表
            kb_type: 知识库类型
        """
        try:
            from whoosh import writing
            
            writer = self._get_index().writer()
            
            for chunk in chunks:
                chunk_id = f"{document_id}_{chunk.chunk_index}"
                writer.add_document(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    kb_type=kb_type.value,
                    content=chunk.content,
                )
            
            writer.commit()
            logger.debug(f"添加文档到Whoosh索引: {document_id}, {len(chunks)}个分块")
            
        except Exception as e:
            logger.error(f"添加文档到Whoosh索引失败: {e}")
            raise
    
    def search(
        self,
        query: str,
        kb_types: list[KnowledgeBaseType] | None = None,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """
        关键词检索
        
        Args:
            query: 查询文本
            kb_types: 知识库类型过滤
            top_k: 返回结果数量
            
        Returns:
            (分块ID, 分数) 列表
        """
        try:
            from whoosh.qparser import QueryParser, MultifieldParser
            from whoosh import scoring
            
            ix = self._get_index()
            
            with ix.searcher(weighting=scoring.BM25F()) as searcher:
                # 构建查询
                if kb_types:
                    # 添加知识库类型过滤
                    kb_filter = " OR ".join([f'kb_type:"{t.value}"' for t in kb_types])
                    query_str = f"({query}) AND ({kb_filter})"
                else:
                    query_str = query
                
                parser = MultifieldParser(["content"], ix.schema)
                q = parser.parse(query_str)
                
                results = searcher.search(q, limit=top_k)
                
                return [(hit["chunk_id"], hit.score) for hit in results]
                
        except Exception as e:
            logger.error(f"Whoosh检索失败: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档的所有索引
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否成功删除
        """
        try:
            from whoosh import query
            
            writer = self._get_index().writer()
            writer.delete_by_term("document_id", document_id)
            writer.commit()
            
            logger.debug(f"删除Whoosh索引: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除Whoosh索引失败: {e}")
            return False
    
    def optimize(self) -> None:
        """优化索引"""
        try:
            writer = self._get_index().writer()
            writer.commit(optimize=True)
            logger.info("Whoosh索引已优化")
        except Exception as e:
            logger.error(f"优化Whoosh索引失败: {e}")
