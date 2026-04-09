"""
文档仓库单元测试

测试 ChromaDocumentRepository 的查询功能。
"""

from __future__ import annotations

import pytest
import uuid
from datetime import datetime

from app.domain.rag.document import Document
from app.domain.rag.document_chunk import DocumentChunk
from app.domain.rag.knowledge_base_type import KnowledgeBaseType
from app.infrastructure.persistence.chroma.chroma_document_repo import ChromaDocumentRepository
from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
from app.llm.llm_factory import LLMFactory


@pytest.fixture
def embedding():
    """创建 embedding 模型"""
    return LLMFactory.create_embedding()


@pytest.fixture
def document_repo(embedding):
    """创建文档仓库实例"""
    repo = ChromaDocumentRepository.for_test(embedding)
    return repo


@pytest.fixture
def vector_store(embedding):
    """创建向量存储实例"""
    store = ChromaVectorStore(embedding=embedding)
    return store


class TestChromaDocumentRepository:
    """ChromaDocumentRepository 测试类"""
    
    def test_list_empty(self, document_repo):
        """测试空列表查询"""
        documents = document_repo.list()
        assert isinstance(documents, list)
        assert len(documents) == 0
    
    def test_save_and_get(self, document_repo):
        """测试保存和获取文档"""
        # 创建测试文档
        doc = Document(
            id=str(uuid.uuid4()),
            title="测试文档",
            source="test.txt",
            doc_type="txt",
            kb_type=KnowledgeBaseType.FAQ,
            content="这是一个测试文档的内容",
            kb_id="test_kb_001",
        )
        
        # 保存
        saved = document_repo.save(doc)
        assert saved.id == doc.id
        
        # 获取
        retrieved = document_repo.get(doc.id)
        assert retrieved is not None
        assert retrieved.id == doc.id
        assert retrieved.title == doc.title
    
    def test_list_with_kb_id_filter(self, document_repo, vector_store, embedding):
        """测试按 kb_id 过滤查询"""
        import asyncio
        
        kb_id = f"test_kb_{uuid.uuid4().hex[:8]}"
        doc_id = str(uuid.uuid4())
        
        # 创建并存储文档
        content = "测试文档内容，用于验证 kb_id 过滤功能"
        chunks = [
            DocumentChunk(content=content, chunk_index=0, metadata={}),
        ]
        
        # 生成嵌入向量
        embeddings = asyncio.get_event_loop().run_until_complete(
            embedding.aembed_documents([content])
        )
        
        # 存储到向量库
        vector_store.add_chunks(
            document_id=doc_id,
            title="测试文档",
            source="test.txt",
            chunks=chunks,
            embeddings=embeddings,
            kb_type=KnowledgeBaseType.FAQ,
            kb_id=kb_id,
        )
        
        # 查询应该能查到
        documents = document_repo.list(kb_id=kb_id)
        assert len(documents) >= 1
        
        # 验证文档信息正确
        found = False
        for doc in documents:
            if doc.id == doc_id:
                found = True
                assert doc.title == "测试文档"
                assert doc.kb_id == kb_id
                break
        
        assert found, f"应该能找到 doc_id={doc_id} 的文档"
        
        # 查询不同的 kb_id 应该查不到
        other_documents = document_repo.list(kb_id="non_existent_kb")
        for doc in other_documents:
            assert doc.id != doc_id
    
    def test_list_returns_unique_documents(self, document_repo, vector_store, embedding):
        """测试列表返回唯一文档（不重复）"""
        import asyncio
        
        kb_id = f"test_kb_{uuid.uuid4().hex[:8]}"
        doc_id = str(uuid.uuid4())
        
        # 创建多个分块的文档
        chunks = [
            DocumentChunk(content="第一块内容", chunk_index=0, metadata={}),
            DocumentChunk(content="第二块内容", chunk_index=1, metadata={}),
            DocumentChunk(content="第三块内容", chunk_index=2, metadata={}),
        ]
        
        # 生成嵌入向量
        texts = [c.content for c in chunks]
        embeddings = asyncio.get_event_loop().run_until_complete(
            embedding.aembed_documents(texts)
        )
        
        # 存储到向量库
        vector_store.add_chunks(
            document_id=doc_id,
            title="多分块测试文档",
            source="test.txt",
            chunks=chunks,
            embeddings=embeddings,
            kb_type=KnowledgeBaseType.FAQ,
            kb_id=kb_id,
        )
        
        # 查询
        documents = document_repo.list(kb_id=kb_id)
        
        # 检查 doc_id 只出现一次
        doc_ids = [d.id for d in documents]
        assert doc_ids.count(doc_id) == 1, f"文档 {doc_id} 应该只出现一次，但出现了 {doc_ids.count(doc_id)} 次"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
