<template>
  <div class="page home-page">
    <div class="scroll-area">
      <!-- 时间范围选择 -->
      <div class="period-selector">
        <el-radio-group v-model="period" size="small" @change="loadData">
          <el-radio-button label="month">当月</el-radio-button>
          <el-radio-button label="year">当年</el-radio-button>
          <el-radio-button label="last12">前12个月</el-radio-button>
        </el-radio-group>
        <el-button
          text
          circle
          size="small"
          :loading="refreshing"
          @click="refresh"
          class="refresh-btn"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <!-- 收支概览卡片 -->
      <StatsBanner
        v-if="stats"
        :stats="stats"
        :title="periodTitle"
        :period="periodSubtitle"
      />
      <div v-else-if="statsLoading" class="loading-card">
        <el-skeleton :rows="3" animated />
      </div>

      <!-- 收支分布（一行两列） -->
      <section class="section">
        <div class="section-title">收支分布</div>
        <div class="pie-row">
          <div class="pie-item">
            <div class="chart-label">收入</div>
            <div v-if="loading" class="loading-inner">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else class="chart-container">
              <div ref="incomePieRef" class="chart" style="min-height: 200px;"></div>
              <div v-if="incomeCategories.length === 0" class="empty-chart">暂无收入记录</div>
            </div>
          </div>
          <div class="pie-item">
            <div class="chart-label">支出</div>
            <div v-if="loading" class="loading-inner">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else class="chart-container">
              <div ref="expensePieRef" class="chart" style="min-height: 200px;"></div>
              <div v-if="expenseCategories.length === 0" class="empty-chart">暂无支出记录</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 收支趋势柱状图 -->
      <section class="section">
        <div class="section-title">收支趋势</div>
        <div v-if="loading" class="loading-inner">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else class="chart-container">
          <div ref="lineChartRef" class="chart" style="min-height: 280px;"></div>
          <div v-if="trendData.length === 0" class="empty-chart">暂无记录</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen, Refresh } from '@element-plus/icons-vue'
import StatsBanner from '@/components/StatsBanner.vue'
import { getStats, getRecords } from '@/api/accounting'
import type { StatsResponse, TransactionRecord } from '@/types'
import * as echarts from 'echarts'

const router = useRouter()
const period = ref('month')
const stats = ref<StatsResponse | null>(null)
const records = ref<TransactionRecord[]>([])
const statsLoading = ref(true)
const loading = ref(true)
const refreshing = ref(false)

const incomePieRef = ref<HTMLElement | null>(null)
const expensePieRef = ref<HTMLElement | null>(null)
const lineChartRef = ref<HTMLElement | null>(null)

let incomePieChart: echarts.ECharts | null = null
let expensePieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

const now = new Date()

const periodTitle = computed(() => {
  if (period.value === 'month') return '本月'
  if (period.value === 'year') return '今年'
  return '前12个月'
})

const periodSubtitle = computed(() => {
  if (period.value === 'month') {
    return `${now.getFullYear()}年${now.getMonth() + 1}月`
  }
  if (period.value === 'year') {
    return `${now.getFullYear()}年`
  }
  const endDate = now
  const startDate = new Date(now)
  startDate.setMonth(startDate.getMonth() - 11)
  startDate.setDate(1)
  return `${startDate.getFullYear()}年${startDate.getMonth() + 1}月 - ${endDate.getFullYear()}年${endDate.getMonth() + 1}月`
})

// 收入分类聚合
const incomeCategories = computed(() => {
  const map = new Map<string, { name: string; amount: number; count: number }>()
  records.value.forEach(r => {
    if (r.transaction_type !== 'income') return
    const category = r.category || '其他'
    if (!map.has(category)) {
      map.set(category, { name: category, amount: 0, count: 0 })
    }
    const item = map.get(category)!
    item.amount += r.amount
    item.count += 1
  })
  return Array.from(map.values()).sort((a, b) => b.amount - a.amount)
})

// 支出分类聚合
const expenseCategories = computed(() => {
  const map = new Map<string, { name: string; amount: number; count: number }>()
  records.value.forEach(r => {
    if (r.transaction_type !== 'expense') return
    const category = r.category || '其他'
    if (!map.has(category)) {
      map.set(category, { name: category, amount: 0, count: 0 })
    }
    const item = map.get(category)!
    item.amount += r.amount
    item.count += 1
  })
  return Array.from(map.values()).sort((a, b) => b.amount - a.amount)
})

