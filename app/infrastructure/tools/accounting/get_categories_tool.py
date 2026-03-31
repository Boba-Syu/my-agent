"""
获取分类工具实现

职责：
- 返回支持的记账分类列表

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging

from app.domain.accounting.accounting_tool_interfaces import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
)
from app.domain.agent.agent_tool import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class GetCategoriesTool(AgentTool):
    """获取记账分类工具
    
    返回所有支持的记账分类。
    """
    
    @property
    def name(self) -> str:
        return "get_accounting_categories"
    
    @property
    def description(self) -> str:
        return "获取所有记账分类（支出分类和收入分类）"
    
    @property
    def parameters(self) -> dict:
        return {}  # 无参数
    
    def execute(self) -> ToolResult:
        """执行获取分类操作
        
        Returns:
            工具执行结果
        """
        try:
            categories = {
                "expense": EXPENSE_CATEGORIES,
                "income": INCOME_CATEGORIES,
            }
            
            # 构建可读文本
            lines = ["📋 记账分类列表", ""]
            
            lines.append("💸 支出分类：")
            for cat in EXPENSE_CATEGORIES:
                lines.append(f"  - {cat}")
            
            lines.extend(["", "💰 收入分类："])
            for cat in INCOME_CATEGORIES:
                lines.append(f"  - {cat}")
            
            content = "\n".join(lines)
            
            return ToolResult.success_result(content=content, data=categories)
            
        except Exception as e:
            logger.error(f"获取分类失败: {e}", exc_info=True)
            return ToolResult.error_result(f"获取分类失败: {str(e)}")
