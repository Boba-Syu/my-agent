"""
HTTP 路由

FastAPI 路由定义。
"""

from __future__ import annotations

from app.interfaces.http.routes.agent_routes import router as agent_router
from app.interfaces.http.routes.accounting_routes import router as accounting_router
from app.interfaces.http.routes.rag_routes import router as rag_router

__all__ = [
    "agent_router",
    "accounting_router",
    "rag_router",
]
