<template>
  <div class="page records-page">
    <!-- 顶部栏 -->
    <header class="page-header">
      <div class="header-left">
        <el-button text circle @click="showSidebar = true">
          <el-icon><Menu /></el-icon>
        </el-button>
        <span class="header-title">记账记录</span>
      </div>
      <div class="header-actions">
        <el-button text circle @click="refreshing ? undefined : refresh()" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button text circle @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
    </header>

    <!-- 筛选区 -->
    <div class="filter-bar">
      <div class="filter-box">
        <!-- 日期范围 -->
        <div class="date-filter">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
            size="small"
            style="width: 100%"
            @change="onDateChange"
          />
        </div>

        <!-- 类型筛选 -->
        <div class="filter-row">
          <span
            v-for="t in typeFilters"
            :key="t.value"
            :class="['filter-chip', { active: selectedType === t.value }]"
            @click="selectedType = t.value; fetchRecords()"
          >{{ t.label }}</span>
        </div>

        <!-- 分类筛选 -->
        <div class="filter-row" v-if="categories.length">
          <span
            :class="['filter-chip', { active: selectedCategory === '' }]"
            @click="selectedCategory = ''; fetchRecords()"
          >全部</span>
          <span
            v-for="c in categories"
            :key="c"
            :class="['filter-chip', { active: selectedCategory === c }]"
            @click="selectedCategory = c; fetchRecords()"
          >{{ c }}</span>
        </div>
      </div>
    </div>

    <!-- 汇总行 -->
    <div class="summary-bar" v-if="records.length">
      <span class="sum-item">共 <b>{{ records.length }}</b> 笔</span>
      <span class="sum-item income">收入 <b>+¥{{ incomeSum.toFixed(2) }}</b></span>
      <span class="sum-item expense">支出 <b>-¥{{ expenseSum.toFixed(2) }}</b></span>
    </div>

    <!-- 列表 -->
    <div class="scroll-area">
      <div v-if="loading" class="loading-wrap">
        <el-skeleton :rows="6" animated style="padding: 16px;" />
      </div>
      <template v-else-if="records.length">
        <!-- 按日期分组 -->
        <template v-for="group in groupedRecords" :key="group.date">
          <div class="date-label">{{ group.date }}</div>
          <div class="card">
            <div
              v-for="r in group.items"
              :key="r.id"
              class="record-row"
              @click="openEditDialog(r)"
            >
              <RecordItem :record="r" />
              <el-icon class="edit-hint"><Edit /></el-icon>
            </div>
          </div>
        </template>

        <!-- 加载更多 -->
        <div class="load-more" v-if="hasMore">
          <el-button text @click="loadMore" :loading="moreLoading">加载更多</el-button>
        </div>
      </template>
      <div v-else class="empty-tip">
        <el-icon class="empty-icon"><Document /></el-icon>
        <div>暂无记录</div>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <RecordFormDialog
      v-model:visible="dialogVisible"
      :edit-record="editingRecord"
      @saved="onRecordSaved"
    />

    <!-- 侧边栏 -->
    <el-drawer
      v-model="showSidebar"
      title="菜单"
      size="70%"
      :with-header="false"
    >
      <div class="sidebar-content">
        <div class="sidebar-header">
          <span class="sidebar-title">记账助手</span>
        </div>
        <div class="sidebar-menu">
          <div class="menu-item" @click="router.push('/'); showSidebar = false">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </div>
          <div class="menu-item active">
            <el-icon><Document /></el-icon>
            <span>记录</span>
          </div>
          <div class="menu-item" @click="router.push('/stats'); showSidebar = false">
            <el-icon><TrendCharts /></el-icon>
            <span>统计</span>
          </div>
          <div class="menu-item" @click="router.push('/chat'); showSidebar = false">
            <el-icon><ChatDotRound /></el-icon>
            <span>AI助手</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Refresh, Edit, Menu, HomeFilled, Document, TrendCharts, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import RecordItem from '@/components/RecordItem.vue'
import RecordFormDialog from '@/components/RecordFormDialog.vue'
import { getRecords, getCategories, deleteRecord } from '@/api/accounting'
import type { TransactionRecord, TransactionType } from '@/types'

const router = useRouter()
const records = ref<TransactionRecord[]>([])
const loading = ref(true)
const moreLoading = ref(false)
const hasMore = ref(false)
const refreshing = ref(false)
const PAGE_SIZE = 30

const selectedType = ref<TransactionType | ''>('')
const selectedCategory = ref('')
const categories = ref<string[]>([])
const dateRange = ref<[string, string] | null>(null)

const dialogVisible = ref(false)
const editingRecord = ref<TransactionRecord | null>(null)
const showSidebar = ref(false)

const typeFilters = [
  { label: '全部', value: '' },
  { label: '支出', value: 'expense' },
  { label: '收入', value: 'income' },
]

const dateShortcuts = [
  { text: '本月', value: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth(), 1), now] } },
  { text: '上月', value: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth() - 1, 1), new Date(now.getFullYear(), now.getMonth(), 0)] } },
  { text: '近3月', value: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth() - 2, 1), now] } },
  { text: '今年', value: () => { const now = new Date(); return [new Date(now.getFullYear(), 0, 1), now] } },
]

