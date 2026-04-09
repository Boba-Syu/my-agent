<template>
  <div class="doc-manager">
    <div class="doc-header">
      <h3 class="doc-title">
        <el-icon><Document /></el-icon>
        文档管理
        <el-tag v-if="selectedKb" size="small" type="info">
          {{ selectedKb.name }}
        </el-tag>
      </h3>
      <div class="doc-actions">
        <el-button
          type="primary"
          size="small"
          :icon="Plus"
          :disabled="!selectedKb"
          title="新建文本"
          @click="showCreateTextDialog = true"
        />
        <el-button
          type="success"
          size="small"
          :icon="Upload"
          :disabled="!selectedKb"
          title="上传文件"
          @click="showUploadDialog = true"
        />
      </div>
    </div>
    
    <div class="doc-content">
      <el-empty v-if="!selectedKb" description="请先选择知识库">
        <el-button type="primary" @click="$emit('show-selector')">
          去选择知识库
        </el-button>
      </el-empty>
      
      <el-empty v-else-if="currentDocuments.length === 0" description="暂无文档">
        <template #description>
          <p>该知识库暂无文档</p>
          <p class="empty-hint">点击上方按钮创建或上传文档</p>
        </template>
      </el-empty>
      
      <div v-else class="doc-list">
        <el-scrollbar>
          <div
            v-for="doc in currentDocuments"
            :key="doc.id"
            class="doc-item"
          >
            <div class="doc-item-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="doc-item-info">
              <div class="doc-item-title">{{ doc.title }}</div>
              <div class="doc-item-meta">
                <el-tag size="small" :type="doc.docType === 'markdown' ? 'primary' : 'success'">
                  {{ doc.docType === 'markdown' ? 'Markdown' : 'Text' }}
                </el-tag>
                <span class="doc-item-chunks">{{ doc.chunkCount }} 个分块</span>
                <span class="doc-item-time">{{ formatTime(doc.createdAt) }}</span>
              </div>
            </div>
            <el-dropdown trigger="click" @command="handleCommand($event, doc)">
              <el-button
                type="primary"
                link
                :icon="More"
                class="doc-item-more"
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
      </div>
    </div>
    
    <!-- 创建文本文档对话框 -->
    <el-dialog
      v-model="showCreateTextDialog"
      title="新建文本文档"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="textFormRef"
        :model="textForm"
        :rules="textFormRules"
        label-width="60px"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="textForm.title"
            placeholder="请输入文档标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="textForm.content"
            type="textarea"
            :rows="10"
            placeholder="请输入文档内容"
            maxlength="50000"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="分块策略" prop="chunkingStrategy">
          <el-select v-model="textForm.chunkingStrategy" style="width: 100%">
            <el-option
              v-for="opt in chunkingOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        
        <template v-if="showSizeSettings">
          <el-form-item label="分块大小" prop="chunkSize">
            <el-input-number
              v-model="textForm.chunkSize"
              :min="100"
              :max="2000"
              :step="100"
              style="width: 100%"
            />
          </el-form-item>
          
          <el-form-item label="重叠大小" prop="chunkOverlap">
            <el-input-number
              v-model="textForm.chunkOverlap"
              :min="0"
              :max="500"
              :step="10"
              style="width: 100%"
            />
          </el-form-item>
        </template>
        
        <el-form-item v-if="showSeparatorInput" label="分隔符" prop="separator">
          <el-input
            v-model="textForm.separator"
            placeholder="请输入分隔符，如：### 或 ---"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateTextDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreateText">
          创建
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 上传文件对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :limit="1"
        accept=".md,.txt,.markdown"
        style="margin-bottom: 20px"
      >
        <el-icon class="el-icon--upload"><Upload /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .md, .txt, .markdown 格式文件
          </div>
        </template>
      </el-upload>
      
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="分块策略">
          <el-select v-model="uploadForm.chunkingStrategy" style="width: 100%">
            <el-option
              v-for="opt in chunkingOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        
        <template v-if="uploadShowSizeSettings">
          <el-form-item label="分块大小">
            <el-input-number
              v-model="uploadForm.chunkSize"
              :min="100"
              :max="2000"
              :step="100"
              style="width: 100%"
            />
          </el-form-item>
          
          <el-form-item label="重叠大小">
            <el-input-number
              v-model="uploadForm.chunkOverlap"
              :min="0"
              :max="500"
              :step="10"
              style="width: 100%"
            />
          </el-form-item>
        </template>
        
        <el-form-item v-if="uploadShowSeparatorInput" label="分隔符">
          <el-input
            v-model="uploadForm.separator"
            placeholder="请输入分隔符，如：### 或 ---"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          @click="submitUpload"
        >
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile, UploadInstance, FormInstance, FormRules } from 'element-plus'
import {
  Document,
  Plus,
  Upload,
  More,
  Delete,
} from '@element-plus/icons-vue'
import { useRagStore } from '@/stores/rag'
import type { Document as DocType, ChunkingStrategy } from '@/types/rag'

