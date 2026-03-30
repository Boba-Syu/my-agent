"""
SQLite 客户端模块
基于 SQLAlchemy，封装常用的数据库操作，并在首次使用时自动建表
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_sqlite_config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，供业务模型继承"""
    pass


class SQLiteClient:
    """
    SQLite 数据库客户端

    提供连接管理、原生 SQL 执行和 ORM Session 两种使用方式。

    使用示例:
        client = SQLiteClient()

        # 原生 SQL 查询
        rows = client.query("SELECT * FROM conversations LIMIT 10")

        # 原生 SQL 写操作
        client.execute("INSERT INTO conversations(id, content) VALUES (:id, :content)",
                       {"id": "abc", "content": "hello"})

        # ORM Session（推荐）
        with client.session() as session:
            session.add(some_orm_obj)
    """

    _instance: SQLiteClient | None = None  # 单例缓存

    def __new__(cls) -> "SQLiteClient":
        """简单单例，避免重复创建引擎"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        sqlite_cfg = get_sqlite_config()
        db_path = Path(sqlite_cfg.get("path", "./data/agent.db"))

        # 自动创建父目录
        db_path.parent.mkdir(parents=True, exist_ok=True)

        db_url = f"sqlite:///{db_path.resolve()}"
        self._engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,  # 设为 True 可打印所有 SQL（调试用）
        )
        self._SessionFactory = sessionmaker(
            bind=self._engine, autocommit=False, autoflush=False
        )

        # 初始化建表
        self._init_tables()
        self._initialized = True
        logger.info(f"SQLite 数据库已连接：{db_url}")

    def _init_tables(self) -> None:
        """初始化内置表结构"""
        with self._engine.connect() as conn:
            # 会话记录表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          TEXT PRIMARY KEY,
                    thread_id   TEXT NOT NULL,
                    role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content     TEXT NOT NULL,
                    model       TEXT,
                    created_at  DATETIME DEFAULT (datetime('now'))
                )
            """))
            # 通用键值存储表（可扩展）
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key         TEXT PRIMARY KEY,
                    value       TEXT NOT NULL,
                    updated_at  DATETIME DEFAULT (datetime('now'))
                )
            """))
            conn.commit()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        上下文管理器：获取 ORM Session，自动提交/回滚

        用法:
            with client.session() as s:
                s.add(obj)
        """
        sess = self._SessionFactory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        """
        执行写操作 SQL（INSERT / UPDATE / DELETE / DDL）

        Args:
            sql:    SQL 语句，参数占位符使用 :name 格式
            params: 参数字典
        """
        with self._engine.connect() as conn:
            conn.execute(text(sql), params or {})
            conn.commit()

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        """
        执行查询 SQL，返回字典列表

        Args:
            sql:    SQL 语句，参数占位符使用 :name 格式
            params: 参数字典

        Returns:
            [{"col1": val1, "col2": val2, ...}, ...]
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def save_message(
        self,
        msg_id: str,
        thread_id: str,
        role: str,
        content: str,
        model: str | None = None,
    ) -> None:
        """
        保存一条对话消息

        Args:
            msg_id:    消息唯一 ID
            thread_id: 会话线程 ID
            role:      角色（user / assistant / system）
            content:   消息内容
            model:     使用的模型名（可选）
        """
        self.execute(
            """
            INSERT OR REPLACE INTO conversations(id, thread_id, role, content, model)
            VALUES (:id, :thread_id, :role, :content, :model)
            """,
            {"id": msg_id, "thread_id": thread_id, "role": role, "content": content, "model": model},
        )

    def get_history(self, thread_id: str, limit: int = 50) -> list[dict]:
        """
        获取指定会话的历史消息

        Args:
            thread_id: 会话线程 ID
            limit:     最多返回条数

        Returns:
            按时间升序排列的消息列表
        """
        return self.query(
            """
            SELECT id, thread_id, role, content, model, created_at
            FROM conversations
            WHERE thread_id = :thread_id
            ORDER BY created_at ASC
            LIMIT :limit
            """,
            {"thread_id": thread_id, "limit": limit},
        )
