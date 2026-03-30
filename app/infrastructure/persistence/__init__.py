"""
持久化基础设施

实现领域层定义的仓库接口。
"""

from __future__ import annotations

from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository

__all__ = [
    "SQLiteTransactionRepository",
]
