"""
Agent 消息模型

定义 Agent 对话中的消息值对象。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.shared.value_object import ValueObject

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """消息角色类型"""
    
    USER = "user"
    """用户消息"""
    
    ASSISTANT = "assistant"
    """AI 助手消息"""
    
    TOOL = "tool"
    """工具返回消息"""
    
    SYSTEM = "system"
    """系统消息"""


@dataclass(frozen=True)
class ToolCall:
    """
    工具调用值对象
    
    记录 AI 调用工具的请求信息。
    """
    
    id: str
    """调用 ID"""
    
    name: str
    """工具名称"""
    
    arguments: dict[str, Any]
    """调用参数"""


@dataclass(frozen=True)
class AgentMessage(ValueObject):
    """
    Agent 消息值对象
    
    代表对话中的一条消息，不可变。
    
    Example:
        # 用户消息
        msg = AgentMessage(
            role=MessageRole.USER,
            content="今天天气如何？"
        )
        
        # AI 带工具调用的消息
        msg = AgentMessage(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[ToolCall(
                id="call_001",
                name="get_weather",
                arguments={"city": "北京"}
            )]
        )
    """
    
    role: MessageRole
    """消息角色"""
    
    content: str
    """消息内容"""
    
    tool_calls: list[ToolCall] | None = None
    """工具调用列表（仅 AI 消息可能有）"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """元数据（模型信息、token 数等）"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """消息时间戳"""
    
    def is_tool_call(self) -> bool:
        """是否是带工具调用的消息"""
        return self.role == MessageRole.ASSISTANT and bool(self.tool_calls)
    
    def is_final_response(self) -> bool:
        """是否是最终回复消息（非工具调用）"""
        return self.role == MessageRole.ASSISTANT and not self.tool_calls
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "content": self.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in (self.tool_calls or [])
            ] or None,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def user_message(cls, content: str) -> AgentMessage:
        """快速创建用户消息"""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant_message(
        cls,
        content: str,
        tool_calls: list[ToolCall] | None = None,
    ) -> AgentMessage:
        """快速创建助手消息"""
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )
    
    @classmethod
    def tool_message(cls, content: str, tool_call_id: str | None = None) -> AgentMessage:
        """快速创建工具消息"""
        metadata = {"tool_call_id": tool_call_id} if tool_call_id else {}
        return cls(role=MessageRole.TOOL, content=content, metadata=metadata)
