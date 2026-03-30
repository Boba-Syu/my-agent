"""
工具适配器

将领域层的 AgentTool 适配为 LangChain 工具。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.domain.agent.agent_tool import AgentTool, ToolResult

logger = logging.getLogger(__name__)


def _create_args_schema(tool: AgentTool) -> type[BaseModel] | None:
    """
    根据工具的 parameters 定义创建 Pydantic 模型
    
    Args:
        tool: 领域层工具
        
    Returns:
        Pydantic 模型类或 None（无参数时）
    """
    params = tool.parameters
    if not params or params.get("type") != "object":
        return None
    
    properties = params.get("properties", {})
    required = set(params.get("required", []))
    
    if not properties:
        return None
    
    # 动态创建 Pydantic 模型
    annotations = {}
    field_definitions = {}
    
    for prop_name, prop_schema in properties.items():
        # 推断类型
        prop_type = prop_schema.get("type", "string")
        if prop_type == "string":
            py_type = str
        elif prop_type == "integer":
            py_type = int
        elif prop_type == "number":
            py_type = float
        elif prop_type == "boolean":
            py_type = bool
        else:
            py_type = str
        
        # 可选字段
        if prop_name not in required:
            py_type = py_type | None
        
        annotations[prop_name] = py_type
        field_definitions[prop_name] = Field(
            default=None if prop_name not in required else ...,
            description=prop_schema.get("description", ""),
        )
    
    # 创建模型类
    model_name = f"{tool.name.title()}Args"
    model = type(
        model_name,
        (BaseModel,),
        {
            "__annotations__": annotations,
            **field_definitions,
        },
    )
    
    return model


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
        
        # 创建 args_schema
        args_schema = _create_args_schema(_domain_tool)

        def _run(**kwargs: Any) -> str:
            """执行工具的包装函数
            
            LangChain 会传递命名参数，直接转发给工具的 execute 方法。
            """
            try:
                result = _domain_tool.execute(**kwargs)
                if result.success:
                    return result.content
                else:
                    return f"工具执行错误: {result.error_message}"
            except Exception as e:
                logger.error(f"工具执行异常: {e}", exc_info=True)
                return f"工具执行异常: {str(e)}"

        return StructuredTool.from_function(
            func=_run,
            name=_domain_tool.name,
            description=_domain_tool.description,
            args_schema=args_schema,
        )


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
