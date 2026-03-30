"""
记账 Agent 模块
基于 ReactAgent 封装的记账专用 Agent，预置系统提示词和记账工具集。

优化特性：
- Agent 实例缓存：按 (model, date) 缓存，避免每次请求重建
- 智能日期刷新：每天自动更新系统提示词中的当前日期
- 数据库自动初始化：首次调用时自动建表
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, date
from typing import Any

from app.agent.react_agent import ReactAgent
from app.db.accounting_db import init_accounting_tables
from app.llm.llm_factory import LLMFactory
from app.tools.accounting_sql_tool import (
    add_transaction,
    query_accounting_data,
    execute_accounting_sql,
    get_accounting_categories,
)
from app.tools.accounting_stats_tool import (
    stats_by_period,
    stats_by_category,
    stats_monthly_trend,
)
from app.tools.accounting_export_tool import (
    export_to_excel,
    export_to_markdown,
)
from app.tools.calculator_tool import calculator
from app.tools.datetime_tool import get_current_datetime

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# 记账 Agent 专用工具列表
# ────────────────────────────────────────────────────────────
ACCOUNTING_TOOLS = [
    get_current_datetime,
    add_transaction,
    query_accounting_data,
    execute_accounting_sql,
    get_accounting_categories,
    stats_by_period,
    stats_by_category,
    stats_monthly_trend,
    export_to_excel,
    export_to_markdown,
    calculator,
]

# ────────────────────────────────────────────────────────────
# 全局缓存：按 (model, date) 缓存 Agent 实例
# ────────────────────────────────────────────────────────────
_agent_cache: dict[tuple[str, date], ReactAgent] = {}
_cache_lock = threading.Lock()
_tables_initialized = False  # 数据库表初始化标志


def _get_cache_key(model: str) -> tuple[str, date]:
    """生成缓存键：(模型名, 当前日期)"""
    return (model, date.today())


def _build_system_prompt(target_date: date | None = None) -> str:
    """
    构建含当前时间的系统提示词。

    Args:
        target_date: 目标日期，默认为今天。用于缓存场景下构建特定日期的提示词。

    Returns:
        包含当前日期和记账规则的系统提示词字符串
    """
    now = datetime.now() if target_date is None else datetime.combine(target_date, datetime.min.time())
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_names[now.weekday()]
    today_str = now.strftime("%Y-%m-%d")

    # 计算昨天日期（处理月初边界）
    yesterday = now.replace(day=now.day - 1) if now.day > 1 else now
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    return f"""你是一个智能记账助手，帮助用户记录和分析日常收支。

## 当前时间（重要）
- 今天日期：{today_str}（{weekday}）
- 当前时间：{now.strftime("%H:%M")}
- **当用户没有说明日期时，一律使用今天的日期 {today_str} 作为 transaction_date**
- 如需获取最新时间，可调用 get_current_datetime 工具

## 核心能力
1. **记账录入**：识别用户自然语言中的记账意图，提取交易类型、分类、金额、日期和备注，调用 add_transaction 工具存入数据库
2. **数据查询**：根据用户需求查询记账记录，支持按时间、分类等条件过滤
3. **统计分析**：统计收支汇总、分类占比、月度趋势等
4. **数据导出**：将记账数据导出为 Excel 或 Markdown 文件
5. **计算支持**：对数值进行精确计算

## 记账规则
- **支出（expense）分类**：三餐、日用品、学习、交通、娱乐、医疗、其他
- **收入（income）分类**：工资、奖金、理财、其他
- 日期格式：YYYY-MM-DD，用户未说明日期时默认使用今天 {today_str}
- 金额必须为正数

## 信息提取规则
用户说"花了30块吃饭" → transaction_type=expense, category=三餐, amount=30, transaction_date={today_str}
用户说"今天收到工资5000" → transaction_type=income, category=工资, amount=5000, transaction_date={today_str}
用户说"买书花了80，用于学习" → transaction_type=expense, category=学习, amount=80, note=买书, transaction_date={today_str}
用户说"昨天打车15块" → transaction_type=expense, category=交通, amount=15, transaction_date={yesterday_str}

## 响应规范
- 记账成功后给用户友好确认，包含关键信息
- 查询/统计结果要清晰直观地展示
- 遇到模糊信息（如分类不明确）时，优先合理推断，而非多次追问
- 如果用户提供的分类不在支持列表中，自动映射到最相近的分类（如"餐厅"→"三餐"，"出行"→"交通"）

