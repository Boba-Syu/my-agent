"""
Agent 框架启动入口 (DDD 架构)

运行方式：
    # 开发模式（热重载）
    uv run python main.py

    # 或直接用 uvicorn
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

接口文档：
    Swagger UI : http://localhost:8000/docs
    ReDoc      : http://localhost:8000/redoc
"""

from __future__ import annotations

import logging
import logging.config

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_server_config
from app.interfaces.http.routes import agent_router, accounting_router, rag_router
from app.utils.logging_utils import TraceIdFormatter

# ---------------------------------------------------------------------------
# 日志配置：带 TraceID 的格式化输出
# ---------------------------------------------------------------------------
_handler = logging.StreamHandler()
_handler.setFormatter(
    TraceIdFormatter(
        fmt="%(asctime)s [%(levelname)-5s] [tid=%(trace_id)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# 根 logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(_handler)

# 屏蔽第三方库的冗余日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI 应用实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="My Agent - DDD 可扩展 Agent 框架",
    description=(
        "基于 DDD（领域驱动设计）架构的可扩展 Agent 框架\n\n"
        "**架构特点：**\n"
        "- 领域层独立：核心业务逻辑与框架无关\n"
        "- 基础设施可替换：支持 LangGraph、Agno 等多种实现\n"
        "- 四层架构：领域层/应用层/基础设施层/接口层\n"
        "- AbstractAgent 抽象：可轻松切换底层框架\n\n"
        "**功能特性：**\n"
        "- 多轮对话（通过 thread_id 保持上下文）\n"
        "- 三层工具扩展（Tool / MCP / Skill）\n"
        "- 流式输出（SSE）\n"
        "- 模型切换（deepseek-v3 / deepseek-r1）\n"
        "- 向量数据库支持（Milvus）\n\n"
        "**当前实现：**\n"
        "- 记账 Agent（收入/支出管理、数据可视化）\n\n"
        "此框架设计用于快速构建各类垂直领域 Agent。\n"
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# 中间件：CORS（允许前端 dev server 和生产来源）
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------
app.include_router(agent_router)
app.include_router(accounting_router)
app.include_router(rag_router)


# ---------------------------------------------------------------------------
# 根路由：API 存活检查
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "message": "My Agent API is running (DDD Architecture)",
        "docs": "/docs",
        "version": "0.2.0",
        "architecture": "ddd",
    }


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    server_cfg = get_server_config()

    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8000)
    reload = server_cfg.get("reload", True)
    debug = server_cfg.get("debug", True)

    logger.info(f"启动 Agent 服务（DDD 架构）：http://{host}:{port}")
    logger.info(f"Swagger 文档：http://127.0.0.1:{port}/docs")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if debug else "info",
    )
