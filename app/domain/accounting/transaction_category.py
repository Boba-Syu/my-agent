"""
交易分类值对象

定义记账分类的领域概念。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Self

from app.domain.shared.value_object import ValueObject
from app.domain.accounting.transaction import TransactionType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransactionCategory(ValueObject):
    """
    交易分类值对象
    
    分类是值对象，基于名称和类型相等。
    
    Example:
        category = TransactionCategory(
            name="餐饮",
            type=TransactionType.EXPENSE,
            icon="🍔",
        )
    """
    
    name: str
    """分类名称"""
    
    category_type: TransactionType
    """分类类型（收入/支出）"""
    
    icon: str = ""
    """分类图标（可选）"""
    
    description: str = ""
    """分类描述（可选）"""
    
    def __post_init__(self):
        """规范化名称"""
        object.__setattr__(self, "name", self.name.strip())
    
    @property
    def type_str(self) -> str:
        """类型字符串表示"""
        return "收入" if self.category_type == TransactionType.INCOME else "支出"
    
    @classmethod
    def income_category(
        cls,
        name: str,
        icon: str = "",
        description: str = "",
    ) -> Self:
        """创建收入分类"""
        return cls(
            name=name,
            category_type=TransactionType.INCOME,
            icon=icon,
            description=description,
        )
    
    @classmethod
    def expense_category(
        cls,
        name: str,
        icon: str = "",
        description: str = "",
    ) -> Self:
        """创建支出分类"""
        return cls(
            name=name,
            category_type=TransactionType.EXPENSE,
            icon=icon,
            description=description,
        )


# 默认分类定义
DEFAULT_EXPENSE_CATEGORIES: list[TransactionCategory] = [
    TransactionCategory.expense_category("餐饮", "🍔", "三餐、零食、饮料"),
    TransactionCategory.expense_category("交通", "🚗", "公交、地铁、打车、加油"),
    TransactionCategory.expense_category("购物", "🛍️", "日用品、服装、电子产品"),
    TransactionCategory.expense_category("娱乐", "🎮", "游戏、电影、旅游"),
    TransactionCategory.expense_category("居住", "🏠", "房租、水电、物业"),
    TransactionCategory.expense_category("医疗", "🏥", "看病、买药"),
    TransactionCategory.expense_category("教育", "📚", "学费、书籍、培训"),
    TransactionCategory.expense_category("通讯", "📱", "话费、网费"),
    TransactionCategory.expense_category("其他", "📝", "其他支出"),
]

DEFAULT_INCOME_CATEGORIES: list[TransactionCategory] = [
    TransactionCategory.income_category("工资", "💰", "月薪、奖金"),
    TransactionCategory.income_category("兼职", "💼", "副业、兼职收入"),
    TransactionCategory.income_category("投资", "📈", "股票、基金、理财收益"),
    TransactionCategory.income_category("红包", "🧧", "红包、礼金"),
    TransactionCategory.income_category("其他", "📝", "其他收入"),
]


def get_default_categories(
    transaction_type: TransactionType | None = None,
) -> list[TransactionCategory]:
    """
    获取默认分类列表
    
    Args:
        transaction_type: 交易类型过滤，None 返回所有
        
    Returns:
        分类列表
    """
    if transaction_type == TransactionType.INCOME:
        return DEFAULT_INCOME_CATEGORIES
    elif transaction_type == TransactionType.EXPENSE:
        return DEFAULT_EXPENSE_CATEGORIES
    else:
        return DEFAULT_INCOME_CATEGORIES + DEFAULT_EXPENSE_CATEGORIES


def get_category_names(transaction_type: TransactionType) -> list[str]:
    """
    获取分类名称列表
    
    Args:
        transaction_type: 交易类型
        
    Returns:
        分类名称列表
    """
    categories = get_default_categories(transaction_type)
    return [c.name for c in categories]
