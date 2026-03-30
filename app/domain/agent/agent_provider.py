"""
Agent Provider 协议

定义创建 Agent 实例的接口契约，属于领域层。
基础设施层实现此协议来提供具体的 Agent 实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.agent.abstract_agent import AbstractAgent
    from app.domain.agent.agent_tool import AgentTool


class AgentProvider(ABC):
    """
    Agent Provider 抽象基类
    
    定义创建 Agent 实例的标准接口。不同的 Agent 实现
    （如 LangGraph、Agno、AutoGen 等）需要提供对应的 Provider。
    
    此协议属于领域层，不依赖任何具体框架。
    
    Example:
        class LangGraphAgentProvider(AgentProvider):
            def create_agent(self, config, tools, system_prompt):
                return LangGraphAgent(...)
        
        # 使用
        provider = LangGraphAgentProvider()
        agent = provider.create_agent(config, tools, "你是一个助手")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称，用于配置识别（如 'langgraph', 'agno'）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Provider 描述"""
        pass

    @abstractmethod
    def create_agent(
        self,
        model: str,
        tools: list[AgentTool],
        system_prompt: str,
        **kwargs,
    ) -> AbstractAgent:
        """
        创建 Agent 实例
        
        Args:
            model: 模型名称
            tools: 工具列表
            system_prompt: 系统提示词
            **kwargs: 额外的配置参数
                - max_iterations: 最大迭代次数
                - timeout: 超时时间（秒）
                - temperature: 温度参数
                - max_tokens: 最大 token 数
                
        Returns:
            Agent 实例
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查此 Provider 是否可用（依赖是否已安装）
        
        Returns:
            True 如果依赖已安装且可用
        """
        pass