const incomeSum = computed(() =>
  records.value.filter(r => r.transaction_type === 'income').reduce((s, r) => s + r.amount, 0),
)
const expenseSum = computed(() =>
  records.value.filter(r => r.transaction_type === 'expense').reduce((s, r) => s + r.amount, 0),
)

const groupedRecords = computed(() => {
  const map = new Map<string, TransactionRecord[]>()
  for (const r of records.value) {
    const list = map.get(r.transaction_date) ?? []
    list.push(r)
    map.set(r.transaction_date, list)
  }
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, items]) => ({ date, items }))
})

function onDateChange() {
  fetchRecords()
}

async function fetchRecords(reset = true) {
  if (reset) { loading.value = true; records.value = [] }
  const data = await getRecords({
    transaction_type: selectedType.value || undefined,
    category: selectedCategory.value || undefined,
    start_date: dateRange.value?.[0] || undefined,
    end_date: dateRange.value?.[1] || undefined,
    limit: PAGE_SIZE,
  })
  records.value = data
  hasMore.value = data.length === PAGE_SIZE
  loading.value = false
}

async function loadMore() {
  moreLoading.value = true
  const data = await getRecords({
    transaction_type: selectedType.value || undefined,
    category: selectedCategory.value || undefined,
    start_date: dateRange.value?.[0] || undefined,
    end_date: dateRange.value?.[1] || undefined,
    limit: records.value.length + PAGE_SIZE,
  })
  records.value = data
  hasMore.value = data.length === records.value.length + PAGE_SIZE
  moreLoading.value = false
}

async function refresh() {
  refreshing.value = true
  await fetchRecords()
  refreshing.value = false
}

function openCreateDialog() {
  editingRecord.value = null
  dialogVisible.value = true
}

function openEditDialog(record: TransactionRecord) {
  editingRecord.value = record
  dialogVisible.value = true
}

async function handleDelete(record: TransactionRecord) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这笔${record.transaction_type === 'income' ? '收入' : '支出'}记录吗？\n${record.category} ¥${record.amount.toFixed(2)}`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await deleteRecord(record.id)
    if (res.success) {
      fetchRecords()
    }
  } catch {
    // 用户取消，不做处理
  }
}

function onRecordSaved() {
  fetchRecords()
}

onMounted(async () => {
  const [_, cats] = await Promise.allSettled([fetchRecords(), getCategories()])
  if (cats.status === 'fulfilled') {
    categories.value = [...cats.value.expense_categories, ...cats.value.income_categories]
  }
  loading.value = false
})
</script>

<style scoped>
.records-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 500;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.header-actions :deep(.el-button) {
  color: #6b7280;
}

.header-actions :deep(.el-button:hover) {
  color: #1f2937;
  background: #f3f4f6;
}

.filter-bar {
  background: #fff;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.filter-box {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.date-filter {
  margin-bottom: 0;
}

.date-filter :deep(.el-input__wrapper) {
  box-shadow: none;
  background: #f3f4f6;
  border-radius: 8px;
}

.filter-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
}
.filter-row::-webkit-scrollbar { display: none; }

.filter-chip {
  white-space: nowrap;
  border-radius: 16px;
  padding: 6px 14px;
  font-size: 13px;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.filter-chip.active {
  background: #1f2937;
  color: #fff;
}

.summary-bar {
  display: flex;
  gap: 16px;
  padding: 10px 16px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  flex-shrink: 0;
}

.sum-item { color: #6b7280; }
.sum-item b { font-weight: 500; }
.sum-item.income b { color: #059669; }
.sum-item.expense b { color: #dc2626; }

.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px 16px;
  background: #fff;
}

.loading-wrap { margin: 0; }

.date-label {
  font-size: 12px;
  color: #9ca3af;
  margin: 16px 0 8px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.date-label:first-child { margin-top: 0; }

.card {
  background: #fff;
  border-radius: 12px;
  padding: 0;
  border: 1px solid #f0f0f0;
  overflow: hidden;
}

.record-row {
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
}
.record-row:last-child {
  border-bottom: none;
}
.record-row:active {
  background: #f9fafb;
}
.record-row .edit-hint {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #d1d5db;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}
.record-row:hover .edit-hint {
  opacity: 1;
}

.load-more {
  text-align: center;
  padding: 16px 0;
}

.load-more :deep(.el-button) {
  color: #6b7280;
}

.empty-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
  font-size: 14px;
  color: #9ca3af;
}
.empty-icon {
  font-size: 48px;
  color: #d1d5db;
}

/* 侧边栏样式 */
.sidebar-content {
  padding: 16px 0;
}

.sidebar-header {
  padding: 16px 20px 24px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.sidebar-menu {
  padding: 8px 12px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: #6b7280;
  margin-bottom: 4px;
}

.menu-item:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.menu-item.active {
  background: #1f2937;
  color: #fff;
}

.menu-item .el-icon {
  font-size: 20px;
}

.menu-item span {
  font-size: 15px;
  font-weight: 500;
}
</style>
