"""
记账 Agent API 路由模块

提供记账相关的 HTTP 接口：
- POST /accounting/chat       - 记账对话接口
- POST /accounting/chat/stream - 流式记账对话（SSE）
- GET  /accounting/records    - 查询记账记录
- POST /accounting/records    - 创建记账记录
- PUT  /accounting/records/{id} - 更新记账记录
- DELETE /accounting/records/{id} - 删除记账记录
- GET  /accounting/stats      - 收支统计汇总
- GET  /accounting/categories - 获取所有分类
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, ToolMessage

from app.agent.accounting_agent import (
    create_accounting_agent,
    get_cached_agent_info,
    clear_agent_cache,
)
from app.db.accounting_db import (
    query_transactions,
    insert_transaction,
    update_transaction,
    delete_transaction,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
)
from app.db.sqlite_client import SQLiteClient
from app.utils.logging_utils import set_trace_id, get_trace_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/accounting", tags=["记账 Agent"])


# ────────────────────────────────────────────────────────────
# 请求 / 响应模型
# ────────────────────────────────────────────────────────────


class AccountingChatRequest(BaseModel):
    """记账对话请求体"""

    message: str = Field(..., description="用户输入，例如：'花了50块吃饭'", min_length=1, max_length=5000)
    model: str = Field(default="deepseek-v3", description="LLM 模型名称")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="会话线程 ID，相同 ID 可保持多轮上下文",
    )


class AccountingChatResponse(BaseModel):
    """记账对话响应体"""

    reply: str = Field(..., description="Agent 回复内容")
    thread_id: str = Field(..., description="会话线程 ID")
    model: str = Field(..., description="使用的模型名称")


class TransactionRecord(BaseModel):
    """记账记录"""

    id: int
    transaction_type: str
    category: str
    amount: float
    note: str = ""
    transaction_date: str
    created_at: str = ""


class StatsResponse(BaseModel):
    """收支统计响应"""

    income_total: float
    expense_total: float
    net: float
    income_count: int
    expense_count: int
    start_date: str
    end_date: str


# ────────────────────────────────────────────────────────────
# 路由定义
# ────────────────────────────────────────────────────────────


@router.post("/chat", response_model=AccountingChatResponse, summary="记账对话接口")
async def accounting_chat(request: AccountingChatRequest) -> AccountingChatResponse:
    """
    与记账 Agent 进行自然语言对话。

    支持：
    - 自然语言录入记账（"花了30块吃饭"）
    - 查询/统计收支数据（"本月花了多少钱"）
    - 导出数据（"导出本月记录为 Excel"）
    - 计算分析（"上个月三餐和交通共花了多少"）

    优化：Agent 实例已缓存，无需担心性能问题
    """
    tid = set_trace_id()
    logger.info("[tid=%s] POST /chat | thread=%s | message: %s", tid, request.thread_id, request.message[:100])
    try:
        agent = create_accounting_agent(model=request.model)
        reply = await agent.ainvoke(
            message=request.message,
            thread_id=request.thread_id,
        )
        logger.info("[tid=%s] POST /chat 完成 | thread=%s", tid, request.thread_id)
        return AccountingChatResponse(
            reply=reply,
            thread_id=request.thread_id,
            model=request.model,
        )
    except Exception as e:
        logger.error("[tid=%s] POST /chat 失败: %s", tid, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"记账 Agent 执行失败：{str(e)}")


@router.post("/chat/stream", summary="流式记账对话接口（SSE）")
async def accounting_chat_stream(request: AccountingChatRequest) -> StreamingResponse:
    """
    流式记账对话，使用 Server-Sent Events 逐步返回结果。

    SSE 消息格式：
    - 正常内容：data: <文本内容>\n\n
    - 工具调用开始：data: [TOOL_CALL] {"name": "工具名", "args": {...}}\n\n
    - 工具结果：data: [TOOL_RESULT] {"name": "工具名", "result": "..."}\n\n
    - 完成标记：data: [DONE]\n\n
    - 错误：data: [ERROR] 错误信息\n\n

    优化：使用异步 astream() 替代同步 stream()，不阻塞事件循环
    """
    tid = set_trace_id()
    logger.info("[tid=%s] POST /chat/stream | thread=%s | message: %s", tid, request.thread_id, request.message[:100])

    async def generate() -> AsyncGenerator[str, None]:
        agent = None
        try:
            agent = create_accounting_agent(model=request.model)
            last_final_content = ""  # 记录上次 yield 的最终回复内容
            yielded_tool_calls = set()  # 已推送过的工具调用 ID
            yielded_tool_results = set()  # 已推送过的工具结果 ID

            async for chunk in agent.astream(
                message=request.message,
                thread_id=request.thread_id,
            ):
                # 检查是否是错误标记
                if chunk.get("__error__"):
                    error_msg = chunk["__error__"]
                    logger.error("[tid=%s] astream 返回错误: %s", tid, error_msg)
                    yield f"data: [ERROR] {error_msg}\n\n"
                    return

                messages = chunk.get("messages", [])
                if not messages:
                    continue

                # 遍历消息，推送工具调用状态和最终回复
                for msg in messages:
                    # 处理工具调用（AIMessage 带 tool_calls）
                    if isinstance(msg, AIMessage):
                        tool_calls = getattr(msg, "tool_calls", None) or []
                        for tc in tool_calls:
                            tc_id = tc.get("id", "")
                            if tc_id and tc_id not in yielded_tool_calls:
                                yielded_tool_calls.add(tc_id)
                                # 推送工具调用开始标记
                                tool_call_info = {
                                    "name": tc.get("name", "?"),
                                    "args": tc.get("args", {}),
                                    "id": tc_id,
                                }
                                yield f"data: [TOOL_CALL] {json.dumps(tool_call_info, ensure_ascii=False)}\n\n"

                        # 处理最终回复（没有 tool_calls 的 AIMessage）
                        if not tool_calls:
                            content = getattr(msg, "content", "")
                            if content:
                                if isinstance(content, list):
                                    # 过滤 reasoning 类型
                                    content = "".join(
                                        p.get("text", "")
                                        for p in content
                                        if isinstance(p, dict) and p.get("type") != "reasoning"
                                    )
                                if content and content != last_final_content:
                                    # 只 yield 新的内容（增量）
                                    new_content = content[len(last_final_content):]
                                    if new_content:
                                        # SSE 格式：将内容中的换行符替换为 \ndata: 以保持多行在一个消息中
                                        escaped_content = new_content.replace('\n', '\ndata: ')
                                        yield f"data: {escaped_content}\n\n"
                                        last_final_content = content

                    # 处理工具返回结果（ToolMessage）
                    elif isinstance(msg, ToolMessage):
                        msg_id = getattr(msg, "tool_call_id", "") or str(id(msg))
                        if msg_id and msg_id not in yielded_tool_results:
                            yielded_tool_results.add(msg_id)
                            # 推送工具结果标记
                            result_preview = str(msg.content)[:500]  # 限制长度
                            tool_result_info = {
                                "name": msg.name,
                                "result": result_preview,
                                "id": msg_id,
                            }
                            yield f"data: [TOOL_RESULT] {json.dumps(tool_result_info, ensure_ascii=False)}\n\n"

            logger.info("[tid=%s] POST /chat/stream 完成 | thread=%s | 最终内容长度=%d", tid, request.thread_id, len(last_final_content))
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("[tid=%s] POST /chat/stream 失败: %s", tid, e, exc_info=True)
            error_msg = str(e)
            # 提供友好的错误信息
            if "TimeoutError" in error_msg or "timeout" in error_msg.lower():
                error_msg = "处理时间过长，请稍后再试"
            elif "rate limit" in error_msg.lower():
                error_msg = "服务繁忙，请稍后再试"
            yield f"data: [ERROR] {error_msg}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/records", response_model=list[TransactionRecord], summary="查询记账记录")
async def get_records(
    transaction_type: str | None = Query(default=None, description="交易类型: expense / income"),
    category: str | None = Query(default=None, description="分类名称"),
    start_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=1000, description="返回条数限制"),
) -> list[TransactionRecord]:
    """查询记账记录，支持多维度过滤"""
    try:
        rows = query_transactions(
            transaction_type=transaction_type,
            category=category,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return [
            TransactionRecord(
                id=r["id"],
                transaction_type=r["transaction_type"],
                category=r["category"],
                amount=r["amount"],
                note=r.get("note") or "",
                transaction_date=r["transaction_date"],
                created_at=str(r.get("created_at") or ""),
            )
            for r in rows
        ]
    except Exception as e:
        logger.error(f"查询记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/stats", response_model=StatsResponse, summary="收支统计")
async def get_stats(
    start_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
) -> StatsResponse:
    """统计指定时间段内的收支总额"""
    from datetime import date
    import calendar

    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime("%Y-%m-%d")

    try:
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

        return StatsResponse(
            income_total=income_total,
            expense_total=expense_total,
            net=income_total - expense_total,
            income_count=income_count,
            expense_count=expense_count,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.error(f"统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"统计失败：{str(e)}")


@router.get("/categories", summary="获取所有分类")
async def get_categories() -> dict:
    """返回支出和收入的所有支持分类"""
    return {
        "expense_categories": EXPENSE_CATEGORIES,
        "income_categories": INCOME_CATEGORIES,
    }


# ────────────────────────────────────────────────────────────
# 管理接口（Agent 缓存管理）
# ────────────────────────────────────────────────────────────


@router.get("/admin/cache", summary="获取 Agent 缓存信息")
async def get_cache_info() -> dict:
    """获取当前 Agent 实例缓存状态（调试用）"""
    return get_cached_agent_info()


@router.post("/admin/cache/clear", summary="清空 Agent 缓存")
async def clear_cache() -> dict:
    """清空 Agent 实例缓存，下次请求将重新创建 Agent（热更新用）"""
    count = clear_agent_cache()
    return {"success": True, "cleared_count": count}


# ────────────────────────────────────────────────────────────
# CRUD 路由（新增/更新/删除）
# ────────────────────────────────────────────────────────────


class CreateRecordRequest(BaseModel):
    """创建记录请求体"""

    transaction_type: str = Field(..., description="交易类型: expense / income")
    category: str = Field(..., description="分类名称")
    amount: float = Field(..., description="金额", gt=0)
    note: str = Field(default="", description="备注")
    transaction_date: str | None = Field(default=None, description="交易日期 YYYY-MM-DD")


class UpdateRecordRequest(BaseModel):
    """更新记录请求体"""

    transaction_type: str | None = Field(default=None, description="交易类型: expense / income")
    category: str | None = Field(default=None, description="分类名称")
    amount: float | None = Field(default=None, description="金额", gt=0)
    note: str | None = Field(default=None, description="备注")
    transaction_date: str | None = Field(default=None, description="交易日期 YYYY-MM-DD")


class OperationResponse(BaseModel):
    """操作响应体"""

    success: bool
    message: str = ""
    record: TransactionRecord | None = None


def _row_to_record(r: dict) -> TransactionRecord:
    """将数据库行转换为 TransactionRecord"""
    return TransactionRecord(
        id=r["id"],
        transaction_type=r["transaction_type"],
        category=r["category"],
        amount=r["amount"],
        note=r.get("note") or "",
        transaction_date=r["transaction_date"],
        created_at=str(r.get("created_at") or ""),
    )


@router.post("/records", response_model=OperationResponse, summary="创建记账记录")
async def create_record(request: CreateRecordRequest) -> OperationResponse:
    """手动创建一条记账记录"""
    try:
        result = insert_transaction(
            transaction_type=request.transaction_type,
            category=request.category,
            amount=request.amount,
            note=request.note,
            transaction_date=request.transaction_date,
        )
        if not result["success"]:
            return OperationResponse(success=False, message=result["error"])
        return OperationResponse(
            success=True,
            message="创建成功",
            record=_row_to_record(result["record"]),
        )
    except Exception as e:
        logger.error(f"创建记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败：{str(e)}")


@router.put("/records/{record_id}", response_model=OperationResponse, summary="更新记账记录")
async def update_record(record_id: int, request: UpdateRecordRequest) -> OperationResponse:
    """更新指定记账记录"""
    try:
        result = update_transaction(
            record_id=record_id,
            transaction_type=request.transaction_type,
            category=request.category,
            amount=request.amount,
            note=request.note,
            transaction_date=request.transaction_date,
        )
        if not result["success"]:
            return OperationResponse(success=False, message=result["error"])
        return OperationResponse(
            success=True,
            message="更新成功",
            record=_row_to_record(result["record"]),
        )
    except Exception as e:
        logger.error(f"更新记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


@router.delete("/records/{record_id}", response_model=OperationResponse, summary="删除记账记录")
async def delete_record(record_id: int) -> OperationResponse:
    """删除指定记账记录"""
    try:
        result = delete_transaction(record_id=record_id)
        if not result["success"]:
            return OperationResponse(success=False, message=result["error"])
        return OperationResponse(
            success=True,
            message="删除成功",
            record=_row_to_record(result["record"]),
        )
    except Exception as e:
        logger.error(f"删除记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")
