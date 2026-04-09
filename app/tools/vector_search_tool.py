"""
向量检索工具
调用 ChromaClient 进行语义相似度检索，适用于知识库问答场景

扩展方式：调整检索参数（k、filter）或在此文件中新增文档入库工具
"""

import logging
from functools import lru_cache

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_chroma_client():
    """
    延迟初始化 ChromaClient（避免模块加载时立即连接，减少启动开销）
    使用 lru_cache 确保单例复用
    """
    # 延迟导入，避免循环依赖
    from app.db.chroma_client import ChromaClient
    from app.llm.llm_factory import LLMFactory

    embedding = LLMFactory.create_embedding()
    return ChromaClient(embedding)


@tool
def vector_search(query: str, k: int = 4) -> str:
    """
    在本地向量知识库中进行语义相似度检索。

    适用于查询已存储的文档、知识片段等内容。
    如果知识库为空，将返回提示信息。

    Args:
        query: 查询文本，使用自然语言描述
        k:     返回最相似的文档数量（默认 4）

    Returns:
        检索到的相关文档内容，或无结果提示
    """
    logging.debug("vector_search 工具调用，入参：query={}", query)

    try:
        client = _get_chroma_client()
        results = client.similarity_search_with_score(query=query, k=k)

        if not results:
            return f"知识库中未找到与「{query}」相关的内容。\n提示：请先向知识库添加文档。"

        formatted = []
        for idx, (doc, score) in enumerate(results, 1):
            source = doc.metadata.get("source", "未知来源")
            formatted.append(
                f"[{idx}] 相似度：{score:.4f} | 来源：{source}\n    {doc.page_content}"
            )

        return f"找到 {len(results)} 条相关内容：\n\n" + "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"向量检索失败：{e}", exc_info=True)
        return f"向量检索失败：{e}\n请确保 Ollama 服务已启动且 bge-m3:latest 模型已下载。"
