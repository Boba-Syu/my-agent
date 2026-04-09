// 知识库类型
export interface KnowledgeBase {
  id: string
  name: string
  description: string
  kbType: 'faq' | 'regulation' | string
  documentCount: number
  createdAt: string
  updatedAt: string
}

// 创建知识库请求
export interface CreateKnowledgeBaseRequest {
  name: string
  description: string
  kbType: 'faq' | 'regulation' | string
}

// 文档类型
export interface Document {
  id: string
  kbId: string
  title: string
  content: string
  docType: 'markdown' | 'text'
  chunkCount: number
  createdAt: string
  updatedAt: string
}

// 分块策略类型
export type ChunkingStrategy = 'none' | 'fixed_size' | 'separator' | 'paragraph'

// 创建文本文档请求
export interface CreateTextDocumentRequest {
  kbId: string
  title: string
  content: string
  chunkingStrategy?: ChunkingStrategy
  chunkSize?: number
  chunkOverlap?: number
  separator?: string
}

// 上传文档请求
export interface UploadDocumentRequest {
  kbId: string
  file: File
}

// RAG 查询请求
export interface RagQueryRequest {
  query: string
  kbId: string
  kbType?: string
  topK?: number
  stream?: boolean
}

// RAG 查询响应
export interface RagQueryResponse {
  answer: string
  sources: RetrievalSource[]
  process: RagProcess
}

// 检索来源
export interface RetrievalSource {
  documentId: string
  documentTitle: string
  chunkIndex: number
  content: string
  score: number
}

// RAG 处理流程
export interface RagProcess {
  queryDecomposition: QueryDecompositionStep
  vectorRetrieval: VectorRetrievalStep
  keywordRetrieval: KeywordRetrievalStep
  reranking: RerankingStep
  answerGeneration: AnswerGenerationStep
}

// 查询分解步骤
export interface QueryDecompositionStep {
  status: 'pending' | 'running' | 'completed' | 'failed'
  originalQuery: string
  subQueries: string[]
  startTime?: string
  endTime?: string
}

// 向量检索步骤
export interface VectorRetrievalStep {
  status: 'pending' | 'running' | 'completed' | 'failed'
  totalChunks: number
  retrievedChunks: RetrievedChunk[]
  startTime?: string
  endTime?: string
}

// 关键词检索步骤
export interface KeywordRetrievalStep {
  status: 'pending' | 'running' | 'completed' | 'failed'
  keywords: string[]
  matchedChunks: RetrievedChunk[]
  startTime?: string
  endTime?: string
}

// 重排序步骤
export interface RerankingStep {
  status: 'pending' | 'running' | 'completed' | 'failed'
  inputChunks: number
  outputChunks: number
  rankedChunks: RankedChunk[]
  startTime?: string
  endTime?: string
}

// 答案生成步骤
export interface AnswerGenerationStep {
  status: 'pending' | 'running' | 'completed' | 'failed'
  usedChunks: number
  tokensGenerated: number
  startTime?: string
  endTime?: string
}

// 检索到的块
export interface RetrievedChunk {
  chunkId: string
  documentId: string
  documentTitle: string
  content: string
  score: number
}

// 重排序后的块
export interface RankedChunk extends RetrievedChunk {
  originalRank: number
  newRank: number
}

// SSE 事件类型
export interface RagStreamEvent {
  type: 'process' | 'chunk' | 'sources' | 'complete' | 'error'
  data: RagProcess | string | RetrievalSource[] | RagQueryResponse | { message: string }
}

// 流程步骤状态（用于UI展示）
export interface ProcessStepStatus {
  key: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  icon: string
  description?: string
  details?: Record<string, any>
}
