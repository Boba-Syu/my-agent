"""
值对象基类

值对象是基于属性相等的不可变对象，没有唯一标识。
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    值对象基类
    
    特性：
    - 不可变（frozen=True）
    - 基于属性相等（而非标识）
    - 无生命周期概念
    
    Example:
        @dataclass(frozen=True)
        class Money(ValueObject):
            amount: Decimal
            currency: str
            
        m1 = Money(Decimal("100"), "CNY")
        m2 = Money(Decimal("100"), "CNY")
        assert m1 == m2  # True，基于属性相等
    """

    def __eq__(self, other: object) -> bool:
        """
        基于属性值相等
        
        两个值对象所有属性相同则视为相等。
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """基于属性值的哈希"""
        return hash(tuple(self.__dict__.values()))

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"
