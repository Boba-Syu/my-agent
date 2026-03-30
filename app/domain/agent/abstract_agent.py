"""
Agent 抽象基类

定义 Agent 的核心能力边界，独立于任何底层框架实现。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator

from app.domain.agent.agent_response import AgentResponse, AgentChunk, ToolUpdateResult
from app.domain.agent.agent_tool import AgentTool

logger = logging.getLogger(__name__)


class AbstractAgent(ABC):
    """
    Agent 抽象基类
    
    领域层核心抽象，定义 Agent 的通用能力：
    - 对话（同步/异步/流式）
    - 工具管理
    - 系统提示词配置
    - 会话管理
    
    此抽象独立于任何底层框架（LangGraph、AutoGen 等），
    允许未来替换底层实现而不影响上层业务代码。
    
    Example:
        class MyAgent(AbstractAgent):
            def invoke(self, message, thread_id):
                # 具体实现
                return AgentResponse(content="...")
        
        # 使用
        agent = MyAgent(...)
        response = await agent.ainvoke("你好", "session-001")
    """

    def __init__(
        self,
        system_prompt: str,
        max_iterations: int = 10,
        timeout: int = 120,
    ) -> None:
        """
        初始化 Agent
        
        Args:
            system_prompt: 系统提示词，定义 Agent 的行为准则
            max_iterations: 最大迭代次数（防止无限循环）
            timeout: 调用超时时间（秒）
        """
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._timeout = timeout
        self._tools: list[AgentTool] = []

    # -------------------------------------------------------------------------
    # 对话接口
    # -------------------------------------------------------------------------

    @abstractmethod
    def invoke(self, message: str, thread_id: str) -> AgentResponse:
        """
        同步调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID，相同 ID 共享上下文
            
        Returns:
            Agent 响应
        """
        pass

    @abstractmethod
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """
        异步调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Returns:
            Agent 响应
        """
        pass

    @abstractmethod
    def stream(self, message: str, thread_id: str) -> Iterator[AgentChunk]:
        """
        同步流式调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Yields:
            流式响应块
        """
        pass

    @abstractmethod
    async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
        """
        异步流式调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Yields:
            流式响应块
        """
        pass

    # -------------------------------------------------------------------------
    # 工具管理
    # -------------------------------------------------------------------------

    @abstractmethod
    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """
        动态添加工具
        
        Args:
            tools: 要添加的工具列表
            
        Returns:
            更新结果，包含成功添加和跳过的工具
        """
        pass

    @abstractmethod
    def remove_tools(self, tool_names: list[str]) -> ToolUpdateResult:
        """
        动态移除工具
        
        Args:
            tool_names: 要移除的工具名称列表
            
        Returns:
            更新结果，包含成功移除和未找到的工具
        """
        pass

    # -------------------------------------------------------------------------
    # 配置管理
    # -------------------------------------------------------------------------

    @abstractmethod
    def update_system_prompt(self, prompt: str) -> None:
        """
        更新系统提示词
        
        更新后 Agent 行为会立即改变。
        
        Args:
            prompt: 新的系统提示词
        """
        pass

    # -------------------------------------------------------------------------
    # 属性
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def tools(self) -> list[AgentTool]:
        """当前可用的工具列表"""
        pass

    @property
    def system_prompt(self) -> str:
        """当前系统提示词"""
        return self._system_prompt

    @property
    def max_iterations(self) -> int:
        """最大迭代次数"""
        return self._max_iterations

    @property
    def timeout(self) -> int:
        """超时时间（秒）"""
        return self._timeout

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"tools_count={len(self._tools)}, "
            f"max_iterations={self._max_iterations}, "
            f"timeout={self._timeout}s)"
        )
