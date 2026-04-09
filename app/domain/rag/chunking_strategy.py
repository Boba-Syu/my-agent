"""
分块策略定义

定义文档分块的各种策略。
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class ChunkingStrategyType(Enum):
    """分块策略类型"""
    
    NONE = "none"
    """不分块，完整保存"""
    
    FIXED_SIZE = "fixed_size"
    """固定大小分块"""
    
    SEPARATOR = "separator"
    """按分隔符分块"""
    
    PARAGRAPH = "paragraph"
    """按段落分块（双换行）"""


@dataclass(frozen=True)
class ChunkingConfig:
    """分块配置"""
    
    strategy: ChunkingStrategyType
    """分块策略"""
    
    chunk_size: int = 500
    """分块大小（固定大小时使用）"""
    
    chunk_overlap: int = 50
    """分块重叠大小"""
    
    separator: str = ""
    """分隔符（按分隔符分块时使用）"""
    
    @classmethod
    def no_chunking(cls) -> ChunkingConfig:
        """不分块的配置"""
        return cls(strategy=ChunkingStrategyType.NONE)
    
    @classmethod
    def fixed_size(
        cls,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> ChunkingConfig:
        """固定大小分块配置"""
        return cls(
            strategy=ChunkingStrategyType.FIXED_SIZE,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    
    @classmethod
    def by_separator(
        cls,
        separator: str,
        chunk_overlap: int = 50,
    ) -> ChunkingConfig:
        """按分隔符分块配置"""
        return cls(
            strategy=ChunkingStrategyType.SEPARATOR,
            separator=separator,
            chunk_overlap=chunk_overlap,
        )
    
    @classmethod
    def by_paragraph(cls, chunk_overlap: int = 50) -> ChunkingConfig:
        """按段落分块配置"""
        return cls(
            strategy=ChunkingStrategyType.PARAGRAPH,
            separator="\n\n",
            chunk_overlap=chunk_overlap,
        )
