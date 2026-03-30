"""
工具适配器

将领域层的 AgentTool 适配为 LangChain 工具。
"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from langchain_core.tools import StructuredTool

from app.domain.agent.agent_tool import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class ToolAdapter:
    """
    工具适配器
    
    将领域层的 AgentTool 适配为 LangChain StructuredTool。
    
    Example:
        domain_tool = CalculatorTool()
        adapter = ToolAdapter(domain_tool)
        langchain_tool = adapter.to_langchain_tool()
        
        # 现在 langchain_tool 可以传入 LangGraph
    """

    def __init__(self, domain_tool: AgentTool):
        """
        初始化适配器
        
        Args:
            domain_tool: 领域层工具
        """
        self._domain_tool = domain_tool

    def to_langchain_tool(self) -> StructuredTool:
        """
        转换为 LangChain 工具
        
        Returns:
            LangChain StructuredTool 实例
        """
        # 捕获 self 引用
        _domain_tool = self._domain_tool

        def _run(**kwargs: Any) -> str:
            """执行工具的包装函数"""
            try:
                result = _domain_tool.execute(**kwargs)
                if result.success:
                    return result.content
                else:
                    return f"工具执行错误: {result.error_message}"
            except Exception as e:
                logger.error(f"工具执行异常: {e}", exc_info=True)
                return f"工具执行异常: {str(e)}"

        # 构建 args_schema
        args_schema = self._build_args_schema()

        return StructuredTool.from_function(
            func=_run,
            name=self._domain_tool.name,
            description=self._domain_tool.description,
            args_schema=args_schema,
        )

    def _build_args_schema(self) -> type | None:
        """
        构建参数模式
        
        从工具的 execute 方法参数推断。
        """
        sig = inspect.signature(self._domain_tool.execute)
        params = list(sig.parameters.items())
        
        # 跳过 self 参数
        if params and params[0][0] == "self":
            params = params[1:]
        
        # 如果有 **kwargs，使用工具定义的 parameters
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for _, p in params):
            return None  # StructuredTool 会自动从 parameters 属性读取
        
        return None


def to_langchain_tool(domain_tool: AgentTool) -> StructuredTool:
    """
    快速转换函数
    
    Args:
        domain_tool: 领域层工具
        
    Returns:
        LangChain 工具
    """
    adapter = ToolAdapter(domain_tool)
    return adapter.to_langchain_tool()
