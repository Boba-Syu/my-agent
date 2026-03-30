"""
记账数据库工具
提供自然语言驱动的 SQL 查询和记账记录插入工具，供 Agent 调用。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.db.sqlite_client import SQLiteClient
from app.db.accounting_db import (
    insert_transaction,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    TRANSACTION_TYPE_EXPENSE,
    TRANSACTION_TYPE_INCOME,
)

logger = logging.getLogger(__name__)


@tool
def add_transaction(
    transaction_type: str,
    category: str,
    amount: float,
    note: str = "",
    transaction_date: str = "",
) -> str:
    """
    向数据库中新增一条记账记录（支出或收入）。

    Args:
        transaction_type: 交易类型，必须是 'expense'（支出）或 'income'（收入）
        category: 分类。
                  支出分类：三餐、日用品、学习、交通、娱乐、医疗、其他
                  收入分类：工资、奖金、理财、其他
        amount: 金额，必须大于 0 的数字
        note: 备注说明（可选，默认为空）
        transaction_date: 交易日期，格式 'YYYY-MM-DD'（可选，默认为今天）

    Returns:
        插入结果描述字符串
    """
    result = insert_transaction(
        transaction_type=transaction_type,
        category=category,
        amount=amount,
        note=note,
        transaction_date=transaction_date if transaction_date else None,
    )
    if result.get("success"):
        record = result.get("record", {})
        type_cn = "支出" if transaction_type == TRANSACTION_TYPE_EXPENSE else "收入"
        return (
            f"✅ 记账成功！\n"
            f"类型: {type_cn} | 分类: {record.get('category')} | "
            f"金额: ¥{record.get('amount')} | 日期: {record.get('transaction_date')} | "
            f"备注: {record.get('note') or '无'} | ID: {record.get('id')}"
        )
    else:
        return f"❌ 记账失败: {result.get('error')}"


@tool
def query_accounting_data(sql: str) -> str:
    """
    执行自定义 SQL 查询语句，从记账数据库中检索数据。
    仅支持 SELECT 语句，禁止 INSERT/UPDATE/DELETE/DROP 等写操作。

    数据库表：transactions
    字段说明：
      - id: 记录ID（整数，自增）
      - transaction_type: 交易类型（'expense' 支出 / 'income' 收入）
      - category: 分类（如 三餐、工资 等）
      - amount: 金额（浮点数）
      - note: 备注（文本）
      - transaction_date: 交易日期（'YYYY-MM-DD' 格式）
      - created_at: 创建时间（DATETIME）

    常用查询示例：
      - 查询本月支出合计: SELECT SUM(amount) FROM transactions WHERE transaction_type='expense' AND transaction_date LIKE '2025-01%'
      - 按分类汇总: SELECT category, SUM(amount) as total FROM transactions WHERE transaction_type='expense' GROUP BY category
      - 查询最近10条: SELECT * FROM transactions ORDER BY id DESC LIMIT 10

    Args:
        sql: 合法的 SQLite SELECT 语句

    Returns:
        查询结果 JSON 字符串，或错误说明
    """
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return "❌ 安全限制：仅允许执行 SELECT 查询语句"

    try:
        db = SQLiteClient()
        rows = db.query(sql)
        if not rows:
            return "查询结果为空（0 条记录）"
        return json.dumps(rows, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"SQL 查询执行失败: {e}")
        return f"❌ 查询失败: {str(e)}"


@tool
def execute_accounting_sql(sql: str) -> str:
    """
    执行自定义 SQL 写操作语句（INSERT / UPDATE / DELETE）。
    注意：此工具用于高级数据操作，一般记账请使用 add_transaction 工具。
    禁止执行 DROP / ALTER / CREATE 等 DDL 语句。

    Args:
        sql: 合法的 SQLite INSERT / UPDATE / DELETE 语句

    Returns:
        执行结果描述
    """
    sql_stripped = sql.strip().upper()
    forbidden = ["DROP", "ALTER", "CREATE", "TRUNCATE", "ATTACH", "DETACH"]
    for keyword in forbidden:
        if keyword in sql_stripped:
            return f"❌ 安全限制：禁止执行包含 {keyword} 的语句"

    try:
        db = SQLiteClient()
        db.execute(sql)
        return "✅ SQL 执行成功"
    except Exception as e:
        logger.error(f"SQL 执行失败: {e}")
        return f"❌ SQL 执行失败: {str(e)}"


@tool
def get_accounting_categories() -> str:
    """
    获取记账系统支持的所有分类信息。

    Returns:
        支出分类和收入分类的详细说明
    """
    return (
        f"支出分类（transaction_type='expense'）: {', '.join(EXPENSE_CATEGORIES)}\n"
        f"收入分类（transaction_type='income'）: {', '.join(INCOME_CATEGORIES)}"
    )
