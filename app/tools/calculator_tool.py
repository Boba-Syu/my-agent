"""
计算器工具
使用 @tool 装饰器，支持基础数学表达式计算

扩展方式：在此文件中修改 calculator 函数逻辑，或新增其他数学工具函数
"""

import ast
import operator
from langchain_core.tools import tool
import logging

# 允许的安全运算符白名单
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    """安全递归求值 AST 节点，仅允许数学运算，防止代码注入"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        operand = _safe_eval(node.operand)
        return _SAFE_OPERATORS[type(node.op)](operand)
    raise ValueError(f"不支持的表达式元素：{ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """
    安全的数学表达式计算器。

    支持：加(+)、减(-)、乘(*)、除(/)、幂(**)、取模(%)、整除(//)
    不支持：函数调用、变量、字符串等非数学表达式

    Args:
        expression: 数学表达式字符串，例如 "2 + 3 * 4" 或 "2 ** 10"

    Returns:
        计算结果字符串，或错误说明
    """
    logging.debug("calculator 工具调用，入参：expression={}", expression)
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)
        # 如果结果是整数，去掉小数点
        if result == int(result):
            return str(int(result))
        return str(round(result, 10))
    except ZeroDivisionError:
        return "错误：除数不能为零"
    except ValueError as e:
        return f"错误：不支持的表达式 - {e}"
    except SyntaxError:
        return f"错误：表达式语法有误 - '{expression}'"
    except Exception as e:
        return f"计算失败：{e}"
