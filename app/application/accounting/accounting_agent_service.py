"""
记账 Agent 应用服务

基于 DDD 架构的记账 Agent，使用 AbstractAgent 抽象。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date, datetime

from app.application.agent.dto import ChatRequest, ChatResponse, StreamChunk
from app.application.agent.agent_service import AgentService
from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_tool import AgentTool, ToolResult
from app.infrastructure.agent.cache.agent_cache import AgentCache, InMemoryAgentCache
from app.infrastructure.agent.langgraph.langgraph_agent import LangGraphAgent
from app.infrastructure.agent.langgraph.tool_adapter import ToolAdapter
from app.infrastructure.llm.llm_provider import LLMProvider
from app.infrastructure.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class AddTransactionTool(AgentTool):
    """添加记账工具"""
    
    @property
    def name(self) -> str:
        return "add_transaction"
    
    @property
    def description(self) -> str:
        return """
        添加一条记账记录。
        Args:
            transaction_type: 交易类型，"income"(收入) 或 "expense"(支出)
            category: 分类名称
            amount: 金额（正数）
            transaction_date: 交易日期 YYYY-MM-DD
            note: 备注（可选）
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "description": '交易类型，"income"(收入) 或 "expense"(支出)',
                },
                "category": {
                    "type": "string",
                    "description": "分类名称",
                },
                "amount": {
                    "type": "number",
                    "description": "金额（正数）",
                },
                "transaction_date": {
                    "type": "string",
                    "description": "交易日期 YYYY-MM-DD",
                },
                "note": {
                    "type": "string",
                    "description": "备注（可选）",
                },
            },
            "required": ["transaction_type", "category", "amount", "transaction_date"],
        }
    
    def execute(
        self,
        transaction_type: str,
        category: str,
        amount: float,
        transaction_date: str,
        note: str = "",
    ) -> ToolResult:
        try:
            from app.db.accounting_db import insert_transaction
            result = insert_transaction(
                transaction_type=transaction_type,
                category=category,
                amount=amount,
                transaction_date=transaction_date,
                note=note,
            )
            if result["success"]:
                return ToolResult.success_result(
                    f"记账成功：{category} {transaction_type} {amount}元"
                )
            else:
                return ToolResult.error_result(result.get("error", "未知错误"))
        except Exception as e:
            return ToolResult.error_result(str(e))


class QueryAccountingTool(AgentTool):
    """查询记账数据工具"""
    
    @property
    def name(self) -> str:
        return "query_accounting_data"
    
    @property
    def description(self) -> str:
        return """
        查询记账记录。
        Args:
            sql: SELECT 查询语句
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SELECT 查询语句",
                },
            },
            "required": ["sql"],
        }
    
    def execute(self, sql: str) -> ToolResult:
        try:
            from app.db.sqlite_client import SQLiteClient
            db = SQLiteClient()
            rows = db.query(sql, {})
            return ToolResult.success_result(str(rows))
        except Exception as e:
            return ToolResult.error_result(str(e))


class StatsByPeriodTool(AgentTool):
    """按时间段统计工具"""
    
    @property
    def name(self) -> str:
        return "stats_by_period"
    
    @property
    def description(self) -> str:
        return """
        统计指定时间段的收支情况。
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期 YYYY-MM-DD",
                },
            },
            "required": ["start_date", "end_date"],
        }
    
    def execute(self, start_date: str, end_date: str) -> ToolResult:
        try:
            from app.db.sqlite_client import SQLiteClient
            db = SQLiteClient()
            rows = db.query(
                """
                SELECT transaction_type, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE transaction_date BETWEEN :start AND :end
                GROUP BY transaction_type
                """,
                {"start": start_date, "end": end_date},
            )
            return ToolResult.success_result(str(rows))
        except Exception as e:
            return ToolResult.error_result(str(e))


class GetCategoriesTool(AgentTool):
    """获取分类工具"""
    
    @property
    def name(self) -> str:
        return "get_accounting_categories"
    
    @property
    def description(self) -> str:
        return "获取所有记账分类"
    
    @property
    def parameters(self) -> dict:
        return {}  # 无参数
    
    def execute(self) -> ToolResult:
        from app.db.accounting_db import EXPENSE_CATEGORIES, INCOME_CATEGORIES
        categories = {
            "expense": EXPENSE_CATEGORIES,
            "income": INCOME_CATEGORIES,
        }
        return ToolResult.success_result(str(categories))


class GetCurrentDatetimeTool(AgentTool):
    """获取当前时间工具"""
    
    @property
    def name(self) -> str:
        return "get_current_datetime"
    
    @property
    def description(self) -> str:
        return "获取当前日期和时间"
    
    @property
    def parameters(self) -> dict:
        return {}  # 无参数
    
    def execute(self) -> ToolResult:
        now = datetime.now()
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        result = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "weekday": weekday_names[now.weekday()],
            "datetime": now.isoformat(),
        }
        return ToolResult.success_result(str(result))


