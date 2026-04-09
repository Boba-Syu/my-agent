import axios from 'axios'
import type {
  KnowledgeBase,
  CreateKnowledgeBaseRequest,
  Document,
  CreateTextDocumentRequest,
  RagQueryRequest,
  RagQueryResponse,
  RagStreamEvent,
  ChunkingStrategy,
} from '@/types/rag'

const API_BASE = '/api/v1/rag'

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== 知识库 API ====================

// 获取所有知识库
export async function getKnowledgeBases(): Promise<KnowledgeBase[]> {
  const response = await api.get('/knowledge-bases')
  return response.data
}

// 获取单个知识库
export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const response = await api.get(`/knowledge-bases/${id}`)
  return response.data
}

// 创建知识库
export async function createKnowledgeBase(data: CreateKnowledgeBaseRequest): Promise<KnowledgeBase> {
  const response = await api.post('/knowledge-bases', data)
  return response.data
}

// 更新知识库
export async function updateKnowledgeBase(
  id: string,
  data: Partial<CreateKnowledgeBaseRequest>
): Promise<KnowledgeBase> {
  const response = await api.put(`/knowledge-bases/${id}`, data)
  return response.data
}

// 删除知识库
export async function deleteKnowledgeBase(id: string): Promise<void> {
  await api.delete(`/knowledge-bases/${id}`)
}

// ==================== 文档 API ====================

// 获取知识库下的所有文档
export async function getDocuments(kbId?: string): Promise<Document[]> {
  const params = kbId ? { kbId: kbId } : {}
  const response = await api.get('/documents', { params })
  return response.data
}

// 创建纯文本文档
export async function createTextDocument(data: CreateTextDocumentRequest): Promise<Document> {
  const response = await api.post('/documents/text', data)
  return response.data
}

// 上传文件文档
export async function uploadDocument(
  kbId: string,
  file: File,
  chunkingStrategy: ChunkingStrategy = 'fixed_size',
  chunkSize: number = 500,
  chunkOverlap: number = 50,
  separator: string = ''
): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('kbId', kbId)
  formData.append('chunking_strategy', chunkingStrategy)
  formData.append('chunk_size', chunkSize.toString())
  formData.append('chunk_overlap', chunkOverlap.toString())
  formData.append('separator', separator)
  
  const response = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

// 删除文档
export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`)
}

// ==================== RAG 查询 API ====================

// 同步查询
export async function queryRag(data: RagQueryRequest): Promise<RagQueryResponse> {
  const response = await api.post('/query', data)
  return response.data
}

// 流式查询（SSE）
export function streamQueryRag(
  data: RagQueryRequest,
  onEvent: (event: RagStreamEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const params = new URLSearchParams({
    query: data.query,
    kb_id: data.kbId,
    ...(data.kbType && { kb_type: data.kbType }),
    ...(data.topK && { top_k: data.topK.toString() }),
  })
  
  const url = `${API_BASE}/query/stream?${params.toString()}`
  const eventSource = new EventSource(url)
  
  eventSource.onmessage = (event) => {
    try {
      const parsedData = JSON.parse(event.data)
      onEvent(parsedData)
      
      // 如果是完成或错误事件，关闭连接
      if (parsedData.type === 'complete' || parsedData.type === 'error') {
        eventSource.close()
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err)
      onError?.(err as Error)
      eventSource.close()
    }
  }
  
  eventSource.onerror = (error) => {
    console.error('SSE error:', error)
    onError?.(new Error('EventSource connection failed'))
    eventSource.close()
  }
  
  // 返回取消函数
  return () => {
    eventSource.close()
  }
}

// ==================== 健康检查 ====================

export async function healthCheck(): Promise<{ status: string }> {
  const response = await api.get('/health')
  return response.data
}
