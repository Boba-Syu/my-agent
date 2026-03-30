"""
通用子域 (Shared Subdomain)

领域层的基础组件，被其他子域共享使用。
包含实体、值对象、聚合根、领域事件和仓库的基类。
"""

from __future__ import annotations

from app.domain.shared.entity import Entity
from app.domain.shared.value_object import ValueObject
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.repository import Repository

__all__ = [
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "Repository",
]
