"""
Agent 相关请求/响应模型
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求体"""
    
    message: str = Field(..., description="用户输入的消息", min_length=1, max_length=10000)
    model: str = Field(default="deepseek-v3", description="使用的 LLM 模型名称")
    system_prompt: str | None = Field(default=None, description="自定义系统提示词")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="会话线程 ID，相同 ID 可保持多轮上下文",
    )
    use_all_tools: bool = Field(default=True, description="是否使用全部工具")


class ChatResponse(BaseModel):
    """对话响应体"""
    
    reply: str = Field(..., description="Agent 回复内容")
    thread_id: str = Field(..., description="本次对话的线程 ID")
    model: str = Field(..., description="实际使用的模型名称")


class ToolInfo(BaseModel):
    """工具信息"""
    
    name: str
    description: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    
    status: str
    version: str = "0.2.0"
    architecture: str = "ddd"
