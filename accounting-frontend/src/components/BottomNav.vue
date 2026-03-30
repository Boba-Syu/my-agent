<template>
  <nav class="bottom-nav">
    <router-link
      v-for="tab in tabs"
      :key="tab.path"
      :to="tab.path"
      class="nav-item"
      active-class="active"
    >
      <component :is="tab.icon" class="nav-icon" />
      <span class="nav-label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { House, ChatDotRound, List } from '@element-plus/icons-vue'

const tabs = [
  { path: '/home', label: '首页', icon: House },
  { path: '/chat', label: '记账', icon: ChatDotRound },
  { path: '/records', label: '记录', icon: List },
]
</script>

<style scoped>
.bottom-nav {
  display: flex;
  background: #fff;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
  z-index: 100;
  height: var(--nav-height);
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: var(--color-text-muted);
  font-size: 11px;
  transition: color 0.2s;
}

.nav-item.active {
  color: var(--color-primary);
}

.nav-icon {
  width: 22px;
  height: 22px;
}
</style>
