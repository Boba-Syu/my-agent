import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { ChatMessage } from '@/types'
import { streamChat } from '@/api/accounting'
import { nanoid } from '@/utils/nanoid'

const STORAGE_KEY = 'chat-messages'
const THREAD_ID_KEY = 'chat-thread-id'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const threadId = ref('')

  // 从 localStorage 加载历史记录
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        messages.value = JSON.parse(stored)
      }
      const storedThreadId = localStorage.getItem(THREAD_ID_KEY)
      if (storedThreadId) {
        threadId.value = storedThreadId
      } else {
        // 初始化 threadId
        threadId.value = 'chat-' + new Date().toISOString().slice(0, 10)
        localStorage.setItem(THREAD_ID_KEY, threadId.value)
      }
    } catch (e) {
      console.error('Failed to load chat history:', e)
    }
  }

  // 保存到 localStorage
  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value))
      localStorage.setItem(THREAD_ID_KEY, threadId.value)
    } catch (e) {
      console.error('Failed to save chat history:', e)
    }
  }

  // 监听消息变化自动保存
  watch(messages, saveToStorage, { deep: true })
  watch(threadId, saveToStorage)

  // 初始化
  loadFromStorage()

  // 发送消息
  function sendMessage(text: string): Promise<void> {
    return new Promise((resolve) => {
      const trimmed = text.trim()
      if (!trimmed || isStreaming.value) {
        resolve()
        return
      }

      // 添加用户消息
      messages.value.push({
        id: nanoid(),
        role: 'user',
        content: trimmed,
        timestamp: Date.now(),
      })

      // 添加 AI 占位消息
      const botMsgId = nanoid()
      const botMsg: ChatMessage = {
        id: botMsgId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        loading: true,
      }
      messages.value.push(botMsg)

      isStreaming.value = true

      let lastFullContent = ''

      streamChat(
        { message: trimmed, thread_id: threadId.value },
        (chunk) => {
          console.log('[chatStore] 收到 chunk:', JSON.stringify(chunk))
          const target = messages.value.find((m) => m.id === botMsgId)
          if (target) {
            // 追加新内容，而不是覆盖
            target.content += chunk
            lastFullContent = target.content
            console.log('[chatStore] 更新后 content 长度:', target.content.length, '内容:', target.content)
          }
        },
        () => {
          const target = messages.value.find((m) => m.id === botMsgId)
          if (target) target.loading = false
          isStreaming.value = false
          resolve()
        },
        (err) => {
          const target = messages.value.find((m) => m.id === botMsgId)
          if (target) {
            target.content = lastFullContent || `❌ 请求失败：${err}`
            target.loading = false
          }
          isStreaming.value = false
          resolve()
        },
      )
    })
  }

  // 清空消息
  function clearMessages() {
    if (isStreaming.value) return
    messages.value = []
    saveToStorage()
  }

  return {
    messages,
    isStreaming,
    threadId,
    sendMessage,
    clearMessages,
    loadFromStorage,
  }
})
