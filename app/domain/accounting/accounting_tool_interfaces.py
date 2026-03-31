"""
记账工具接口定义

职责：
- 定义记账领域工具的抽象接口
- 领域层定义，不依赖任何基础设施

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.agent.agent_tool import AgentTool, ToolResult


class AddTransactionService(ABC):
    """添加记账服务接口
    
    由基础设施层实现，领域层的工具通过此接口进行记账操作。
    """
    
    @abstractmethod
    def add_transaction(
        self,
        transaction_type: str,
        category: str,
        amount: Decimal,
        transaction_date: date,
        note: str = "",
    ) -> dict[str, Any]:
        """添加记账记录
        
        Args:
            transaction_type: 交易类型 "income" 或 "expense"
            category: 分类名称
            amount: 金额
            transaction_date: 交易日期
            note: 备注
            
        Returns:
            操作结果字典
        """
        pass


class AccountingQueryService(ABC):
    """记账查询服务接口
    
    由基础设施层实现，领域层的工具通过此接口查询数据。
    """
    
    @abstractmethod
    def query_by_sql(self, sql: str, params: dict | None = None) -> list[dict]:
        """执行SQL查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        pass
    
    @abstractmethod
    def stats_by_period(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """统计指定时间段收支
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计结果
        """
        pass
    
    @abstractmethod
    def get_categories(self) -> dict[str, list[str]]:
        """获取所有分类
        
        Returns:
            分类字典 {"expense": [...], "income": [...]}
        """
        pass


# 分类常量（领域知识）
EXPENSE_CATEGORIES = ["三餐", "日用品", "学习", "交通", "娱乐", "医疗", "其他"]
INCOME_CATEGORIES = ["工资", "奖金", "理财", "其他"]


def normalize_category(user_input: str, transaction_type: str) -> str | None:
    """规范化用户输入的分类
    
    将用户的自然语言描述映射到标准分类。
    
    Args:
        user_input: 用户输入的分类描述
        transaction_type: 交易类型
        
    Returns:
        标准分类名称，无法映射时返回 None
    """
    user_input = user_input.strip().lower()
    
    # 映射规则
    expense_mapping = {
        "餐": "三餐", "饭": "三餐", "吃": "三餐", "餐厅": "三餐", "外卖": "三餐",
        "日用": "日用品", "生活用品": "日用品", "超市": "日用品",
        "学": "学习", "书": "学习", "课程": "学习", "教育": "学习",
        "车": "交通", "地铁": "交通", "公交": "交通", "打车": "交通", "油费": "交通", "出行": "交通",
        "玩": "娱乐", "游戏": "娱乐", "电影": "娱乐", "唱k": "娱乐", "ktv": "娱乐",
        "药": "医疗", "医院": "医疗", "看病": "医疗", "体检": "医疗",
    }
    
    income_mapping = {
        "薪": "工资", "月薪": "工资", " paycheck": "工资",
        "奖": "奖金", "年终奖": "奖金", "红包": "奖金",
        "投资": "理财", "股票": "理财", "基金": "理财", "利息": "理财",
    }
    
    mapping = expense_mapping if transaction_type == "expense" else income_mapping
    
    # 直接匹配
    if user_input in mapping:
        return mapping[user_input]
    
    # 关键词匹配
    for key, value in mapping.items():
        if key in user_input or user_input in key:
            return value
    
    # 检查是否已经是标准分类
    valid_categories = EXPENSE_CATEGORIES if transaction_type == "expense" else INCOME_CATEGORIES
    if user_input in [c.lower() for c in valid_categories]:
        for c in valid_categories:
            if c.lower() == user_input:
                return c
    
    return None
