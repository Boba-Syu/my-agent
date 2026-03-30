"""
仓库接口基类

仓库模式用于持久化和检索聚合根，屏蔽底层存储细节。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.domain.shared.aggregate_root import AggregateRoot

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AggregateRoot)


class Repository(ABC, Generic[T]):
    """
    仓库接口基类
    
    仓库是领域层定义的接口，由基础设施层实现：
    - 领域层定义仓库契约
    - 基础设施层提供具体实现（SQLite、MongoDB 等）
    - 每个聚合根对应一个仓库
    
    特性：
    - 操作对象是聚合根
    - 透明持久化
    - 支持事务边界
    
    Example:
        class OrderRepository(Repository[Order]):
            @abstractmethod
            def get_by_customer(self, customer_id: str) -> list[Order]: ...
        
        # 基础设施层实现
        class SQLiteOrderRepository(OrderRepository):
            def get(self, id: str) -> Order | None:
                # SQLite 实现
                pass
    """

    @abstractmethod
    def get(self, id: str) -> T | None:
        """
        根据 ID 获取聚合根
        
        Args:
            id: 聚合根标识
            
        Returns:
            聚合根实例，不存在则返回 None
        """
        pass

    @abstractmethod
    def save(self, aggregate: T) -> T:
        """
        保存聚合根
        
        如果聚合根已存在则更新，否则创建。
        
        Args:
            aggregate: 要保存的聚合根
            
        Returns:
            保存后的聚合根（可能包含生成的 ID）
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除聚合根
        
        Args:
            id: 要删除的聚合根标识
            
        Returns:
            是否成功删除
        """
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查聚合根是否存在
        
        Args:
            id: 聚合根标识
            
        Returns:
            是否存在
        """
        pass
