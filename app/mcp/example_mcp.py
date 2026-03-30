"""
MCP（Model Context Protocol）示例扩展模块

MCP 是一种标准化协议，允许 AI 模型与外部工具、数据源安全交互。
此文件演示 MCP 工具的封装模式，可替换为真实 MCP 服务对接。

扩展方式：
1. 复制此文件，重命名为 xxx_mcp.py
2. 修改 MCPTool 类的 name/description/run 方法
3. 在需要时实例化并调用，或通过 mcp_to_langchain_tool() 转换为 LangChain tool
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


class BaseMCPTool(ABC):
    """
    MCP 工具基类
    所有 MCP 工具应继承此类并实现 name、description 和 run 方法
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（供 LLM 理解工具用途）"""
        ...

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """
        工具执行逻辑

        Args:
            **kwargs: 工具调用参数

        Returns:
            执行结果字符串
        """
        ...

    def to_langchain_tool(self) -> StructuredTool:
        """
        将 MCP 工具转换为 LangChain StructuredTool，
        使其可以直接传入 ReactAgent 的 tools 列表

        Returns:
            LangChain StructuredTool 实例
        """
        # 捕获 self 引用
        _self = self

        def _run(**kwargs: Any) -> str:
            return _self.run(**kwargs)

        return StructuredTool.from_function(
            func=_run,
            name=self.name,
            description=self.description,
        )


class ExampleMCPTool(BaseMCPTool):
    """
    示例 MCP 工具：模拟获取天气信息

    实际使用时，替换 run 方法中的逻辑，对接真实 MCP 服务端点
    （例如：通过 HTTP 请求调用 MCP 服务器）
    """

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return (
            "获取指定城市的天气信息。"
            "当用户询问天气时使用此工具。"
            "参数：city（城市名称，字符串）"
        )

    def run(self, city: str = "北京") -> str:
        """
        获取城市天气（当前为模拟数据）

        Args:
            city: 城市名称

        Returns:
            天气信息字符串
        """
        # -------------------------------------------------------
        # TODO：替换为真实 MCP 服务调用
        # 示例：
        #   import httpx
        #   response = httpx.post(
        #       "http://mcp-server/tools/call",
        #       json={"name": "get_weather", "arguments": {"city": city}}
        #   )
        #   return response.json()["result"]
        # -------------------------------------------------------
        logger.debug(f"MCP 工具调用：get_weather, city={city}")
        mock_data = {
            "北京": "晴天，温度 22°C，湿度 45%，东南风 3 级",
            "上海": "多云，温度 18°C，湿度 70%，东风 2 级",
            "广州": "小雨，温度 26°C，湿度 85%，南风 2 级",
        }
        weather = mock_data.get(city, f"{city}：晴天，温度 20°C，湿度 50%（模拟数据）")
        return f"{city} 当前天气：{weather}"


# 导出可用的 MCP 工具实例
example_mcp_tool = ExampleMCPTool()

# 转换为 LangChain 工具（可直接加入 Agent 工具列表）
get_weather = example_mcp_tool.to_langchain_tool()
