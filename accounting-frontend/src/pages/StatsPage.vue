<template>
  <div class="page stats-page">
    <!-- 顶部栏 -->
    <header class="page-header">
      <el-button text @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <span class="header-title">数据统计</span>
      <div style="width: 32px"></div>
    </header>

    <div class="scroll-area">
      <!-- 时间范围选择 -->
      <div class="period-selector">
        <el-radio-group v-model="period" size="small" @change="loadData">
          <el-radio-button label="week">本周</el-radio-button>
          <el-radio-button label="month">本月</el-radio-button>
          <el-radio-button label="year">今年</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 概览卡片 -->
      <StatsBanner
        v-if="stats"
        :stats="stats"
        :title="periodTitle"
        :period="periodSubtitle"
      />
      <div v-else-if="loading" class="loading-card">
        <el-skeleton :rows="3" animated />
      </div>

      <!-- 分类统计 -->
      <section class="section">
        <div class="section-title">分类统计</div>
        <div v-if="loading" class="loading-inner">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else class="category-stats">
          <div
            v-for="cat in categoryStats"
            :key="cat.name"
            class="category-item"
          >
            <div class="cat-header">
              <span class="cat-name">{{ cat.name }}</span>
              <span :class="['cat-amount', cat.type]">
                {{ cat.type === 'expense' ? '-' : '+' }}¥{{ cat.amount.toFixed(2) }}
              </span>
            </div>
            <div class="cat-bar">
              <div
                :class="['bar-fill', cat.type]"
                :style="{ width: `${cat.percent}%` }"
              />
            </div>
            <div class="cat-detail">
              <span class="cat-count">{{ cat.count }}笔</span>
              <span class="cat-percent">{{ cat.percent.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 收支趋势图表 -->
      <section class="section">
        <div class="section-title">收支趋势</div>
        <div v-if="loading" class="loading-inner">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else class="chart-container">
          <div ref="lineChartRef" class="chart"></div>
        </div>
        <!-- 收支趋势表格 -->
        <div v-if="!loading && trendData.length > 0" class="table-container">
          <el-table :data="trendData" border stripe style="width: 100%" size="small">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="income" label="收入" width="120">
              <template #default="{ row }">
                <span class="amount income">¥{{ row.income.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="expense" label="支出" width="120">
              <template #default="{ row }">
                <span class="amount expense">¥{{ row.expense.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="net" label="净额" width="120">
              <template #default="{ row }">
                <span :class="['amount', row.net >= 0 ? 'income' : 'expense']">
                  {{ row.net >= 0 ? '+' : '' }}¥{{ row.net.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>

      <!-- 分类支出图表 -->
      <section class="section">
        <div class="section-title">分类支出</div>
        <div v-if="loading" class="loading-inner">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else class="chart-container">
          <div ref="barChartRef" class="chart"></div>
        </div>
        <!-- 分类统计表格 -->
        <div v-if="!loading && categoryStats.length > 0" class="table-container">
          <el-table :data="categoryStats" border stripe style="width: 100%" size="small">
            <el-table-column prop="name" label="分类" width="120" />
            <el-table-column prop="type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.type === 'income' ? 'success' : 'danger'" size="small">
                  {{ row.type === 'income' ? '收入' : '支出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="{ row }">
                <span :class="['amount', row.type]">
                  {{ row.type === 'income' ? '+' : '-' }}¥{{ row.amount.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="笔数" width="80" />
            <el-table-column prop="percent" label="占比" width="100">
              <template #default="{ row }">
                {{ row.percent.toFixed(1) }}%
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>

      <!-- 记录详情表格 -->
      <section class="section">
        <div class="section-title">记录详情</div>
        <div v-if="loading" class="loading-inner">
          <el-skeleton :rows="5" animated />
        </div>
        <el-table v-else :data="records" border stripe style="width: 100%">
          <el-table-column prop="transaction_date" label="日期" width="180" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="amount" label="金额" width="120">
            <template #default="{ row }">
              <span :class="['amount', row.transaction_type]">
                {{ row.transaction_type === 'income' ? '+' : '-' }}¥{{ row.amount.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="备注" />
        </el-table>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import StatsBanner from '@/components/StatsBanner.vue'
import { getStats, getRecords } from '@/api/accounting'
import type { StatsResponse, TransactionRecord } from '@/types'

const router = useRouter()
const period = ref('month')
const stats = ref<StatsResponse | null>(null)
const records = ref<TransactionRecord[]>([])
const loading = ref(true)

const lineChartRef = ref<HTMLElement | null>(null)
const barChartRef = ref<HTMLElement | null>(null)

let lineChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

const now = new Date()

const periodTitle = computed(() => {
  if (period.value === 'week') return '本周'
  if (period.value === 'month') return '本月'
  return '今年'
})

const periodSubtitle = computed(() => {
  if (period.value === 'week') {
    const startOfWeek = new Date(now)
    startOfWeek.setDate(now.getDate() - now.getDay())
    return `${startOfWeek.getMonth() + 1}月${startOfWeek.getDate()}日 - ${now.getMonth() + 1}月${now.getDate()}日`
  }
  if (period.value === 'month') {
    return `${now.getFullYear()}年${now.getMonth() + 1}月`
  }
  return `${now.getFullYear()}年`
})

const categoryStats = computed(() => {
  const map = new Map<string, { name: string; type: string; amount: number; count: number; percent: number }>()

  records.value.forEach(r => {
    const type = r.transaction_type
    const category = r.category || '其他'

    if (!map.has(category)) {
      map.set(category, { name: category, type, amount: 0, count: 0, percent: 0 })
    }

    const item = map.get(category)!
    item.amount += r.amount
    item.count += 1
  })

  const list = Array.from(map.values())

  // 计算总金额和百分比
  const totalAmount = list.reduce((sum, item) => sum + item.amount, 0)
  list.forEach(item => {
    item.percent = totalAmount > 0 ? (item.amount / totalAmount) * 100 : 0
  })

  // 按金额降序排序
  return list.sort((a, b) => b.amount - a.amount)
})

async function loadData() {
  loading.value = true

  try {
    // 计算日期范围
    let startDate = ''
    let endDate = ''

    if (period.value === 'month') {
      startDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      endDate = formatDate(lastDay)
    } else if (period.value === 'year') {
      startDate = `${now.getFullYear()}-01-01`
      endDate = `${now.getFullYear()}-12-31`
    } else {
      // 前12个月
      const end = new Date(now)
      const start = new Date(now)
      start.setMonth(start.getMonth() - 11)
      start.setDate(1)
      startDate = formatDate(start)
      endDate = formatDate(end)
    }

    const [s, r] = await Promise.allSettled([
      getStats(startDate, endDate),
      getRecords({
        start_date: startDate,
        end_date: endDate,
      }),
    ])

    if (s.status === 'fulfilled') {
      stats.value = s.value
    }

    if (r.status === 'fulfilled') {
      records.value = r.value
    }

    // 更新图表
    await nextTick()
    updateCharts()
  } catch (e) {
    console.error('[StatsPage] 加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

function formatDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function updateCharts() {
  // 更新折线图
  if (lineChartRef.value && records.value.length > 0) {
    if (!lineChart) {
      lineChart = echarts.init(lineChartRef.value)
    }

    // 按日期聚合数据
    const dateMap = new Map<string, { income: number; expense: number }>()

    records.value.forEach(r => {
      const date = r.transaction_date.split(' ')[0] // 取日期部分
      if (!dateMap.has(date)) {
        dateMap.set(date, { income: 0, expense: 0 })
      }

      const item = dateMap.get(date)!
      if (r.transaction_type === 'income') {
        item.income += r.amount
      } else {
        item.expense += r.amount
      }
    })

    const dates = Array.from(dateMap.keys()).sort()
    const incomeData = dates.map(d => dateMap.get(d)!.income)
    const expenseData = dates.map(d => dateMap.get(d)!.expense)

    lineChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['收入', '支出'],
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '收入',
          type: 'line',
          smooth: true,
          data: incomeData,
          itemStyle: { color: '#10b981' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.05)' }
            ])
          }
        },
        {
          name: '支出',
          type: 'line',
          smooth: true,
          data: expenseData,
          itemStyle: { color: '#f43f5e' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(244, 63, 94, 0.3)' },
              { offset: 1, color: 'rgba(244, 63, 94, 0.05)' }
            ])
          }
        }
      ]
    })
  }

  // 更新柱状图
  if (barChartRef.value && categoryStats.value.length > 0) {
    if (!barChart) {
      barChart = echarts.init(barChartRef.value)
    }

    const categories = categoryStats.value.map(c => c.name)
    const amounts = categoryStats.value.map(c => c.amount)
    const colors = categoryStats.value.map(c => c.type === 'expense' ? '#f43f5e' : '#10b981')

    barChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '金额',
          type: 'bar',
          data: amounts.map((val, idx) => ({
            value: val,
            itemStyle: { color: colors[idx] }
          })),
          barWidth: '60%'
        }
      ]
    })
  }
}

onMounted(() => {
  loadData()

  // 窗口大小改变时重绘图表
  window.addEventListener('resize', () => {
    lineChart?.resize()
    barChart?.resize()
  })
})
</script>

<style scoped>
.stats-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 8px 4px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 16px;
}

.period-selector {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
}

.loading-card {
  margin: 16px;
  padding: 20px;
  background: #fff;
  border-radius: var(--radius-card);
}

.section {
  margin: 16px;
  background: #fff;
  border-radius: var(--radius-card);
  padding: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.loading-inner {
  padding: 20px 0;
}

.category-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.category-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cat-name {
  font-size: 13px;
  color: var(--color-text-primary);
}

.cat-amount {
  font-size: 15px;
  font-weight: 600;
}

.cat-amount.income { color: #10b981; }
.cat-amount.expense { color: #f43f5e; }

.cat-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.bar-fill.income { background: #10b981; }
.bar-fill.expense { background: #10b981; }

.cat-detail {
  display: flex;
  justify-content: space-between;
}

.cat-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.cat-percent {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.chart-container {
  padding: 16px 0;
}

.chart {
  width: 100%;
  height: 300px;
}
</style>
