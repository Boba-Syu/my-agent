"""
记账应用层 DTO

数据传输对象，用于应用层与接口层之间的数据交换。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.accounting.money import Money
from app.domain.accounting.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateTransactionDTO:
    """创建交易请求 DTO"""
    
    transaction_type: str
    """交易类型：income/expense"""
    
    category: str
    """分类"""
    
    amount: float
    """金额"""
    
    transaction_date: str
    """交易日期 YYYY-MM-DD"""
    
    note: str = ""
    """备注"""


@dataclass(frozen=True)
class TransactionDTO:
    """交易数据 DTO"""
    
    id: int
    """交易 ID"""
    
    transaction_type: str
    """交易类型"""
    
    category: str
    """分类"""
    
    amount: float
    """金额"""
    
    transaction_date: str
    """交易日期"""
    
    note: str
    """备注"""
    
    created_at: str | None = None
    """创建时间"""
    
    @classmethod
    def from_entity(cls, entity: Transaction) -> TransactionDTO:
        """从领域实体创建 DTO"""
        return cls(
            id=entity.id or 0,
            transaction_type=entity.transaction_type.value,
            category=entity.category,
            amount=float(entity.amount.amount),
            transaction_date=entity.transaction_date.isoformat(),
            note=entity.note,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
        )


@dataclass(frozen=True)
class TransactionQueryDTO:
    """交易查询 DTO"""
    
    transaction_type: str | None = None
    """交易类型过滤"""
    
    category: str | None = None
    """分类过滤"""
    
    start_date: str | None = None
    """开始日期"""
    
    end_date: str | None = None
    """结束日期"""
    
    limit: int = 100
    """返回条数限制"""


@dataclass(frozen=True)
class StatisticsDTO:
    """统计数据 DTO"""
    
    income_total: float
    """收入总额"""
    
    expense_total: float
    """支出总额"""
    
    net: float
    """净收支"""
    
    income_count: int
    """收入笔数"""
    
    expense_count: int
    """支出笔数"""
    
    start_date: str | None = None
    """统计开始日期"""
    
    end_date: str | None = None
    """统计结束日期"""
    
    @classmethod
    def from_domain(cls, stats: Any) -> StatisticsDTO:
        """从领域统计对象创建 DTO"""
        return cls(
            income_total=float(stats.income_total.amount),
            expense_total=float(stats.expense_total.amount),
            net=float(stats.net.amount),
            income_count=stats.income_count,
            expense_count=stats.expense_count,
            start_date=stats.start_date.isoformat() if stats.start_date else None,
            end_date=stats.end_date.isoformat() if stats.end_date else None,
        )
