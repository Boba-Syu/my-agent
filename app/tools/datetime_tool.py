"""
日期时间工具
提供获取当前日期、时间等工具，供 Agent 在记账时判断"今天"是哪一天。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_current_datetime() -> str:
    """
    获取当前的日期和时间信息。

    当用户没有明确说明记账日期时，应先调用此工具获取当前日期，
    再将该日期作为 transaction_date 传入 add_transaction。

    Returns:
        包含当前日期、时间、星期的字符串，格式示例：
        当前日期: 2026-03-26
        当前时间: 14:32:05
        星期: 星期四
        本周起始（周一）: 2026-03-23
        本月起始: 2026-03-01
        本年起始: 2026-01-01
    """
    now = datetime.now()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_names[now.weekday()]

    # 本周周一
    week_start = now - timedelta(days=now.weekday())

    return (
        f"当前日期: {now.strftime('%Y-%m-%d')}\n"
        f"当前时间: {now.strftime('%H:%M:%S')}\n"
        f"星期: {weekday}\n"
        f"本周起始（周一）: {week_start.strftime('%Y-%m-%d')}\n"
        f"本月起始: {now.strftime('%Y-%m-01')}\n"
        f"本年起始: {now.strftime('%Y-01-01')}"
    )
