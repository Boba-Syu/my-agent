"""
PDF 处理器

处理PDF文件的解析和分块。
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class PDFProcessor(DocumentProcessor):
    """
    PDF 处理器
    
    使用 PyPDF2 或 pdfplumber 解析PDF文件。
    """
    
    @property
    def supported_types(self) -> list[str]:
        """支持的文件类型"""
        return ["pdf"]
    
    def can_process(self, file_path: str) -> bool:
        """检查是否能处理"""
        return file_path.lower().endswith(".pdf")
    
    def extract_text(self, file_path: str) -> str:
        """
        提取PDF文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本
        """
        try:
            # 优先使用 pdfplumber（效果更好）
            try:
                import pdfplumber
                return self._extract_with_pdfplumber(file_path)
            except ImportError:
                pass
            
            # 备选 PyPDF2
            try:
                import PyPDF2
                return self._extract_with_pypdf2(file_path)
            except ImportError:
                pass
            
            raise ImportError("未找到PDF解析库，请安装: uv add pdfplumber 或 uv add PyPDF2")
            
        except Exception as e:
            logger.error(f"解析PDF失败: {file_path}, 错误: {e}")
            raise ValueError(f"无法解析PDF: {file_path}")
    
    def _extract_with_pdfplumber(self, file_path: str) -> str:
        """使用pdfplumber提取文本"""
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- 第{page_num}页 ---\n{page_text}")
        
        return "\n".join(text_parts)
    
    def _extract_with_pypdf2(self, file_path: str) -> str:
        """使用PyPDF2提取文本"""
        import PyPDF2
        
        text_parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- 第{page_num}页 ---\n{page_text}")
        
        return "\n".join(text_parts)
    
    def split_into_chunks(
        self,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[DocumentChunk]:
        """
        将文本分块
        
        继承文本处理器的分块逻辑，同时保留页码信息。
        """
        if not content:
            return []
        
        # 按页分割内容
        pages = content.split("\n--- 第")
        
        chunks = []
        index = 0
        
        for page in pages:
            if not page.strip():
                continue
            
            # 提取页码
            page_num = 0
            if "页 ---" in page:
                parts = page.split("页 ---", 1)
                try:
                    page_num = int(parts[0])
                    page = parts[1] if len(parts) > 1 else ""
                except ValueError:
                    pass
            
            # 对每页内容进行分块
            start = 0
            while start < len(page):
                end = start + chunk_size
                
                if end >= len(page):
                    chunk_content = page[start:].strip()
                    if chunk_content:
                        chunks.append(DocumentChunk(
                            content=chunk_content,
                            chunk_index=index,
                            metadata={"page": page_num, "char_start": start},
                        ))
                    break
                
                # 尝试在段落边界分割
                chunk_end = end
                for i in range(end, max(start, end - 100), -1):
                    if i < len(page) and page[i] in "\n\r":
                        chunk_end = i
                        break
                
                chunk_content = page[start:chunk_end].strip()
                if chunk_content:
                    chunks.append(DocumentChunk(
                        content=chunk_content,
                        chunk_index=index,
                        metadata={"page": page_num, "char_start": start},
                    ))
                    index += 1
                
                start = chunk_end - chunk_overlap
        
        logger.debug(f"PDF分块完成: {len(chunks)}个分块")
        return chunks
    
    def process(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> tuple[str, list[DocumentChunk]]:
        """处理PDF文档"""
        text = self.extract_text(file_path)
        chunks = self.split_into_chunks(text, chunk_size, chunk_overlap)
        return text, chunks
