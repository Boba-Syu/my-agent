# RAG 系统架构设计文档

## 1. 概述

本文档定义了基于DDD架构的企业级RAG（检索增强生成）系统设计方案。

### 1.1 核心特性

- **Agentic RAG**: 智能查询分解和知识库路由
- **混合检索**: 向量检索 + 关键词检索
- **多知识库支持**: FAQ和规章制度两种类型
- **可扩展文档处理**: 支持PDF、Word、TXT等多种格式
- **百炼云服务**: 使用阿里百炼text-embedding-v4和qwen3-vl-rerank

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        接口层 (Interface Layer)                  │
│    POST /api/v1/rag/query         - RAG查询接口                 │
│    POST /api/v1/rag/documents     - 文档上传接口                │
│    GET  /api/v1/rag/documents     - 文档列示接口                │
├─────────────────────────────────────────────────────────────────┤
│                        应用层 (Application Layer)                │
│    RAGService                     - RAG检索流程编排             │
│    DocumentService                - 文档处理管道                │
├─────────────────────────────────────────────────────────────────┤
│                        领域层 (Domain Layer)                     │
│  ┌──────────────┬──────────────┬──────────────┬────────────────┐ │
│  │   Document   │ DocumentChunk│  Query       │ SearchResult   │ │
│  │   聚合根      │ 值对象        │ 值对象        │ 值对象          │ │
│  └──────────────┴──────────────┴──────────────┴────────────────┘ │
│  ┌──────────────┬──────────────┬──────────────┬────────────────┐ │
│  │ Document     │ VectorStore  │ KeywordIndex │ Reranker       │ │
│  │ Repository   │ Interface    │ Interface    │ Interface      │ │
│  └──────────────┴──────────────┴──────────────┴────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      基础设施层 (Infrastructure Layer)           │
│  ┌──────────────┬──────────────┬──────────────┬────────────────┐ │
│  │MilvusVector  │WhooshKeyword │BailianRerank │PDFProcessor    │ │
│  │Store         │Index         │(qwen3-vl)    │WordProcessor   │ │
│  │              │              │              │TextProcessor   │ │
│  └──────────────┴──────────────┴──────────────┴────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 检索流程

```
用户查询
    ↓
[查询分解] → 子问题1, 子问题2, ...
    ↓
[知识库路由] → FAQ / 规章制度
    ↓
[并行混合检索]
    ├── 向量检索 (Milvus) ──┐
    └── 关键词检索 (Whoosh) ─┘
    ↓
[RAG-Fusion] → 结果融合与去重
    ↓
[重排序] (百炼Reranker) → Top 10
    ↓
[答案生成] → 最终回答
```

## 3. 领域层 (Domain Layer)

### 3.1 核心领域模型

#### Document 聚合根

```python
class Document(AggregateRoot):
    - id: str
    - title: str
    - source: str
    - doc_type: str          # pdf/word/txt/md
    - kb_type: KnowledgeBaseType
    - content: str
    - chunks: list[DocumentChunk]
    - status: DocumentStatus
```

#### KnowledgeBaseType 枚举

```python
class KnowledgeBaseType(Enum):
    FAQ = "faq"              # 面向客户的常见问题
    REGULATION = "regulation" # 面向员工的企业规章制度
```

### 3.2 领域接口

| 接口 | 职责 | 实现 |
|------|------|------|
| DocumentRepository | 文档持久化 | MilvusDocumentRepository |
| VectorStore | 向量存储 | MilvusVectorStore |
| KeywordIndex | 关键词索引 | WhooshKeywordIndex |
| Reranker | 结果重排序 | BailianReranker |
| DocumentProcessor | 文档解析 | PDF/Word/Text处理器 |

## 4. 应用层 (Application Layer)

### 4.1 RAGService 检索流程

```python
class RAGService:
    async def query(request: RAGQueryRequest) -> RAGQueryResponse:
        # 1. 查询分解
        query = await self._decompose_query(request)
        
        # 2. 并行混合检索
        results = await self._parallel_search(query)
        
        # 3. RAG-Fusion
        fused = self._rag_fusion(results)
        
        # 4. 重排序
        ranked = await self._rerank(fused)
        
        # 5. 答案生成
        answer = await self._generate_answer(ranked)
        
        return RAGQueryResponse(answer, sources)
```

### 4.2 DocumentService 处理流程

```python
class DocumentService:
    async def upload_document(request):
        # 1. 解析文档
        processor = factory.get_processor(file_path)
        content, chunks = processor.process(file_path)
        
        # 2. 创建Document聚合根
        document = Document(...)
        
        # 3. 生成Embedding
        embeddings = await embedding.embed_documents(chunks)
        
        # 4. 存储到向量库
        vector_store.add_chunks(document_id, chunks, embeddings)
        
        # 5. 存储到关键词索引
        keyword_index.add_document(document_id, chunks)
        
        # 6. 保存文档元数据
        repository.save(document)
```

## 5. 基础设施层 (Infrastructure Layer)

### 5.1 向量存储 - MilvusVectorStore

