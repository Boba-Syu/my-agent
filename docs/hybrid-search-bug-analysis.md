# 混合检索问题分析与修复文档

## 问题概述

在审查混合检索（Hybrid Search）实现时，发现**向量检索**和**关键词检索**都存在严重问题，导致检索结果不准确或内容丢失。

---

## 1. 向量检索问题 (ChromaVectorStore)

### 问题位置
`app/infrastructure/persistence/chroma/chroma_vector_store.py`

### 问题描述

#### 1.1 similarity_search 返回错误的ID (第171行)

**问题代码**:
```python
for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
    score = 1.0 - min(distance, 1.0)
    chunks.append((str(metadata.get("chunk_index", 0)), score))  # ❌ 错误
```

**问题分析**:
- 返回的是 `chunk_index`（如 "0", "1"）
- 而不是 Chroma 的实际记录 ID
- 这会导致 `get_chunk_by_id()` 无法正确获取分块

#### 1.2 get_chunk_by_id 查询方式不正确 (第211行)

**问题代码**:
```python
results = store.get(where={"chunk_index": int(chunk_id)})
```

**问题分析**:
- 使用 `chunk_index` 查询，在有多个文档时会返回多个结果
- 无法唯一定位一个分块
- 应该使用 Chroma 返回的实际 ID 进行查询

### 修复方案

1. `similarity_search` 应该返回 Chroma 的实际 `ids` 而不是 `chunk_index`
2. `get_chunk_by_id` 应该直接使用 Chroma ID 查询

---

## 2. 关键词检索问题 (HybridSearchTool)

### 问题位置
`app/infrastructure/tools/rag/hybrid_search_tool.py`

### 问题描述

#### 2.1 关键词检索返回硬编码占位符 (第295行)

**问题代码**:
```python
chunk = DocumentChunk(
    content=f"[Keyword匹配] 文档片段",  # ❌ 硬编码占位符
    chunk_index=int(idx) if idx.isdigit() else 0,
    metadata={"chunk_id": chunk_id, "document_id": doc_id},
)
```

**问题分析**:
- 关键词检索的实际内容完全丢失
- 返回给用户的只是占位符文本
- 无法提供有意义的检索结果

#### 2.2 无法通过关键词检索获取实际内容

**问题分析**:
- `WhooshKeywordIndex.search()` 只返回 `chunk_id` 和分数
- 没有提供获取完整内容的方法
- 需要通过 `chunk_id` 从向量存储查询实际内容

### 修复方案

1. 扩展 `KeywordIndex` 接口，添加通过 `chunk_id` 获取内容的方法
2. 在 `HybridSearchTool` 中，关键词检索后从向量存储获取实际内容
3. 或者修改 `WhooshKeywordIndex` 存储并返回完整内容

---

## 3. RRF融合问题

### 问题位置
`app/infrastructure/tools/rag/hybrid_search_tool.py` 第339、349行

### 问题描述

**问题代码**:
```python
content_key = result.content[:100]  # 使用前100字符作为key
```

**问题分析**:
- 使用内容前100字符作为去重key
- 但关键词检索的 `content` 是硬编码的占位符
- 会导致关键词检索结果无法正确去重

### 修复方案

1. 修复关键词检索，使其返回实际内容
2. 或者使用 `chunk_id` 作为去重key

---

## 4. 修复计划

### 4.1 修复 ChromaVectorStore

**修改文件**: `app/infrastructure/persistence/chroma/chroma_vector_store.py`

**修改内容**:
1. `similarity_search` 方法返回 `(id, score)` 而不是 `(chunk_index, score)`
2. `get_chunk_by_id` 方法使用 Chroma ID 直接查询

### 4.2 扩展 KeywordIndex 接口

**修改文件**: `app/domain/rag/keyword_index.py`

**新增方法**:
```python
@abstractmethod
def get_chunk_content(self, chunk_id: str) -> str | None:
    """根据chunk_id获取分块内容"""
    pass
```

### 4.3 实现 WhooshKeywordIndex 新方法

**修改文件**: `app/infrastructure/persistence/whoosh/whoosh_keyword_index.py`

**修改内容**:
1. 在 `add_document` 时存储完整内容
2. 实现 `get_chunk_content` 方法

### 4.4 修复 HybridSearchTool

**修改文件**: `app/infrastructure/tools/rag/hybrid_search_tool.py`

**修改内容**:
1. `_keyword_search` 方法获取实际分块内容
2. 修改 RRF 融合的去重key（可选：使用 chunk_id）

---

## 5. 预期修复效果

修复后：

1. **向量检索**: 返回正确的 Chroma ID，能准确获取分块内容
2. **关键词检索**: 返回实际的分块内容，不再使用占位符
3. **混合融合**: 基于实际内容进行 RRF 融合，结果更准确
4. **用户体验**: 检索结果包含真实内容，可直接用于回答问题

---

## 6. 测试验证

修复后需要验证：

1. 向量检索能正确返回文档内容
2. 关键词检索能正确返回文档内容
3. 混合检索结果包含真实内容，无占位符
4. 融合去重逻辑正确工作
