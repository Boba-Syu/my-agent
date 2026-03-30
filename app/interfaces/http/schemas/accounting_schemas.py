"""
记账相关请求/响应模型
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


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
    note: str | None = ""
    transaction_date: str
    created_at: str | None = ""


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


class StatsResponse(BaseModel):
    """收支统计响应"""
    
    income_total: float
    expense_total: float
    net: float
    income_count: int
    expense_count: int
    start_date: str
    end_date: str


class CategorySummary(BaseModel):
    """分类汇总"""
    
    category: str
    total: float
    count: int


class DailySummary(BaseModel):
    """每日汇总"""
    
    date: str
    income: float
    expense: float
    count: int


class CategoriesResponse(BaseModel):
    """分类列表响应"""
    
    expense_categories: list[str]
    income_categories: list[str]
