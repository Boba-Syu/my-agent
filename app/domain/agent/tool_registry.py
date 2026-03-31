"""
工具注册表接口

职责：
- 定义工具注册表的领域层接口
- 基础设施层实现此接口

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.agent.agent_tool import AgentTool


class ToolRegistry(ABC):
    """工具注册表接口
    
    定义工具注册表的契约，由基础设施层实现。
    
    Example:
        registry = ToolRegistryImpl()  # 基础设施层实现
        registry.register(CalculatorTool())
        tools = registry.get_all_tools()
    """
    
    @abstractmethod
    def register(self, tool: AgentTool) -> None:
        """注册工具
        
        Args:
            tool: 工具实例
        """
        pass
    
    @abstractmethod
    def get(self, name: str) -> AgentTool | None:
        """获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例，不存在返回 None
        """
        pass
    
    @abstractmethod
    def get_all_tools(self) -> list[AgentTool]:
        """获取所有工具
        
        Returns:
            工具列表
        """
        pass
    
    @abstractmethod
    def unregister(self, name: str) -> bool:
        """注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功注销
        """
        pass
