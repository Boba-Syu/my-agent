"""
交易聚合根

记账系统的核心领域模型，代表一笔收入或支出。
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.accounting.money import Money

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """交易类型"""
    
    INCOME = "income"
    """收入"""
    
    EXPENSE = "expense"
    """支出"""


class Transaction(AggregateRoot):
    """
    记账交易聚合根
    
    聚合边界包含交易的所有属性：
    - 交易类型（收入/支出）
    - 分类
    - 金额
    - 交易日期
    - 备注
    
    业务规则：
    - 金额必须为正数
    - 分类必须符合交易类型
    - 交易日期不能是未来的日期
    
    Example:
        transaction = Transaction(
            id=None,
            transaction_type=TransactionType.EXPENSE,
            category="餐饮",
            amount=Money(Decimal("50.00")),
            transaction_date=date.today(),
            note="午餐",
        )
        
        # 更新交易
        transaction.update(
            category="外卖",
            note="外卖午餐",
        )
    """

    def __init__(
        self,
        id: int | None,
        transaction_type: TransactionType,
        category: str,
        amount: Money,
        transaction_date: date,
        note: str = "",
        created_at: datetime | None = None,
    ):
        """
        初始化交易聚合根
        
        Args:
            id: 交易 ID，None 表示新交易
            transaction_type: 交易类型（收入/支出）
            category: 分类名称
            amount: 金额（Money 值对象）
            transaction_date: 交易日期
            note: 备注
            created_at: 创建时间
            
        Raises:
            ValueError: 参数验证失败
        """
        super().__init__(str(id) if id else None)
        
        # 验证金额
        if not amount.is_positive():
            raise ValueError("交易金额必须为正数")
        
        # 验证日期
        if transaction_date > date.today():
            raise ValueError("交易日期不能是未来日期")
        
        self._id = id
        self._transaction_type = transaction_type
        self._category = category
        self._amount = amount
        self._transaction_date = transaction_date
        self._note = note
        self._created_at = created_at or datetime.now()
        self._version = 0
        
        logger.debug(f"创建交易: {self}")

    # -------------------------------------------------------------------------
    # 属性
    # -------------------------------------------------------------------------

    @property
    def transaction_type(self) -> TransactionType:
        """交易类型"""
        return self._transaction_type

    @property
    def transaction_type_str(self) -> str:
        """交易类型字符串"""
        return "收入" if self._transaction_type == TransactionType.INCOME else "支出"

    @property
    def category(self) -> str:
        """分类"""
        return self._category

    @property
    def amount(self) -> Money:
        """金额"""
        return self._amount

    @property
    def transaction_date(self) -> date:
        """交易日期"""
        return self._transaction_date

    @property
    def note(self) -> str:
        """备注"""
        return self._note

    @property
    def created_at(self) -> datetime:
        """创建时间"""
        return self._created_at

    @property
    def version(self) -> int:
        """版本号（乐观锁）"""
        return self._version

    @property
    def is_income(self) -> bool:
        """是否为收入"""
        return self._transaction_type == TransactionType.INCOME

    @property
    def is_expense(self) -> bool:
        """是否为支出"""
        return self._transaction_type == TransactionType.EXPENSE

    # -------------------------------------------------------------------------
    # 业务方法
    # -------------------------------------------------------------------------

    def update(
        self,
        category: str | None = None,
        amount: Money | None = None,
        transaction_date: date | None = None,
        note: str | None = None,
    ) -> None:
        """
        更新交易信息
        
        遵循业务规则进行更新，递增版本号。
        
        Args:
            category: 新分类
            amount: 新金额
            transaction_date: 新日期
            note: 新备注
            
        Raises:
            ValueError: 参数验证失败
        """
        if amount is not None:
            if not amount.is_positive():
                raise ValueError("金额必须为正数")
            self._amount = amount
        
        if transaction_date is not None:
            if transaction_date > date.today():
                raise ValueError("交易日期不能是未来日期")
            self._transaction_date = transaction_date
        
        if category is not None:
            self._category = category
        
        if note is not None:
            self._note = note
        
        self._increment_version()
        logger.debug(f"交易已更新: {self}")

    def to_snapshot(self) -> dict:
        """
        生成快照
        
        Returns:
            交易的字典表示
        """
        return {
            "id": self._id,
            "transaction_type": self._transaction_type.value,
            "category": self._category,
            "amount": float(self._amount.amount),
            "transaction_date": self._transaction_date.isoformat(),
            "note": self._note,
            "created_at": self._created_at.isoformat(),
            "version": self._version,
        }

    def __repr__(self) -> str:
        return (
            f"Transaction("
            f"id={self._id}, "
            f"type={self._transaction_type.value}, "
            f"category={self._category!r}, "
            f"amount={self._amount.format()}, "
            f"date={self._transaction_date.isoformat()}"
            f")"
        )
