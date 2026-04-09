"""
测试文档仓库修复
验证 ChromaDocumentRepository 能正确获取文档内容
"""

from __future__ import annotations

import asyncio
import sys
sys.path.insert(0, "c:/Users/19148/PycharmProjects/my-agent")

from app.infrastructure.persistence.chroma.chroma_document_repo import ChromaDocumentRepository


def test_list_documents():
    """测试文档列表查询"""
    print("=" * 60)
    print("测试文档列表查询")
    print("=" * 60)
    
    repo = ChromaDocumentRepository()
    
    # 查询指定知识库的文档
    kb_id = "a3abd1f4-6729-48c4-9e89-7f2cf69d5713"
    documents = repo.list(kb_id=kb_id, limit=10)
    
    print(f"\n查询到 {len(documents)} 个文档:\n")
    
    for i, doc in enumerate(documents, 1):
        print(f"{i}. ID: {doc.id}")
        print(f"   标题: {doc.title}")
        print(f"   来源: {doc.source}")
        print(f"   类型: {doc.doc_type}")
        print(f"   知识库: {doc.kb_type.value}")
        print(f"   内容长度: {len(doc.content)} 字符")
        print(f"   内容预览: {doc.content[:100]}..." if len(doc.content) > 100 else f"   内容: {doc.content}")
        print()
    
    return documents


def test_get_document():
    """测试单个文档获取"""
    print("=" * 60)
    print("测试单个文档获取")
    print("=" * 60)
    
    repo = ChromaDocumentRepository()
    
    # 先列表获取一个文档ID
    kb_id = "a3abd1f4-6729-48c4-9e89-7f2cf69d5713"
    documents = repo.list(kb_id=kb_id, limit=1)
    
    if not documents:
        print("没有找到文档，跳过单个文档获取测试")
        return None
    
    doc_id = documents[0].id
    print(f"\n获取文档 ID: {doc_id}\n")
    
    doc = repo.get(doc_id)
    
    if doc:
        print(f"文档获取成功:")
        print(f"  标题: {doc.title}")
        print(f"  内容长度: {len(doc.content)} 字符")
        print(f"  内容预览: {doc.content[:200]}..." if len(doc.content) > 200 else f"  内容: {doc.content}")
    else:
        print("文档获取失败: 返回 None")
    
    return doc


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("ChromaDocumentRepository 修复验证测试")
    print("=" * 60 + "\n")
    
    try:
        # 测试列表查询
        docs = test_list_documents()
        
        print("\n" + "-" * 60 + "\n")
        
        # 测试单个获取
        doc = test_get_document()
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        if docs:
            print(f"✓ 列表查询成功: 返回 {len(docs)} 个文档")
            # 检查是否有内容
            has_content = any(len(d.content) > 50 for d in docs)  # 内容大于占位符长度
            if has_content:
                print("✓ 文档内容已正确获取")
            else:
                print("⚠ 文档内容可能仍为占位符")
        else:
            print("✗ 列表查询失败: 没有返回文档")
        
        if doc:
            print(f"✓ 单个获取成功: 文档 '{doc.title}'")
            if len(doc.content) > 50:
                print("✓ 文档内容已正确获取")
            else:
                print("⚠ 文档内容可能仍为占位符")
        else:
            print("✗ 单个获取失败")
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
