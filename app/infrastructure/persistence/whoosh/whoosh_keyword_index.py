"""
Whoosh 关键词索引实现

使用Whoosh实现倒排索引，支持关键词检索。
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from app.config import get_sqlite_config
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.keyword_index import KeywordIndex
from app.domain.rag.knowledge_base_type import KnowledgeBaseType

logger = logging.getLogger(__name__)


class ChineseAnalyzer:
    """
    中文分词分析器

    使用jieba进行中文分词，兼容Whoosh的分析器接口。
    """

    def __init__(self):
        """初始化中文分词器"""
        # 不存储jieba模块引用，避免pickle问题
        self._initialized = False

    def _ensure_initialized(self):
        """延迟初始化jieba"""
        if not self._initialized:
            try:
                import jieba
                import sys
                # 启用并行分词（仅支持POSIX系统，Windows不支持）
                if sys.platform != 'win32':
                    jieba.enable_parallel()
                    logger.debug("已启用jieba并行分词模式")
                self._initialized = True
            except ImportError:
                logger.error("jieba未安装，请运行: uv add jieba")
                raise

    def __call__(self, value, **kwargs):
        """
        对文本进行分词

        Args:
            value: 待分词的文本
            **kwargs: Whoosh可能传递的额外参数（如mode）

        Yields:
            分词后的token
        """
        from whoosh.analysis import Token
        import jieba

        self._ensure_initialized()

        # 使用jieba进行中文分词
        words = jieba.cut(value)

        # 过滤掉空白字符和标点符号
        pos = 0
        for word in words:
            word = word.strip()
            if word and not re.match(r'^[\s\u3000-\u303f\uff00-\uffef]+$', word):
                token = Token()
                token.text = word
                token.pos = pos
                token.boost = 1.0
                token.stopped = False
                yield token
                pos += 1

    def __getstate__(self):
        """支持pickle序列化"""
        return {}

    def __setstate__(self, state):
        """支持pickle反序列化"""
        self._initialized = False


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
                    # 创建中文分词器
                    chinese_analyzer = ChineseAnalyzer()
                    
                    # 创建schema，content字段使用中文分词器
                    schema = Schema(
                        chunk_id=ID(stored=True),
                        document_id=ID(stored=True),
                        kb_type=KEYWORD(stored=True),
                        content=TEXT(stored=True, analyzer=chinese_analyzer),
                    )
                    self._index = index.create_in(self._index_dir, schema)
                    logger.info("创建新的Whoosh索引，已配置中文分词器")
            except ImportError as e:
                logger.error(f"依赖库未安装: {e}")
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

    def get_chunk_content(self, chunk_id: str) -> str | None:
        """
        根据chunk_id获取分块内容

        Args:
            chunk_id: 分块ID (格式: {document_id}_{chunk_index})

        Returns:
            分块内容，不存在返回None
        """
        try:
            from whoosh.qparser import QueryParser

            ix = self._get_index()
            with ix.searcher() as searcher:
                parser = QueryParser("chunk_id", ix.schema)
                q = parser.parse(chunk_id)
                results = searcher.search(q, limit=1)

                if results:
                    return results[0]["content"]
                return None

        except Exception as e:
            logger.error(f"获取分块内容失败: {chunk_id}, 错误: {e}")
            return None
