"""
Agent 工厂

根据配置创建不同的 Agent 实现实例。
工厂模式解耦了具体实现与业务代码。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.agent.abstract_agent import AbstractAgent
    from app.domain.agent.agent_provider import AgentProvider
    from app.domain.agent.agent_tool import AgentTool

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent 工厂
    
    负责根据配置创建对应的 Agent 实例。
    支持通过配置切换不同的 Agent 实现（agno、langgraph 等）。
    
    默认实现为 agno，可通过以下方式切换：
    - 配置文件中设置：agent.implementation = "langgraph"
    - 代码中指定：factory = AgentFactory(default_implementation="langgraph")
    
    Example:
        # 使用默认配置创建工厂
        factory = AgentFactory()
        
        # 创建 Agent
        agent = factory.create_agent(
            model="deepseek-v3",
            tools=[CalculatorTool()],
            system_prompt="你是一个记账助手"
        )
        
        # 指定实现类型
        agent = factory.create_agent(
            model="deepseek-v3",
            tools=[CalculatorTool()],
            system_prompt="你是一个记账助手",
            implementation="langgraph"
        )
    """

    # 默认实现类型
    DEFAULT_IMPLEMENTATION = "agno"
    
    # Provider 注册表（延迟加载）
    _providers: dict[str, AgentProvider] | None = None

    def __init__(self, default_implementation: str | None = None) -> None:
        """
        初始化工厂
        
        Args:
            default_implementation: 默认实现类型，None 时使用配置或 agno
        """
        self._default_implementation = default_implementation
        self._ensure_providers_loaded()

    @classmethod
    def _load_providers(cls) -> dict[str, AgentProvider]:
        """
        加载所有可用的 Provider
        
        Returns:
            Provider 名称到实例的映射
        """
        providers: dict[str, AgentProvider] = {}
        
        # 加载 Agno Provider（默认）
        try:
            from app.infrastructure.agent.agno.agno_agent_provider import AgnoAgentProvider
            agno_provider = AgnoAgentProvider()
            if agno_provider.is_available():
                providers[agno_provider.name] = agno_provider
                logger.info(f"已加载 Provider: {agno_provider.name}")
        except ImportError as e:
            logger.warning(f"Agno Provider 加载失败: {e}")
        
        # 加载 LangGraph Provider
        try:
            from app.infrastructure.agent.langgraph.langgraph_agent_provider import LangGraphAgentProvider
            langgraph_provider = LangGraphAgentProvider()
            if langgraph_provider.is_available():
                providers[langgraph_provider.name] = langgraph_provider
                logger.info(f"已加载 Provider: {langgraph_provider.name}")
        except ImportError as e:
            logger.warning(f"LangGraph Provider 加载失败: {e}")
        
        return providers

    @classmethod
    def _ensure_providers_loaded(cls) -> None:
        """确保 Provider 已加载"""
        if cls._providers is None:
            cls._providers = cls._load_providers()

    @classmethod
    def register_provider(cls, provider: AgentProvider) -> None:
        """
        注册自定义 Provider
        
        Args:
            provider: Provider 实例
        """
        cls._ensure_providers_loaded()
        if cls._providers is not None:
            cls._providers[provider.name] = provider
            logger.info(f"已注册 Provider: {provider.name}")

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        获取所有可用的 Provider 名称
        
        Returns:
            Provider 名称列表
        """
        cls._ensure_providers_loaded()
        if cls._providers is not None:
            return list(cls._providers.keys())
        return []

    def _get_implementation_type(self, override: str | None = None) -> str:
        """
        确定要使用的实现类型
        
        优先级：override 参数 > 构造函数默认值 > 配置文件 > 默认值
        
        Args:
            override: 显式指定的实现类型
            
        Returns:
            实现类型名称
        """
        if override:
            return override
        
        if self._default_implementation:
            return self._default_implementation
        
        # 从配置读取
        try:
            from app.config import get_agent_config
            config = get_agent_config()
            impl = config.get("implementation")
            if impl:
                return impl
        except Exception as e:
            logger.warning(f"读取 Agent 配置失败: {e}")
        
        return self.DEFAULT_IMPLEMENTATION

    def create_agent(
        self,
        model: str,
        tools: list[AgentTool],
        system_prompt: str,
        implementation: str | None = None,
        **kwargs,
    ) -> AbstractAgent:
        """
        创建 Agent 实例
        
        Args:
            model: 模型名称
            tools: 工具列表
            system_prompt: 系统提示词
            implementation: 指定实现类型，None 时使用默认
            **kwargs: 传递给 Provider 的额外参数
                - max_iterations: 最大迭代次数
                - timeout: 超时时间
                
        Returns:
            Agent 实例
            
        Raises:
            ValueError: 如果指定的实现不可用
            RuntimeError: 如果没有可用的 Provider
        """
        self._ensure_providers_loaded()
        
        impl_type = self._get_implementation_type(implementation)
        
        if self._providers is None or impl_type not in self._providers:
            available = self.get_available_providers()
            if not available:
                raise RuntimeError(
                    "没有可用的 Agent Provider，请确保至少安装了一种实现:\n"
                    "- Agno: uv add agno\n"
                    "- LangGraph: uv add langgraph langchain-openai"
                )
            raise ValueError(
                f"未知的 Agent 实现: '{impl_type}'\n"
                f"可用的实现: {', '.join(available)}"
            )
        
        provider = self._providers[impl_type]
        
        logger.info(
            f"创建 Agent: implementation={impl_type}, "
            f"model={model}, tools={len(tools)}"
        )
        
        return provider.create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            **kwargs,
        )

    def get_provider_info(self) -> dict[str, str]:
        """
        获取所有 Provider 的信息
        
        Returns:
            Provider 名称到描述的映射
        """
        self._ensure_providers_loaded()
        if self._providers is not None:
            return {
                name: provider.description 
                for name, provider in self._providers.items()
            }
        return {}
