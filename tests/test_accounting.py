"""
记账 Agent 测试脚本

运行方式：
    uv run python tests/test_accounting.py

功能覆盖：
1. 数据库表初始化
2. 自然语言记账（支出 / 收入）
3. 收支统计查询
4. 分类统计
5. 数据导出（Excel + Markdown）
"""

from __future__ import annotations

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.accounting_db import init_accounting_tables
from app.agent.accounting_agent import create_accounting_agent


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def run_test(agent, message: str, thread_id: str = "test-001") -> str:
    print(f"\n👤 用户: {message}")
    reply = agent.invoke(message, thread_id=thread_id)
    print(f"🤖 Agent: {reply}")
    return reply


def main() -> None:
    separator("初始化记账数据库")
    init_accounting_tables()
    print("✅ 数据库表初始化完成")

    separator("创建记账 Agent")
    agent = create_accounting_agent(model="deepseek-v3")
    print("✅ 记账 Agent 创建成功")

    separator("测试 1：记录支出")
    run_test(agent, "今天早上花了15块钱吃早饭", thread_id="t1")
    run_test(agent, "午饭花了32元，在食堂", thread_id="t1")
    run_test(agent, "打车去公司花了28块", thread_id="t1")
    run_test(agent, "买了一本Python书，花了89元，用于学习", thread_id="t1")

    separator("测试 2：记录收入")
    run_test(agent, "今天收到本月工资12000元", thread_id="t2")
    run_test(agent, "收到年终奖5000块", thread_id="t2")

    separator("测试 3：查询统计")
    run_test(agent, "统计一下今天的收支情况", thread_id="t3")
    run_test(agent, "本月各类支出分别是多少？", thread_id="t3")
    run_test(agent, "查询最近5条记账记录", thread_id="t3")

    separator("测试 4：复杂计算")
    run_test(agent, "今天三餐一共花了多少钱？把所有三餐的金额加起来", thread_id="t4")

    separator("测试 5：导出数据")
    run_test(agent, "把所有记账记录导出为Markdown格式", thread_id="t5")

    separator("测试完成 ✅")


if __name__ == "__main__":
    main()