## 工具使用顺序
获取当前时间 → get_current_datetime（需要确认当前日期时使用）
记账 → add_transaction
查询明细 → query_accounting_data（使用 SELECT SQL）
统计汇总 → stats_by_period 或 stats_by_category
月度趋势 → stats_monthly_trend
导出文件 → export_to_excel 或 export_to_markdown
计算 → calculator
"""


def _init_tables_once() -> None:
    """确保数据库表只初始化一次（线程安全）"""
    global _tables_initialized
    if not _tables_initialized:
        with _cache_lock:
            if not _tables_initialized:
                init_accounting_tables()
                _tables_initialized = True
                logger.info("数据库表初始化完成")


def _create_agent_instance(model: str) -> ReactAgent:
    """
    创建新的记账 Agent 实例（内部函数，不处理缓存逻辑）

    Args:
        model: 使用的 LLM 模型名称

    Returns:
        新创建的 ReactAgent 实例
    """
    llm = LLMFactory.create_llm(model)
    agent = ReactAgent(
        llm=llm,
        tools=ACCOUNTING_TOOLS,
        system_prompt=_build_system_prompt(),
    )
    return agent


def create_accounting_agent(model: str = "deepseek-v3") -> ReactAgent:
    """
    创建并返回一个配置好的记账 Agent 实例。

    优化特性：
    - 使用缓存避免重复创建（按 model + date 缓存）
    - 数据库表只初始化一次
    - 每天自动刷新系统提示词中的日期

    Args:
        model: 使用的 LLM 模型名称，默认 deepseek-v3

    Returns:
        配置好工具和提示词的 ReactAgent 实例
    """
    # 确保表结构已初始化（只执行一次）
    _init_tables_once()

    # 计算缓存键
    cache_key = _get_cache_key(model)

    # 检查缓存
    if cache_key in _agent_cache:
        logger.debug(f"命中 Agent 缓存: model={model}, date={cache_key[1]}")
        return _agent_cache[cache_key]

    # 未命中缓存，创建新实例
    with _cache_lock:
        # 双重检查，避免多线程竞争
        if cache_key in _agent_cache:
            return _agent_cache[cache_key]

        agent = _create_agent_instance(model)
        _agent_cache[cache_key] = agent

        # 清理过期缓存（保留最近 7 天的缓存）
        _cleanup_old_cache()

        logger.info(
            f"创建记账 Agent 并缓存: model={model}, date={cache_key[1]}, "
            f"工具数={len(ACCOUNTING_TOOLS)}, "
            f"缓存大小={len(_agent_cache)}"
        )
        return agent


def _cleanup_old_cache() -> None:
    """清理过期缓存，只保留最近 7 天的 Agent 实例"""
    global _agent_cache
    today = date.today()
    keys_to_remove = [
        key for key in _agent_cache.keys()
        if (today - key[1]).days > 7
    ]
    for key in keys_to_remove:
        del _agent_cache[key]
        logger.debug(f"清理过期缓存: model={key[0]}, date={key[1]}")


def get_cached_agent_info() -> dict[str, Any]:
    """
    获取当前缓存状态信息（用于调试和监控）

    Returns:
        包含缓存信息的字典
    """
    today = date.today()
    return {
        "cache_size": len(_agent_cache),
        "cached_keys": [
            {"model": key[0], "date": key[1].isoformat()}
            for key in _agent_cache.keys()
        ],
        "today_keys": [
            {"model": key[0]}
            for key in _agent_cache.keys()
            if key[1] == today
        ],
    }


def clear_agent_cache() -> int:
    """
    清空 Agent 缓存（用于热更新或调试）

    Returns:
        被清空的缓存项数量
    """
    global _agent_cache
    count = len(_agent_cache)
    _agent_cache.clear()
    logger.info(f"Agent 缓存已清空，共清理 {count} 项")
    return count


def refresh_agent_cache(model: str = "deepseek-v3") -> ReactAgent:
    """
    强制刷新指定模型的 Agent 缓存（用于系统提示词需要立即更新的场景）

    Args:
        model: 需要刷新的模型名称

    Returns:
        新创建的 Agent 实例
    """
    cache_key = _get_cache_key(model)

    with _cache_lock:
        # 如果存在旧缓存，先移除
        if cache_key in _agent_cache:
            del _agent_cache[cache_key]
            logger.info(f"移除旧缓存: model={model}, date={cache_key[1]}")

        # 创建新实例
        agent = _create_agent_instance(model)
        _agent_cache[cache_key] = agent

    logger.info(f"Agent 缓存已刷新: model={model}, date={cache_key[1]}")
    return agent
