"""
文档处理器模块

提供各种文档格式的解析和分块功能。
"""

from __future__ import annotations

from app.infrastructure.rag.processors.text_processor import TextProcessor
from app.infrastructure.rag.processors.pdf_processor import PDFProcessor
from app.infrastructure.rag.processors.word_processor import WordProcessor
from app.infrastructure.rag.processors.processor_factory import ProcessorFactory

__all__ = [
    "TextProcessor",
    "PDFProcessor",
    "WordProcessor",
    "ProcessorFactory",
]
