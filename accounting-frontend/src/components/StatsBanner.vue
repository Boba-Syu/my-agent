<template>
  <div class="stats-banner">
    <div class="banner-header">
      <span>{{ title }}</span>
      <span class="banner-period">{{ period }}</span>
    </div>
    <div class="net-amount">
      <span class="net-label">净收入</span>
      <span :class="['net-value', stats.net >= 0 ? 'income' : 'expense']">
        {{ stats.net >= 0 ? '+' : '' }}¥{{ stats.net.toFixed(2) }}
      </span>
    </div>
    <div class="banner-row">
      <div class="stat-item">
        <span class="stat-label">收入</span>
        <span class="stat-value income">+¥{{ stats.income_total.toFixed(2) }}</span>
        <span class="stat-count">{{ stats.income_count }}笔</span>
      </div>
      <div class="divider" />
      <div class="stat-item">
        <span class="stat-label">支出</span>
        <span class="stat-value expense">-¥{{ stats.expense_total.toFixed(2) }}</span>
        <span class="stat-count">{{ stats.expense_count }}笔</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import type { StatsResponse } from '@/types'

const props = defineProps<{
  stats: StatsResponse
  title?: string
  period?: string
}>()

onMounted(() => {
  console.log('[StatsBanner] 收到的 stats:', props.stats)
  console.log('[StatsBanner] title:', props.title)
  console.log('[StatsBanner] period:', props.period)
})
</script>

<style scoped>
.stats-banner {
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 20px;
  color: var(--color-text-primary);
  margin: 16px;
  box-shadow: var(--shadow-card);
}

.banner-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  opacity: 0.95;
}

.banner-period {
  font-size: 12px;
  opacity: 0.75;
  font-weight: 400;
}

.net-amount {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 16px;
}

.net-label {
  font-size: 12px;
  opacity: 0.8;
}

.net-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.net-value.income { color: #666666; }
.net-value.expense { color: #666666; }

.banner-row {
  display: flex;
  align-items: center;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stat-item:last-child {
  align-items: flex-end;
}

.divider {
  width: 1px;
  height: 40px;
  background: #e0e0e0;
  margin: 0 12px;
}

.stat-label {
  font-size: 12px;
  opacity: 0.75;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
}

.stat-value.income { color: #a7f3d0; }
.stat-value.expense { color: #fca5a5; }

.stat-count {
  font-size: 11px;
  opacity: 0.65;
}
</style>
