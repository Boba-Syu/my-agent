"""
tools 包入口
统一导出所有基础工具（非记账类），Agent 创建时按需传入

新增工具步骤：
1. 如果工具需要访问数据库，应在 app/infrastructure/tools/ 下实现
2. 如果工具是纯计算/查询类，可在本目录下新建 xxx_tool.py
3. 在此文件中 import 并添加到 ALL_TOOLS 列表

注意：记账相关工具已迁移到 app/infrastructure/tools/accounting/
"""

from __future__ import annotations

# 基础工具（无需数据库访问）
from app.tools.calculator_tool import calculator
from app.tools.search_tool import search
from app.tools.vector_search_tool import vector_search

# 从 infrastructure 层导入已实现的工具（适配器模式）
# 这些工具实现了 AgentTool 接口，需要转换为 LangChain 工具格式
from app.infrastructure.tools.accounting.calculator_tool import CalculatorTool
from app.infrastructure.tools.accounting.datetime_tool import GetCurrentDatetimeTool
from app.infrastructure.agent.langgraph.tool_adapter import ToolAdapter

# 创建 LangChain 格式的计算器工具（使用 infrastructure 实现）
_calculator_tool = CalculatorTool()
calculator_v2 = ToolAdapter.to_langchain_tool(_calculator_tool)

# 创建 LangChain 格式的日期时间工具
_datetime_tool = GetCurrentDatetimeTool()
get_current_datetime = ToolAdapter.to_langchain_tool(_datetime_tool)

# 所有可用基础工具列表（Agent 默认使用全部工具）
# 注意：记账工具通过 dependencies.py 单独注入，不在此列表
ALL_TOOLS = [
    calculator,           # 计算器（旧版 @tool 装饰器）
    search,               # 搜索工具
    vector_search,        # 向量搜索工具
    get_current_datetime, # 获取当前时间
]

__all__ = [
    "calculator",
    "search",
    "vector_search",
    "get_current_datetime",
    "ALL_TOOLS",
]
