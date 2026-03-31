"""
Agent 缓存实现

提供 Agent 实例的缓存管理，避免重复创建。
继承领域层定义的接口。
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_cache import AgentCache as AgentCacheInterface

logger = logging.getLogger(__name__)

# 导出领域层接口
AgentCache = AgentCacheInterface


class InMemoryAgentCache(AgentCache):
    """
    内存中的 Agent 缓存
    
    简单的字典实现，适用于单进程部署。
    """

    def __init__(self):
        self._cache: dict[str, AbstractAgent] = {}

    def get(self, key: str) -> AbstractAgent | None:
        """获取缓存的 Agent"""
        agent = self._cache.get(key)
        if agent:
            logger.debug(f"Agent 缓存命中: {key}")
        return agent

    def set(self, key: str, agent: AbstractAgent) -> None:
        """缓存 Agent"""
        self._cache[key] = agent
        logger.info(f"Agent 已缓存: {key}")

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            logger.info(f"Agent 缓存已删除: {key}")
            return True
        return False

    def clear(self) -> int:
        """清空缓存"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Agent 缓存已清空: {count} 个")
        return count

    def keys(self) -> list[str]:
        """获取所有缓存键"""
        return list(self._cache.keys())

    def info(self) -> dict[str, Any]:
        """获取缓存信息"""
        return {
            "count": len(self._cache),
            "keys": self.keys(),
            "type": "in_memory",
        }
