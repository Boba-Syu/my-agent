import axios from 'axios'
import type {
  ChatRequest,
  ChatResponse,
  TransactionRecord,
  StatsResponse,
  CategoriesResponse,
  RecordsQuery,
  CreateRecordRequest,
  UpdateRecordRequest,
  OperationResponse,
} from '@/types'

const http = axios.create({
  baseURL: '/api/v1/accounting',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

/** 非流式对话 */
export function chatWithAgent(req: ChatRequest): Promise<ChatResponse> {
  return http.post<ChatResponse>('/chat', req).then(r => r.data)
}

/**
 * 流式对话（SSE）
 * onChunk 每次收到数据片段时回调
 * onDone  流结束时回调
 */
export function streamChat(
  req: ChatRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): () => void {
  const ctrl = new AbortController()

  fetch('/api/v1/accounting/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: ctrl.signal,
  })
    .then(async res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        console.log('[streamChat] 收到原始数据:', repr(chunk))
        buffer += chunk
        console.log('[streamChat] 缓冲区:', repr(buffer))

        // 按 SSE 格式分割：每个数据块以空行分隔
        const parts = buffer.split('\n\n')
        // 最后一个可能不完整，留到下次
        buffer = parts.pop() ?? ''
        console.log('[streamChat] 分割后 parts:', parts.length, '缓冲区剩余:', repr(buffer))

        for (const part of parts) {
          if (!part.trim()) continue
          console.log('[streamChat] 处理 part:', repr(part))
          const lines = part.split('\n')
          let currentData = ''

          for (const line of lines) {
            const trimmed = line.trim()
            if (trimmed.startsWith('data:')) {
              // 累积多行 data: (去掉 data: 前缀后直接累积，保留换行符)
              const dataContent = trimmed.slice(5).trim()
              if (currentData) {
                currentData += '\n' + dataContent  // 多行之间用换行符连接
              } else {
                currentData = dataContent
              }
            }
          }

          console.log('[streamChat] 解析出完整 data:', repr(currentData))
          if (currentData === '[DONE]') {
            console.log('[streamChat] 收到 [DONE]')
            onDone()
            return
          }
          if (currentData.startsWith('[ERROR]')) {
            onError(currentData.slice(7).trim())
            return
          }
          if (currentData) {
            console.log('[streamChat] 调用 onChunk:', repr(currentData))
            onChunk(currentData)
          }
        }
      }
      console.log('[streamChat] 流结束')
      onDone()
    })
    .catch(err => {
      console.error('[streamChat] 错误:', err)
      if (err.name !== 'AbortError') onError(String(err))
    })

  // 简单的 repr 函数用于调试
  function repr(s: string): string {
    return JSON.stringify(s)
  }

  // 返回取消函数
  return () => ctrl.abort()
}

/** 查询记账记录 */
export function getRecords(query: RecordsQuery = {}): Promise<TransactionRecord[]> {
  return http.get<TransactionRecord[]>('/records', { params: query }).then(r => r.data)
}

/** 收支统计 */
export function getStats(startDate?: string, endDate?: string): Promise<StatsResponse> {
  const params: Record<string, string> = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  return http
    .get<StatsResponse>('/stats', { params })
    .then(r => r.data)
}

/** 获取分类列表 */
export function getCategories(): Promise<CategoriesResponse> {
  return http.get<CategoriesResponse>('/categories').then(r => r.data)
}

/** 创建记账记录 */
export function createRecord(req: CreateRecordRequest): Promise<OperationResponse> {
  return http.post<OperationResponse>('/records', req).then(r => r.data)
}

/** 更新记账记录 */
export function updateRecord(id: number, req: UpdateRecordRequest): Promise<OperationResponse> {
  return http.put<OperationResponse>(`/records/${id}`, req).then(r => r.data)
}

/** 删除记账记录 */
export function deleteRecord(id: number): Promise<OperationResponse> {
  return http.delete<OperationResponse>(`/records/${id}`).then(r => r.data)
}
