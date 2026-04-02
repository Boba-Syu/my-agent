"""
RAG文档处理器单元测试

测试PDF、Word、TXT等文档处理器
"""

from __future__ import annotations

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.domain.rag.document_processor import DocumentProcessor
from app.infrastructure.rag.processors.text_processor import TextProcessor
from app.infrastructure.rag.processors.processor_factory import ProcessorFactory


class TestTextProcessor:
    """文本处理器测试"""
    
    @pytest.fixture
    def processor(self) -> TextProcessor:
        """文本处理器实例"""
        return TextProcessor()
    
    def test_supported_types(self, processor: TextProcessor):
        """支持的文件类型"""
        types = processor.supported_types
        
        assert "txt" in types
        assert "md" in types
        assert "markdown" in types
        assert "csv" in types
        assert "py" in types
    
    def test_can_process(self, processor: TextProcessor):
        """检查是否能处理"""
        assert processor.can_process("/path/to/file.txt")
        assert processor.can_process("/path/to/file.md")
        assert processor.can_process("/path/to/file.py")
        assert processor.can_process("/path/to/file.TXT")  # 大小写不敏感
        assert not processor.can_process("/path/to/file.pdf")
        assert not processor.can_process("/path/to/file")
    
    def test_split_into_chunks(self, processor: TextProcessor):
        """文本分块"""
        content = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
        
        chunks = processor.split_into_chunks(content, chunk_size=20, chunk_overlap=5)
        
        assert len(chunks) > 0
        # 验证每个分块都有内容
        for chunk in chunks:
            assert chunk.content.strip()
            assert chunk.chunk_index >= 0
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
    
    def test_split_into_chunks_empty(self, processor: TextProcessor):
        """空内容分块"""
        chunks = processor.split_into_chunks("", chunk_size=100)
        
        assert chunks == []
    
    def test_split_into_chunks_small_content(self, processor: TextProcessor):
        """小内容分块"""
        content = "短内容"
        
        chunks = processor.split_into_chunks(content, chunk_size=100)
        
        assert len(chunks) == 1
        assert chunks[0].content == "短内容"
    
    def test_extract_text_file_not_found(self, processor: TextProcessor):
        """文件不存在应抛出异常"""
        with pytest.raises(ValueError, match="无法读取文件"):
            processor.extract_text("/nonexistent/file.txt")
    
    def test_process_integration(self, processor: TextProcessor):
        """处理流程集成测试"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("第一行内容\n")
            f.write("第二行内容\n")
            f.write("第三行内容\n")
            temp_path = f.name
        
        try:
            text, chunks = processor.process(temp_path, chunk_size=50, chunk_overlap=10)
            
            assert "第一行内容" in text
            assert "第二行内容" in text
            assert "第三行内容" in text
            assert len(chunks) > 0
        finally:
            os.unlink(temp_path)


class TestProcessorFactory:
    """处理器工厂测试"""
    
    @pytest.fixture
    def factory(self) -> ProcessorFactory:
        """处理器工厂实例"""
        return ProcessorFactory()
    
    def test_get_processor_txt(self, factory: ProcessorFactory):
        """获取TXT处理器"""
        processor = factory.get_processor("test.txt")
        
        assert processor is not None
        assert processor.can_process("test.txt")
    
    def test_get_processor_md(self, factory: ProcessorFactory):
        """获取MD处理器"""
        processor = factory.get_processor("test.md")
        
        assert processor is not None
        assert processor.can_process("test.md")
    
    def test_get_processor_unsupported_raises(self, factory: ProcessorFactory):
        """获取不支持的处理器应抛出异常"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            factory.get_processor("test.unknown")
    
    def test_register_processor(self, factory: ProcessorFactory):
        """注册新处理器类"""
        # 创建一个测试用的处理器类
        class TestProcessor(DocumentProcessor):
            @property
            def supported_types(self):
                return ["xyztest"]
            
            def can_process(self, file_path: str) -> bool:
                return file_path.endswith(".xyztest")
            
            def extract_text(self, file_path: str) -> str:
                return "test"
            
            def split_into_chunks(self, content, chunk_size=500, chunk_overlap=50):
                return []
            
            def process(self, file_path, chunk_size=500, chunk_overlap=50):
                return "", []
        
        factory.register_processor(TestProcessor)
        
        # 验证处理器被注册
        result = factory.get_processor("test.xyztest")
        assert isinstance(result, TestProcessor)


class TestDocumentProcessorInterface:
    """文档处理器接口测试"""
    
    def test_abstract_methods(self):
        """验证抽象方法"""
        # DocumentProcessor是抽象类，不能直接实例化
        with pytest.raises(TypeError):
            DocumentProcessor()
    
    def test_concrete_processor_implements_interface(self):
        """具体处理器实现接口"""
        processor = TextProcessor()
        
        # 验证实现了所有抽象方法
        assert hasattr(processor, 'supported_types')
        assert hasattr(processor, 'can_process')
        assert hasattr(processor, 'extract_text')
        assert hasattr(processor, 'split_into_chunks')
        assert hasattr(processor, 'process')


class TestDocumentChunkCreation:
    """文档分块创建集成测试"""
    
    def test_chunk_metadata_values(self):
        """分块元数据值正确性"""
        metadata = {"page": 1, "paragraph": 2, "section": "intro"}
        
        chunk = DocumentChunk(
            content="测试内容",
            chunk_index=0,
            metadata=metadata
        )
        
        # 验证元数据正确保存
        assert chunk.metadata["page"] == 1
        assert chunk.metadata["paragraph"] == 2
        assert chunk.metadata["section"] == "intro"


# 标记需要外部依赖的测试
pytestmark = [
    pytest.mark.unit,
]
