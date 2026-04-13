"""最小化测试 - 直接查询Chroma"""
import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
coll = client.get_collection("rag_vectors")
print(f"count() = {coll.count()}")

results = coll.get(limit=10000, include=["documents", "metadatas"])
print(f"get() 返回 = {len(results['ids'])} 条")