class CalculatorTool(AgentTool):
    """计算器工具"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """
        执行数学计算。
        Args:
            expression: 数学表达式，如 "100 + 50 * 2"
        """
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": '数学表达式，如 "100 + 50 * 2"',
                },
            },
            "required": ["expression"],
        }
    
    def execute(self, expression: str) -> ToolResult:
        try:
            # 安全计算
            import ast
            import operator
            
            allowed_operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_node(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    op_type = type(node.op)
                    if op_type in allowed_operators:
                        return allowed_operators[op_type](
                            eval_node(node.left), eval_node(node.right)
                        )
                elif isinstance(node, ast.UnaryOp):
                    if isinstance(node.op, ast.USub):
                        return -eval_node(node.operand)
                elif isinstance(node, ast.Expression):
                    return eval_node(node.body)
                raise ValueError(f"不支持的表达式: {expression}")
            
            tree = ast.parse(expression, mode='eval')
            result = eval_node(tree)
            return ToolResult.success_result(str(result))
        except Exception as e:
            return ToolResult.error_result(f"计算错误: {str(e)}")


class AccountingAgentService:
    """
    记账 Agent 应用服务
    
    基于 DDD 架构，使用 AbstractAgent 抽象。
    支持 LangGraph、Agno 等多种底层实现。
    
    Example:
        service = AccountingAgentService()
        response = await service.chat("花了50块吃饭", "deepseek-v3", "session-001")
    """

    # 记账专用工具列表
    ACCOUNTING_TOOLS: list[AgentTool] = [
        AddTransactionTool(),
        QueryAccountingTool(),
        StatsByPeriodTool(),
        GetCategoriesTool(),
        GetCurrentDatetimeTool(),
        CalculatorTool(),
    ]

    def __init__(
        self,
        agent_cache: AgentCache | None = None,
        llm_provider: LLMProvider | None = None,
    ):
        """
        初始化记账 Agent 服务
        
        Args:
            agent_cache: Agent 缓存，None 时自动创建
            llm_provider: LLM 提供器，None 时自动创建
        """
        self._agent_cache = agent_cache or InMemoryAgentCache()
        self._llm_provider = llm_provider or LLMProvider()
        self._today = date.today()

    def _get_or_create_agent(self, model: str) -> AbstractAgent:
        """
        获取或创建记账 Agent
        
        Args:
            model: 模型名称
            
        Returns:
            Agent 实例
        """
        cache_key = f"accounting:{model}:{self._today}"
        
        agent = self._agent_cache.get(cache_key)
        if agent is not None:
            logger.debug(f"命中记账 Agent 缓存: {cache_key}")
            return agent
        
        # 创建新 Agent
        llm_config = self._llm_provider.get_config(model)
        system_prompt = self._build_system_prompt()
        
        agent = LangGraphAgent(
            llm_config=llm_config,
            system_prompt=system_prompt,
            tool_adapters=[ToolAdapter(t) for t in self.ACCOUNTING_TOOLS],
        )
        
        self._agent_cache.set(cache_key, agent)
        logger.info(f"创建记账 Agent: {cache_key}")
        
        return agent

    def _build_system_prompt(self) -> str:
        """
        构建记账专用系统提示词
        
        Returns:
            系统提示词
        """
        now = datetime.now()
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekday_names[now.weekday()]
        today_str = now.strftime("%Y-%m-%d")
        
        # 计算昨天日期
        yesterday = now.replace(day=now.day - 1) if now.day > 1 else now
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        return f"""你是一个智能记账助手，帮助用户记录和分析日常收支。

## 当前时间（重要）
- 今天日期：{today_str}（{weekday}）
- 当前时间：{now.strftime("%H:%M")}
- **当用户没有说明日期时，一律使用今天的日期 {today_str}**
- 如需获取最新时间，可调用 get_current_datetime 工具

## 核心能力
1. **记账录入**：识别用户自然语言中的记账意图，提取交易类型、分类、金额、日期和备注，调用 add_transaction 工具存入数据库
2. **数据查询**：根据用户需求查询记账记录，支持按时间、分类等条件过滤
3. **统计分析**：统计收支汇总、分类占比、月度趋势等
4. **计算支持**：对数值进行精确计算

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
统计汇总 → stats_by_period
获取分类 → get_accounting_categories
计算 → calculator
"""

    async def chat(self, message: str, model: str, thread_id: str) -> ChatResponse:
        """
        记账对话
        
        Args:
            message: 用户消息
            model: 模型名称
            thread_id: 会话 ID
            
        Returns:
            响应
        """
        logger.info(f"AccountingAgentService.chat: model={model}, thread={thread_id}")
        
        agent = self._get_or_create_agent(model)
        response = await agent.ainvoke(message, thread_id)
        
        return ChatResponse(
            content=response.content,
            thread_id=thread_id,
            model=model,
            metadata=response.metadata,
        )

    async def stream_chat(
        self,
        message: str,
        model: str,
        thread_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式记账对话
        
        Args:
            message: 用户消息
            model: 模型名称
            thread_id: 会话 ID
            
        Yields:
            流式响应块
        """
        logger.info(f"AccountingAgentService.stream_chat: model={model}, thread={thread_id}")
        
        agent = self._get_or_create_agent(model)
        
        async for chunk in agent.astream(message, thread_id):
            if chunk.type.name == "CONTENT":
                yield StreamChunk(content=chunk.content)
            elif chunk.type.name == "TOOL_CALL":
                yield StreamChunk(is_tool_call=True, tool_name=chunk.tool_call.name if chunk.tool_call else None)
            elif chunk.type.name == "ERROR":
                yield StreamChunk(is_error=True, error_message=chunk.content)
            elif chunk.type.name == "DONE":
                yield StreamChunk(is_done=True)

    def clear_cache(self) -> int:
        """
        清空缓存
        
        Returns:
            清除的数量
        """
        return self._agent_cache.clear()

    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存信息
        """
        return self._agent_cache.info()
