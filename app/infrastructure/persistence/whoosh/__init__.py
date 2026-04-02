"""
Whoosh 关键词索引实现

提供倒排索引支持，用于混合检索。
"""

from __future__ import annotations

from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

__all__ = ["WhooshKeywordIndex"]
