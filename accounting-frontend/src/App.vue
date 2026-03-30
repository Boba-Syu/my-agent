<template>
  <!-- 移动端容器 -->
  <div class="mobile-shell">
    <!-- 全局顶部标题栏 -->
    <header class="global-header">
      <!-- 设置按钮 - 左侧 -->
      <button class="sidebar-trigger" @click.stop="toggleSidebar" type="button">
        <el-icon><Fold /></el-icon>
      </button>
      <div class="header-title">记账Agent</div>
      <div class="header-spacer"></div>
    </header>

    <router-view v-slot="{ Component }">
      <keep-alive :include="['HomePage', 'RecordsPage']">
        <component :is="Component" class="page-view" />
      </keep-alive>
    </router-view>
    <BottomNav />
    <Sidebar />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Fold, Setting, ChatDotRound } from '@element-plus/icons-vue'
import BottomNav from '@/components/BottomNav.vue'
import Sidebar from '@/components/Sidebar.vue'
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const chatStore = useChatStore()
const themeStore = useThemeStore()
const { toggleSidebar, initTheme } = themeStore

onMounted(() => {
  initTheme()
})

function goToChat() {
  router.push('/chat')
}
</script>

<style>
/* 移动端外壳：适配主流手机分辨率 */
.mobile-shell {
  max-width: 100%;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  position: relative;
  overflow: hidden;
}

/* 全局顶部标题栏 */
.global-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 50px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #e0e0e0;
  z-index: 1000;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #1f2937;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.header-spacer {
  width: 36px;
}

.page-view {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: 50px;
}

/* 侧边栏入口按钮 - 放在header内 */
.sidebar-trigger {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  pointer-events: auto;
}

.sidebar-trigger:hover {
  background: #f5f5f5;
}

.sidebar-trigger .el-icon {
  font-size: 20px;
  color: #666;
}
</style>
