"""
记账子域

定义记账领域的核心概念：
- Transaction: 交易聚合根
- Money: 金额值对象
- TransactionCategory: 交易分类
- TransactionRepository: 仓库接口
- TransactionStatistics: 统计数据
- AccountingToolInterfaces: 记账工具接口
"""

from __future__ import annotations

from app.domain.accounting.accounting_tool_interfaces import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    normalize_category,
)
from app.domain.accounting.money import Money
from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.accounting.transaction_category import TransactionCategory
from app.domain.accounting.transaction_repository import TransactionRepository
from app.domain.accounting.transaction_statistics import TransactionStatistics

__all__ = [
    "Money",
    "Transaction",
    "TransactionType",
    "TransactionCategory",
    "TransactionRepository",
    "TransactionStatistics",
    "EXPENSE_CATEGORIES",
    "INCOME_CATEGORIES",
    "normalize_category",
]
