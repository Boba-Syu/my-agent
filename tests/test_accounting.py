"""
记账 Agent 测试脚本（DDD 架构版本）

运行方式：
    uv run python tests/test_accounting.py

功能覆盖：
1. 数据库表初始化（通过 Repository）
2. TransactionService 直接操作交易记录
3. AccountingAgentService 自然语言记账
4. 收支统计查询
5. 分类统计
"""

from __future__ import annotations

import sys
import os
import asyncio
import logging

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_accounting")

from app.db.sqlite_client import SQLiteClient
from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository
from app.application.accounting.transaction_service import TransactionService
from app.application.accounting.accounting_agent_service import AccountingAgentService
from app.application.accounting.dto import CreateTransactionDTO
from app.application.agent.agent_factory import AgentFactory
from app.infrastructure.agent.cache.agent_cache import InMemoryAgentCache
from app.infrastructure.tools.accounting import (
    AddTransactionTool,
    CalculatorTool,
    GetCategoriesTool,
    GetCurrentDatetimeTool,
    QueryAccountingTool,
    StatsByPeriodTool,
)


def separator(title: str) -> None:
    """打印分隔符"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def init_database() -> None:
    """初始化数据库表"""
    # 通过 SQLiteClient 直接执行建表语句
    # 实际项目中应该通过迁移脚本完成
    db = SQLiteClient()
    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN ('expense', 'income')),
            category        TEXT NOT NULL,
            amount          REAL NOT NULL CHECK(amount > 0),
            note            TEXT DEFAULT '',
            transaction_date TEXT NOT NULL DEFAULT (date('now')),
            created_at      DATETIME DEFAULT (datetime('now'))
        )
    """)
    logger.info("数据库表初始化完成")


def create_services() -> tuple[TransactionService, AccountingAgentService]:
    """
    创建应用服务
    
    Returns:
        (TransactionService, AccountingAgentService) 元组
    """
    # 创建 Repository
    repository = SQLiteTransactionRepository()
    
    # 创建 TransactionService
    transaction_service = TransactionService(repository=repository)
    
    # 创建 AccountingAgentService 所需的依赖
    agent_cache = InMemoryAgentCache()
    agent_factory = AgentFactory()
    
    # 创建记账工具列表（通过依赖注入获取 Repository）
    accounting_tools = [
        AddTransactionTool(repository=repository),
        QueryAccountingTool(repository=repository),
        StatsByPeriodTool(repository=repository),
        GetCategoriesTool(),
        GetCurrentDatetimeTool(),
        CalculatorTool(),
    ]

    # 创建 AccountingAgentService（使用 langgraph 实现）
    agent_factory = AgentFactory(default_implementation="langgraph")
    accounting_agent_service = AccountingAgentService(
        agent_cache=agent_cache,
        agent_factory=agent_factory,
        accounting_tools=accounting_tools,
    )
    
    return transaction_service, accounting_agent_service


def test_transaction_service(transaction_service: TransactionService) -> None:
    """测试 TransactionService"""
    separator("测试 TransactionService")
    
    # 创建支出记录
    expense = transaction_service.create_transaction(CreateTransactionDTO(
        transaction_type="expense",
        category="三餐",
        amount=25.5,
        transaction_date="2026-04-01",
        note="午餐",
    ))
    logger.info(f"创建支出记录: ID={expense.id}, 分类={expense.category}, 金额={expense.amount}")
    
    # 创建收入记录
    income = transaction_service.create_transaction(CreateTransactionDTO(
        transaction_type="income",
        category="工资",
        amount=15000.0,
        transaction_date="2026-04-01",
        note="月薪",
    ))
    logger.info(f"创建收入记录: ID={income.id}, 分类={income.category}, 金额={income.amount}")
    
    # 查询所有记录
    from app.application.accounting.dto import TransactionQueryDTO
    transactions = transaction_service.list_transactions(TransactionQueryDTO(limit=10))
    logger.info(f"查询到 {len(transactions)} 条记录")
    
    # 统计
    stats = transaction_service.get_statistics("2026-04-01", "2026-04-30")
    logger.info(f"月度统计: 收入={stats.income_total}, 支出={stats.expense_total}, 结余={stats.net}")


async def test_accounting_agent(accounting_service: AccountingAgentService) -> None:
    """测试 AccountingAgentService"""
    separator("测试 AccountingAgentService")
    
    test_cases = [
        ("t1", "今天早上花了15块钱吃早饭"),
        ("t1", "午饭花了32元，在食堂"),
        ("t2", "今天收到本月工资12000元"),
        ("t3", "统计一下今天的收支情况"),
    ]
    
    for thread_id, message in test_cases:
        logger.info(f"\n👤 用户: {message}")
        try:
            response = await accounting_service.chat(
                message=message,
                model="deepseek-v3",
                thread_id=thread_id,
            )
            logger.info(f"🤖 Agent: {response.content[:200]}...")
        except Exception as e:
            logger.error(f"Agent 调用失败: {e}")


def test_categories() -> None:
    """测试分类常量"""
    separator("测试分类常量")
    
    from app.domain.accounting.accounting_tool_interfaces import (
        EXPENSE_CATEGORIES,
        INCOME_CATEGORIES,
        normalize_category,
    )
    
    logger.info(f"支出分类: {EXPENSE_CATEGORIES}")
    logger.info(f"收入分类: {INCOME_CATEGORIES}")
    
    # 测试分类归一化
    test_inputs = ["吃饭", "工资", "打车", "奖金"]
    for input_str in test_inputs:
        expense_cat = normalize_category(input_str, "expense")
        income_cat = normalize_category(input_str, "income")
        logger.info(f"输入 '{input_str}' -> 支出: {expense_cat}, 收入: {income_cat}")


def main() -> None:
    """主函数"""
    separator("初始化")
    
    # 初始化数据库
    init_database()
    
    # 创建服务
    transaction_service, accounting_agent_service = create_services()
    logger.info("服务创建成功")
    
    # 测试 TransactionService
    test_transaction_service(transaction_service)
    
    # 测试分类常量
    test_categories()
    
    # 测试 AccountingAgentService（需要 API Key）
    separator("记账 Agent 测试（需要阿里百炼 API Key）")
    logger.info("如需跳过 Agent 测试，请注释掉下面这行代码")
    
    try:
        asyncio.run(test_accounting_agent(accounting_agent_service))
    except Exception as e:
        logger.error(f"Agent 测试失败: {e}")
        logger.info("提示: 请检查 application.toml 中的 API Key 配置")
    
    separator("测试完成 ✅")


if __name__ == "__main__":
    main()
