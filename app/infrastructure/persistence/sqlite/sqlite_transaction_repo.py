"""
SQLite 交易仓库实现

实现领域层的 TransactionRepository 接口。
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from app.db.sqlite_client import SQLiteClient
from app.domain.accounting.money import Money
from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.accounting.transaction_repository import TransactionRepository
from app.domain.accounting.transaction_statistics import TransactionStatistics

logger = logging.getLogger(__name__)


class SQLiteTransactionRepository(TransactionRepository):
    """
    SQLite 交易仓库实现
    
    实现领域层的 TransactionRepository 接口，
    提供交易的持久化功能。
    """

    def __init__(self, client: SQLiteClient | None = None):
        """
        初始化仓库
        
        Args:
            client: SQLite 客户端，None 时自动创建
        """
        self._client = client or SQLiteClient()

    def get(self, id: str) -> Transaction | None:
        """
        根据 ID 获取交易
        
        Args:
            id: 交易 ID
            
        Returns:
            交易聚合根，不存在则返回 None
        """
        rows = self._client.query(
            "SELECT * FROM transactions WHERE id = :id",
            {"id": int(id)},
        )
        if not rows:
            return None
        return self._row_to_entity(rows[0])

    def list(
        self,
        transaction_type: TransactionType | None = None,
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """
        查询交易列表
        
        Args:
            transaction_type: 按类型过滤
            category: 按分类过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回条数限制
            
        Returns:
            交易列表
        """
        conditions = []
        params: dict[str, Any] = {}
        
        if transaction_type:
            conditions.append("transaction_type = :type")
            params["type"] = transaction_type.value
        
        if category:
            conditions.append("category = :category")
            params["category"] = category
        
        if start_date:
            conditions.append("transaction_date >= :start_date")
            params["start_date"] = start_date.isoformat()
        
        if end_date:
            conditions.append("transaction_date <= :end_date")
            params["end_date"] = end_date.isoformat()
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
            SELECT * FROM transactions
            {where_clause}
            ORDER BY transaction_date DESC, id DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        rows = self._client.query(sql, params)
        return [self._row_to_entity(row) for row in rows]

    def save(self, transaction: Transaction) -> Transaction:
        """
        保存交易

        如果交易已有 ID 则更新，否则创建。

        Args:
            transaction: 交易聚合根

        Returns:
            保存后的交易（包含生成的 ID）
        """
        if transaction.id is None:
            # 插入新记录
            self._client.execute(
                """
                INSERT INTO transactions
                (transaction_type, category, amount, transaction_date, note, created_at)
                VALUES (:type, :category, :amount, :date, :note, datetime('now'))
                """,
                {
                    "type": transaction.transaction_type.value,
                    "category": transaction.category,
                    "amount": float(transaction.amount.amount),
                    "date": transaction.transaction_date.isoformat(),
                    "note": transaction.note,
                },
            )
            # 查询刚插入的记录（通过最大 ID）
            rows = self._client.query(
                "SELECT * FROM transactions ORDER BY id DESC LIMIT 1"
            )
            if rows:
                return self._row_to_entity(rows[0])
            raise RuntimeError("保存交易失败：无法获取刚插入的记录")
        else:
            # 更新现有记录
            self._client.execute(
                """
                UPDATE transactions
                SET transaction_type = :type,
                    category = :category,
                    amount = :amount,
                    transaction_date = :date,
                    note = :note
                WHERE id = :id
                """,
                {
                    "id": transaction.id,
                    "type": transaction.transaction_type.value,
                    "category": transaction.category,
                    "amount": float(transaction.amount.amount),
                    "date": transaction.transaction_date.isoformat(),
                    "note": transaction.note,
                },
            )
            return transaction

    def delete(self, id: str) -> bool:
        """
        删除交易
        
        Args:
            id: 交易 ID
            
        Returns:
            是否成功删除
        """
        result = self._client.execute(
            "DELETE FROM transactions WHERE id = :id",
            {"id": int(id)},
        )
        return result.rowcount > 0

    def exists(self, id: str) -> bool:
        """
        检查交易是否存在
        
        Args:
            id: 交易 ID
            
        Returns:
            是否存在
        """
        rows = self._client.query(
            "SELECT 1 FROM transactions WHERE id = :id LIMIT 1",
            {"id": int(id)},
        )
        return len(rows) > 0

    def get_statistics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionStatistics:
        """
        获取统计数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计数据
        """
        params: dict[str, Any] = {}
        conditions = []
        
        if start_date:
            conditions.append("transaction_date >= :start")
            params["start"] = start_date.isoformat()
        
        if end_date:
            conditions.append("transaction_date <= :end")
            params["end"] = end_date.isoformat()
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
            SELECT transaction_type, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            {where_clause}
            GROUP BY transaction_type
        """
        
        rows = self._client.query(sql, params)
        
        income_total = Money.zero()
        expense_total = Money.zero()
        income_count = 0
        expense_count = 0
        
        for row in rows:
            if row["transaction_type"] == "income":
                income_total = Money(Decimal(str(row["total"] or 0)))
                income_count = row["count"]
            elif row["transaction_type"] == "expense":
                expense_total = Money(Decimal(str(row["total"] or 0)))
                expense_count = row["count"]
        
        return TransactionStatistics(
            income_total=income_total,
            expense_total=expense_total,
            income_count=income_count,
            expense_count=expense_count,
            start_date=start_date,
            end_date=end_date,
        )

    def get_categories_summary(
        self,
        transaction_type: TransactionType,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取分类汇总
        
        Args:
            transaction_type: 交易类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            按分类汇总的列表
        """
        params: dict[str, Any] = {"type": transaction_type.value}
        conditions = ["transaction_type = :type"]
        
        if start_date:
            conditions.append("transaction_date >= :start")
            params["start"] = start_date.isoformat()
        
        if end_date:
            conditions.append("transaction_date <= :end")
            params["end"] = end_date.isoformat()
        
        sql = f"""
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE {' AND '.join(conditions)}
            GROUP BY category
            ORDER BY total DESC
        """
        
        rows = self._client.query(sql, params)
        return [
            {
                "category": row["category"],
                "total": float(row["total"]),
                "count": row["count"],
            }
            for row in rows
        ]

    def get_daily_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        获取每日汇总
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            按日汇总的列表
        """
        sql = """
            SELECT 
                transaction_date as date,
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expense,
                COUNT(*) as count
            FROM transactions
            WHERE transaction_date BETWEEN :start AND :end
            GROUP BY transaction_date
            ORDER BY transaction_date
        """
        
        rows = self._client.query(
            sql,
            {"start": start_date.isoformat(), "end": end_date.isoformat()},
        )
        
        return [
            {
                "date": row["date"],
                "income": float(row["income"] or 0),
                "expense": float(row["expense"] or 0),
                "count": row["count"],
            }
            for row in rows
        ]

    def _row_to_entity(self, row: dict) -> Transaction:
        """
        将数据库行转换为领域实体
        
        Args:
            row: 数据库行字典
            
        Returns:
            交易聚合根
        """
        from datetime import datetime
        
        created_at = None
        if row.get("created_at"):
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except (ValueError, TypeError):
                pass
        
        return Transaction(
            id=row["id"],
            transaction_type=TransactionType(row["transaction_type"]),
            category=row["category"],
            amount=Money(Decimal(str(row["amount"]))),
            transaction_date=date.fromisoformat(row["transaction_date"]),
            note=row.get("note", ""),
            created_at=created_at,
        )
