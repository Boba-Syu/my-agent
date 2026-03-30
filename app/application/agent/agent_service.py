"""
Agent 应用服务

协调 Agent 领域对象完成用户用例。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.application.agent.agent_factory import AgentFactory
from app.application.agent.dto import ChatRequest, ChatResponse, StreamChunk
from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_response import ChunkType
from app.infrastructure.agent.cache.agent_cache import AgentCache
from app.infrastructure.llm.llm_provider import LLMProvider
from app.infrastructure.tools.tool_registry import ToolRegistry

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
        llm_provider: LLMProvider | None = None,
        agent_factory: AgentFactory | None = None,
    ):
        """
        初始化应用服务
        
        Args:
            agent_cache: Agent 缓存
            tool_registry: 工具注册表
            llm_provider: LLM 提供器，None 时自动创建
            agent_factory: Agent 工厂，None 时自动创建
        """
        self._agent_cache = agent_cache
        self._tool_registry = tool_registry
        self._llm_provider = llm_provider or LLMProvider()
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
        system_prompt = custom_prompt or self._get_default_system_prompt()
        
        # 使用工厂创建 Agent（具体实现由配置决定，默认 agno）
        agent = self._agent_factory.create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        
        return agent

    def _get_default_system_prompt(self) -> str:
        """
        获取默认系统提示词
        
        Returns:
            默认系统提示词
        """
        return (
            "你是一个智能记账助手，帮助用户管理日常收支。\n"
            "你可以：\n"
            "1. 记录收入和支出\n"
            "2. 查询收支记录\n"
            "3. 统计收支数据\n"
            "4. 分析消费习惯\n"
            "请友好地回答用户的问题。"
        )

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
