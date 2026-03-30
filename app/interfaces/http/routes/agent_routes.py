"""
Agent API 路由

基于 DDD 架构的通用 Agent 接口。
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.application.agent.agent_service import AgentService
from app.application.agent.dto import ChatRequest as ChatRequestDTO
from app.interfaces.http.dependencies import AgentServiceDep
from app.interfaces.http.schemas.agent_schemas import (
    ChatRequest,
    ChatResponse,
    ToolInfo,
    HealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Agent"])


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check() -> HealthResponse:
    """检查服务是否正常运行"""
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse, summary="对话接口")
async def chat(
    request: ChatRequest,
    service: AgentServiceDep,
) -> ChatResponse:
    """
    与 Agent 进行对话
    
    - 支持多轮上下文（通过 thread_id）
    - 支持选择不同模型
    - 支持自定义系统提示词
    """
    logger.info(
        f"收到对话请求：thread_id={request.thread_id}, model={request.model}, "
        f"message_len={len(request.message)}"
    )
    
    try:
        response = await service.chat(ChatRequestDTO(
            message=request.message,
            model=request.model,
            thread_id=request.thread_id,
            system_prompt=request.system_prompt,
        ))
        
        return ChatResponse(
            reply=response.content,
            thread_id=response.thread_id,
            model=response.model,
        )
    except Exception as e:
        logger.error(f"Agent 执行失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent 执行失败：{str(e)}")


@router.post("/chat/stream", summary="流式对话接口（SSE）")
async def chat_stream(
    request: ChatRequest,
    service: AgentServiceDep,
) -> StreamingResponse:
    """
    与 Agent 进行流式对话，使用 Server-Sent Events 逐步返回结果
    """
    logger.info(f"收到流式对话请求：thread_id={request.thread_id}")
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in service.stream_chat(ChatRequestDTO(
                message=request.message,
                model=request.model,
                thread_id=request.thread_id,
                system_prompt=request.system_prompt,
            )):
                if chunk.is_done:
                    yield "data: [DONE]\n\n"
                elif chunk.is_error:
                    yield f"data: [ERROR] {chunk.error_message}\n\n"
                elif chunk.is_tool_call:
                    tool_info = {"type": "tool_call", "name": chunk.tool_name}
                    yield f"data: [TOOL_CALL] {json.dumps(tool_info)}\n\n"
                else:
                    # SSE 格式
                    escaped = chunk.content.replace('\n', '\ndata: ')
                    yield f"data: {escaped}\n\n"
        except Exception as e:
            logger.error(f"流式 Agent 执行失败：{e}", exc_info=True)
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools", response_model=list[ToolInfo], summary="查询可用工具列表")
async def list_tools() -> list[ToolInfo]:
    """返回当前 Agent 可使用的所有工具信息"""
    # TODO: 从 ToolRegistry 获取工具列表
    return [
        ToolInfo(name="calculator", description="执行数学计算"),
        ToolInfo(name="datetime", description="获取当前日期时间"),
    ]


@router.get("/admin/cache", summary="获取 Agent 缓存信息")
async def get_cache_info(service: AgentServiceDep) -> dict:
    """获取当前 Agent 实例缓存状态（调试用）"""
    return service.get_cache_info()


@router.post("/admin/cache/clear", summary="清空 Agent 缓存")
async def clear_cache(service: AgentServiceDep) -> dict:
    """清空 Agent 实例缓存，下次请求将重新创建 Agent（热更新用）"""
    count = service.clear_cache()
    return {"success": True, "cleared_count": count}
