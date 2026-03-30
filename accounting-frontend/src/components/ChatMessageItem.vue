<template>
  <div :class="['chat-msg', msg.role]">
    <!-- 用户消息 -->
    <template v-if="msg.role === 'user'">
      <div class="bubble user-bubble">
        {{ msg.content }}
        <div class="bubble-arrow arrow-right"></div>
      </div>
      <div class="avatar user-avatar">
        <el-icon><User /></el-icon>
      </div>
    </template>

    <!-- Assistant 消息 -->
    <template v-else>
      <div class="avatar bot-avatar">
        <el-icon><Service /></el-icon>
      </div>
      <div class="bubble bot-bubble">
        <div class="bubble-arrow arrow-left"></div>
        <!-- 加载中光标动画 -->
        <template v-if="msg.loading && !msg.content">
          <span class="typing-dot" />
          <span class="typing-dot" />
          <span class="typing-dot" />
        </template>
        <template v-else>
          <!-- Markdown 渲染 -->
          <MarkdownRenderer :content="msg.content + (msg.loading ? '▍' : '')" />
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '@/types'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { User, Service } from '@element-plus/icons-vue'

defineProps<{ msg: ChatMessage }>()
</script>

<style scoped>
.chat-msg {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
}

/* 用户消息靠右 */
.chat-msg.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.user-avatar {
  background: #e0e0e0;
  color: #666;
}

.bot-avatar {
  background: #07c160;
  color: #fff;
}

.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.5;
  word-break: break-word;
  position: relative;
}

.user-bubble {
  background: #95ec69;
  color: #000;
  border-top-right-radius: 4px;
}

.bot-bubble {
  background: #fff;
  color: #000;
  border: 1px solid #e0e0e0;
  border-top-left-radius: 4px;
}

/* 气泡箭头 */
.bubble-arrow {
  position: absolute;
  top: 12px;
  width: 0;
  height: 0;
  border-style: solid;
}

.arrow-right {
  right: -6px;
  border-width: 6px 0 6px 6px;
  border-color: transparent transparent transparent #95ec69;
}

.arrow-left {
  left: -6px;
  border-width: 6px 6px 6px 0;
  border-color: transparent #fff transparent transparent;
}

/* 打点加载动画 */
.typing-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #aaa;
  border-radius: 50%;
  margin: 0 2px;
  animation: typing-bounce 1.2s infinite ease-in-out;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40% { transform: translateY(-5px); opacity: 1; }
}
</style>
