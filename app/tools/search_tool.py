"""
搜索工具
当前为模拟实现（返回示例结果），可替换为真实的搜索 API（如 Tavily、SerpAPI 等）

扩展方式：替换 search 函数内部实现，接入真实搜索服务
"""
import logging

from langchain_core.tools import tool


@tool
def search(query: str, max_results: int = 3) -> str:
    """
    在互联网上搜索相关信息。

    当需要获取实时信息、新闻、事实性知识时使用此工具。

    Args:
        query:       搜索关键词或问题
        max_results: 返回结果数量（默认 3）

    Returns:
        搜索结果摘要文本
    """
    # -------------------------------------------------------
    # TODO：将下方模拟实现替换为真实搜索 API 调用
    # 示例：接入 Tavily
    #   from tavily import TavilyClient
    #   client = TavilyClient(api_key=...)
    #   results = client.search(query, max_results=max_results)
    #   return "\n".join(r["content"] for r in results["results"])
    # -------------------------------------------------------
    logging.debug("calculator 工具调用，入参：query={}", query)
    mock_results = [
        {
            "title": f"搜索结果 {i + 1}：关于「{query}」",
            "snippet": f"这是关于「{query}」的示例搜索结果 {i + 1}。"
                       f"请将此工具替换为真实搜索 API（如 Tavily、SerpAPI）以获取真实信息。",
            "url": f"https://example.com/result-{i + 1}",
        }
        for i in range(min(max_results, 5))
    ]

    formatted = []
    for idx, r in enumerate(mock_results, 1):
        formatted.append(f"[{idx}] {r['title']}\n    {r['snippet']}\n    来源：{r['url']}")

    return "\n\n".join(formatted) if formatted else f"未找到关于「{query}」的相关信息"