```python
class MilvusVectorStore(VectorStore):
    def add_chunks(self, document_id, chunks, embeddings, kb_type):
        # 使用Milvus Lite本地文件模式
        store.add_texts(texts, metadatas)
    
    def similarity_search(self, query_embedding, kb_types, top_k):
        # 向量相似度检索
        return store.similarity_search_with_score(...)
```

**配置**:
```toml
[database.milvus]
uri = "./data/milvus_rag.db"
collection_name = "rag_vectors"
```

### 5.2 关键词索引 - WhooshKeywordIndex

```python
class WhooshKeywordIndex(KeywordIndex):
    def search(self, query, kb_types, top_k):
        # 使用BM25算法
        return searcher.search(q, limit=top_k)
```

### 5.3 百炼Reranker

```python
class BailianReranker(Reranker):
    def rerank(self, query, results, top_k):
        # 使用百炼qwen3-vl-rerank或LLM打分
        return ranked_results
```

### 5.4 文档处理器

| 处理器 | 支持格式 | 依赖库 |
|--------|----------|--------|
| PDFProcessor | .pdf | pdfplumber / PyPDF2 |
| WordProcessor | .docx | python-docx |
| TextProcessor | .txt/.md/.csv | 内置 |

## 6. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Embedding | 百炼 text-embedding-v4 | 1024维，OpenAI兼容API |
| Rerank | 百炼 qwen3-vl-rerank | LLM相关性打分 |
| 向量库 | Milvus Lite | 本地文件模式 |
| 关键词索引 | Whoosh | Python纯实现 |
| LLM | 百炼 deepseek-v3 | OpenAI兼容API |

## 7. API 接口

### 7.1 RAG 查询

```http
POST /api/v1/rag/query
Content-Type: application/json

{
    "query": "如何申请退款？",
    "kb_types": ["faq"],
    "top_k": 10
}

Response:
{
    "answer": "您可以通过以下步骤申请退款...",
    "sources": [
        {
            "document_id": "doc-001",
            "document_title": "退款政策",
            "content": "退款流程说明...",
            "score": 0.95
        }
    ]
}
```

### 7.2 文档上传

```http
POST /api/v1/rag/documents/upload?kb_type=faq
Content-Type: multipart/form-data

file: (binary)

Response:
{
    "id": "doc-001",
    "title": "产品手册.pdf",
    "status": "processed",
    "chunk_count": 15
}
```

## 8. 目录结构

```
app/
├── domain/rag/                      # RAG领域层
│   ├── document.py                  # 文档聚合根
│   ├── document_chunk.py            # 文档分块值对象
│   ├── knowledge_base_type.py       # 知识库类型枚举
│   ├── query.py                     # 查询值对象
│   ├── search_result.py             # 检索结果值对象
│   ├── document_repository.py       # 文档仓库接口
│   ├── vector_store.py              # 向量存储接口
│   ├── keyword_index.py             # 关键词索引接口
│   ├── reranker.py                  # 重排序接口
│   └── document_processor.py        # 文档处理器接口
│
├── application/rag/                 # RAG应用层
│   ├── rag_service.py               # RAG检索服务
│   ├── document_service.py          # 文档处理服务
│   └── dto.py                       # DTO定义
│
├── infrastructure/
│   ├── persistence/
│   │   ├── milvus/                  # Milvus实现
│   │   │   ├── milvus_vector_store.py
│   │   │   └── milvus_document_repo.py
│   │   └── whoosh/                  # Whoosh实现
│   │       └── whoosh_keyword_index.py
│   └── rag/
│       ├── processors/              # 文档处理器
│       │   ├── text_processor.py
│       │   ├── pdf_processor.py
│       │   ├── word_processor.py
│       │   └── processor_factory.py
│       └── reranker/
│           └── bailian_reranker.py  # 百炼Reranker
│
├── interfaces/http/routes/
│   └── rag_routes.py                # RAG API路由
│
└── prompts/rag/
    └── __init__.py                  # RAG提示词
```

## 9. 配置说明

### 9.1 application.toml

```toml
[llm]
api_key = "your-bailian-api-key"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
default_model = "deepseek-v3"

[embedding]
api_key = "your-bailian-api-key"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "text-embedding-v4"
dimensions = 1024

[database.milvus]
uri = "./data/milvus_rag.db"
collection_name = "rag_vectors"
```

## 10. 扩展指南

### 10.1 添加新的文档处理器

```python
class ExcelProcessor(DocumentProcessor):
    @property
    def supported_types(self):
        return ["xlsx", "xls"]
    
    def process(self, file_path, chunk_size, chunk_overlap):
        # 实现Excel解析逻辑
        pass

# 注册到工厂
factory.register_processor(ExcelProcessor)
```

### 10.2 添加新的知识库类型

```python
class KnowledgeBaseType(Enum):
    FAQ = "faq"
    REGULATION = "regulation"
    PRODUCT = "product"  # 新产品知识库
```

## 11. 性能优化

- **批量Embedding**: 文档分块后批量生成向量
- **并行检索**: 多个子查询并行执行
- **缓存机制**: 热门查询结果缓存
- **索引优化**: Whoosh定期合并段
