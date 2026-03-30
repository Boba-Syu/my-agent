<template>
  <div class="record-item">
    <div class="record-icon">
      <el-icon :size="20" :color="iconColor">
        <component :is="categoryIcon" />
      </el-icon>
    </div>
    <div class="record-main">
      <div class="record-top">
        <span class="record-category">{{ record.category }}</span>
        <span :class="['record-amount', record.transaction_type]">
          {{ record.transaction_type === 'income' ? '+' : '-' }}¥{{ record.amount.toFixed(2) }}
        </span>
      </div>
      <div class="record-bottom">
        <span class="record-note">{{ record.note || '无备注' }}</span>
        <span class="record-date">{{ record.transaction_date }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TransactionRecord } from '@/types'
import type { Component } from 'vue'
import {
  Food, ShoppingBag, Reading, Van, Basketball, FirstAidKit, Money, Present, TrendCharts, Box
} from '@element-plus/icons-vue'

const props = defineProps<{ record: TransactionRecord }>()

// 分类图标映射 - 简约灰白风格
const CATEGORY_ICONS: Record<string, Component> = {
  '三餐': Food,
  '日用品': ShoppingBag,
  '学习': Reading,
  '交通': Van,
  '娱乐': Basketball,
  '医疗': FirstAidKit,
  '工资': Money,
  '奖金': Present,
  '理财': TrendCharts,
  '其他': Box,
}

const categoryIcon = computed(() => CATEGORY_ICONS[props.record.category] ?? Box)
const iconColor = computed(() => props.record.transaction_type === 'income' ? '#81c784' : '#9ca3af')
</script>

<style scoped>
.record-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}
.record-item:last-child { border-bottom: none; }

.record-icon {
  width: 40px;
  height: 40px;
  background: #f5f7ff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.record-main { flex: 1; min-width: 0; }

.record-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}

.record-category {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.record-amount {
  font-size: 15px;
  font-weight: 600;
}
.record-amount.income { color: var(--color-income); }
.record-amount.expense { color: var(--color-expense); }

.record-bottom {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-muted);
}

.record-note {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}
</style>
