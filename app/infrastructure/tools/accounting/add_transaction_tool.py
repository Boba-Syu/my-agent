"""
添加记账工具实现

职责：
- 实现添加记账记录功能
- 通过 TransactionRepository 接口操作数据

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.accounting.accounting_tool_interfaces import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    normalize_category,
)
from app.domain.accounting.money import Money
from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.agent.agent_tool import AgentTool, ToolResult

if TYPE_CHECKING:
    from app.domain.accounting.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class AddTransactionTool(AgentTool):
    """添加记账工具
    
    通过 TransactionRepository 接口添加记账记录，
    不直接访问数据库。
    """
    
    def __init__(self, repository: TransactionRepository) -> None:
        """初始化工具
        
        Args:
            repository: 交易仓库接口
        """
        self._repository = repository
    
    @property
    def name(self) -> str:
        return "add_transaction"
    
    @property
    def description(self) -> str:
        return """
        添加一条记账记录。
        
        Args:
            transaction_type: 交易类型，"income"(收入) 或 "expense"(支出)
            category: 分类名称
            amount: 金额（正数）
            transaction_date: 交易日期 YYYY-MM-DD
            note: 备注（可选）
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "description": '交易类型，"income"(收入) 或 "expense"(支出)',
                },
                "category": {
                    "type": "string",
                    "description": "分类名称",
                },
                "amount": {
                    "type": "number",
                    "description": "金额（正数）",
                },
                "transaction_date": {
                    "type": "string",
                    "description": "交易日期 YYYY-MM-DD",
                },
                "note": {
                    "type": "string",
                    "description": "备注（可选）",
                },
            },
            "required": ["transaction_type", "category", "amount", "transaction_date"],
        }
    
    def execute(
        self,
        transaction_type: str,
        category: str,
        amount: float,
        transaction_date: str,
        note: str = "",
    ) -> ToolResult:
        """执行添加记账操作
        
        Args:
            transaction_type: 交易类型
            category: 分类
            amount: 金额
            transaction_date: 日期字符串
            note: 备注
            
        Returns:
            工具执行结果
        """
        try:
            # 验证交易类型
            if transaction_type not in ("income", "expense"):
                return ToolResult.error_result(
                    f"无效的交易类型: {transaction_type}，应为 'income' 或 'expense'"
                )
            
            # 规范化分类
            normalized_category = normalize_category(category, transaction_type)
            if normalized_category is None:
                valid_categories = (
                    EXPENSE_CATEGORIES if transaction_type == "expense" else INCOME_CATEGORIES
                )
                return ToolResult.error_result(
                    f"无效的分类: {category}，{transaction_type} 的有效分类为: {valid_categories}"
                )
            
            # 验证金额
            if amount <= 0:
                return ToolResult.error_result(f"金额必须大于 0，当前值: {amount}")
            
            # 解析日期
            try:
                trans_date = date.fromisoformat(transaction_date)
            except ValueError:
                return ToolResult.error_result(f"无效的日期格式: {transaction_date}，应为 YYYY-MM-DD")
            
            # 创建领域实体
            transaction = Transaction(
                id=None,
                transaction_type=TransactionType(transaction_type),
                category=normalized_category,
                amount=Money(Decimal(str(amount))),
                transaction_date=trans_date,
                note=note,
            )
            
            # 通过 Repository 保存
            saved = self._repository.save(transaction)
            
            logger.info(f"记账成功: {saved.id} - {saved.category} {saved.transaction_type.value} {saved.amount.amount}")
            
            return ToolResult.success_result(
                content=f"记账成功：{normalized_category} {transaction_type} {amount}元",
                data={
                    "transaction_id": saved.id,
                    "transaction_type": transaction_type,
                    "category": normalized_category,
                    "amount": amount,
                    "transaction_date": transaction_date,
                    "note": note,
                },
            )
            
        except Exception as e:
            logger.error(f"记账失败: {e}", exc_info=True)
            return ToolResult.error_result(f"记账失败: {str(e)}")
