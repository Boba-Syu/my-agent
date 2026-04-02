"""
文档处理器工厂

根据文件类型创建对应的文档处理器。
"""

from __future__ import annotations

import logging
from typing import Type

from app.domain.rag.document_processor import DocumentProcessor
from app.infrastructure.rag.processors.text_processor import TextProcessor
from app.infrastructure.rag.processors.pdf_processor import PDFProcessor
from app.infrastructure.rag.processors.word_processor import WordProcessor

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """
    文档处理器工厂
    
    根据文件类型自动选择并创建对应的文档处理器。
    
    Example:
        factory = ProcessorFactory()
        processor = factory.get_processor("document.pdf")
        text, chunks = processor.process("document.pdf")
    """
    
    # 默认处理器
    _processors: list[Type[DocumentProcessor]] = [
        PDFProcessor,
        WordProcessor,
        TextProcessor,  # 作为fallback
    ]
    
    def __init__(self):
        """初始化工厂"""
        self._processor_instances: dict[str, DocumentProcessor] = {}
    
    def get_processor(self, file_path: str) -> DocumentProcessor:
        """
        获取文件对应的处理器
        
        Args:
            file_path: 文件路径
            
        Returns:
            对应的文档处理器
            
        Raises:
            ValueError: 找不到合适的处理器
        """
        # 检查缓存
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        if ext in self._processor_instances:
            return self._processor_instances[ext]
        
        # 查找合适的处理器
        for processor_class in self._processors:
            processor = processor_class()
            if processor.can_process(file_path):
                self._processor_instances[ext] = processor
                logger.debug(f"选择处理器: {processor_class.__name__} for {file_path}")
                return processor
        
        raise ValueError(f"不支持的文件类型: {file_path}")
    
    def register_processor(self, processor_class: Type[DocumentProcessor]) -> None:
        """
        注册自定义处理器
        
        Args:
            processor_class: 处理器类
        """
        self._processors.insert(0, processor_class)  # 插入到最前面
        logger.info(f"注册文档处理器: {processor_class.__name__}")
    
    def get_supported_types(self) -> list[str]:
        """
        获取支持的文件类型
        
        Returns:
            文件扩展名列表
        """
        types = set()
        for processor_class in self._processors:
            processor = processor_class()
            types.update(processor.supported_types)
        return sorted(list(types))
