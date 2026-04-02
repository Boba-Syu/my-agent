"""
文档处理器接口

定义文档解析和分块的领域层契约。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.domain.rag.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentProcessor(ABC):
    """
    文档处理器接口
    
    定义文档解析和分块的领域层契约，由基础设施层实现。
    
    支持策略模式，不同文档类型使用不同的处理器：
    - PDF处理器：使用PyPDF2/pdfplumber
    - Word处理器：使用python-docx
    - 文本处理器：直接读取
    
    Example:
        class PDFProcessor(DocumentProcessor):
            def can_process(self, file_path):
                return file_path.endswith('.pdf')
            
            def process(self, file_path):
                # 解析PDF并分块
                pass
    """
    
    @property
    @abstractmethod
    def supported_types(self) -> list[str]:
        """
        支持的文档类型列表
        
        Returns:
            文件扩展名列表，如 ["pdf", "docx"]
        """
        pass
    
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """
        检查是否能处理指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否能处理
        """
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """
        提取文档文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
            
        Raises:
            ValueError: 文件格式不支持或解析失败
        """
        pass
    
    @abstractmethod
    def split_into_chunks(
        self,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[DocumentChunk]:
        """
        将文本分块
        
        Args:
            content: 文本内容
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
            
        Returns:
            分块列表
        """
        pass
    
    @abstractmethod
    def process(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> tuple[str, list[DocumentChunk]]:
        """
        处理文档（提取文本+分块）
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            (原始文本, 分块列表)
        """
        pass
