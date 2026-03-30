"""
日志工具模块

提供 TraceID 上下文管理和带 trace_id 字段的日志 Formatter。
使用 contextvars.ContextVar 保证异步/多线程环境下 trace_id 互不污染。

使用示例：
    from app.utils.logging_utils import set_trace_id, get_trace_id

    set_trace_id("req-abc123")
    logger.info("处理记账请求")  # 输出中自动携带 [trace_id=req-abc123]
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

# ─────────────────────────────────────────────
# ContextVar：存储当前异步上下文的 trace_id
# ─────────────────────────────────────────────
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def set_trace_id(trace_id: str | None = None) -> str:
    """
    设置当前上下文的 trace_id。

    Args:
        trace_id: 指定 trace_id；为 None 时自动生成 UUID（取前 8 位）

    Returns:
        实际使用的 trace_id
    """
    tid = trace_id or uuid.uuid4().hex[:8]
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """获取当前上下文的 trace_id，未设置时返回 '-'。"""
    return _trace_id_var.get()


# ─────────────────────────────────────────────
# 自定义 Formatter：在日志中注入 trace_id
# ─────────────────────────────────────────────
class TraceIdFormatter(logging.Formatter):
    """
    在每条日志记录中动态注入当前 trace_id。

    格式示例：
        2026-03-26 14:32:05 [INFO ] [tid=a1b2c3d4] app.api.accounting_routes - 记账请求开始
    """

    def format(self, record: logging.LogRecord) -> str:
        record.trace_id = get_trace_id()
        return super().format(record)
