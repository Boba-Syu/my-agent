"""
向量检索召回测试

仅测试向量检索效果，因为Whoosh关键词索引当前不存在。
"""

from __future__ import annotations

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_vector_recall():
    """测试向量检索召回效果"""
    from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
    from app.llm.llm_factory import LLMFactory

    logger.info("=" * 70)
    logger.info("向量检索召回测试")
    logger.info("=" * 70)

    # 初始化
    vector_store = ChromaVectorStore()
    embedding = LLMFactory.create_embedding()

    # 测试查询集
    test_cases = [
        {
            "query": "如何创建AI应用",
            "expected_keywords": ["创建", "AI应用", "项目"],
        },
        {
            "query": "智能体怎么搭建",
            "expected_keywords": ["智能体", "创建", "搭建"],
        },
        {
            "query": "应用模板使用方法",
            "expected_keywords": ["模板", "应用", "创建"],
        },
        {
            "query": "什么是工作流",
            "expected_keywords": ["工作流", "流程", "节点"],
        },
        {
            "query": "用户界面怎么设计",
            "expected_keywords": ["界面", "UI", "组件"],
        },
    ]

    results_summary = []

    for i, case in enumerate(test_cases, 1):
        query = case["query"]
        expected = case["expected_keywords"]

        logger.info(f"\n{'─' * 70}")
        logger.info(f"测试 {i}/{len(test_cases)}: {query}")
        logger.info(f"期望包含: {', '.join(expected)}")
        logger.info(f"{'─' * 70}")

        # 生成查询向量
        query_embedding = await embedding.aembed_query(query)

        # 执行检索
        results = vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=5
        )

        # 获取内容
        retrieved_contents = []
        for chunk_id, score in results:
            chunk = vector_store.get_chunk_by_id(chunk_id)
            if chunk:
                retrieved_contents.append({
                    "chunk_id": chunk_id,
                    "score": score,
                    "content": chunk.content[:200],
                })

        # 显示结果
        for j, item in enumerate(retrieved_contents, 1):
            logger.info(f"\n  [{j}] 相似度: {item['score']:.4f}")
            logger.info(f"      ID: {item['chunk_id']}")
            logger.info(f"      内容: {item['content']}...")

        # 检查相关性（简单关键词匹配）
        match_count = 0
        for item in retrieved_contents:
            content = item['content']
            for kw in expected:
                if kw in content:
                    match_count += 1
                    break

        relevance = match_count / len(retrieved_contents) if retrieved_contents else 0
        results_summary.append({
            "query": query,
            "retrieved": len(retrieved_contents),
            "relevance": relevance,
        })

        logger.info(f"\n  召回数量: {len(retrieved_contents)}")
        logger.info(f"  相关度: {relevance * 100:.1f}%")

    # 汇总
    logger.info(f"\n{'=' * 70}")
    logger.info("测试汇总")
    logger.info(f"{'=' * 70}")

    total_queries = len(results_summary)
    total_retrieved = sum(r["retrieved"] for r in results_summary)
    avg_relevance = sum(r["relevance"] for r in results_summary) / total_queries

    for r in results_summary:
        status = "✓" if r["relevance"] >= 0.6 else "✗"
        logger.info(f"{status} {r['query']}: 召回{r['retrieved']}条, 相关度{r['relevance']*100:.1f}%")

    logger.info(f"\n总计: {total_queries}个查询")
    logger.info(f"平均召回: {total_retrieved/total_queries:.1f}条/查询")
    logger.info(f"平均相关度: {avg_relevance*100:.1f}%")

    if avg_relevance >= 0.6:
        logger.info("\n✅ 向量检索效果良好")
    else:
        logger.info("\n⚠️ 向量检索效果一般，建议优化")


async def test_different_topk():
    """测试不同top_k的召回效果"""
    from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
    from app.llm.llm_factory import LLMFactory

    logger.info("\n" + "=" * 70)
    logger.info("不同Top-K召回效果对比")
    logger.info("=" * 70)

    vector_store = ChromaVectorStore()
    embedding = LLMFactory.create_embedding()

    query = "AI应用开发教程"
    query_embedding = await embedding.aembed_query(query)

    for top_k in [3, 5, 10]:
        results = vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k
        )

        logger.info(f"\nTop-{top_k}: 返回 {len(results)} 条结果")
        for i, (chunk_id, score) in enumerate(results[:3], 1):
            chunk = vector_store.get_chunk_by_id(chunk_id)
            preview = chunk.content[:80] if chunk else "N/A"
            logger.info(f"  [{i}] 相似度: {score:.4f} | {preview}...")


if __name__ == "__main__":
    asyncio.run(test_vector_recall())
    asyncio.run(test_different_topk())
