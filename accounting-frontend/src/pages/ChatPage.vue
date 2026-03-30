<template>
  <div class="page chat-page">
    <!-- 圆角矩形聊天框容器 -->
    <div class="chat-container">
      <!-- 消息列表 -->
      <div class="messages-area" ref="messagesArea">
        <!-- 空状态引导 -->
        <div v-if="messages.length === 0" class="welcome-wrap">
          <div class="guide-chips">
            <div
              v-for="g in guideItems"
              :key="g"
              class="guide-chip"
              @click="sendMessage(g)"
            >{{ g }}</div>
          </div>
        </div>

        <ChatMessageItem
          v-for="msg in messages"
          :key="msg.id"
          :msg="msg"
        />
      </div>

      <!-- 快捷短语 -->
      <QuickPhrases :phrases="quickPhrases" @select="sendMessage" />

      <!-- 输入栏 -->
      <div class="input-bar">
        <el-input
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          :placeholder="isStreaming ? 'AI 正在回复...' : '告诉我记账内容...'"
          :disabled="isStreaming"
          class="chat-input"
          @keydown.enter.exact.prevent="handleEnter"
        />
        <el-button
          type="primary"
          circle
          :disabled="!inputText.trim() || isStreaming"
          class="send-btn"
          @click="handleEnter"
        >
          <el-icon><Promotion /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Delete, Promotion, ChatDotRound } from '@element-plus/icons-vue'
import ChatMessageItem from '@/components/ChatMessageItem.vue'
import QuickPhrases from '@/components/QuickPhrases.vue'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

// 使用全局 store 的状态
const messages = computed(() => chatStore.messages)
const isStreaming = computed(() => chatStore.isStreaming)
const threadId = computed(() => chatStore.threadId)

const inputText = ref('')
const messagesArea = ref<HTMLElement | null>(null)

const quickPhrases = [
  '花了30块吃饭',
  '打车15元',
  '本月消费统计',
  '按分类汇总',
  '收到工资5000',
  '今日账单',
  '导出本月记录',
  '最近10条记录',
]

const guideItems = [
  '花了30块吃午饭',
  '本月支出统计',
  '按分类统计支出',
  '收到工资5000元',
]

async function scrollToBottom() {
  await nextTick()
  if (messagesArea.value) {
    messagesArea.value.scrollTop = messagesArea.value.scrollHeight
  }
}

async function sendMessage(text: string) {
  const trimmed = text.trim()
  if (!trimmed || isStreaming.value) return

  inputText.value = ''

  // 使用 store 发送消息
  await chatStore.sendMessage(trimmed)
  scrollToBottom()
}

function handleEnter() {
  sendMessage(inputText.value)
}

function clearMessages() {
  if (isStreaming.value) return
  chatStore.clearMessages()
}

onMounted(() => {
  // 支持从首页快捷按钮带 prompt 跳转
  const prompt = route.query.prompt as string | undefined
  if (prompt) {
    nextTick(() => sendMessage(prompt))
  }
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
  padding: 8px 12px 12px;
}

/* 圆角矩形聊天框容器 */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.welcome-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0 16px;
  gap: 8px;
}

.guide-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.guide-chip {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  padding: 6px 16px;
  font-size: 13px;
  color: #576b95;
  cursor: pointer;
  transition: all 0.15s;
}
.guide-chip:active {
  background: #576b95;
  color: #fff;
}

.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px 16px;
  background: #f7f7f7;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.chat-input { flex: 1; }
.chat-input :deep(.el-textarea__inner) {
  background: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.send-btn { flex-shrink: 0; }
.send-btn :deep(.el-button) {
  background: #07c160;
  border-color: #07c160;
}
</style>
