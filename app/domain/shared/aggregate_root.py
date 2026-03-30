"""
聚合根基类

聚合根是聚合的入口实体，定义了事务边界和一致性边界。
"""

from __future__ import annotations

import logging

from app.domain.shared.entity import Entity

logger = logging.getLogger(__name__)


class AggregateRoot(Entity):
    """
    聚合根基类
    
    聚合是领域对象的集群，作为数据修改的单元：
    - 聚合根是聚合的唯一入口
    - 外部对象只能引用聚合根
    - 聚合内部对象由聚合根统一管理
    - 每个聚合对应一个事务
    
    特性：
    - 继承自 Entity，有唯一标识
    - 包含版本号（乐观锁）
    - 管理聚合内领域事件
    
    Example:
        class Order(AggregateRoot):
            def __init__(self, id: str, customer_id: str):
                super().__init__(id)
                self._customer_id = customer_id
                self._items: list[OrderItem] = []
                self._version = 0
            
            def add_item(self, product: str, quantity: int, price: Money):
                item = OrderItem(product, quantity, price)
                self._items.append(item)
                self._version += 1
                self.add_event(OrderItemAdded(self.id, product, quantity))
    """

    def __init__(self, id: str | None = None) -> None:
        """
        初始化聚合根
        
        Args:
            id: 聚合根的唯一标识
        """
        super().__init__(id)
        self._version = 0

    @property
    def version(self) -> int:
        """
        版本号（乐观锁）
        
        每次聚合修改时递增，用于并发控制。
        """
        return self._version

    def _increment_version(self) -> None:
        """递增版本号"""
        self._version += 1

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id!r}, version={self._version})"
