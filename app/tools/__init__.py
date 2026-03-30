"""
tools 包入口
统一导出所有工具，Agent 创建时按需传入

新增工具步骤：
1. 在 tools/ 目录下新建 xxx_tool.py，用 @tool 装饰器定义工具函数
2. 在此文件中 import 并添加到 ALL_TOOLS 列表
"""

from app.tools.calculator_tool import calculator
from app.tools.search_tool import search
from app.tools.vector_search_tool import vector_search

# 所有可用工具列表（Agent 默认使用全部工具）
ALL_TOOLS = [
    calculator,
    search,
    vector_search,
]

__all__ = ["calculator", "search", "vector_search", "ALL_TOOLS"]
