"""
记账 API 路由

基于 DDD 架构的记账 Agent 接口。
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.application.accounting.accounting_agent_service import AccountingAgentService
from app.application.accounting.dto import CreateTransactionDTO, TransactionQueryDTO
from app.application.accounting.transaction_service import TransactionService
from app.interfaces.http.dependencies import (
    AccountingAgentServiceDep,
    TransactionServiceDep,
)
from app.interfaces.http.schemas.accounting_schemas import (
    AccountingChatRequest,
    AccountingChatResponse,
    TransactionRecord,
    CreateRecordRequest,
    UpdateRecordRequest,
    OperationResponse,
    StatsResponse,
    CategoriesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/accounting", tags=["记账 Agent"])


# ───────────────────────────────────────────────────────────
# 记账对话接口
# ───────────────────────────────────────────────────────────

@router.post("/chat", response_model=AccountingChatResponse, summary="记账对话接口")
async def accounting_chat(
    request: AccountingChatRequest,
    service: AccountingAgentServiceDep,
) -> AccountingChatResponse:
    """
    与记账 Agent 进行自然语言对话。
    
    支持：
    - 自然语言录入记账（"花了30块吃饭"）
    - 查询/统计收支数据（"本月花了多少钱"）
    - 计算分析（"上个月三餐和交通共花了多少"）
    """
    logger.info(
        f"记账对话请求：thread={request.thread_id}, model={request.model}, "
        f"message={request.message[:100]}"
    )
    
    try:
        response = await service.chat(
            message=request.message,
            model=request.model,
            thread_id=request.thread_id,
        )
        
        return AccountingChatResponse(
            reply=response.content,
            thread_id=request.thread_id,
            model=request.model,
        )
    except Exception as e:
        logger.error(f"记账 Agent 执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"记账 Agent 执行失败：{str(e)}")


@router.post("/chat/stream", summary="流式记账对话接口（SSE）")
async def accounting_chat_stream(
    request: AccountingChatRequest,
    service: AccountingAgentServiceDep,
) -> StreamingResponse:
    """
    流式记账对话，使用 Server-Sent Events 逐步返回结果。
    """
    logger.info(f"流式记账对话请求：thread={request.thread_id}")
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in service.stream_chat(
                message=request.message,
                model=request.model,
                thread_id=request.thread_id,
            ):
                if chunk.is_done:
                    yield "data: [DONE]\n\n"
                elif chunk.is_error:
                    yield f"data: [ERROR] {chunk.error_message}\n\n"
                elif chunk.is_tool_call:
                    tool_info = {"type": "tool_call", "name": chunk.tool_name}
                    yield f"data: [TOOL_CALL] {json.dumps(tool_info, ensure_ascii=False)}\n\n"
                else:
                    escaped = chunk.content.replace('\n', '\ndata: ')
                    yield f"data: {escaped}\n\n"
        except Exception as e:
            logger.error(f"流式记账 Agent 失败: {e}", exc_info=True)
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ───────────────────────────────────────────────────────────
# 交易记录 CRUD 接口
# ───────────────────────────────────────────────────────────

@router.get("/records", response_model=list[TransactionRecord], summary="查询记账记录")
async def get_records(
    transaction_type: str | None = Query(default=None, description="交易类型: expense / income"),
    category: str | None = Query(default=None, description="分类名称"),
    start_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=1000, description="返回条数限制"),
    service: TransactionServiceDep = None,
) -> list[TransactionRecord]:
    """查询记账记录，支持多维度过滤"""
    try:
        transactions = service.list_transactions(TransactionQueryDTO(
            transaction_type=transaction_type,
            category=category,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ))
        
        return [
            TransactionRecord(
                id=t.id,
                transaction_type=t.transaction_type,
                category=t.category,
                amount=t.amount,
                note=t.note,
                transaction_date=t.transaction_date,
                created_at=t.created_at or "",
            )
            for t in transactions
        ]
    except Exception as e:
        logger.error(f"查询记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.post("/records", response_model=OperationResponse, summary="创建记账记录")
async def create_record(
    request: CreateRecordRequest,
    service: TransactionServiceDep,
) -> OperationResponse:
    """手动创建一条记账记录"""
    try:
        # 使用今天日期作为默认
        transaction_date = request.transaction_date or date.today().isoformat()
        
        transaction = service.create_transaction(CreateTransactionDTO(
            transaction_type=request.transaction_type,
            category=request.category,
            amount=request.amount,
            transaction_date=transaction_date,
            note=request.note,
        ))
        
        return OperationResponse(
            success=True,
            message="创建成功",
            record=TransactionRecord(
                id=transaction.id,
                transaction_type=transaction.transaction_type,
                category=transaction.category,
                amount=transaction.amount,
                note=transaction.note,
                transaction_date=transaction.transaction_date,
                created_at=transaction.created_at or "",
            ),
        )
    except Exception as e:
        logger.error(f"创建记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败：{str(e)}")


@router.put("/records/{record_id}", response_model=OperationResponse, summary="更新记账记录")
async def update_record(
    record_id: int,
    request: UpdateRecordRequest,
    service: TransactionServiceDep,
) -> OperationResponse:
    """更新指定记账记录"""
    try:
        # 获取现有记录
        existing = service.get_transaction(str(record_id))
        if not existing:
            return OperationResponse(success=False, message="记录不存在")
        
        # 更新（只更新提供的字段）
        transaction = service.update_transaction(
            str(record_id),
            CreateTransactionDTO(
                transaction_type=request.transaction_type or existing.transaction_type,
                category=request.category or existing.category,
                amount=request.amount or existing.amount,
                transaction_date=request.transaction_date or existing.transaction_date,
                note=request.note if request.note is not None else existing.note,
            ),
        )
        
        if not transaction:
            return OperationResponse(success=False, message="更新失败")
        
        return OperationResponse(
            success=True,
            message="更新成功",
            record=TransactionRecord(
                id=transaction.id,
                transaction_type=transaction.transaction_type,
                category=transaction.category,
                amount=transaction.amount,
                note=transaction.note,
                transaction_date=transaction.transaction_date,
                created_at=transaction.created_at or "",
            ),
        )
    except Exception as e:
        logger.error(f"更新记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


@router.delete("/records/{record_id}", response_model=OperationResponse, summary="删除记账记录")
async def delete_record(
    record_id: int,
    service: TransactionServiceDep,
) -> OperationResponse:
    """删除指定记账记录"""
    try:
        success = service.delete_transaction(str(record_id))
        if success:
            return OperationResponse(success=True, message="删除成功")
        else:
            return OperationResponse(success=False, message="记录不存在或删除失败")
    except Exception as e:
        logger.error(f"删除记账记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


# ───────────────────────────────────────────────────────────
# 统计接口
# ───────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse, summary="收支统计")
async def get_stats(
    start_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    service: TransactionServiceDep = None,
) -> StatsResponse:
    """统计指定时间段内的收支总额"""
    import calendar
    
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).isoformat()
    
    try:
        stats = service.get_statistics(start_date, end_date)
        
        return StatsResponse(
            income_total=stats.income_total,
            expense_total=stats.expense_total,
            net=stats.net,
            income_count=stats.income_count,
            expense_count=stats.expense_count,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.error(f"统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"统计失败：{str(e)}")


@router.get("/categories", response_model=CategoriesResponse, summary="获取所有分类")
async def get_categories() -> CategoriesResponse:
    """返回支出和收入的所有支持分类"""
    from app.db.accounting_db import EXPENSE_CATEGORIES, INCOME_CATEGORIES
    
    return CategoriesResponse(
        expense_categories=EXPENSE_CATEGORIES,
        income_categories=INCOME_CATEGORIES,
    )


# ───────────────────────────────────────────────────────────
# 管理接口
# ───────────────────────────────────────────────────────────

@router.get("/admin/cache", summary="获取记账 Agent 缓存信息")
async def get_cache_info(service: AccountingAgentServiceDep) -> dict:
    """获取当前记账 Agent 实例缓存状态（调试用）"""
    return service.get_cache_info()


@router.post("/admin/cache/clear", summary="清空记账 Agent 缓存")
async def clear_cache(service: AccountingAgentServiceDep) -> dict:
    """清空记账 Agent 实例缓存，下次请求将重新创建 Agent（热更新用）"""
    count = service.clear_cache()
    return {"success": True, "cleared_count": count}
