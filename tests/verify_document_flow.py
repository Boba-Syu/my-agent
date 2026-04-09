"""
验证文档创建和查询流程

运行方式:
    uv run python tests/verify_document_flow.py
"""

from __future__ import annotations

import asyncio
import uuid
import tempfile
import os

from app.application.rag.dto import DocumentUploadRequest
from app.application.rag.document_service import DocumentService
from app.infrastructure.persistence.chroma.chroma_document_repo import ChromaDocumentRepository
from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex
from app.llm.llm_factory import LLMFactory


async def verify_document_flow():
    """验证完整的文档创建和查询流程"""
    
    print("=" * 60)
    print("开始验证文档创建和查询流程")
    print("=" * 60)
    
    # 初始化组件
    embedding = LLMFactory.create_embedding()
    repo = ChromaDocumentRepository()
    vector_store = ChromaVectorStore(embedding=embedding)
    keyword_index = WhooshKeywordIndex()
    
    print(f"\n1. 组件初始化完成")
    print(f"   - Repository 集合: rag_vectors")
    print(f"   - VectorStore 集合: rag_vectors")
    
    # 创建服务
    service = DocumentService(
        document_repository=repo,
        vector_store=vector_store,
        keyword_index=keyword_index,
    )
    
    # 生成测试知识库ID
    kb_id = f"test_kb_{uuid.uuid4().hex[:8]}"
    print(f"\n2. 测试知识库ID: {kb_id}")
    
    # 创建临时文件
    content = "这是一个测试文档的内容，用于验证文档创建和查询功能。\n\n这是第二段内容。"
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    print(f"\n3. 创建临时文件: {temp_path}")
    print(f"   内容长度: {len(content)} 字符")
    
    try:
        # 创建文档请求 - 不分块
        request = DocumentUploadRequest(
            file_path=temp_path,
            title="测试文档",
            kb_type="faq",
            kb_id=kb_id,
            chunking_strategy="none",
        )
        
        print(f"\n4. 创建文档...")
        result = await service.upload_document(request)
        print(f"   ✓ 文档创建成功")
        print(f"   - ID: {result.id}")
        print(f"   - 标题: {result.title}")
        print(f"   - 分块数: {result.chunk_count}")
        print(f"   - kb_id: {result.kb_id}")
        
        # 查询文档列表
        print(f"\n5. 查询文档列表 (kb_id={kb_id})...")
        documents = service.list_documents(kb_id=kb_id)
        print(f"   ✓ 查询完成，找到 {len(documents)} 个文档")
        
        for doc in documents:
            print(f"   - {doc.id}: {doc.title} (kb_id={doc.kb_id})")
        
        # 验证
        if len(documents) > 0:
            found = any(d.id == result.id for d in documents)
            if found:
                print(f"\n✅ 验证成功: 创建的文档可以在列表中查询到")
            else:
                print(f"\n❌ 验证失败: 创建的文档 ID={result.id} 不在查询结果中")
                print(f"   查询返回的文档IDs: {[d.id for d in documents]}")
        else:
            print(f"\n❌ 验证失败: 查询结果为空")
            
        # 查询所有文档（不带过滤）
        print(f"\n6. 查询所有文档（不带过滤）...")
        all_docs = service.list_documents()
        print(f"   找到 {len(all_docs)} 个文档")
        
    finally:
        # 清理
        os.unlink(temp_path)
        print(f"\n7. 清理临时文件")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_document_flow())
