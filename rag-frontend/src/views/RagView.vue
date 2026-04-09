<template>
  <div class="rag-page">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="header-left">
        <el-button
          type="primary"
          link
          :icon="isCollapse ? Expand : Fold"
          class="menu-btn"
          @click="toggleSidebar"
        />
        <h1 class="header-title">
          <el-icon><ChatLineRound /></el-icon>
          RAG 知识库
        </h1>
      </div>
      <div class="header-right">
        <el-tag v-if="selectedKb" type="success" effect="dark">
          {{ selectedKb.name }}
        </el-tag>
        <el-tag v-else type="info">未选择知识库</el-tag>
      </div>
    </header>
    
    <!-- 主体内容 -->
    <div class="main-content">
      <!-- 左侧边栏 -->
      <aside :class="['sidebar', { collapsed: isCollapse }]">
        <el-tabs v-model="activeTab" class="sidebar-tabs">
          <el-tab-pane label="知识库" name="kb">
            <KnowledgeBaseSelector @select-kb="activeTab = 'docs'" />
          </el-tab-pane>
          <el-tab-pane label="文档" name="docs">
            <DocumentManager @show-selector="activeTab = 'kb'" />
          </el-tab-pane>
        </el-tabs>
      </aside>
      
      <!-- 中间内容区 -->
      <main class="center-panel">
        <RagChat />
      </main>
      
      <!-- 右侧边栏 -->
      <aside :class="['right-panel', { collapsed: isRightCollapse }]">
        <div class="panel-header">
          <span>处理流程</span>
          <el-button
            type="primary"
            link
            :icon="isRightCollapse ? ArrowLeft : ArrowRight"
            @click="toggleRightPanel"
          />
        </div>
        <div v-show="!isRightCollapse" class="panel-content">
          <RagFlowViewer :steps="processSteps" />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Fold,
  Expand,
  ChatLineRound,
  ArrowLeft,
  ArrowRight,
} from '@element-plus/icons-vue'
import KnowledgeBaseSelector from '@/components/KnowledgeBaseSelector.vue'
import DocumentManager from '@/components/DocumentManager.vue'
import RagChat from '@/components/RagChat.vue'
import RagFlowViewer from '@/components/RagFlowViewer.vue'
import { useRagStore } from '@/stores/rag'

const store = useRagStore()

const isCollapse = ref(false)
const isRightCollapse = ref(false)
const activeTab = ref('kb')

const selectedKb = computed(() => store.selectedKb)
const processSteps = computed(() => store.processSteps)

function toggleSidebar() {
  isCollapse.value = !isCollapse.value
}

function toggleRightPanel() {
  isRightCollapse.value = !isRightCollapse.value
}

// 初始化加载数据
onMounted(() => {
  store.loadKnowledgeBases()
})
</script>

<style scoped lang="scss">
.rag-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.header {
  height: 50px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.menu-btn {
  font-size: 18px;
}

.header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-icon {
    color: #409eff;
  }
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

.sidebar {
  width: 380px;
  flex-shrink: 0;
  transition: width 0.3s;
  
  &.collapsed {
    width: 0;
    overflow: hidden;
    padding: 0;
  }
}

.sidebar-tabs {
  height: 100%;
  
  :deep(.el-tabs__header) {
    margin-bottom: 0;
    background: #fff;
    border-radius: 12px 12px 0 0;
    padding: 0 16px;
  }
  
  :deep(.el-tabs__content) {
    height: calc(100% - 40px);
  }
  
  :deep(.el-tab-pane) {
    height: 100%;
  }
}

.center-panel {
  flex: 1;
  min-width: 400px;
  overflow: hidden;
}

.right-panel {
  width: 360px;
  flex-shrink: 0;
  background: transparent;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
  
  &.collapsed {
    width: 40px;
    
    .panel-header {
      border-radius: 12px;
    }
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px 12px 0 0;
  font-weight: 600;
  color: #303133;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
}
</style>
