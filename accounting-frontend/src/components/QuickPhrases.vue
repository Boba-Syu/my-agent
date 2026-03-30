<template>
  <div class="quick-phrases">
    <!-- 快捷短语已移除 -->
  </div>
</template>

<script setup lang="ts">
defineEmits<{ (e: 'select', phrase: string): void }>()
</script>

<style scoped>
.quick-phrases {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  overflow-x: auto;
  scrollbar-width: none;
  flex-shrink: 0;
  background: #fff;
  border-top: 1px solid var(--color-border);
}
.quick-phrases::-webkit-scrollbar { display: none; }

.phrase-chip {
  white-space: nowrap;
  background: #f0f4ff;
  color: var(--color-primary);
  border: 1px solid #dce4ff;
  border-radius: 20px;
  padding: 5px 14px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.phrase-chip:active {
  background: var(--color-primary);
  color: #fff;
  transform: scale(0.96);
}
</style>
