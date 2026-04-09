"""
测试文本文档API

直接测试 /documents/text 和 /documents?kbId=xxx 接口

运行方式:
    uv run python tests/test_text_document_api.py
"""

from __future__ import annotations

import asyncio
import uuid
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.application.rag.dto import DocumentUploadRequest, CreateTextDocumentRequest
from app.application.rag.document_service import DocumentService
from app.infrastructure.persistence.chroma.chroma_document_repo import ChromaDocumentRepository
from app.infrastructure.persistence.chroma.chroma_vector_store import ChromaVectorStore
from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex
from app.llm.llm_factory import LLMFactory


async def test_text_document_api():
    """测试文本文档创建和查询"""
    
    print("=" * 70)
    print("测试文本文档API")
    print("=" * 70)
    
    # 初始化组件
    embedding = LLMFactory.create_embedding()
    repo = ChromaDocumentRepository()
    vector_store = ChromaVectorStore(embedding=embedding)
    keyword_index = WhooshKeywordIndex()
    
    print(f"\n1. 组件初始化")
    print(f"   Repository 集合: {repo._client._collection_name}")
    print(f"   VectorStore 集合: {vector_store._collection_name}")
    
    # 创建服务
    service = DocumentService(
        document_repository=repo,
        vector_store=vector_store,
        keyword_index=keyword_index,
    )
    
    # 测试知识库ID
    kb_id = f"test_kb_{uuid.uuid4().hex[:8]}"
    print(f"\n2. 测试知识库ID: {kb_id}")
    
    # 模拟前端请求 - 创建文本文档
    title = "测试文本文档"
    content = "这是一个测试文本文档的内容。\n\n这是第二段内容，用于验证分块功能。"
    
    print(f"\n3. 创建文本文档")
    print(f"   标题: {title}")
    print(f"   内容长度: {len(content)} 字符")
    print(f"   kbId: {kb_id}")
    
    # 创建临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        # 创建文档（不分块）
        request = DocumentUploadRequest(
            file_path=temp_path,
            title=title,
            kb_type="faq",
            kb_id=kb_id,
            chunking_strategy="none",  # 不分块
        )
        
        result = await service.upload_document(request)
        
        print(f"\n4. 文档创建成功")
        print(f"   ID: {result.id}")
        print(f"   标题: {result.title}")
        print(f"   kb_id: {result.kb_id}")
        print(f"   kb_type: {result.kb_type}")
        print(f"   分块数: {result.chunk_count}")
        print(f"   状态: {result.status}")
        
        # 立即查询
        print(f"\n5. 查询文档列表 (kb_id={kb_id})")
        documents = service.list_documents(kb_id=kb_id)
        print(f"   查询结果: {len(documents)} 个文档")
        
        for doc in documents:
            print(f"   - ID: {doc.id}, 标题: {doc.title}, kb_id: {doc.kb_id}")
        
        # 验证
        found = any(d.id == result.id for d in documents)
        if found:
            print(f"\n✅ 测试通过: 创建的文档可以在列表中查询到")
        else:
            print(f"\n❌ 测试失败: 创建的文档 ID={result.id} 不在查询结果中")
            
            # 调试：查询所有文档
            print(f"\n6. 调试：查询所有文档（不带kb_id过滤）")
            all_docs = service.list_documents()
            print(f"   所有文档数: {len(all_docs)}")
            for doc in all_docs:
                print(f"   - ID: {doc.id}, kb_id: {doc.kb_id}")
        
        # 调试：直接查询Chroma
        print(f"\n7. 调试：直接查询Chroma集合")
        chroma_results = repo._client.get_all(limit=10)
        print(f"   Chroma返回记录数: {len(chroma_results.get('ids', []))}")
        for i, metadata in enumerate(chroma_results.get('metadatas', [])[:3]):
            print(f"   记录{i}: document_id={metadata.get('document_id')}, kb_id={metadata.get('kb_id')}")
                
    finally:
        os.unlink(temp_path)
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_text_document_api())
