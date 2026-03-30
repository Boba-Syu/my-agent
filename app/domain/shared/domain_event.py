"""
领域事件基类

领域事件表示领域中发生的有意义的事情，用于解耦领域逻辑。
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    领域事件基类
    
    领域事件是值对象（不可变），用于：
    - 记录领域中发生的事实
    - 解耦聚合之间的依赖
    - 实现最终一致性
    - 支持审计和日志
    
    特性：
    - 有唯一事件ID
    - 包含发生时间戳
    - 不可变（值对象）
    
    Example:
        @dataclass(frozen=True)
        class OrderCreated(DomainEvent):
            order_id: str
            customer_id: str
            total_amount: Money
            
        # 在聚合中发布事件
        order.add_event(OrderCreated(order.id, customer_id, total))
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()), kw_only=True)
    occurred_at: datetime = field(default_factory=datetime.now, kw_only=True)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"event_id={self.event_id!r}, "
            f"occurred_at={self.occurred_at.isoformat()!r}"
            f")"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        将事件转换为字典
        
        Returns:
            事件的字典表示
        """
        return {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            **{
                k: v
                for k, v in self.__dict__.items()
                if k not in ("event_id", "occurred_at")
            },
        }
