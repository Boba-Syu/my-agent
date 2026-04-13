"""直接查询Chroma数据库，确认数据状态"""
from __future__ import annotations

import chromadb

# 直接连接数据库（不通过任何封装）
client = chromadb.PersistentClient(path="./data/chroma_db")

# 列出所有集合
print("=== 所有集合 ===")
for coll in client.list_collections():
    print(f"  - {coll.name}")

# 检查 rag_vectors 集合
print("\n=== rag_vectors 集合 ===")
try:
    coll = client.get_collection("rag_vectors")
    count = coll.count()
    print(f"  记录数: {count}")

    if count > 0:
        # 读取所有数据
        results = coll.get(limit=count, include=["documents", "metadatas"])
        print(f"  实际返回: {len(results['ids'])} 条")
        for i, (doc_id, content, meta) in enumerate(zip(results['ids'][:5], results['documents'][:5], results['metadatas'][:5])):
            doc_title = meta.get('title', meta.get('document_id', 'N/A'))[:30]
            print(f"    {i+1}. {doc_id[:20]}... | {doc_title}")
    else:
        print("  集合为空！")
except Exception as e:
    print(f"  错误: {e}")

# 检查 agent_vectors 集合
print("\n=== agent_vectors 集合 ===")
try:
    coll = client.get_collection("agent_vectors")
    count = coll.count()
    print(f"  记录数: {count}")
except Exception as e:
    print(f"  错误: {e}")

print("\n=== 完成 ===")
