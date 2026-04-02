"""
Agent 框架 Hello World 测试（DDD 架构版本）

运行方式：
    uv run python tests/test_helloworld.py

功能：
- 使用 AgentFactory 创建 Agent（符合 DDD 架构）
- 测试基础对话和工具调用
"""

from __future__ import annotations

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.application.agent.agent_factory import AgentFactory
from app.infrastructure.tools.accounting import CalculatorTool, GetCurrentDatetimeTool


def main() -> None:
    print("=" * 60)
    print("Agent 框架 Hello World 测试")
    print("=" * 60)

    # 使用 AgentFactory 创建 Agent（符合 DDD 架构）
    factory = AgentFactory()

    # 创建工具列表
    tools = [
        CalculatorTool(),
        GetCurrentDatetimeTool(),
    ]

    # 创建 Agent
    agent = factory.create_agent(
        model="deepseek-v3",
        tools=tools,
        system_prompt="你是一个智能助手，尽量简洁地回答用户问题。",
    )

    print(f"Agent 创建成功，工具列表: {[t.name for t in tools]}")
    print("=" * 60)

    # 测试 1：普通对话
    print("\n【测试 1】普通对话")
    response = agent.invoke("你好，介绍一下你自己", thread_id="test-001")
    print(f"用户: 你好，介绍一下你自己")
    print(f"Agent: {response.content}")

    # 测试 2：工具调用（计算）
    print("\n【测试 2】工具调用（计算）")
    response = agent.invoke("帮我计算 (256 + 128) * 3 的结果", thread_id="test-001")
    print(f"用户: 帮我计算 (256 + 128) * 3 的结果")
    print(f"Agent: {response.content}")

    # 测试 3：获取当前时间
    print("\n【测试 3】获取当前时间")
    response = agent.invoke("现在几点了？今天是几号？", thread_id="test-001")
    print(f"用户: 现在几点了？今天是几号？")
    print(f"Agent: {response.content}")

    print("\n" + "=" * 60)
    print("测试完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
