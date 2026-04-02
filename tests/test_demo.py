"""
Agent 框架使用示例测试类（DDD 架构版本）

展示以下使用场景：
1. AgentFactory —— 创建 Agent 实例（符合 DDD 架构）
2. Repository 模式 —— 通过接口操作数据库
3. TransactionService —— 应用层服务使用示例
4. SQLite 客户端 —— 基础数据库操作
5. FastAPI 接口 —— 通过 httpx 调用 API

注意：此版本已更新为使用 DDD 架构，原 ReactAgent 直接实例化方式已废弃。
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os

# 将项目根目录加入 sys.path，使 `app` 包可以直接 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_demo")


# ===========================================================================
# 1. AgentFactory 使用示例（DDD 架构）
# ===========================================================================

def demo_agent_factory() -> None:
    """演示如何通过 AgentFactory 创建 Agent"""
    logger.info("=" * 60)
    logger.info("【1】AgentFactory 示例（DDD 架构）")

    from app.application.agent.agent_factory import AgentFactory
    from app.infrastructure.tools.accounting import (
        CalculatorTool,
        GetCurrentDatetimeTool,
    )

    # 创建工厂（使用 langgraph 实现）
    factory = AgentFactory(default_implementation="langgraph")
    logger.info(f"可用 Provider: {factory.get_available_providers()}")

    # 创建工具
    tools = [
        CalculatorTool(),
        GetCurrentDatetimeTool(),
    ]

    # 使用工厂创建 Agent
    agent = factory.create_agent(
        model="deepseek-v3",
        tools=tools,
        system_prompt="你是一个智能助手，可以使用计算器和日期工具帮助用户。",
    )

    logger.info(f"Agent 创建成功，工具数量: {len(tools)}")

    # 测试同步调用
    response = agent.invoke("帮我计算 100 + 200", thread_id="demo-001")
    logger.info(f"计算结果: {response.content}")


# ===========================================================================
# 2. Repository 模式使用示例
# ===========================================================================

def demo_repository() -> None:
    """演示 Repository 模式"""
    logger.info("=" * 60)
    logger.info("【2】Repository 模式示例")

    from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository
    from app.domain.accounting.transaction import Transaction, TransactionType
    from app.domain.accounting.money import Money
    from datetime import date
    from decimal import Decimal

    # 创建 Repository
    repository = SQLiteTransactionRepository()

    # 创建交易实体
    transaction = Transaction(
        id=None,
        transaction_type=TransactionType("expense"),
        category="三餐",
        amount=Money(Decimal("35.5")),
        transaction_date=date.today(),
        note="午餐",
    )

    # 保存
    saved = repository.save(transaction)
    logger.info(f"保存交易: ID={saved.id}, 分类={saved.category}, 金额={saved.amount.amount}")

    # 查询
    transactions = repository.list(limit=5)
    logger.info(f"查询到 {len(transactions)} 条交易记录")

    # 统计
    stats = repository.get_statistics()
    logger.info(f"统计: 收入={stats.income_total.amount}, 支出={stats.expense_total.amount}")


# ===========================================================================
# 3. TransactionService 使用示例
# ===========================================================================

def demo_transaction_service() -> None:
    """演示 TransactionService 应用层服务"""
    logger.info("=" * 60)
    logger.info("【3】TransactionService 应用层服务示例")

    from app.application.accounting.transaction_service import TransactionService
    from app.application.accounting.dto import CreateTransactionDTO
    from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository

    # 创建 Repository 和 Service
    repository = SQLiteTransactionRepository()
    service = TransactionService(repository=repository)

    # 创建交易
    transaction = service.create_transaction(CreateTransactionDTO(
        transaction_type="expense",
        category="交通",
        amount=25.0,
        transaction_date="2026-04-01",
        note="打车",
    ))
    logger.info(f"创建交易: ID={transaction.id}")

    # 查询
    from app.application.accounting.dto import TransactionQueryDTO
    transactions = service.list_transactions(TransactionQueryDTO(limit=5))
    logger.info(f"查询到 {len(transactions)} 条记录")


# ===========================================================================
# 4. SQLite 客户端使用示例
# ===========================================================================

def demo_sqlite() -> None:
    """演示 SQLite 客户端的基础操作"""
    logger.info("=" * 60)
    logger.info("【4】SQLite 客户端示例")

    from app.db.sqlite_client import SQLiteClient

    db = SQLiteClient()

    # 建表
    db.execute("""
        CREATE TABLE IF NOT EXISTS demo_users (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            age    INTEGER,
            remark TEXT
        )
    """)
    logger.info("表 demo_users 创建成功（已存在则跳过）")

    # 插入数据
    db.execute(
        "INSERT INTO demo_users (name, age, remark) VALUES (:name, :age, :remark)",
        {"name": "张三", "age": 28, "remark": "测试用户A"},
    )
    db.execute(
        "INSERT INTO demo_users (name, age, remark) VALUES (:name, :age, :remark)",
        {"name": "李四", "age": 32, "remark": "测试用户B"},
    )
    logger.info("插入 2 条测试数据")

    # 查询所有
    rows = db.query("SELECT id, name, age, remark FROM demo_users")
    logger.info(f"查询结果（共 {len(rows)} 条）：")
    for row in rows:
        logger.info(f"  {row}")

    # 清理测试数据
    db.execute("DROP TABLE IF EXISTS demo_users")
    logger.info("测试表已清理")


# ===========================================================================
# 5. FastAPI HTTP 接口调用示例（需要服务已启动）
# ===========================================================================

def demo_http_api(base_url: str = "http://127.0.0.1:8000") -> None:
    """
    演示通过 httpx 调用 FastAPI 接口

    前提：需要先启动服务 `uv run python main.py`
    """
    logger.info("=" * 60)
    logger.info("【5】FastAPI HTTP 接口示例")

    try:
        import httpx
    except ImportError:
        logger.warning("httpx 未安装，跳过 HTTP 接口示例。可通过 `uv add httpx` 安装")
        return

    with httpx.Client(base_url=base_url, timeout=60) as client:
        # 健康检查
        resp = client.get("/api/v1/health")
        logger.info(f"健康检查：{resp.json()}")

        # 查询分类
        resp = client.get("/api/v1/accounting/categories")
        categories = resp.json()
        logger.info(f"支出分类：{categories.get('expense_categories', [])}")
        logger.info(f"收入分类：{categories.get('income_categories', [])}")


# ===========================================================================
# 主入口
# ===========================================================================

def run_all_local_demos() -> None:
    """运行所有本地示例（无需 API Key）"""
    demos = [
        ("Repository 模式", demo_repository),
        ("TransactionService", demo_transaction_service),
        ("SQLite 客户端", demo_sqlite),
    ]
    for name, fn in demos:
        try:
            fn()
        except Exception as e:
            logger.error(f"示例【{name}】执行失败：{e}", exc_info=True)


def run_all_agent_demos() -> None:
    """运行所有 Agent 相关示例（需要阿里百炼 API Key）"""
    try:
        demo_agent_factory()
    except Exception as e:
        logger.error(f"AgentFactory 示例执行失败：{e}", exc_info=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 框架使用示例（DDD 架构）")
    parser.add_argument(
        "--mode",
        choices=["local", "agent", "http", "all"],
        default="local",
        help=(
            "运行模式：\n"
            "  local  - 本地示例（Repository/Service/SQLite），无需 API Key\n"
            "  agent  - Agent 示例（需要阿里百炼 API Key）\n"
            "  http   - HTTP 接口示例（需要先启动 main.py 服务）\n"
            "  all    - 运行全部示例\n"
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="FastAPI 服务地址（http 模式下使用）",
    )
    args = parser.parse_args()

    if args.mode == "local":
        run_all_local_demos()

    elif args.mode == "agent":
        run_all_agent_demos()

    elif args.mode == "http":
        demo_http_api(base_url=args.base_url)

    elif args.mode == "all":
        run_all_local_demos()
        run_all_agent_demos()
        demo_http_api(base_url=args.base_url)