const store = useRagStore()

const selectedKb = computed(() => store.selectedKb)
const currentDocuments = computed(() => store.currentDocuments)

// 创建文本文档
const showCreateTextDialog = ref(false)
const creating = ref(false)
const textFormRef = ref<FormInstance>()

const textForm = ref({
  title: '',
  content: '',
  chunkingStrategy: 'none' as ChunkingStrategy,
  chunkSize: 500,
  chunkOverlap: 50,
  separator: '',
})

const chunkingOptions = [
  { label: '不分块（完整保存）', value: 'none' },
  { label: '固定大小分块', value: 'fixed_size' },
  { label: '按段落分块', value: 'paragraph' },
  { label: '按分隔符分块', value: 'separator' },
]

const showSeparatorInput = computed(() => textForm.value.chunkingStrategy === 'separator')
const showSizeSettings = computed(() => textForm.value.chunkingStrategy === 'fixed_size')

const textFormRules: FormRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' },
  ],
  content: [
    { required: true, message: '请输入文档内容', trigger: 'blur' },
    { min: 10, message: '内容至少 10 个字符', trigger: 'blur' },
  ],
}

async function submitCreateText() {
  if (!textFormRef.value) return
  
  await textFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    creating.value = true
    try {
      await store.createTextDocument(
        textForm.value.title,
        textForm.value.content,
        textForm.value.chunkingStrategy,
        textForm.value.chunkSize,
        textForm.value.chunkOverlap,
        textForm.value.separator
      )
      ElMessage.success('创建成功')
      showCreateTextDialog.value = false
      // 重置表单
      textForm.value = {
        title: '',
        content: '',
        chunkingStrategy: 'none',
        chunkSize: 500,
        chunkOverlap: 50,
        separator: '',
      }
    } catch (error) {
      ElMessage.error('创建失败')
    } finally {
      creating.value = false
    }
  })
}

// 上传文件
const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)

const uploadForm = ref({
  chunkingStrategy: 'fixed_size' as ChunkingStrategy,
  chunkSize: 500,
  chunkOverlap: 50,
  separator: '',
})

const uploadShowSeparatorInput = computed(() => uploadForm.value.chunkingStrategy === 'separator')
const uploadShowSizeSettings = computed(() => uploadForm.value.chunkingStrategy === 'fixed_size')

function handleFileChange(uploadFile: UploadFile) {
  selectedFile.value = uploadFile.raw || null
}

function handleFileRemove() {
  selectedFile.value = null
}

async function submitUpload() {
  if (!selectedFile.value) return
  
  uploading.value = true
  try {
    await store.uploadDocument(
      selectedFile.value,
      uploadForm.value.chunkingStrategy,
      uploadForm.value.chunkSize,
      uploadForm.value.chunkOverlap,
      uploadForm.value.separator
    )
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    selectedFile.value = null
    uploadRef.value?.clearFiles()
    // 重置表单
    uploadForm.value = {
      chunkingStrategy: 'fixed_size',
      chunkSize: 500,
      chunkOverlap: 50,
      separator: '',
    }
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 删除文档
async function handleCommand(command: string, doc: DocType) {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除文档 "${doc.title}" 吗？`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
      await store.deleteDocument(doc.id)
      ElMessage.success('删除成功')
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败')
      }
    }
  }
}

// 格式化时间
function formatTime(time: string): string {
  const date = new Date(time)
  return date.toLocaleDateString('zh-CN')
}

defineEmits<{
  (e: 'show-selector'): void
}>()
</script>

<style scoped lang="scss">
.doc-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.doc-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-icon {
    font-size: 18px;
    color: #67c23a;
  }
}

.doc-actions {
  display: flex;
  gap: 8px;
}

.doc-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.doc-list {
  flex: 1;
  padding: 12px;
  overflow: hidden;
}

.doc-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  background: #f9fafb;
  transition: all 0.2s;
  
  &:hover {
    background: #f0f2f5;
  }
}

.doc-item-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 6px;
  margin-right: 12px;
  flex-shrink: 0;
  
  .el-icon {
    font-size: 18px;
    color: #409eff;
  }
}

.doc-item-info {
  flex: 1;
  min-width: 0;
}

.doc-item-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-item-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.doc-item-chunks {
  color: #67c23a;
}

.doc-item-time {
  color: #c0c4cc;
}

.empty-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>
