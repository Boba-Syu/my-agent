"""
记账 Agent 应用服务

基于 DDD 架构，使用 AbstractAgent 抽象。
支持 LangGraph、Agno 等多种底层实现。

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.application.agent.dto import ChatRequest, ChatResponse, StreamChunk
from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_response import ChunkType
from app.prompts import build_accounting_prompt

if TYPE_CHECKING:
    from app.application.agent.agent_factory import AgentFactory
    from app.domain.agent.agent_cache import AgentCache
    from app.domain.agent.agent_tool import AgentTool

logger = logging.getLogger(__name__)


class AccountingAgentService:
    """
    记账 Agent 应用服务
    
    基于 DDD 架构，使用 AbstractAgent 抽象。
    支持 LangGraph、Agno 等多种底层实现。
    
    关键设计：
    - 不直接依赖任何具体的基础设施实现
    - 通过 AgentFactory 创建 Agent
    - 通过提示词加载器构建系统提示词
    - 工具通过构造函数依赖注入
    
    Example:
        service = AccountingAgentService(
            agent_cache=InMemoryAgentCache(),
            agent_factory=AgentFactory(),
            accounting_tools=[...],
        )
        response = await service.chat("花了50块吃饭", "deepseek-v3", "session-001")
    """

    def __init__(
        self,
        agent_cache: AgentCache,
        agent_factory: AgentFactory,
        accounting_tools: list[AgentTool],
    ):
        """
        初始化记账 Agent 服务
        
        Args:
            agent_cache: Agent 缓存
            agent_factory: Agent 工厂，用于创建 Agent 实例
            accounting_tools: 记账专用工具列表
        """
        self._agent_cache = agent_cache
        self._agent_factory = agent_factory
        self._accounting_tools = accounting_tools
        self._today = date.today()

    def _get_or_create_agent(self, model: str) -> AbstractAgent:
        """
        获取或创建记账 Agent
        
        使用 AgentFactory 根据配置创建 Agent，
        不直接实例化任何具体实现。
        
        Args:
            model: 模型名称
            
        Returns:
            Agent 实例
        """
        cache_key = f"accounting:{model}:{self._today}"
        
        agent = self._agent_cache.get(cache_key)
        if agent is not None:
            logger.debug(f"命中记账 Agent 缓存: {cache_key}")
            return agent
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        # 使用工厂创建 Agent（符合 DDD，依赖抽象而非具体实现）
        agent = self._agent_factory.create_agent(
            model=model,
            tools=self._accounting_tools,
            system_prompt=system_prompt,
        )
        
        self._agent_cache.set(cache_key, agent)
        logger.info(f"创建记账 Agent: {cache_key}")
        
        return agent

    def _build_system_prompt(self) -> str:
        """
        构建记账专用系统提示词
        
        使用提示词加载器从文件构建提示词，
        不再硬编码在代码中。
        
        Returns:
            系统提示词
        """
        now = datetime.now()
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekday_names[now.weekday()]
        today_str = now.strftime("%Y-%m-%d")
        
        # 计算昨天日期
        from datetime import timedelta
        yesterday = now - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        
        # 使用提示词加载器构建提示词
        return build_accounting_prompt(
            today=today_str,
            weekday=weekday,
            yesterday=yesterday_str,
        )

    async def chat(self, message: str, model: str, thread_id: str) -> ChatResponse:
        """
        记账对话
        
        Args:
            message: 用户消息
            model: 模型名称
            thread_id: 会话 ID
            
        Returns:
            响应
        """
        logger.info(f"AccountingAgentService.chat: model={model}, thread={thread_id}")
        
        agent = self._get_or_create_agent(model)
        response = await agent.ainvoke(message, thread_id)
        
        return ChatResponse(
            content=response.content,
            thread_id=thread_id,
            model=model,
            metadata=response.metadata,
        )

    async def stream_chat(
        self,
        message: str,
        model: str,
        thread_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式记账对话
        
        Args:
            message: 用户消息
            model: 模型名称
            thread_id: 会话 ID
            
        Yields:
            流式响应块
        """
        logger.info(f"AccountingAgentService.stream_chat: model={model}, thread={thread_id}")
        
        agent = self._get_or_create_agent(model)
        
        async for chunk in agent.astream(message, thread_id):
            if chunk.type == ChunkType.CONTENT:
                yield StreamChunk(content=chunk.content)
            elif chunk.type == ChunkType.TOOL_CALL:
                yield StreamChunk(
                    is_tool_call=True,
                    tool_name=chunk.tool_call.name if chunk.tool_call else None,
                )
            elif chunk.type == ChunkType.ERROR:
                yield StreamChunk(is_error=True, error_message=chunk.content)
            elif chunk.type == ChunkType.DONE:
                yield StreamChunk(is_done=True)

    def clear_cache(self) -> int:
        """
        清空缓存
        
        Returns:
            清除的数量
        """
        return self._agent_cache.clear()

    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存信息
        """
        return self._agent_cache.info()
