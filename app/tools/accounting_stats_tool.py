"""
记账统计计算工具
提供多维度的记账数据统计分析，供 Agent 调用。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, date

from langchain_core.tools import tool

from app.db.sqlite_client import SQLiteClient

logger = logging.getLogger(__name__)


def _get_current_month() -> tuple[str, str]:
    """返回当前月份的起止日期 (start, end)，格式 'YYYY-MM-DD'"""
    today = date.today()
    start = today.replace(day=1).strftime("%Y-%m-%d")
    # 月末：下月1日减1天
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        end = today.replace(month=today.month + 1, day=1)
    end_str = (end.replace(day=1) if today.month != 12 else end).strftime("%Y-%m-%d")
    # 简单处理：直接用 YYYY-MM-31 或当月最后一天
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_str = today.replace(day=last_day).strftime("%Y-%m-%d")
    return start, end_str


@tool
def stats_by_period(
    period: str = "month",
    start_date: str = "",
    end_date: str = "",
) -> str:
    """
    按时间段统计收支总额及净额。

    Args:
        period: 统计周期，可选 'today'（今日）、'week'（本周）、'month'（本月）、'year'（本年）、'custom'（自定义）
        start_date: 自定义起始日期，格式 'YYYY-MM-DD'（仅 period='custom' 时有效）
        end_date:   自定义结束日期，格式 'YYYY-MM-DD'（仅 period='custom' 时有效）

    Returns:
        统计结果字符串
    """
    today = date.today()
    db = SQLiteClient()

    if period == "today":
        start = end = today.strftime("%Y-%m-%d")
    elif period == "week":
        start = (today - __import__("datetime").timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
    elif period == "month":
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        start = today.replace(day=1).strftime("%Y-%m-%d")
        end = today.replace(day=last_day).strftime("%Y-%m-%d")
    elif period == "year":
        start = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        end = today.replace(month=12, day=31).strftime("%Y-%m-%d")
    elif period == "custom":
        if not start_date or not end_date:
            return "❌ 自定义周期需要提供 start_date 和 end_date"
        start, end = start_date, end_date
    else:
        return f"❌ 不支持的 period 值: {period}，可选: today/week/month/year/custom"

    rows = db.query(
        """
        SELECT
            transaction_type,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions
        WHERE transaction_date BETWEEN :start AND :end
        GROUP BY transaction_type
        """,
        {"start": start, "end": end},
    )

    income_total = 0.0
    expense_total = 0.0
    income_count = 0
    expense_count = 0

    for row in rows:
        if row["transaction_type"] == "income":
            income_total = row["total"]
            income_count = row["count"]
        elif row["transaction_type"] == "expense":
            expense_total = row["total"]
            expense_count = row["count"]

    net = income_total - expense_total
    period_cn = {"today": "今日", "week": "本周", "month": "本月", "year": "本年", "custom": f"{start}~{end}"}

    return (
        f"📊 {period_cn.get(period, period)} 收支统计（{start} 至 {end}）\n"
        f"  💰 收入: ¥{income_total:.2f}（{income_count} 笔）\n"
        f"  💸 支出: ¥{expense_total:.2f}（{expense_count} 笔）\n"
        f"  📈 净额: ¥{net:.2f}（{'盈余' if net >= 0 else '亏损'}）"
    )


@tool
def stats_by_category(
    transaction_type: str = "expense",
    start_date: str = "",
    end_date: str = "",
) -> str:
    """
    按分类统计金额，了解各类别的消费或收入分布。

    Args:
        transaction_type: 交易类型，'expense'（支出）或 'income'（收入），默认支出
        start_date: 起始日期，格式 'YYYY-MM-DD'（可选，默认本月第一天）
        end_date:   结束日期，格式 'YYYY-MM-DD'（可选，默认今天）

    Returns:
        各分类统计结果字符串
    """
    if transaction_type not in ("expense", "income"):
        return "❌ transaction_type 必须是 'expense' 或 'income'"

    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = today.strftime("%Y-%m-%d")

    db = SQLiteClient()
    rows = db.query(
        """
        SELECT
            category,
            SUM(amount) as total,
            COUNT(*) as count,
            AVG(amount) as avg_amount
        FROM transactions
        WHERE transaction_type = :transaction_type
          AND transaction_date BETWEEN :start AND :end
        GROUP BY category
        ORDER BY total DESC
        """,
        {"transaction_type": transaction_type, "start": start_date, "end": end_date},
    )

    if not rows:
        type_cn = "支出" if transaction_type == "expense" else "收入"
        return f"该时间段内无{type_cn}记录（{start_date} ~ {end_date}）"

    type_cn = "支出" if transaction_type == "expense" else "收入"
    total_all = sum(r["total"] for r in rows)
    lines = [f"📊 {type_cn}分类统计（{start_date} ~ {end_date}）\n"]
    lines.append(f"{'分类':<8} {'金额':>10} {'占比':>8} {'笔数':>6} {'均值':>10}")
    lines.append("-" * 48)
    for row in rows:
        pct = row["total"] / total_all * 100 if total_all > 0 else 0
        lines.append(
            f"{row['category']:<8} ¥{row['total']:>9.2f} {pct:>7.1f}% "
            f"{row['count']:>5}笔 ¥{row['avg_amount']:>8.2f}"
        )
    lines.append("-" * 48)
    lines.append(f"{'合计':<8} ¥{total_all:>9.2f}")

    return "\n".join(lines)


@tool
def stats_monthly_trend(year: str = "") -> str:
    """
    统计指定年份每个月的收支趋势。

    Args:
        year: 年份，格式 'YYYY'（可选，默认当前年）

    Returns:
        月度收支趋势表格字符串
    """
    if not year:
        year = str(date.today().year)

    db = SQLiteClient()
    rows = db.query(
        """
        SELECT
            strftime('%m', transaction_date) as month,
            transaction_type,
            SUM(amount) as total
        FROM transactions
        WHERE strftime('%Y', transaction_date) = :year
        GROUP BY month, transaction_type
        ORDER BY month
        """,
        {"year": year},
    )

    # 整理为 {月份: {income: x, expense: y}}
    monthly: dict[str, dict[str, float]] = {}
    for row in rows:
        m = row["month"]
        if m not in monthly:
            monthly[m] = {"income": 0.0, "expense": 0.0}
        monthly[m][row["transaction_type"]] = row["total"]

    if not monthly:
        return f"{year} 年暂无记账数据"

    lines = [f"📅 {year} 年月度收支趋势\n"]
    lines.append(f"{'月份':<6} {'收入':>10} {'支出':>10} {'净额':>10}")
    lines.append("-" * 40)
    for month_num in sorted(monthly.keys()):
        data = monthly[month_num]
        inc = data.get("income", 0.0)
        exp = data.get("expense", 0.0)
        net = inc - exp
        net_str = f"+¥{net:.2f}" if net >= 0 else f"-¥{abs(net):.2f}"
        lines.append(f"{year}-{month_num}  ¥{inc:>9.2f} ¥{exp:>9.2f} {net_str:>10}")

    return "\n".join(lines)
