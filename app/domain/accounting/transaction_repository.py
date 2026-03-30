"""
交易仓库接口

定义交易聚合根的持久化契约。
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from datetime import date
from typing import Any

from app.domain.shared.repository import Repository
from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.accounting.transaction_statistics import TransactionStatistics

logger = logging.getLogger(__name__)


class TransactionRepository(Repository[Transaction]):
    """
    交易仓库接口
    
    定义交易聚合根的持久化契约，由基础设施层实现。
    
    实现类：
    - SQLiteTransactionRepository: SQLite 实现
    - (未来可扩展) PostgreSQLTransactionRepository
    
    Example:
        class SQLiteTransactionRepository(TransactionRepository):
            def get(self, id: str) -> Transaction | None:
                # SQLite 实现
                pass
            
            def list_by_date_range(self, start: date, end: date) -> list[Transaction]:
                # 自定义查询
                pass
    """

    @abstractmethod
    def get(self, id: str) -> Transaction | None:
        """
        根据 ID 获取交易
        
        Args:
            id: 交易 ID
            
        Returns:
            交易聚合根，不存在则返回 None
        """
        pass

    @abstractmethod
    def list(
        self,
        transaction_type: TransactionType | None = None,
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """
        查询交易列表
        
        Args:
            transaction_type: 按类型过滤
            category: 按分类过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回条数限制
            
        Returns:
            交易列表
        """
        pass

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """
        保存交易
        
        如果交易已有 ID 则更新，否则创建。
        
        Args:
            transaction: 交易聚合根
            
        Returns:
            保存后的交易（可能包含生成的 ID）
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除交易
        
        Args:
            id: 交易 ID
            
        Returns:
            是否成功删除
        """
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查交易是否存在
        
        Args:
            id: 交易 ID
            
        Returns:
            是否存在
        """
        pass

    @abstractmethod
    def get_statistics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionStatistics:
        """
        获取统计数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计数据
        """
        pass

    @abstractmethod
    def get_categories_summary(
        self,
        transaction_type: TransactionType,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取分类汇总
        
        Args:
            transaction_type: 交易类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            按分类汇总的列表，每项包含 category, total, count
        """
        pass

    @abstractmethod
    def get_daily_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        获取每日汇总
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            按日汇总的列表，每项包含 date, income, expense
        """
        pass
