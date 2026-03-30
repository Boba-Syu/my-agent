"""
记账数据库模块
负责初始化记账相关表结构，并提供记账数据的基础 CRUD 操作。

表结构：
  - transactions: 记账流水（支出/收入）
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.db.sqlite_client import SQLiteClient

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# 分类常量
# ────────────────────────────────────────────────────────────

# 交易类型
TRANSACTION_TYPE_EXPENSE = "expense"   # 支出
TRANSACTION_TYPE_INCOME = "income"     # 收入

# 支出分类
EXPENSE_CATEGORIES = ["三餐", "日用品", "学习", "交通", "娱乐", "医疗", "其他"]

# 收入分类
INCOME_CATEGORIES = ["工资", "奖金", "理财", "其他"]

ALL_CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES


def init_accounting_tables() -> None:
    """
    初始化记账相关表结构（幂等，重复调用无副作用）

    建表逻辑：
      transactions —— 记账流水主表
    """
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
    logger.info("记账表 transactions 初始化完成")


def insert_transaction(
    transaction_type: str,
    category: str,
    amount: float,
    note: str = "",
    transaction_date: str | None = None,
) -> dict[str, Any]:
    """
    插入一条记账记录

    Args:
        transaction_type: 交易类型，'expense'（支出）或 'income'（收入）
        category:         分类名称
        amount:           金额（必须 > 0）
        note:             备注（可选）
        transaction_date: 交易日期，格式 'YYYY-MM-DD'，默认今天

    Returns:
        插入结果字典，包含插入成功的记录信息
    """
    # 参数校验
    if transaction_type not in (TRANSACTION_TYPE_EXPENSE, TRANSACTION_TYPE_INCOME):
        return {"success": False, "error": f"无效的交易类型: {transaction_type}，应为 expense 或 income"}

    valid_categories = EXPENSE_CATEGORIES if transaction_type == TRANSACTION_TYPE_EXPENSE else INCOME_CATEGORIES
    if category not in valid_categories:
        return {
            "success": False,
            "error": f"无效的分类: {category}，{transaction_type} 类型的有效分类为: {valid_categories}",
        }

    if amount <= 0:
        return {"success": False, "error": f"金额必须大于 0，当前值: {amount}"}

    if transaction_date is None:
        transaction_date = datetime.now().strftime("%Y-%m-%d")

    db = SQLiteClient()
    db.execute(
        """
        INSERT INTO transactions (transaction_type, category, amount, note, transaction_date)
        VALUES (:transaction_type, :category, :amount, :note, :transaction_date)
        """,
        {
            "transaction_type": transaction_type,
            "category": category,
            "amount": amount,
            "note": note,
            "transaction_date": transaction_date,
        },
    )

    # 查回刚插入的记录
    rows = db.query(
        "SELECT * FROM transactions ORDER BY id DESC LIMIT 1"
    )
    record = rows[0] if rows else {}
    logger.info(f"记账记录已插入: {record}")
    return {"success": True, "record": record}


def update_transaction(
    record_id: int,
    transaction_type: str | None = None,
    category: str | None = None,
    amount: float | None = None,
    note: str | None = None,
    transaction_date: str | None = None,
) -> dict[str, Any]:
    """
    更新一条记账记录

    Args:
        record_id:        记录 ID
        transaction_type: 交易类型（可选，传 None 则不更新）
        category:         分类名称（可选）
        amount:           金额（可选）
        note:             备注（可选）
        transaction_date: 交易日期（可选）

    Returns:
        更新结果字典
    """
    db = SQLiteClient()

    # 先查询记录是否存在
    rows = db.query("SELECT * FROM transactions WHERE id = :id", {"id": record_id})
    if not rows:
        return {"success": False, "error": f"记录不存在: id={record_id}"}

    existing = rows[0]

    # 合并：只更新传入的字段，未传入的保留原值
    t_type = transaction_type if transaction_type is not None else existing["transaction_type"]
    cat = category if category is not None else existing["category"]
    amt = amount if amount is not None else existing["amount"]
    n = note if note is not None else (existing.get("note") or "")
    td = transaction_date if transaction_date is not None else existing["transaction_date"]

    # 校验交易类型
    if t_type not in (TRANSACTION_TYPE_EXPENSE, TRANSACTION_TYPE_INCOME):
        return {"success": False, "error": f"无效的交易类型: {t_type}"}

    # 校验分类
    valid_categories = EXPENSE_CATEGORIES if t_type == TRANSACTION_TYPE_EXPENSE else INCOME_CATEGORIES
    if cat not in valid_categories:
        return {"success": False, "error": f"无效的分类: {cat}，{t_type} 类型的有效分类为: {valid_categories}"}

    # 校验金额
    if amt <= 0:
        return {"success": False, "error": f"金额必须大于 0，当前值: {amt}"}

    db.execute(
        """
        UPDATE transactions
        SET transaction_type = :transaction_type,
            category = :category,
            amount = :amount,
            note = :note,
            transaction_date = :transaction_date
        WHERE id = :id
        """,
        {
            "id": record_id,
            "transaction_type": t_type,
            "category": cat,
            "amount": amt,
            "note": n,
            "transaction_date": td,
        },
    )

    updated_rows = db.query("SELECT * FROM transactions WHERE id = :id", {"id": record_id})
    record = updated_rows[0] if updated_rows else {}
    logger.info(f"记账记录已更新: id={record_id}, record={record}")
    return {"success": True, "record": record}


def delete_transaction(record_id: int) -> dict[str, Any]:
    """
    删除一条记账记录

    Args:
        record_id: 记录 ID

    Returns:
        删除结果字典
    """
    db = SQLiteClient()

    rows = db.query("SELECT * FROM transactions WHERE id = :id", {"id": record_id})
    if not rows:
        return {"success": False, "error": f"记录不存在: id={record_id}"}

    db.execute("DELETE FROM transactions WHERE id = :id", {"id": record_id})
    logger.info(f"记账记录已删除: id={record_id}")
    return {"success": True, "record": rows[0]}


def query_transactions(
    transaction_type: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    查询记账记录

    Args:
        transaction_type: 过滤交易类型（可选）
        category:         过滤分类（可选）
        start_date:       起始日期 'YYYY-MM-DD'（可选）
        end_date:         结束日期 'YYYY-MM-DD'（可选）
        limit:            最大返回条数

    Returns:
        记账记录列表
    """
    conditions = []
    params: dict[str, Any] = {"limit": limit}

    if transaction_type:
        conditions.append("transaction_type = :transaction_type")
        params["transaction_type"] = transaction_type
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if start_date:
        conditions.append("transaction_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("transaction_date <= :end_date")
        params["end_date"] = end_date

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM transactions {where_clause} ORDER BY transaction_date DESC, id DESC LIMIT :limit"

    db = SQLiteClient()
    return db.query(sql, params)
