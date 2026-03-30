"""
交易统计数据

收支统计的值对象。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.accounting.money import Money

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransactionStatistics:
    """
    交易统计数据值对象
    
    汇总指定时间段内的收支情况。
    
    Example:
        stats = TransactionStatistics(
            income_total=Money(Decimal("10000")),
            expense_total=Money(Decimal("5000")),
            income_count=2,
            expense_count=15,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        
        print(f"结余: {stats.net.format()}")  # "¥5000.00"
    """
    
    income_total: Money
    """收入总额"""
    
    expense_total: Money
    """支出总额"""
    
    income_count: int
    """收入笔数"""
    
    expense_count: int
    """支出笔数"""
    
    start_date: date | None = None
    """统计开始日期"""
    
    end_date: date | None = None
    """统计结束日期"""
    
    @property
    def net(self) -> Money:
        """
        净收支（收入 - 支出）
        
        Returns:
            净金额，正数表示盈余，负数表示赤字
        """
        return self.income_total - self.expense_total
    
    @property
    def total_count(self) -> int:
        """总笔数"""
        return self.income_count + self.expense_count
    
    @property
    def income_average(self) -> Money:
        """平均收入"""
        if self.income_count == 0:
            return Money.zero()
        return self.income_total / self.income_count
    
    @property
    def expense_average(self) -> Money:
        """平均支出"""
        if self.expense_count == 0:
            return Money.zero()
        return self.expense_total / self.expense_count
    
    @property
    def is_surplus(self) -> bool:
        """是否盈余（收入 > 支出）"""
        return self.net.is_positive()
    
    @property
    def is_deficit(self) -> bool:
        """是否赤字（支出 > 收入）"""
        return self.net.is_negative()
    
    @property
    def expense_ratio(self) -> float:
        """支出占比"""
        total = self.income_total.amount + self.expense_total.amount
        if total == 0:
            return 0.0
        return float(self.expense_total.amount / total)
    
    @property
    def savings_rate(self) -> float:
        """储蓄率（结余/收入）"""
        if self.income_total.is_zero():
            return 0.0
        return float(self.net.amount / self.income_total.amount)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "income_total": self.income_total.to_dict(),
            "expense_total": self.expense_total.to_dict(),
            "net": self.net.to_dict(),
            "income_count": self.income_count,
            "expense_count": self.expense_count,
            "total_count": self.total_count,
            "income_average": self.income_average.to_dict(),
            "expense_average": self.expense_average.to_dict(),
            "is_surplus": self.is_surplus,
            "is_deficit": self.is_deficit,
            "expense_ratio": self.expense_ratio,
            "savings_rate": self.savings_rate,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }
    
    @classmethod
    def empty(cls, start_date: date | None = None, end_date: date | None = None) -> TransactionStatistics:
        """创建空的统计数据"""
        return cls(
            income_total=Money.zero(),
            expense_total=Money.zero(),
            income_count=0,
            expense_count=0,
            start_date=start_date,
            end_date=end_date,
        )
