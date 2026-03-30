"""
领域实体基类

实体是有唯一标识的领域对象，标识在对象生命周期内保持不变。
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any

from app.domain.shared.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class Entity(ABC):
    """
    领域实体基类
    
    特性：
    - 有唯一标识（id）
    - 基于标识相等（而非属性）
    - 可发布领域事件
    
    Example:
        class User(Entity):
            def __init__(self, id: str, name: str):
                super().__init__(id)
                self._name = name
    """

    def __init__(self, id: str | None = None) -> None:
        """
        初始化实体
        
        Args:
            id: 实体的唯一标识，为 None 表示新实体尚未持久化
        """
        self._id = id
        self._events: list[DomainEvent] = []

    @property
    def id(self) -> str | None:
        """实体的唯一标识"""
        return self._id

    def add_event(self, event: DomainEvent) -> None:
        """
        添加领域事件
        
        事件将在事务提交后统一发布。
        
        Args:
            event: 要发布的领域事件
        """
        self._events.append(event)
        logger.debug(f"领域事件已添加: {event.__class__.__name__}")

    def clear_events(self) -> list[DomainEvent]:
        """
        清空并返回所有待发布的事件
        
        Returns:
            清空的领域事件列表
        """
        events = self._events.copy()
        self._events.clear()
        return events

    def __eq__(self, other: object) -> bool:
        """
        基于标识相等
        
        两个实体只要标识相同就视为相等，无论属性是否相同。
        """
        if not isinstance(other, self.__class__):
            return False
        return self._id is not None and self._id == other._id

    def __hash__(self) -> int:
        """基于标识的哈希"""
        return hash(self._id) if self._id else id(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id!r})"
