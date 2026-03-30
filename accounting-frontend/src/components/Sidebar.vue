<template>
  <div class="sidebar-overlay" v-if="sidebarOpen" @click="toggleSidebar"></div>
  <div class="sidebar" :class="{ open: sidebarOpen }">
    <div class="sidebar-header">
      <span class="sidebar-title">设置</span>
      <el-icon @click="toggleSidebar"><Close /></el-icon>
    </div>
    <div class="sidebar-content">
      <div class="section">
        <div class="section-title">主题颜色</div>
        <div class="theme-grid">
          <div
            v-for="color in themeColors"
            :key="color.key"
            class="theme-option"
            :class="{ active: currentColor === color.key }"
            @click="setTheme(color.key)"
          >
            <div class="theme-preview" :style="{ backgroundColor: color.value.primary }"></div>
            <span class="theme-label">{{ color.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import type { ThemeColor } from '@/stores/theme'

const themeStore = useThemeStore()
const { currentColor, sidebarOpen, setTheme, toggleSidebar } = themeStore

const themeColors = [
  { key: 'pink' as ThemeColor, label: '樱花粉', value: { primary: '#FF9AA2' } },
  { key: 'purple' as ThemeColor, label: '葡萄紫', value: { primary: '#B19CD9' } },
  { key: 'blue' as ThemeColor, label: '天空蓝', value: { primary: '#8EC5FC' } },
  { key: 'mint' as ThemeColor, label: '薄荷绿', value: { primary: '#6BCB77' } },
  { key: 'peach' as ThemeColor, label: '蜜桃橙', value: { primary: '#FFB389' } }
]
</script>

<style scoped>
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 999;
  transition: opacity 0.3s;
}

.sidebar {
  position: fixed;
  top: 0;
  left: -280px;
  width: 280px;
  height: 100%;
  background: #fff;
  z-index: 1000;
  transition: left 0.3s ease;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.sidebar.open {
  left: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.sidebar-header .el-icon {
  font-size: 20px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: color 0.2s;
}

.sidebar-header .el-icon:hover {
  color: var(--color-primary);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 12px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-bg);
}

.theme-option:hover {
  border-color: var(--color-border);
  transform: translateY(-2px);
}

.theme-option.active {
  border-color: var(--color-primary);
  background: rgba(107, 203, 119, 0.05);
}

.theme-preview {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.theme-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}
</style>
