<template>
  <div class="rag-chat">
    <!-- 消息列表 -->
    <div ref="messagesContainer" class="messages-container">
      <el-empty v-if="messages.length === 0" description="开始对话">
        <template #description>
          <p>选择知识库后，开始提问</p>
          <p class="hint">AI 将基于知识库内容回答您的问题</p>
        </template>
      </el-empty>
      
      <template v-else>
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'" :size="20"><User /></el-icon>
            <el-icon v-else :size="20"><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            <div v-if="msg.role === 'user'" class="user-text">
              {{ msg.content }}
            </div>
            <div v-else class="assistant-content">
              <div v-if="msg.isStreaming" class="streaming-text">
                <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
                <span class="streaming-cursor"></span>
              </div>
              <div v-else class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
              
              <!-- 来源文档 -->
              <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
                <div class="sources-title">
                  <el-icon><Link /></el-icon>
                  参考来源
                </div>
                <div class="sources-list">
                  <el-tag
                    v-for="(source, i) in msg.sources"
                    :key="i"
                    size="small"
                    type="info"
                    class="source-tag"
                    :title="source.content"
                  >
                    {{ source.documentTitle }}
                    <span class="source-score">{{ (source.score * 100).toFixed(0) }}%</span>
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      
      <!-- 当前流式消息 -->
      <div v-if="isStreaming" class="message assistant streaming">
        <div class="message-avatar">
          <el-icon :size="20"><ChatDotRound /></el-icon>
        </div>
        <div class="message-content">
          <div class="streaming-text">
            <div class="markdown-body" v-html="renderMarkdown(streamingContent)"></div>
            <span class="streaming-cursor"></span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-wrapper">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="输入您的问题..."
          :disabled="!selectedKb || isStreaming"
          @keydown.enter.prevent="handleSend"
        />
        <div class="input-actions">
          <span v-if="selectedKb" class="selected-kb">
            <el-icon><Collection /></el-icon>
            {{ selectedKb.name }}
          </span>
          <span v-else class="no-kb-hint">请先选择知识库</span>
          <el-button
            type="primary"
            :disabled="!canSend"
            :loading="isStreaming"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import {
  User,
  ChatDotRound,
  Promotion,
  Collection,
  Link,
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { useRagStore } from '@/stores/rag'
import type { RetrievalSource, RagProcess } from '@/types/rag'

const store = useRagStore()

const selectedKb = computed(() => store.selectedKb)
const isStreaming = computed(() => store.isStreaming)

// 消息列表
interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: RetrievalSource[]
  isStreaming?: boolean
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const streamingContent = ref('')
const messagesContainer = ref<HTMLDivElement>()
const currentCancelFn = ref<(() => void) | null>(null)
const currentSources = ref<RetrievalSource[]>([])

const canSend = computed(() => {
  return selectedKb.value && inputMessage.value.trim() && !isStreaming.value
})

// Markdown 渲染器
const md = new MarkdownIt({
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (__) {}
    }
    return ''
  },
})

function renderMarkdown(content: string): string {
  return md.render(content)
}

// 发送消息
function handleSend() {
  if (!canSend.value) return
  
  const query = inputMessage.value.trim()
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: query,
  })
  
  // 清空输入
  inputMessage.value = ''
  streamingContent.value = ''
  currentSources.value = []
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom()
  })
  
  // 开始流式查询
  currentCancelFn.value = store.streamQuery(
    query,
    (chunk) => {
      // 收到 chunk
      streamingContent.value += chunk
      nextTick(() => {
        scrollToBottom()
      })
    },
    (process) => {
      // 流程更新（由 RagFlowViewer 组件处理）
    },
    () => {
      // 完成
      messages.value.push({
        role: 'assistant',
        content: streamingContent.value,
        sources: currentSources.value,
      })
      streamingContent.value = ''
      currentSources.value = []
      currentCancelFn.value = null
      nextTick(() => {
        scrollToBottom()
      })
    },
    (error) => {
      // 错误
      messages.value.push({
        role: 'assistant',
        content: `抱歉，处理过程中出现错误：${error}`,
      })
      streamingContent.value = ''
      currentCancelFn.value = null
      nextTick(() => {
        scrollToBottom()
      })
    }
  )
}

// 监听流程更新，获取 sources
watch(() => store.currentProcess, (process) => {
  if (process?.reranking?.rankedChunks) {
    // 从重排序结果构建 sources
    currentSources.value = process.reranking.rankedChunks.map(chunk => ({
      documentId: chunk.documentId,
      documentTitle: chunk.documentTitle,
      chunkIndex: 0,
      content: chunk.content,
      score: chunk.score,
    }))
  }
}, { deep: true })

// 滚动到底部
function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 组件卸载时取消流式请求
onUnmounted(() => {
  if (currentCancelFn.value) {
    currentCancelFn.value()
  }
})

import { onUnmounted } from 'vue'
</script>

<style scoped lang="scss">
.rag-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  
  &.user {
    flex-direction: row-reverse;
    
    .message-avatar {
      background: #c0c4cc;
    }
    
    .message-content {
      align-items: flex-end;
    }
    
    .user-text {
      background: #95ec69;
      color: #1a1a1a;
      border-radius: 12px 2px 12px 12px;
    }
  }
  
  &.assistant {
    .message-avatar {
      background: #409eff;
      color: #fff;
    }
    
    .message-content {
      align-items: flex-start;
    }
    
    .assistant-content {
      background: #fff;
      border: 1px solid #e4e7ed;
      border-radius: 2px 12px 12px 12px;
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: calc(100% - 60px);
}

.user-text {
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.assistant-content {
  padding: 12px 16px;
  
  :deep(.markdown-body) {
    font-size: 14px;
    line-height: 1.6;
    color: #303133;
    
    p {
      margin: 0 0 12px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    code {
      background: #f5f7fa;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 13px;
    }
    
    pre {
      background: #f5f7fa;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      
      code {
        background: none;
        padding: 0;
      }
    }
    
    ul, ol {
      margin: 0 0 12px;
      padding-left: 20px;
    }
    
    li {
      margin-bottom: 4px;
    }
    
    h1, h2, h3, h4 {
      margin: 16px 0 12px;
      font-weight: 600;
    }
    
    blockquote {
      border-left: 4px solid #409eff;
      padding-left: 12px;
      margin: 12px 0;
      color: #606266;
    }
  }
}

.streaming-text {
  position: relative;
  
  .streaming-cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background: #409eff;
    margin-left: 2px;
    animation: blink 1s infinite;
    vertical-align: middle;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.sources-title {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-tag {
  cursor: help;
  
  .source-score {
    margin-left: 4px;
    opacity: 0.7;
  }
}

.input-area {
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-kb {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #409eff;
  background: #ecf5ff;
  padding: 4px 10px;
  border-radius: 4px;
}

.no-kb-hint {
  font-size: 13px;
  color: #909399;
}
</style>