// 收支趋势数据（当年和前12个月需要按月聚合）
const trendData = computed(() => {
  const dateMap = new Map<string, { income: number; expense: number }>()

  records.value.forEach(r => {
    const date = r.transaction_date.split(' ')[0]
    // 当月按天聚合，当年/前12个月按月聚合
    const key = period.value === 'month' ? date : date.substring(0, 7) // YYYY-MM
    if (!dateMap.has(key)) {
      dateMap.set(key, { income: 0, expense: 0 })
    }
    const item = dateMap.get(key)!
    if (r.transaction_type === 'income') {
      item.income += r.amount
    } else {
      item.expense += r.amount
    }
  })

  const dates = Array.from(dateMap.keys()).sort()
  return dates.map(d => {
    const data = dateMap.get(d)!
    return {
      date: d,
      income: data.income,
      expense: data.expense
    }
  })
})





async function loadData() {
  loading.value = true
  statsLoading.value = true

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

    console.log('[HomePage] 请求数据:', { period: period.value, startDate, endDate })

    const [s, r] = await Promise.allSettled([
      getStats(startDate, endDate),
      getRecords({ start_date: startDate, end_date: endDate, limit: 1000 })
    ])

    if (s.status === 'fulfilled') {
      stats.value = s.value
      console.log('[HomePage] 统计数据:', s.value)
    } else {
      console.error('[HomePage] 统计请求失败:', s.reason)
    }

    if (r.status === 'fulfilled') {
      records.value = r.value
      console.log('[HomePage] 记录数据条数:', r.value.length)
      console.log('[HomePage] 记录数据详情:', r.value.slice(0, 3))
    } else {
      console.error('[HomePage] 记录请求失败:', r.reason)
    }

  } catch (e) {
    console.error('[HomePage] 加载数据失败:', e)
  } finally {
    loading.value = false
    statsLoading.value = false
    // DOM 更新后初始化并更新图表
    await nextTick()
    // 延迟执行确保DOM完全渲染
    setTimeout(() => {
      // 销毁旧图表实例，强制重新创建
      if (incomePieChart) {
        incomePieChart.dispose()
        incomePieChart = null
      }
      if (expensePieChart) {
        expensePieChart.dispose()
        expensePieChart = null
      }
      if (lineChart) {
        lineChart.dispose()
        lineChart = null
      }
      initCharts()
      updateCharts()
    }, 50)
  }
}

function formatDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

async function refresh() {
  refreshing.value = true
  await loadData()
  refreshing.value = false
}

function updateCharts() {
  console.log('[HomePage] updateCharts 开始')
  console.log('[HomePage] records.value 长度:', records.value.length)
  console.log('[HomePage] incomeCategories:', incomeCategories.value)
  console.log('[HomePage] expenseCategories:', expenseCategories.value)
  console.log('[HomePage] trendData:', trendData.value)

  // 确保图表已初始化
  if (!incomePieChart || !expensePieChart || !lineChart) {
    console.log('[HomePage] 图表未初始化，重新初始化')
    initCharts()
  }

  // 深色高区分度配色 - 收入偏深绿色系，支出偏深橙色系
  const incomeColors = ['#388e3c', '#43a047', '#2e7d32', '#66bb6a', '#1b5e20', '#4caf50']
  const expenseColors = ['#e65100', '#ef6c00', '#f57c00', '#fb8c00', '#ff9800', '#f9a825']

  // 更新收入饼图
  if (incomePieChart) {
    const data = incomeCategories.value.map(c => ({
      name: c.name,
      value: c.amount
    }))
    console.log('[HomePage] 收入饼图数据:', data)
    incomePieChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c}'
      },
      legend: { show: false },
      series: [
        {
          name: '收入',
          type: 'pie',
          radius: ['50%', '75%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          color: incomeColors,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2
          },
          label: { show: false },
          data: data.length > 0 ? data : [{ name: '无数据', value: 0, itemStyle: { color: '#e5e7eb' } }]
        }
      ]
    }, true)
    incomePieChart.resize()
  }

  // 更新支出饼图
  if (expensePieChart) {
    const data = expenseCategories.value.map(c => ({
      name: c.name,
      value: c.amount
    }))
    console.log('[HomePage] 支出饼图数据:', data)
    expensePieChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c}'
      },
      legend: { show: false },
      series: [
        {
          name: '支出',
          type: 'pie',
          radius: ['50%', '75%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          color: expenseColors,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2
          },
          label: { show: false },
          data: data.length > 0 ? data : [{ name: '无数据', value: 0, itemStyle: { color: '#e5e7eb' } }]
        }
      ]
    }, true)
    expensePieChart.resize()
  }

  // 更新柱状图（收支趋势）- 浅色高区分度
  if (lineChart) {
    const data = trendData.value
    // 当月显示"DD日"，当年/前12个月显示"MM月"
    const dates = data.map(d => {
      if (period.value === 'month') {
        // 当月数据格式为 YYYY-MM-DD
        return d.date.substring(8) + '日' // DD日
      } else {
        // 当年/前12个月数据格式为 YYYY-MM
        const month = d.date.substring(5, 7)
        return parseInt(month) + '月' // MM月
      }
    })
    const incomeData = data.map(d => d.income)
    const expenseData = data.map(d => d.expense)
    const hasData = data.length > 0

    lineChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const date = params[0]?.axisValue || ''
          const income = params.find(p => p.seriesName === '收入')?.value || 0
          const expense = params.find(p => p.seriesName === '支出')?.value || 0
          return `${date}<br/>收入: ¥${income.toFixed(2)}<br/>支出: ¥${expense.toFixed(2)}`
        }
      },
      legend: { show: false },
      grid: {
        left: '10%',
        right: '4%',
        bottom: '8%',
        top: '5%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: true,
        data: hasData ? dates : ['无数据'],
        axisLine: { show: true, lineStyle: { color: '#e5e7eb' } },
        axisTick: { show: false },
        axisLabel: { fontSize: 10, color: '#6b7280' }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f3f4f6' } },
        axisLabel: { fontSize: 10, color: '#6b7280' }
      },
      series: [
        {
          name: '收入',
          type: 'bar',
          barWidth: '40%',
          data: hasData ? incomeData : [],
          itemStyle: { color: '#2e7d32', borderRadius: [2, 2, 0, 0] }
        },
        {
          name: '支出',
          type: 'bar',
          barWidth: '40%',
          data: hasData ? expenseData : [],
          itemStyle: { color: '#e65100', borderRadius: [2, 2, 0, 0] }
        }
      ]
    }, true)
    lineChart.resize()
  }
}

