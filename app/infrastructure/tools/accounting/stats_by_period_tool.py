"""
按时间段统计工具实现

职责：
- 实现时间段统计功能
- 通过 TransactionRepository 接口查询统计数据

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from app.domain.accounting.transaction import TransactionType
from app.domain.agent.agent_tool import AgentTool, ToolResult

if TYPE_CHECKING:
    from app.domain.accounting.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class StatsByPeriodTool(AgentTool):
    """按时间段统计工具
    
    通过 TransactionRepository 接口查询统计数据，
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
        return "stats_by_period"
    
    @property
    def description(self) -> str:
        return """
        统计指定时间段的收支情况。
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期 YYYY-MM-DD",
                },
            },
            "required": ["start_date", "end_date"],
        }
    
    def execute(self, start_date: str, end_date: str) -> ToolResult:
        """执行统计操作
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            工具执行结果
        """
        try:
            # 解析日期
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            
            # 通过 Repository 获取统计数据
            stats = self._repository.get_statistics(start_date=start, end_date=end)
            
            # 获取分类汇总
            income_by_category = self._repository.get_categories_summary(
                transaction_type=TransactionType("income"),
                start_date=start,
                end_date=end,
            )
            expense_by_category = self._repository.get_categories_summary(
                transaction_type=TransactionType("expense"),
                start_date=start,
                end_date=end,
            )
            
            # 构建结果
            # Money 对象需要通过 .amount 获取 Decimal 值，再转换为 float
            data = {
                "start_date": start_date,
                "end_date": end_date,
                "income": {
                    "total": float(stats.income_total.amount),
                    "count": stats.income_count,
                    "by_category": income_by_category,
                },
                "expense": {
                    "total": float(stats.expense_total.amount),
                    "count": stats.expense_count,
                    "by_category": expense_by_category,
                },
                "net": float(stats.net.amount),
            }
            
            # 构建可读文本
            lines = [
                f"📊 {start_date} 至 {end_date} 收支统计",
                "",
                f"💰 收入：{float(stats.income_total.amount):.2f} 元（{stats.income_count} 笔）",
            ]
            
            if income_by_category:
                for item in income_by_category[:5]:  # 前5个分类
                    lines.append(f"  - {item['category']}: {item['total']:.2f} 元")
            
            lines.extend([
                "",
                f"💸 支出：{float(stats.expense_total.amount):.2f} 元（{stats.expense_count} 笔）",
            ])
            
            if expense_by_category:
                for item in expense_by_category[:5]:  # 前5个分类
                    lines.append(f"  - {item['category']}: {item['total']:.2f} 元")
            
            lines.extend([
                "",
                f"📈 结余：{float(stats.net.amount):.2f} 元",
            ])
            
            content = "\n".join(lines)
            
            logger.info(f"统计完成: 收入={stats.income_total}, 支出={stats.expense_total}")
            
            return ToolResult.success_result(content=content, data=data)
            
        except Exception as e:
            logger.error(f"统计失败: {e}", exc_info=True)
            return ToolResult.error_result(f"统计失败: {str(e)}")
