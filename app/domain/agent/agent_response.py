"""
Agent 响应模型

定义 Agent 调用的响应和流式块。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.shared.value_object import ValueObject

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """流式响应块类型"""
    
    CONTENT = "content"
    """内容块"""
    
    TOOL_CALL = "tool_call"
    """工具调用块"""
    
    TOOL_RESULT = "tool_result"
    """工具结果块"""
    
    THINKING = "thinking"
    """推理过程块"""
    
    ERROR = "error"
    """错误块"""
    
    DONE = "done"
    """完成标记"""


@dataclass(frozen=True)
class ToolCall:
    """
    工具调用信息
    
    记录 AI 调用工具的详细信息。
    """
    
    id: str
    """调用 ID"""
    
    name: str
    """工具名称"""
    
    arguments: dict[str, Any]
    """调用参数"""


@dataclass(frozen=True)
class ToolResult:
    """工具执行结果"""
    
    tool_call_id: str
    """关联的工具调用 ID"""
    
    name: str
    """工具名称"""
    
    content: str
    """结果内容"""
    
    success: bool = True
    """是否成功"""


@dataclass(frozen=True)
class AgentChunk(ValueObject):
    """
    流式响应块
    
    用于流式输出时逐步返回内容。
    """
    
    type: ChunkType
    """块类型"""
    
    content: str = ""
    """内容文本"""
    
    tool_call: ToolCall | None = None
    """工具调用信息"""
    
    tool_result: ToolResult | None = None
    """工具结果信息"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """额外元数据"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """时间戳"""
    
    @classmethod
    def content_chunk(cls, content: str, **metadata) -> AgentChunk:
        """创建内容块"""
        return cls(type=ChunkType.CONTENT, content=content, metadata=metadata)
    
    @classmethod
    def tool_call_chunk(cls, tool_call: ToolCall, **metadata) -> AgentChunk:
        """创建工具调用块"""
        return cls(
            type=ChunkType.TOOL_CALL,
            tool_call=tool_call,
            metadata=metadata,
        )
    
    @classmethod
    def tool_result_chunk(cls, tool_result: ToolResult, **metadata) -> AgentChunk:
        """创建工具结果块"""
        return cls(
            type=ChunkType.TOOL_RESULT,
            tool_result=tool_result,
            metadata=metadata,
        )
    
    @classmethod
    def error_chunk(cls, error_message: str, **metadata) -> AgentChunk:
        """创建错误块"""
        return cls(
            type=ChunkType.ERROR,
            content=error_message,
            metadata=metadata,
        )
    
    @classmethod
    def done_chunk(cls, **metadata) -> AgentChunk:
        """创建完成标记块"""
        return cls(type=ChunkType.DONE, metadata=metadata)


@dataclass(frozen=True)
class AgentResponse(ValueObject):
    """
    Agent 完整响应
    
    包含 Agent 处理后的完整回复内容。
    """
    
    content: str
    """回复内容"""
    
    messages: list[Any] = field(default_factory=list)
    """完整消息历史（领域层消息对象）"""
    
    tool_calls: list[ToolCall] = field(default_factory=list)
    """本次调用使用的工具"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """元数据（模型、token 数、耗时等）"""
    
    def __post_init__(self):
        if self.messages is None:
            object.__setattr__(self, "messages", [])
        if self.tool_calls is None:
            object.__setattr__(self, "tool_calls", [])
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class ToolUpdateResult:
    """
    工具更新结果
    
    记录 add_tools / remove_tools 操作的结果。
    """
    
    success: list[str] = field(default_factory=list)
    """成功处理的工具名称"""
    
    skipped: list[str] = field(default_factory=list)
    """跳过的工具名称（已存在/不存在）"""
    
    failed: list[str] = field(default_factory=list)
    """处理失败的工具名称"""
    
    total: int = 0
    """当前工具总数"""
    
    def __post_init__(self):
        if self.success is None:
            object.__setattr__(self, "success", [])
        if self.skipped is None:
            object.__setattr__(self, "skipped", [])
        if self.failed is None:
            object.__setattr__(self, "failed", [])
