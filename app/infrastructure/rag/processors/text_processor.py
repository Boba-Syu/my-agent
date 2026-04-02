"""
文本处理器

处理纯文本文件的分块。
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class TextProcessor(DocumentProcessor):
    """
    文本处理器
    
    处理纯文本文件（.txt, .md, .csv等）的解析和分块。
    """
    
    @property
    def supported_types(self) -> list[str]:
        """支持的文件类型"""
        return ["txt", "md", "markdown", "csv", "json", "py", "js", "ts", "java"]
    
    def can_process(self, file_path: str) -> bool:
        """检查是否能处理"""
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        return ext in self.supported_types
    
    def extract_text(self, file_path: str) -> str:
        """
        提取文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            文本内容
        """
        try:
            # 尝试多种编码
            encodings = ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]
            
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            # 如果都失败，使用latin-1（不会报错但可能有乱码）
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"读取文本文件失败: {file_path}, 错误: {e}")
            raise ValueError(f"无法读取文件: {file_path}")
    
    def split_into_chunks(
        self,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[DocumentChunk]:
        """
        将文本分块
        
        使用简单的字符滑动窗口分块，优先在段落边界处分割。
        
        Args:
            content: 文本内容
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
            
        Returns:
            分块列表
        """
        if not content:
            return []
        
        chunks = []
        index = 0
        start = 0
        
        while start < len(content):
            # 确定分块结束位置
            end = start + chunk_size
            
            if end >= len(content):
                # 剩余内容作为一个分块
                chunk_content = content[start:].strip()
                if chunk_content:
                    chunks.append(DocumentChunk(
                        content=chunk_content,
                        chunk_index=index,
                        metadata={"char_start": start, "char_end": len(content)},
                    ))
                break
            
            # 尝试在段落边界分割
            chunk_end = end
            for i in range(end, max(start, end - 100), -1):
                if i < len(content) and content[i] in "\n\r":
                    chunk_end = i
                    break
            
            chunk_content = content[start:chunk_end].strip()
            if chunk_content:
                chunks.append(DocumentChunk(
                    content=chunk_content,
                    chunk_index=index,
                    metadata={"char_start": start, "char_end": chunk_end},
                ))
                index += 1
            
            # 下一个分块的起始位置（考虑重叠）
            start = chunk_end - chunk_overlap
        
        logger.debug(f"文本分块完成: {len(chunks)}个分块")
        return chunks
    
    def process(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> tuple[str, list[DocumentChunk]]:
        """
        处理文档
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
            
        Returns:
            (原始文本, 分块列表)
        """
        text = self.extract_text(file_path)
        chunks = self.split_into_chunks(text, chunk_size, chunk_overlap)
        return text, chunks
