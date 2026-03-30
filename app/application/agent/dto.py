"""
Agent 应用层 DTO

数据传输对象，用于应用层与接口层之间的数据交换。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatRequest:
    """
    对话请求 DTO
    
    从接口层传入应用层的对话请求数据。
    """
    
    message: str
    """用户输入消息"""
    
    model: str
    """使用的模型名称"""
    
    thread_id: str
    """会话线程 ID"""
    
    system_prompt: str | None = None
    """自定义系统提示词"""


@dataclass(frozen=True)
class ChatResponse:
    """
    对话响应 DTO
    
    从应用层返回接口层的对话响应数据。
    """
    
    content: str
    """回复内容"""
    
    thread_id: str
    """会话线程 ID"""
    
    model: str
    """使用的模型名称"""
    
    metadata: dict[str, Any] | None = None
    """额外元数据"""
    
    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class StreamChunk:
    """
    流式响应块 DTO
    
    用于流式对话的响应块。
    """
    
    content: str = ""
    """内容块"""
    
    is_tool_call: bool = False
    """是否是工具调用"""
    
    tool_name: str | None = None
    """工具名称（工具调用时）"""
    
    is_done: bool = False
    """是否完成"""
    
    is_error: bool = False
    """是否是错误"""
    
    error_message: str | None = None
    """错误信息"""
