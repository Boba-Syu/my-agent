import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  KnowledgeBase,
  Document,
  RagProcess,
  RagStreamEvent,
  ProcessStepStatus,
  ChunkingStrategy,
} from '@/types/rag'
import * as ragApi from '@/api/rag'

export const useRagStore = defineStore('rag', () => {
  // ==================== State ====================
  
  // 知识库列表
  const knowledgeBases = ref<KnowledgeBase[]>([])
  // 当前选中的知识库
  const selectedKbId = ref<string>('')
  // 文档列表
  const documents = ref<Document[]>([])
  // 加载状态
  const loading = ref(false)
  // 当前处理流程
  const currentProcess = ref<RagProcess | null>(null)
  // 流式回答内容
  const streamingAnswer = ref('')
  // 是否正在流式输出
  const isStreaming = ref(false)
  // 错误信息
  const error = ref<string | null>(null)
  
  // ==================== Getters ====================
  
  // 当前选中的知识库
  const selectedKb = computed(() => {
    return knowledgeBases.value.find(kb => kb.id === selectedKbId.value) || null
  })
  
  // 当前知识库的文档
  const currentDocuments = computed(() => {
    if (!selectedKbId.value) return []
    return documents.value.filter(doc => doc.kbId === selectedKbId.value)
  })
  
  // 流程步骤状态（用于UI展示）
  const processSteps = computed((): ProcessStepStatus[] => {
    if (!currentProcess.value) return []
    
    const process = currentProcess.value
    return [
      {
        key: 'queryDecomposition',
        label: '查询分解',
        status: process.queryDecomposition.status,
        icon: 'Magic',
        description: process.queryDecomposition.subQueries?.length > 0
          ? `分解为 ${process.queryDecomposition.subQueries.length} 个子查询`
          : '分析查询意图',
        details: { subQueries: process.queryDecomposition.subQueries },
      },
      {
        key: 'vectorRetrieval',
        label: '向量检索',
        status: process.vectorRetrieval.status,
        icon: 'Search',
        description: process.vectorRetrieval.retrievedChunks?.length > 0
          ? `从 ${process.vectorRetrieval.totalChunks} 个块中检索到 ${process.vectorRetrieval.retrievedChunks.length} 个`
          : '基于语义相似度检索',
        details: { chunks: process.vectorRetrieval.retrievedChunks },
      },
      {
        key: 'keywordRetrieval',
        label: '关键词检索',
        status: process.keywordRetrieval.status,
        icon: 'Collection',
        description: process.keywordRetrieval.keywords?.length > 0
          ? `关键词: ${process.keywordRetrieval.keywords.join(', ')}`
          : '基于关键词匹配检索',
        details: { keywords: process.keywordRetrieval.keywords },
      },
      {
        key: 'reranking',
        label: '重排序',
        status: process.reranking.status,
        icon: 'Sort',
        description: process.reranking.rankedChunks?.length > 0
          ? `从 ${process.reranking.inputChunks} 个块中筛选出 ${process.reranking.outputChunks} 个`
          : '多维度重排序',
        details: { rankedChunks: process.reranking.rankedChunks },
      },
      {
        key: 'answerGeneration',
        label: '答案生成',
        status: process.answerGeneration.status,
        icon: 'ChatDotRound',
        description: process.answerGeneration.tokensGenerated > 0
          ? `已生成 ${process.answerGeneration.tokensGenerated} 个 token`
          : '基于检索结果生成回答',
        details: { usedChunks: process.answerGeneration.usedChunks },
      },
    ]
  })
  
  // ==================== Actions ====================
  
  // 加载知识库列表
  async function loadKnowledgeBases() {
    loading.value = true
    try {
      knowledgeBases.value = await ragApi.getKnowledgeBases()
      error.value = null
    } catch (err) {
      error.value = '加载知识库列表失败'
      console.error(err)
    } finally {
      loading.value = false
    }
  }
  
  // 选择知识库
  function selectKnowledgeBase(kbId: string) {
    selectedKbId.value = kbId
    // 加载该知识库的文档
    loadDocuments(kbId)
  }
  
  // 创建知识库
  async function createKnowledgeBase(name: string, description: string, kbType: string) {
    loading.value = true
    try {
      const kb = await ragApi.createKnowledgeBase({
        name,
        description,
        kbType,
      })
      knowledgeBases.value.push(kb)
      // 自动选中新创建的知识库
      selectKnowledgeBase(kb.id)
      error.value = null
      return kb
    } catch (err) {
      error.value = '创建知识库失败'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // 删除知识库
  async function deleteKnowledgeBase(kbId: string) {
    loading.value = true
    try {
      await ragApi.deleteKnowledgeBase(kbId)
      knowledgeBases.value = knowledgeBases.value.filter(kb => kb.id !== kbId)
      if (selectedKbId.value === kbId) {
        selectedKbId.value = ''
      }
      error.value = null
    } catch (err) {
      error.value = '删除知识库失败'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // 加载文档列表
  async function loadDocuments(kbId?: string) {
    loading.value = true
    try {
      documents.value = await ragApi.getDocuments(kbId)
      error.value = null
    } catch (err) {
      error.value = '加载文档列表失败'
      console.error(err)
    } finally {
      loading.value = false
    }
  }
  
  // 创建文本文档
  async function createTextDocument(
    title: string,
    content: string,
    chunkingStrategy: ChunkingStrategy = 'none',
    chunkSize: number = 500,
    chunkOverlap: number = 50,
    separator: string = ''
  ) {
    if (!selectedKbId.value) {
      throw new Error('请先选择知识库')
    }
    
    loading.value = true
    try {
      const doc = await ragApi.createTextDocument({
        kbId: selectedKbId.value,
        title,
        content,
        chunkingStrategy,
        chunkSize,
        chunkOverlap,
        separator,
      })
      documents.value.push(doc)
      // 更新知识库文档计数
      const kb = knowledgeBases.value.find(k => k.id === selectedKbId.value)
      if (kb) {
        kb.documentCount++
      }
      error.value = null
      return doc
    } catch (err) {
      error.value = '创建文档失败'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // 上传文档
  async function uploadDocument(
    file: File,
    chunkingStrategy: ChunkingStrategy = 'fixed_size',
    chunkSize: number = 500,
    chunkOverlap: number = 50,
    separator: string = ''
  ) {
    if (!selectedKbId.value) {
      throw new Error('请先选择知识库')
    }
    
    loading.value = true
    try {
      const doc = await ragApi.uploadDocument(
        selectedKbId.value,
        file,
        chunkingStrategy,
        chunkSize,
        chunkOverlap,
        separator
      )
      documents.value.push(doc)
      // 更新知识库文档计数
      const kb = knowledgeBases.value.find(k => k.id === selectedKbId.value)
      if (kb) {
        kb.documentCount++
      }
      error.value = null
      return doc
    } catch (err) {
      error.value = '上传文档失败'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // 删除文档
  async function deleteDocument(docId: string) {
    loading.value = true
    try {
      await ragApi.deleteDocument(docId)
      const doc = documents.value.find(d => d.id === docId)
      documents.value = documents.value.filter(d => d.id !== docId)
      // 更新知识库文档计数
      if (doc && selectedKbId.value) {
        const kb = knowledgeBases.value.find(k => k.id === selectedKbId.value)
        if (kb && kb.documentCount > 0) {
          kb.documentCount--
        }
      }
      error.value = null
    } catch (err) {
      error.value = '删除文档失败'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // 执行 RAG 查询（流式）
  function streamQuery(
    query: string,
    onChunk: (chunk: string) => void,
    onProcessUpdate: (process: RagProcess) => void,
    onComplete: () => void,
    onError: (error: string) => void
  ): () => void {
    if (!selectedKbId.value) {
      onError('请先选择知识库')
      return () => {}
    }
    
    // 重置状态
    streamingAnswer.value = ''
    currentProcess.value = null
    isStreaming.value = true
    error.value = null
    
    const cancelFn = ragApi.streamQueryRag(
      {
        query,
        kbId: selectedKbId.value,
        stream: true,
      },
      (event: RagStreamEvent) => {
        switch (event.type) {
          case 'process':
            currentProcess.value = event.data as RagProcess
            onProcessUpdate(currentProcess.value)
            break
          case 'chunk':
            // 后端发送的是 {content: string}，需要提取 content 字段
            const chunkData = event.data as { content?: string; [key: string]: unknown }
            const chunk = typeof chunkData === 'string' ? chunkData : (chunkData.content || '')
            streamingAnswer.value += chunk
            onChunk(chunk)
            break
          case 'complete':
            isStreaming.value = false
            onComplete()
            break
          case 'error':
            isStreaming.value = false
            const errorData = event.data as { message: string }
            error.value = errorData.message
            onError(errorData.message)
            break
        }
      },
      (err) => {
        isStreaming.value = false
        error.value = err.message
        onError(err.message)
      }
    )
    
    return cancelFn
  }
  
  // 重置流程状态
  function resetProcess() {
    currentProcess.value = null
    streamingAnswer.value = ''
    isStreaming.value = false
    error.value = null
  }
  
  return {
    // State
    knowledgeBases,
    selectedKbId,
    documents,
    loading,
    currentProcess,
    streamingAnswer,
    isStreaming,
    error,
    // Getters
    selectedKb,
    currentDocuments,
    processSteps,
    // Actions
    loadKnowledgeBases,
    selectKnowledgeBase,
    createKnowledgeBase,
    deleteKnowledgeBase,
    loadDocuments,
    createTextDocument,
    uploadDocument,
    deleteDocument,
    streamQuery,
    resetProcess,
  }
})
