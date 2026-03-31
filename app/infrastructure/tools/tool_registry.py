"""
工具注册表

管理所有可用工具的注册和发现。
实现领域层定义的 ToolRegistry 接口。
"""

from __future__ import annotations

import logging
from typing import Type

from app.domain.agent.agent_tool import AgentTool
from app.domain.agent.tool_registry import ToolRegistry as ToolRegistryInterface

logger = logging.getLogger(__name__)

# 导出领域层接口
ToolRegistryInterface = ToolRegistryInterface


class ToolRegistry(ToolRegistryInterface):
    """
    工具注册表实现
    
    管理工具实例的注册、发现和获取。
    继承领域层 ToolRegistry 接口。
    
    Example:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        
        # 获取所有工具
        tools = registry.get_all_tools()
        
        # 获取特定工具
        calc = registry.get("calculator")
    """

    _instance: ToolRegistry | None = None
    _tools: dict[str, AgentTool] = {}

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
        return cls._instance

    def register(self, tool: AgentTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        self._tools[tool.name] = tool
        logger.info(f"工具已注册: {tool.name}")

    def register_many(self, tools: list[AgentTool]) -> None:
        """
        批量注册工具
        
        Args:
            tools: 工具实例列表
        """
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> AgentTool | None:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例，不存在返回 None
        """
        return self._tools.get(name)

    # 别名，向后兼容
    get_tool = get

    def get_all_tools(self) -> list[AgentTool]:
        """
        获取所有工具
        
        Returns:
            工具实例列表
        """
        return list(self._tools.values())

    def get_tool_names(self) -> list[str]:
        """
        获取所有工具名称
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            name: 工具名称
            
        Returns:
            是否存在
        """
        return name in self._tools

    def unregister(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功注销
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"工具已注销: {name}")
            return True
        return False

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        logger.info("工具注册表已清空")

    def count(self) -> int:
        """
        获取工具数量
        
        Returns:
            工具数量
        """
        return len(self._tools)


def get_default_registry() -> ToolRegistry:
    """
    获取默认工具注册表（预加载常用工具）
    
    Returns:
        预加载的工具注册表
    """
    registry = ToolRegistry()
    
    # 如果尚未注册工具，加载默认工具
    if registry.count() == 0:
        # TODO: 加载默认工具
        # from app.infrastructure.tools.calculator_tool import CalculatorTool
        # from app.infrastructure.tools.datetime_tool import DateTimeTool
        # registry.register_many([
        #     CalculatorTool(),
        #     DateTimeTool(),
        # ])
        pass
    
    return registry
