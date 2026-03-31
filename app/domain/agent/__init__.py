"""
Agent 子域

定义 Agent 的核心领域概念：
- AbstractAgent: Agent 抽象基类
- AgentMessage: 消息值对象
- AgentTool: 工具领域接口
- AgentResponse: 响应模型
- AgentCache: 缓存接口
- ToolRegistry: 工具注册表接口
"""

from __future__ import annotations

from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_cache import AgentCache
from app.domain.agent.agent_message import AgentMessage, MessageRole
from app.domain.agent.agent_response import AgentResponse, AgentChunk, ToolResult, ToolCall, ToolUpdateResult
from app.domain.agent.agent_tool import AgentTool
from app.domain.agent.tool_registry import ToolRegistry

__all__ = [
    "AbstractAgent",
    "AgentCache",
    "AgentMessage",
    "MessageRole",
    "AgentTool",
    "AgentResponse",
    "AgentChunk",
    "ToolResult",
    "ToolCall",
    "ToolUpdateResult",
    "ToolRegistry",
]
