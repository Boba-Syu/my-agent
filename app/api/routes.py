"""
FastAPI 路由模块

提供 Agent 的 HTTP 接口，包括：
- POST /chat        - 同步对话接口
- POST /chat/stream - 流式对话接口（Server-Sent Events）
- GET  /health      - 健康检查接口
- GET  /tools       - 查询当前可用工具列表
"""

from __future__ import annotations

import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.react_agent import ReactAgent
from app.llm.llm_factory import LLMFactory
from app.tools import ALL_TOOLS
from app.mcp.example_mcp import get_weather
from app.skills.example_skill import summarize_text
from app.config import get_agent_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/v1", tags=["Agent"])

# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """对话请求体"""

    message: str = Field(..., description="用户输入的消息", min_length=1, max_length=10000)
    model: str = Field(default="deepseek-v3", description="使用的 LLM 模型名称")
    system_prompt: str | None = Field(default=None, description="自定义系统提示词（为空时使用默认值）")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="会话线程 ID，相同 ID 可保持多轮上下文",
    )
    use_all_tools: bool = Field(default=True, description="是否使用全部工具（含 MCP/Skill）")


class ChatResponse(BaseModel):
    """对话响应体"""

    reply: str = Field(..., description="Agent 回复内容")
    thread_id: str = Field(..., description="本次对话的线程 ID")
    model: str = Field(..., description="实际使用的模型名称")


class ToolInfo(BaseModel):
    """工具信息"""

    name: str
    description: str


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# 全局工具列表（基础工具 + MCP 工具 + Skill 工具）
# ---------------------------------------------------------------------------
_EXTENDED_TOOLS = ALL_TOOLS + [get_weather, summarize_text]


def _build_agent(model: str, system_prompt: str | None, use_all_tools: bool) -> ReactAgent:
    """
    根据请求参数构建 ReactAgent 实例

    Args:
        model:        LLM 模型名称
        system_prompt: 自定义系统提示词
        use_all_tools: 是否使用全部工具

    Returns:
        配置好的 ReactAgent 实例
    """
    llm = LLMFactory.create_llm(model)
    tools = _EXTENDED_TOOLS if use_all_tools else ALL_TOOLS
    return ReactAgent(llm=llm, tools=tools, system_prompt=system_prompt)


# ---------------------------------------------------------------------------
# 路由定义
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check() -> HealthResponse:
    """检查服务是否正常运行"""
    return HealthResponse(status="ok")


@router.get("/tools", response_model=list[ToolInfo], summary="查询可用工具列表")
async def list_tools() -> list[ToolInfo]:
    """返回当前 Agent 可使用的所有工具信息"""
    return [
        ToolInfo(name=t.name, description=t.description or "")
        for t in _EXTENDED_TOOLS
    ]


@router.post("/chat", response_model=ChatResponse, summary="对话接口（异步）")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    与 Agent 进行对话

    - 支持多轮上下文（通过 thread_id）
    - 支持选择不同模型
    - 支持自定义系统提示词
    - Agent 会自动选择合适的工具完成任务
    """
    logger.info(
        f"收到对话请求：thread_id={request.thread_id}, model={request.model}, "
        f"message_len={len(request.message)}"
    )

    try:
        agent = _build_agent(
            model=request.model,
            system_prompt=request.system_prompt,
            use_all_tools=request.use_all_tools,
        )
        reply = await agent.ainvoke(
            message=request.message,
            thread_id=request.thread_id,
        )
        return ChatResponse(
            reply=reply,
            thread_id=request.thread_id,
            model=request.model,
        )

    except Exception as e:
        logger.error(f"Agent 执行失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent 执行失败：{str(e)}")


@router.post("/chat/stream", summary="流式对话接口（SSE）")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    与 Agent 进行流式对话，使用 Server-Sent Events 逐步返回结果

    客户端需处理 text/event-stream 格式的响应
    """
    logger.info(f"收到流式对话请求：thread_id={request.thread_id}")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            agent = _build_agent(
                model=request.model,
                system_prompt=request.system_prompt,
                use_all_tools=request.use_all_tools,
            )
            # 流式输出每个步骤
            for chunk in agent.stream(
                message=request.message,
                thread_id=request.thread_id,
            ):
                messages = chunk.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    content = getattr(last_msg, "content", "")
                    if content:
                        if isinstance(content, list):
                            content = "".join(
                                p.get("text", "") if isinstance(p, dict) else str(p)
                                for p in content
                            )
                        yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"

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
