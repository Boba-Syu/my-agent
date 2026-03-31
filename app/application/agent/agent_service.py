"""
Agent 应用服务

协调 Agent 领域对象完成用户用例。

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from app.application.agent.agent_factory import AgentFactory
from app.application.agent.dto import ChatRequest, ChatResponse, StreamChunk
from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_cache import AgentCache
from app.domain.agent.agent_response import ChunkType
from app.domain.agent.tool_registry import ToolRegistry
from app.prompts import build_default_agent_prompt

if TYPE_CHECKING:
    pass  # 无运行时基础设施导入

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agent 应用服务
    
    协调领域层的 Agent 完成用户用例，包括：
    - 对话
    - 流式对话
    - 工具管理
    - Agent 实例缓存
    
    通过 AgentFactory 创建具体实现，只依赖 AbstractAgent 抽象。
    所有基础设施依赖通过构造函数注入，符合 DDD 原则。
    
    Example:
        service = AgentService(
            agent_cache=InMemoryAgentCache(),
            tool_registry=ToolRegistry(),
        )
        
        # 对话
        response = await service.chat(ChatRequest(
            message="你好",
            model="deepseek-v3",
            thread_id="session-001",
        ))
    """

    def __init__(
        self,
        agent_cache: AgentCache,
        tool_registry: ToolRegistry,
        agent_factory: AgentFactory | None = None,
    ):
        """
        初始化应用服务
        
        Args:
            agent_cache: Agent 缓存接口（领域层抽象）
            tool_registry: 工具注册表接口（领域层抽象）
            agent_factory: Agent 工厂，None 时自动创建
        """
        self._agent_cache = agent_cache
        self._tool_registry = tool_registry
        self._agent_factory = agent_factory or AgentFactory()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        对话用例
        
        Args:
            request: 对话请求
            
        Returns:
            对话响应
        """
        logger.info(f"AgentService.chat: model={request.model}, thread={request.thread_id}")
        
        agent = self._get_or_create_agent(request.model, request.system_prompt)
        response = await agent.ainvoke(
            message=request.message,
            thread_id=request.thread_id,
        )
        
        return ChatResponse(
            content=response.content,
            thread_id=request.thread_id,
            model=request.model,
            metadata=response.metadata,
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """
        流式对话用例
        
        Args:
            request: 对话请求
            
        Yields:
            流式响应块
        """
        logger.info(f"AgentService.stream_chat: model={request.model}, thread={request.thread_id}")
        
        agent = self._get_or_create_agent(request.model, request.system_prompt)
        
        async for chunk in agent.astream(
            message=request.message,
            thread_id=request.thread_id,
        ):
            if chunk.type == ChunkType.CONTENT:
                yield StreamChunk(content=chunk.content)
            elif chunk.type == ChunkType.TOOL_CALL:
                yield StreamChunk(
                    is_tool_call=True,
                    tool_name=chunk.tool_call.name if chunk.tool_call else None,
                )
            elif chunk.type == ChunkType.ERROR:
                yield StreamChunk(
                    is_error=True,
                    error_message=chunk.content,
                )
            elif chunk.type == ChunkType.DONE:
                yield StreamChunk(is_done=True)

    def _get_or_create_agent(
        self,
        model: str,
        custom_prompt: str | None = None,
    ) -> AbstractAgent:
        """
        获取或创建 Agent 实例
        
        Args:
            model: 模型名称
            custom_prompt: 自定义系统提示词
            
        Returns:
            Agent 实例
        """
        # 使用模型+提示词的组合作为缓存键
        cache_key = f"{model}:{hash(custom_prompt) if custom_prompt else 'default'}"
        
        agent = self._agent_cache.get(cache_key)
        if agent is None:
            agent = self._create_agent(model, custom_prompt)
            self._agent_cache.set(cache_key, agent)
            logger.info(f"Agent 已创建并缓存: {cache_key}")
        
        return agent

    def _create_agent(
        self,
        model: str,
        custom_prompt: str | None = None,
    ) -> AbstractAgent:
        """
        创建新的 Agent 实例
        
        通过 AgentFactory 创建具体实现，只依赖 AbstractAgent 抽象。
        
        Args:
            model: 模型名称
            custom_prompt: 自定义系统提示词
            
        Returns:
            新的 Agent 实例
        """
        tools = self._tool_registry.get_all_tools()
        
        # 使用提示词加载器获取默认提示词，或使用自定义提示词
        system_prompt = custom_prompt or build_default_agent_prompt()
        
        # 使用工厂创建 Agent（具体实现由配置决定）
        agent = self._agent_factory.create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        
        return agent

    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存统计信息
        """
        return self._agent_cache.info()

    def clear_cache(self) -> int:
        """
        清空缓存
        
        Returns:
            清除的 Agent 数量
        """
        return self._agent_cache.clear()
