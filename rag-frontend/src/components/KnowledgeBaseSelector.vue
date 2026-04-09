<template>
  <div class="kb-selector">
    <div class="kb-header">
      <h3 class="kb-title">
        <el-icon><Collection /></el-icon>
        知识库
      </h3>
      <el-button
        type="primary"
        size="small"
        :icon="Plus"
        @click="showCreateDialog = true"
      >
        新建
      </el-button>
    </div>
    
    <el-scrollbar class="kb-list">
      <el-empty v-if="knowledgeBases.length === 0" description="暂无知识库" />
      
      <div
        v-for="kb in knowledgeBases"
        :key="kb.id"
        :class="['kb-item', { active: selectedKbId === kb.id }]"
        @click="selectKb(kb.id)"
      >
        <div class="kb-item-content">
          <div class="kb-item-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="kb-item-info">
            <div class="kb-item-name">{{ kb.name }}</div>
            <div class="kb-item-meta">
              <el-tag size="small" :type="getKbTypeTag(kb.kbType)">
                {{ getKbTypeLabel(kb.kbType) }}
              </el-tag>
              <span class="kb-item-count">{{ kb.documentCount }} 文档</span>
            </div>
            <div v-if="kb.description" class="kb-item-desc">
              {{ kb.description }}
            </div>
          </div>
        </div>
        
        <el-dropdown trigger="click" @command="handleCommand($event, kb)">
          <el-button
            type="primary"
            link
            :icon="More"
            class="kb-item-more"
            @click.stop
          />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="delete" :icon="Delete">
                删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-scrollbar>
    
    <!-- 创建知识库对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建知识库"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="createForm"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="请输入知识库名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="类型" prop="kbType">
          <el-select v-model="createForm.kbType" placeholder="选择类型" style="width: 100%">
            <el-option label="FAQ 问答" value="faq" />
            <el-option label="规章制度" value="regulation" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Plus,
  Document,
  More,
  Delete,
} from '@element-plus/icons-vue'
import { useRagStore } from '@/stores/rag'
import type { KnowledgeBase } from '@/types/rag'
import type { FormInstance, FormRules } from 'element-plus'

const store = useRagStore()

const knowledgeBases = computed(() => store.knowledgeBases)
const selectedKbId = computed(() => store.selectedKbId)

// 创建对话框
const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()

const createForm = ref({
  name: '',
  kbType: 'faq',
  description: '',
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  kbType: [
    { required: true, message: '请选择类型', trigger: 'change' },
  ],
}

// 选择知识库
function selectKb(id: string) {
  store.selectKnowledgeBase(id)
  emit('select-kb')
}

const emit = defineEmits<{
  (e: 'select-kb'): void
}>()

// 获取类型标签
function getKbTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    faq: 'FAQ',
    regulation: '制度',
    other: '其他',
  }
  return typeMap[type] || type
}

// 获取类型标签样式
function getKbTypeTag(type: string): string {
  const typeMap: Record<string, string> = {
    faq: 'success',
    regulation: 'warning',
    other: 'info',
  }
  return typeMap[type] || 'info'
}

// 处理下拉菜单命令
async function handleCommand(command: string, kb: KnowledgeBase) {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除知识库 "${kb.name}" 吗？此操作不可恢复。`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
      await store.deleteKnowledgeBase(kb.id)
      ElMessage.success('删除成功')
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败')
      }
    }
  }
}

// 提交创建
async function submitCreate() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    creating.value = true
    try {
      await store.createKnowledgeBase(
        createForm.value.name,
        createForm.value.description,
        createForm.value.kbType
      )
      ElMessage.success('创建成功')
      showCreateDialog.value = false
      // 重置表单
      createForm.value = {
        name: '',
        kbType: 'faq',
        description: '',
      }
    } catch (error) {
      ElMessage.error('创建失败')
    } finally {
      creating.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.kb-selector {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.kb-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-icon {
    font-size: 18px;
    color: #409eff;
  }
}

.kb-list {
  flex: 1;
  padding: 12px;
}

.kb-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  
  &:hover {
    background: #f5f7fa;
  }
  
  &.active {
    background: #ecf5ff;
    border-color: #409eff;
  }
}

.kb-item-content {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.kb-item-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  border-radius: 8px;
  flex-shrink: 0;
  
  .el-icon {
    font-size: 20px;
    color: #909399;
  }
}

.kb-item-info {
  flex: 1;
  min-width: 0;
}

.kb-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.kb-item-count {
  font-size: 12px;
  color: #909399;
}

.kb-item-desc {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-item-more {
  opacity: 0;
  transition: opacity 0.2s;
  
  .kb-item:hover & {
    opacity: 1;
  }
}
</style>
