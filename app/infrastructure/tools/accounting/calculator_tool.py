"""
计算器工具实现

职责：
- 安全地执行数学计算表达式

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import ast
import logging
import operator
from typing import Any

from app.domain.agent.agent_tool import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class CalculatorTool(AgentTool):
    """计算器工具
    
    安全地执行数学计算表达式。
    """
    
    # 支持的操作符
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """
        执行数学计算。支持 +, -, *, /, ** 等运算符。
        
        Args:
            expression: 数学表达式字符串，如 "100 * 1.08 + 50"
        """
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '100 + 50 * 2'",
                }
            },
            "required": ["expression"],
        }
    
    def execute(self, expression: str) -> ToolResult:
        """执行计算
        
        Args:
            expression: 数学表达式
            
        Returns:
            工具执行结果
        """
        try:
            result = self._safe_eval(expression)
            return ToolResult.success_result(
                content=str(result),
                data={"expression": expression, "result": result},
            )
        except Exception as e:
            logger.error(f"计算错误: {e}")
            return ToolResult.error_result(f"计算失败: {str(e)}")
    
    def _safe_eval(self, expression: str) -> float:
        """安全地评估数学表达式
        
        Args:
            expression: 表达式字符串
            
        Returns:
            计算结果
        """
        tree = ast.parse(expression.strip(), mode='eval')
        return self._eval_node(tree.body)
    
    def _eval_node(self, node: ast.AST) -> float:
        """递归计算 AST 节点
        
        Args:
            node: AST节点
            
        Returns:
            计算结果
        """
        if isinstance(node, ast.Num):
            return float(node.n)
        elif isinstance(node, ast.Constant):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self._OPERATORS[op_type](operand)
        else:
            raise ValueError(f"不支持的表达式类型: {type(node).__name__}")
