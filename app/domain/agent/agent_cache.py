"""
Agent 缓存接口

职责：
- 定义 Agent 缓存的领域层接口
- 基础设施层实现此接口

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.agent.abstract_agent import AbstractAgent


class AgentCache(ABC):
    """Agent 缓存接口
    
    定义 Agent 缓存的契约，由基础设施层实现。
    
    Example:
        cache = InMemoryAgentCache()  # 基础设施层实现
        cache.set("agent-1", agent)
        agent = cache.get("agent-1")
    """
    
    @abstractmethod
    def get(self, key: str) -> AbstractAgent | None:
        """获取缓存的 Agent
        
        Args:
            key: 缓存键
            
        Returns:
            Agent 实例，不存在返回 None
        """
        pass
    
    @abstractmethod
    def set(self, key: str, agent: AbstractAgent) -> None:
        """缓存 Agent
        
        Args:
            key: 缓存键
            agent: Agent 实例
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """清空缓存
        
        Returns:
            清除的数量
        """
        pass
    
    @abstractmethod
    def info(self) -> dict:
        """获取缓存信息
        
        Returns:
            缓存统计信息
        """
        pass
