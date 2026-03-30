<template>
  <!-- 渲染 Markdown，表格/代码块/列表均支持 -->
  <div class="md-body" v-html="renderedHtml" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()

// 配置 marked：启用 GFM（表格、任务列表等）
marked.setOptions({ gfm: true, breaks: true })

const renderedHtml = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content) as string
})
</script>

<style scoped>
.md-body {
  word-break: break-word;
}

/* Markdown 元素样式 */
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3), .md-body :deep(h4), .md-body :deep(h5), .md-body :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.md-body :deep(h1) { font-size: 1.5em; }
.md-body :deep(h2) { font-size: 1.3em; }
.md-body :deep(h3) { font-size: 1.1em; }

.md-body :deep(p) {
  margin-top: 0;
  margin-bottom: 0.5em;
  line-height: 1.6;
}

.md-body :deep(ul), .md-body :deep(ol) {
  margin-top: 0;
  margin-bottom: 0.5em;
  padding-left: 1.5em;
}

.md-body :deep(li) {
  margin-bottom: 0.25em;
}

.md-body :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'Courier New', monospace;
}

.md-body :deep(pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.md-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.md-body :deep(blockquote) {
  border-left: 4px solid #ddd;
  padding-left: 1em;
  margin: 0.5em 0;
  color: #666;
}

.md-body :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.md-body :deep(a:hover) {
  text-decoration: underline;
}

.md-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
}

.md-body :deep(th), .md-body :deep(td) {
  border: 1px solid #ddd;
  padding: 6px 10px;
  text-align: left;
}

.md-body :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.md-body :deep(hr) {
  border: none;
  border-top: 1px solid #ddd;
  margin: 1em 0;
}
</style>
