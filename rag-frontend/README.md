# RAG 知识库前端

基于 Vue 3 + TypeScript + Element Plus 的 RAG 知识库管理系统前端。

## 功能特性

- **知识库管理**：创建、选择、删除知识库
- **文档管理**：支持 Markdown 文件上传和纯文本创建
- **RAG 问答**：基于知识库的语义检索问答
- **流式输出**：使用 SSE 实现流式回答展示
- **流程可视化**：展示完整的 RAG 处理流程（查询分解、向量检索、关键词检索、重排序、答案生成）

## 技术栈

- Vue 3.4
- TypeScript 5
- Element Plus
- Pinia（状态管理）
- Vue Router
- Axios
- Vite

## 快速开始

### 安装依赖

```bash
cd rag-frontend
npm install
```

### 开发模式

```bash
npm run dev
```

默认端口为 5174，可在 `vite.config.ts` 中修改。

### 生产构建

```bash
npm run build
```

## 项目结构

```
rag-frontend/
├── src/
│   ├── api/              # API 封装
│   │   └── rag.ts        # RAG 相关 API
│   ├── components/       # 组件
│   │   ├── KnowledgeBaseSelector.vue  # 知识库选择器
│   │   ├── DocumentManager.vue        # 文档管理
│   │   ├── RagChat.vue                # RAG 问答
│   │   └── RagFlowViewer.vue          # 流程可视化
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia Store
│   ├── types/            # TypeScript 类型定义
│   ├── views/            # 页面视图
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口文件
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## API 接口说明

前端期望后端提供以下 API 接口：

### 知识库接口

- `GET /api/v1/rag/knowledge-bases` - 获取知识库列表
- `POST /api/v1/rag/knowledge-bases` - 创建知识库
- `DELETE /api/v1/rag/knowledge-bases/{id}` - 删除知识库

### 文档接口

- `GET /api/v1/rag/documents?kb_id={id}` - 获取文档列表
- `POST /api/v1/rag/documents/text` - 创建文本文档
- `POST /api/v1/rag/documents/upload` - 上传文件
- `DELETE /api/v1/rag/documents/{id}` - 删除文档

### RAG 查询接口

- `GET /api/v1/rag/query/stream?query=xxx&kb_id=xxx` - SSE 流式查询

## 代理配置

开发服务器已配置代理，将 `/api` 请求转发到 `http://localhost:8000`：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## License

MIT
