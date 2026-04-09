<template>
  <div class="flow-viewer">
    <div class="flow-header">
      <h4 class="flow-title">
        <el-icon><View /></el-icon>
        RAG 处理流程
      </h4>
      <el-tag v-if="isCompleted" type="success" size="small">已完成</el-tag>
      <el-tag v-else-if="isRunning" type="warning" size="small">处理中...</el-tag>
    </div>
    
    <div class="flow-steps">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        :class="['flow-step', `status-${step.status}`]"
      >
        <!-- 连接线 -->
        <div v-if="index > 0" class="step-connector" />
        
        <div class="step-content">
          <!-- 图标 -->
          <div class="step-icon-wrapper">
            <el-icon v-if="step.status === 'completed'" class="step-icon" :size="20">
              <Check />
            </el-icon>
            <el-icon v-else-if="step.status === 'failed'" class="step-icon" :size="20">
              <Close />
            </el-icon>
            <el-icon v-else-if="step.status === 'running'" class="step-icon spinning" :size="20">
              <Loading />
            </el-icon>
            <el-icon v-else class="step-icon" :size="20">
              <component :is="step.icon" />
            </el-icon>
          </div>
          
          <!-- 信息 -->
          <div class="step-info">
            <div class="step-name">{{ step.label }}</div>
            <div class="step-desc">{{ step.description }}</div>
            
            <!-- 展开详情 -->
            <div v-if="hasDetails(step) && step.status !== 'pending'" class="step-details">
              <el-collapse v-model="activeDetails">
                <el-collapse-item :name="step.key">
                  <template #title>
                    <span class="details-title">查看详情</span>
                  </template>
                  
                  <!-- 查询分解详情 -->
                  <div v-if="step.key === 'queryDecomposition' && step.details?.subQueries" class="detail-content">
                    <div class="detail-label">子查询：</div>
                    <ul class="detail-list">
                      <li v-for="(q, i) in step.details.subQueries" :key="i">{{ q }}</li>
                    </ul>
                  </div>
                  
                  <!-- 向量检索详情 -->
                  <div v-if="step.key === 'vectorRetrieval' && step.details?.chunks" class="detail-content">
                    <div class="detail-label">检索结果（前5条）：</div>
                    <div class="chunk-list">
                      <div
                        v-for="(chunk, i) in step.details.chunks.slice(0, 5)"
                        :key="i"
                        class="chunk-item"
                      >
                        <div class="chunk-header">
                          <span class="chunk-title">{{ chunk.documentTitle }}</span>
                          <el-tag size="small" type="info">{{ (chunk.score * 100).toFixed(1) }}%</el-tag>
                        </div>
                        <div class="chunk-content">{{ truncate(chunk.content, 80) }}</div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 关键词检索详情 -->
                  <div v-if="step.key === 'keywordRetrieval' && step.details?.keywords" class="detail-content">
                    <div class="detail-label">提取关键词：</div>
                    <div class="keyword-list">
                      <el-tag
                        v-for="(kw, i) in step.details.keywords"
                        :key="i"
                        size="small"
                        class="keyword-tag"
                      >
                        {{ kw }}
                      </el-tag>
                    </div>
                  </div>
                  
                  <!-- 重排序详情 -->
                  <div v-if="step.key === 'reranking' && step.details?.rankedChunks" class="detail-content">
                    <div class="detail-label">重排序结果（前5条）：</div>
                    <div class="rank-list">
                      <div
                        v-for="(chunk, i) in step.details.rankedChunks.slice(0, 5)"
                        :key="i"
                        class="rank-item"
                      >
                        <span class="rank-number">#{{ i + 1 }}</span>
                        <span class="rank-title">{{ chunk.documentTitle }}</span>
                        <el-tag size="small" type="success">{{ (chunk.score * 100).toFixed(1) }}%</el-tag>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 答案生成详情 -->
                  <div v-if="step.key === 'answerGeneration'" class="detail-content">
                    <div class="detail-stats">
                      <div class="stat-item">
                        <span class="stat-label">使用文档块：</span>
                        <span class="stat-value">{{ step.details?.usedChunks || 0 }} 个</span>
                      </div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  View,
  Check,
  Close,
  Loading,
} from '@element-plus/icons-vue'
import type { ProcessStepStatus } from '@/types/rag'

const props = defineProps<{
  steps: ProcessStepStatus[]
}>()

const activeDetails = ref<string[]>([])

const isRunning = computed(() => {
  return props.steps.some(s => s.status === 'running')
})

const isCompleted = computed(() => {
  return props.steps.every(s => s.status === 'completed')
})

function hasDetails(step: ProcessStepStatus): boolean {
  return step.details && Object.keys(step.details).length > 0
}

function truncate(text: string, length: number): string {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}
</script>

<style scoped lang="scss">
.flow-viewer {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 16px;
}

.flow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.flow-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 6px;
  
  .el-icon {
    color: #409eff;
  }
}

.flow-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.flow-step {
  position: relative;
  
  &.status-completed .step-icon-wrapper {
    background: #67c23a;
    color: #fff;
  }
  
  &.status-running .step-icon-wrapper {
    background: #409eff;
    color: #fff;
  }
  
  &.status-failed .step-icon-wrapper {
    background: #f56c6c;
    color: #fff;
  }
  
  &.status-pending .step-icon-wrapper {
    background: #f5f7fa;
    color: #c0c4cc;
  }
}

.step-connector {
  position: absolute;
  left: 18px;
  top: -16px;
  width: 2px;
  height: 16px;
  background: #e4e7ed;
}

.step-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
}

.step-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s;
}

.step-icon {
  &.spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-info {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.step-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.step-details {
  margin-top: 8px;
}

.details-title {
  font-size: 12px;
  color: #409eff;
}

.detail-content {
  padding: 8px 0;
}

.detail-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.detail-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: #606266;
  
  li {
    margin-bottom: 4px;
  }
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-item {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.chunk-title {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
}

.chunk-content {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

.keyword-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.keyword-tag {
  margin: 0;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
}

.rank-number {
  font-weight: 600;
  color: #409eff;
  min-width: 24px;
}

.rank-title {
  flex: 1;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-label {
  color: #909399;
}

.stat-value {
  color: #303133;
  font-weight: 500;
}
</style>
