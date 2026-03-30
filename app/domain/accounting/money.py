"""
金额值对象

表示货币金额，保证精度和类型安全。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Self

from app.domain.shared.value_object import ValueObject

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Money(ValueObject):
    """
    金额值对象
    
    使用 Decimal 保证精度，避免浮点数误差。
    
    Example:
        m1 = Money(Decimal("100.50"))
        m2 = Money(Decimal("50.25"))
        m3 = m1 + m2  # Money(Decimal("150.75"))
        
        # 格式化输出
        print(m1.format())  # "¥100.50"
    """
    
    amount: Decimal
    """金额数值"""
    
    currency: str = "CNY"
    """货币代码（默认人民币）"""
    
    PRECISION: int = 2
    """小数精度"""
    
    def __post_init__(self):
        """规范化金额精度"""
        # 四舍五入到指定精度
        quantized = self.amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        object.__setattr__(self, "amount", quantized)
    
    def __add__(self, other: Money) -> Money:
        """金额相加"""
        if not isinstance(other, Money):
            raise TypeError("只能与 Money 类型相加")
        if self.currency != other.currency:
            raise ValueError("不同货币不能相加")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: Money) -> Money:
        """金额相减"""
        if not isinstance(other, Money):
            raise TypeError("只能与 Money 类型相减")
        if self.currency != other.currency:
            raise ValueError("不同货币不能相减")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: int | float | Decimal) -> Money:
        """金额乘以倍数"""
        return Money(self.amount * Decimal(str(multiplier)), self.currency)
    
    def __truediv__(self, divisor: int | float | Decimal) -> Money:
        """金额除以倍数"""
        return Money(self.amount / Decimal(str(divisor)), self.currency)
    
    def __lt__(self, other: Money) -> bool:
        """小于比较"""
        if not isinstance(other, Money):
            raise TypeError("只能与 Money 类型比较")
        return self.amount < other.amount
    
    def __le__(self, other: Money) -> bool:
        """小于等于比较"""
        return self < other or self == other
    
    def __gt__(self, other: Money) -> bool:
        """大于比较"""
        return not self <= other
    
    def __ge__(self, other: Money) -> bool:
        """大于等于比较"""
        return not self < other
    
    def __neg__(self) -> Money:
        """取负"""
        return Money(-self.amount, self.currency)
    
    def __abs__(self) -> Money:
        """绝对值"""
        return Money(abs(self.amount), self.currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: str = "CNY") -> Self:
        """
        从 float 创建（尽量避免使用）
        
        Args:
            amount: 浮点金额
            currency: 货币代码
            
        Returns:
            Money 实例
        """
        return cls(Decimal(str(amount)), currency)
    
    @classmethod
    def zero(cls, currency: str = "CNY") -> Self:
        """创建零金额"""
        return cls(Decimal("0"), currency)
    
    def is_zero(self) -> bool:
        """是否为零"""
        return self.amount == Decimal("0")
    
    def is_positive(self) -> bool:
        """是否为正数"""
        return self.amount > Decimal("0")
    
    def is_negative(self) -> bool:
        """是否为负数"""
        return self.amount < Decimal("0")
    
    def format(self, symbol: bool = True) -> str:
        """
        格式化为字符串
        
        Args:
            symbol: 是否包含货币符号
            
        Returns:
            格式化后的金额字符串
        """
        symbols = {
            "CNY": "¥",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
        }
        
        formatted = f"{self.amount:,.2f}"
        if symbol:
            currency_symbol = symbols.get(self.currency, self.currency)
            return f"{currency_symbol}{formatted}"
        return formatted
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "amount": float(self.amount),
            "currency": self.currency,
        }
