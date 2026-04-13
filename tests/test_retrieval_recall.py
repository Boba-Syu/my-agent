"""
召回测试脚本

读取向量数据库中的数据，测试关键词检索和向量检索的效果。
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_chroma_stats():
    """获取Chroma向量数据库统计信息"""
    logger.info("=" * 60)
    logger.info("Chroma向量数据库统计")
    logger.info("=" * 60)

    try:
        import chromadb
        from app.config import get_config

        config = get_config()
        chroma_cfg = config.get("chroma", {})
        persist_directory = chroma_cfg.get("persist_directory", "./data/chroma_db")
        collection_name = chroma_cfg.get("collection_name", "rag_vectors")

        logger.info(f"数据库路径: {persist_directory}")
        logger.info(f"集合名称: {collection_name}")

        # 连接Chroma
        client = chromadb.PersistentClient(path=persist_directory)

        # 列出所有集合
        collections = client.list_collections()
        logger.info(f"\n集合数量: {len(collections)}")

        for collection_info in collections:
            logger.info(f"\n  集合: {collection_info.name}")
            collection = client.get_collection(collection_info.name)
            count = collection.count()
            logger.info(f"  文档数量: {count}")

            # 获取样本数据
            if count > 0:
                sample = collection.get(limit=min(3, count))
                logger.info(f"\n  样本数据 (前{min(3, count)}条):")
                for i, (doc_id, doc, meta) in enumerate(zip(
                    sample.get('ids', []),
                    sample.get('documents', []),
                    sample.get('metadatas', [])
                )):
                    logger.info(f"    [{i+1}] ID: {doc_id}")
                    logger.info(f"        标题: {meta.get('title', 'N/A')}")
                    logger.info(f"        知识库: {meta.get('kb_type', 'N/A')}")
                    logger.info(f"        内容预览: {doc[:100]}...")

        return True

    except Exception as e:
        logger.error(f"获取Chroma统计失败: {e}")
        return False


def get_whoosh_stats():
    """获取Whoosh关键词索引统计信息"""
    logger.info("\n" + "=" * 60)
    logger.info("Whoosh关键词索引统计")
    logger.info("=" * 60)

    try:
        from whoosh import index
        from app.config import get_sqlite_config

        sqlite_cfg = get_sqlite_config()
        db_path = sqlite_cfg.get("path", "./data/agent.db")
        index_dir = db_path.replace(".db", "_whoosh_index")

        logger.info(f"索引路径: {index_dir}")

        if not index.exists_in(index_dir):
            logger.warning("Whoosh索引不存在")
            return False

        ix = index.open_dir(index_dir)
        logger.info(f"\n索引Schema: {list(ix.schema.names())}")

        with ix.searcher() as searcher:
            doc_count = searcher.doc_count()
            logger.info(f"文档数量: {doc_count}")

            # 获取样本
            if doc_count > 0:
                from whoosh.query import Every
                results = searcher.search(Every(), limit=3)
                logger.info(f"\n样本数据 (前{min(3, doc_count)}条):")
                for i, hit in enumerate(results):
                    logger.info(f"  [{i+1}] Chunk ID: {hit.get('chunk_id', 'N/A')}")
                    logger.info(f"      Doc ID: {hit.get('document_id', 'N/A')}")
                    logger.info(f"      KB Type: {hit.get('kb_type', 'N/A')}")
                    content = hit.get('content', '')
                    logger.info(f"      内容预览: {content[:100]}...")

        return True

    except Exception as e:
        logger.error(f"获取Whoosh统计失败: {e}")
        return False


async def test_vector_search(query: str, top_k: int = 5):
    """测试向量检索"""
    logger.info("\n" + "=" * 60)
    logger.info(f"向量检索测试 | 查询: '{query}'")
    logger.info("=" * 60)

    try:
        from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
        from app.llm.llm_factory import LLMFactory

        # 创建向量存储实例
        vector_store = ChromaVectorStore()

        # 创建embedding实例
        embedding = LLMFactory.create_embedding()

        # 生成查询向量
        query_embedding = await embedding.aembed_query(query)
        logger.info(f"查询向量维度: {len(query_embedding)}")

        # 执行向量检索
        results = vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k
        )

        logger.info(f"\n检索到 {len(results)} 条结果:")
        for i, (chunk_id, score) in enumerate(results, 1):
            logger.info(f"  [{i}] Chunk ID: {chunk_id} | 相似度: {score:.4f}")

            # 尝试获取内容
            chunk = vector_store.get_chunk_by_id(chunk_id)
            if chunk:
                logger.info(f"      内容: {chunk.content[:150]}...")
            else:
                logger.warning(f"      无法获取内容")

        return results

    except Exception as e:
        logger.error(f"向量检索测试失败: {e}", exc_info=True)
        return []


def test_keyword_search(query: str, top_k: int = 5):
    """测试关键词检索"""
    logger.info("\n" + "=" * 60)
    logger.info(f"关键词检索测试 | 查询: '{query}'")
    logger.info("=" * 60)

    try:
        from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

        # 创建关键词索引实例
        keyword_index = WhooshKeywordIndex()

        # 执行关键词检索
        results = keyword_index.search(
            query=query,
            top_k=top_k
        )

        logger.info(f"\n检索到 {len(results)} 条结果:")
        for i, (chunk_id, score) in enumerate(results, 1):
            logger.info(f"  [{i}] Chunk ID: {chunk_id} | BM25分数: {score:.4f}")

            # 获取内容
            content = keyword_index.get_chunk_content(chunk_id)
            if content:
                logger.info(f"      内容: {content[:150]}...")
            else:
                logger.warning(f"      无法获取内容")

        return results

    except Exception as e:
        logger.error(f"关键词检索测试失败: {e}", exc_info=True)
        return []


async def test_hybrid_search(query: str, top_k: int = 5):
    """测试混合检索"""
    logger.info("\n" + "=" * 60)
    logger.info(f"混合检索测试 | 查询: '{query}'")
    logger.info("=" * 60)

    try:
        from app.infrastructure.tools.rag.hybrid_search_tool import HybridSearchTool
        from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
        from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

        # 创建工具实例
        vector_store = ChromaVectorStore()
        keyword_index = WhooshKeywordIndex()

        tool = HybridSearchTool(
            vector_store=vector_store,
            keyword_index=keyword_index,
        )

        # 执行混合检索
        result = tool.execute(
            query=query,
            top_k=top_k
        )

        if result.success:
            logger.info(f"\n检索成功!")
            logger.info(f"结果: {result.data}")
        else:
            logger.error(f"检索失败: {result.error}")

        return result

    except Exception as e:
        logger.error(f"混合检索测试失败: {e}", exc_info=True)
        return None


async def run_recall_tests():
    """运行召回测试"""
    logger.info("\n" + "=" * 60)
    logger.info("开始召回测试")
    logger.info("=" * 60)

    # 1. 获取数据库统计
    chroma_ok = get_chroma_stats()
    whoosh_ok = get_whoosh_stats()

    if not chroma_ok and not whoosh_ok:
        logger.error("数据库都不可用，无法继续测试")
        return

    # 2. 测试查询列表
    test_queries = [
        "年假政策",
        "报销流程",
        "请假申请",
        "工作时间",
        "福利制度",
    ]

    logger.info("\n" + "=" * 60)
    logger.info("开始检索测试")
    logger.info("=" * 60)

    for query in test_queries:
        logger.info(f"\n{'-' * 60}")
        logger.info(f"测试查询: '{query}'")
        logger.info(f"{'-' * 60}")

        # 向量检索
        if chroma_ok:
            await test_vector_search(query, top_k=3)

        # 关键词检索
        if whoosh_ok:
            test_keyword_search(query, top_k=3)

        # 混合检索
        if chroma_ok and whoosh_ok:
            await test_hybrid_search(query, top_k=3)

    logger.info("\n" + "=" * 60)
    logger.info("召回测试完成")
    logger.info("=" * 60)


def main():
    """主函数"""
    # 检查参数
    if len(sys.argv) > 1 and sys.argv[1] == '--stats':
        # 仅显示统计
        get_chroma_stats()
        get_whoosh_stats()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--query':
        # 单查询测试
        query = sys.argv[2] if len(sys.argv) > 2 else "测试查询"
        asyncio.run(run_single_query(query))
        return

    # 运行完整测试
    asyncio.run(run_recall_tests())


async def run_single_query(query: str):
    """运行单个查询测试"""
    logger.info(f"\n执行单查询测试: '{query}'")

    get_chroma_stats()
    get_whoosh_stats()

    await test_vector_search(query, top_k=5)
    test_keyword_search(query, top_k=5)
    await test_hybrid_search(query, top_k=5)


if __name__ == "__main__":
    main()
