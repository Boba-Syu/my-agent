"""
Agent 工具接口

定义工具的领域契约，与具体实现框架无关。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.domain.shared.value_object import ValueObject

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolResult:
    """
    工具执行结果值对象
    
    包装工具执行的返回结果。
    """
    
    content: str
    """结果内容（文本）"""
    
    success: bool = True
    """是否成功执行"""
    
    error_message: str | None = None
    """错误信息（失败时）"""
    
    metadata: dict[str, Any] = None
    """额外元数据"""
    
    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
    
    @classmethod
    def success_result(cls, content: str, **metadata) -> ToolResult:
        """创建成功结果"""
        return cls(content=content, success=True, metadata=metadata)
    
    @classmethod
    def error_result(cls, error_message: str, **metadata) -> ToolResult:
        """创建失败结果"""
        return cls(
            content="",
            success=False,
            error_message=error_message,
            metadata=metadata,
        )


class AgentTool(ABC):
    """
    领域工具接口
    
    定义工具的契约，独立于具体框架（LangChain、MCP 等）。
    所有具体工具实现此接口。
    
    Example:
        class CalculatorTool(AgentTool):
            @property
            def name(self) -> str:
                return "calculator"
            
            @property
            def description(self) -> str:
                return "执行数学计算"
            
            @property
            def parameters(self) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                }
            
            def execute(self, expression: str) -> ToolResult:
                try:
                    result = eval(expression)  # 实际使用安全计算
                    return ToolResult.success_result(str(result))
                except Exception as e:
                    return ToolResult.error_result(str(e))
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        工具唯一名称
        
        用于 LLM 识别和调用工具。
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        工具描述
        
        供 LLM 理解工具用途，应清晰说明：
        - 工具功能
        - 适用场景
        - 参数说明
        """
        pass

    @property
    def parameters(self) -> dict[str, Any]:
        """
        工具参数 JSON Schema
        
        定义工具接受的参数结构。
        默认返回空对象（无参数）。
        """
        return {
            "type": "object",
            "properties": {},
        }

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具调用参数
            
        Returns:
            工具执行结果
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        """基于名称相等"""
        if not isinstance(other, AgentTool):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """基于名称哈希"""
        return hash(self.name)
