"""
查询记账数据工具实现

职责：
- 实现记账数据查询功能
- 通过 TransactionRepository 接口查询数据

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain.agent.agent_tool import AgentTool, ToolResult

if TYPE_CHECKING:
    from app.domain.accounting.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class QueryAccountingTool(AgentTool):
    """查询记账数据工具
    
    通过 TransactionRepository 接口查询数据，
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
        return "query_accounting_data"
    
    @property
    def description(self) -> str:
        return """
        查询记账记录。
        
        支持按条件过滤查询。
        
        Args:
            transaction_type: 交易类型过滤，可选 "income" 或 "expense"
            category: 分类名称过滤
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 最大返回条数，默认 50
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "description": '交易类型过滤，"income" 或 "expense"',
                },
                "category": {
                    "type": "string",
                    "description": "分类名称过滤",
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期 YYYY-MM-DD",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回条数",
                    "default": 50,
                },
            },
            "required": [],
        }
    
    def execute(
        self,
        transaction_type: str | None = None,
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
    ) -> ToolResult:
        """执行查询操作
        
        Args:
            transaction_type: 交易类型过滤
            category: 分类过滤
            start_date: 起始日期
            end_date: 结束日期
            limit: 最大返回条数
            
        Returns:
            工具执行结果
        """
        try:
            from datetime import date
            from app.domain.accounting.transaction import TransactionType
            
            # 构建查询参数
            trans_type = None
            if transaction_type:
                try:
                    trans_type = TransactionType(transaction_type)
                except ValueError:
                    return ToolResult.error_result(
                        f"无效的交易类型: {transaction_type}"
                    )
            
            start = date.fromisoformat(start_date) if start_date else None
            end = date.fromisoformat(end_date) if end_date else None
            
            # 通过 Repository 查询
            transactions = self._repository.list(
                transaction_type=trans_type,
                category=category,
                start_date=start,
                end_date=end,
                limit=limit,
            )
            
            # 转换为可序列化的格式
            results = [
                {
                    "id": t.id,
                    "transaction_type": t.transaction_type.value,
                    "category": t.category,
                    "amount": float(t.amount.amount),
                    "transaction_date": t.transaction_date.isoformat(),
                    "note": t.note,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in transactions
            ]
            
            logger.info(f"查询到 {len(results)} 条记录")
            
            return ToolResult.success_result(
                content=f"查询到 {len(results)} 条记录",
                data={"count": len(results), "records": results},
            )
            
        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            return ToolResult.error_result(f"查询失败: {str(e)}")
