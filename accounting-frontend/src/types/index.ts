// 记账相关类型定义

export type TransactionType = 'expense' | 'income'

export interface TransactionRecord {
  id: number
  transaction_type: TransactionType
  category: string
  amount: number
  note: string
  transaction_date: string
  created_at: string
}

export interface StatsResponse {
  income_total: number
  expense_total: number
  net: number
  income_count: number
  expense_count: number
  start_date: string
  end_date: string
}

export interface CategoriesResponse {
  expense_categories: string[]
  income_categories: string[]
}

export interface ChatResponse {
  reply: string
  thread_id: string
  model: string
}

export interface ChatRequest {
  message: string
  model?: string
  thread_id?: string
}

export interface RecordsQuery {
  transaction_type?: TransactionType
  category?: string
  start_date?: string
  end_date?: string
  limit?: number
}

export interface CreateRecordRequest {
  transaction_type: TransactionType
  category: string
  amount: number
  note?: string
  transaction_date?: string
}

export interface UpdateRecordRequest {
  transaction_type?: TransactionType
  category?: string
  amount?: number
  note?: string
  transaction_date?: string
}

export interface OperationResponse {
  success: boolean
  message: string
  record?: TransactionRecord
}

// 对话消息
export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  loading?: boolean
}

// 分类 emoji 映射
export const CATEGORY_EMOJI: Record<string, string> = {
  三餐: '🍜',
  日用品: '🛒',
  学习: '📚',
  交通: '🚌',
  娱乐: '🎮',
  医疗: '💊',
  工资: '💰',
  奖金: '🎁',
  理财: '📈',
  其他: '📦',
}