onMounted(() => {
  // 直接加载数据，图表会在数据加载完成后初始化
  loadData()

  // 窗口大小改变时重绘图表
  window.addEventListener('resize', () => {
    incomePieChart?.resize()
    expensePieChart?.resize()
    lineChart?.resize()
  })
})

function initCharts() {
  console.log('[HomePage] initCharts 开始')
  console.log('[HomePage] incomePieRef:', incomePieRef.value)
  console.log('[HomePage] expensePieRef:', expensePieRef.value)
  console.log('[HomePage] lineChartRef:', lineChartRef.value)

  if (incomePieRef.value && !incomePieChart) {
    incomePieChart = echarts.init(incomePieRef.value)
    console.log('[HomePage] 收入饼图已初始化')
  }
  if (expensePieRef.value && !expensePieChart) {
    expensePieChart = echarts.init(expensePieRef.value)
    console.log('[HomePage] 支出饼图已初始化')
  }
  if (lineChartRef.value && !lineChart) {
    lineChart = echarts.init(lineChartRef.value)
    console.log('[HomePage] 折线图已初始化')
  }
}
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.scroll-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 24px;
}

.period-selector {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 10;
}

.refresh-btn {
  color: #6b7280;
  margin-left: 12px;
}

.refresh-btn:hover {
  color: #1f2937;
  background: #f3f4f6;
}

.period-selector :deep(.el-radio-button__inner) {
  background: #f3f4f6;
  border-color: #f3f4f6;
  color: #6b7280;
}

.period-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #1f2937;
  border-color: #1f2937;
  color: #fff;
  box-shadow: none;
}

.loading-card {
  margin: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
}

.section {
  margin: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #f0f0f0;
}

.section-title {
  font-size: 15px;
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 16px;
}

.loading-inner {
  padding: 20px 0;
}

.chart-container {
  padding: 8px 0;
  position: relative;
}

.chart {
  width: 100%;
  height: 200px;
}

.chart-container .chart {
  min-height: 200px;
}

.pie-row {
  display: flex;
  gap: 16px;
}

.pie-item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.chart-label {
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 12px;
}

.empty-chart {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #9ca3af;
  font-size: 13px;
}



/* 响应式：适配主流手机分辨率 */
@media (max-width: 375px) {
  .section {
    margin: 12px;
    padding: 16px;
  }
  .pie-row {
    flex-direction: column;
    gap: 20px;
  }
}

@media (max-width: 414px) {
  .section {
    margin: 14px;
    padding: 18px;
  }
  .chart {
    min-height: 180px !important;
  }
}

@media (min-width: 415px) {
  .mobile-shell {
    max-width: 480px;
  }
}
</style>
