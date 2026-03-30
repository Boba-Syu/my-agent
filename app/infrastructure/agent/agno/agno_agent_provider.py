"""
Agno Agent Provider

提供 Agno 实现的 Agent 创建能力。
"""

from __future__ import annotations

import logging

from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_provider import AgentProvider
from app.domain.agent.agent_tool import AgentTool
from app.infrastructure.agent.agno.agno_agent import AgnoAgent
from app.infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class AgnoAgentProvider(AgentProvider):
    """
    Agno Agent Provider
    
    创建 Agno 实现的 Agent 实例。
    Agno 是一个轻量级、高性能的 Agent 框架。
    
    Example:
        provider = AgnoAgentProvider()
        if provider.is_available():
            agent = provider.create_agent(
                model="deepseek-v3",
                tools=[CalculatorTool()],
                system_prompt="你是一个记账助手"
            )
    """

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        """
        初始化 Provider
        
        Args:
            llm_provider: LLM 提供器，None 时自动创建
        """
        self._llm_provider = llm_provider or LLMProvider()

    @property
    def name(self) -> str:
        """Provider 名称"""
        return "agno"

    @property
    def description(self) -> str:
        """Provider 描述"""
        return "Agno 轻量级 Agent 框架，高性能，原生支持流式输出"

    def create_agent(
        self,
        model: str,
        tools: list[AgentTool],
        system_prompt: str,
        **kwargs,
    ) -> AbstractAgent:
        """
        创建 Agno Agent 实例
        
        Args:
            model: 模型名称
            tools: 工具列表
            system_prompt: 系统提示词
            **kwargs: 额外参数
                - max_iterations: 最大迭代次数（默认 10）
                - timeout: 超时时间（默认 120 秒）
                
        Returns:
            AgnoAgent 实例
            
        Raises:
            ImportError: 如果 agno 未安装
        """
        if not self.is_available():
            raise ImportError(
                "Agno 未安装，请运行: uv add agno\n"
                "或切换其他 Agent 实现: agent.implementation = 'langgraph'"
            )

        llm_config = self._llm_provider.get_config(model)
        
        max_iterations = kwargs.get("max_iterations", 10)
        timeout = kwargs.get("timeout", 120)

        agent = AgnoAgent(
            llm_config=llm_config,
            system_prompt=system_prompt,
            tools=tools,
            max_iterations=max_iterations,
            timeout=timeout,
        )

        logger.info(f"AgnoAgent 已创建: model={model}, tools={len(tools)}")
        return agent

    def is_available(self) -> bool:
        """
        检查 Agno 是否可用
        
        Returns:
            True 如果 agno 已安装
        """
        try:
            import agno
            return True
        except ImportError:
            return False
