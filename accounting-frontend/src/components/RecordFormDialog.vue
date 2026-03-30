<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑记录' : '新增记录'"
    width="360px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="70px"
      label-position="left"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="类型" prop="transaction_type">
        <el-radio-group v-model="form.transaction_type" @change="onTypeChange">
          <el-radio-button value="expense">支出</el-radio-button>
          <el-radio-button value="income">收入</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="分类" prop="category">
        <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
          <el-option
            v-for="c in currentCategories"
            :key="c"
            :label="c"
            :value="c"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="金额" prop="amount">
        <el-input-number
          v-model="form.amount"
          :min="0.01"
          :precision="2"
          :step="1"
          placeholder="请输入金额"
          controls-position="right"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="日期" prop="transaction_date">
        <el-date-picker
          v-model="form.transaction_date"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.note"
          type="textarea"
          :rows="2"
          placeholder="可选备注"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '添加' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { TransactionRecord, TransactionType, CategoriesResponse } from '@/types'
import { createRecord, updateRecord, getCategories } from '@/api/accounting'

const props = defineProps<{
  visible: boolean
  editRecord?: TransactionRecord | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'saved'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const categories = ref<CategoriesResponse>({ expense_categories: [], income_categories: [] })

const isEdit = computed(() => !!props.editRecord)

const form = reactive({
  transaction_type: 'expense' as TransactionType,
  category: '',
  amount: 0,
  note: '',
  transaction_date: '',
})

const rules: FormRules = {
  transaction_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  transaction_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

const currentCategories = computed(() => {
  if (form.transaction_type === 'income') return categories.value.income_categories
  return categories.value.expense_categories
})

function onTypeChange() {
  form.category = ''
}

function resetForm() {
  form.transaction_type = 'expense'
  form.category = ''
  form.amount = 0
  form.note = ''
  form.transaction_date = new Date().toISOString().slice(0, 10)
}

function fillForm(record: TransactionRecord) {
  form.transaction_type = record.transaction_type
  form.category = record.category
  form.amount = record.amount
  form.note = record.note || ''
  form.transaction_date = record.transaction_date
}

watch(() => props.visible, async (val) => {
  if (val) {
    const [catRes] = await Promise.allSettled([getCategories()])
    if (catRes.status === 'fulfilled') categories.value = catRes.value
    if (props.editRecord) {
      fillForm(props.editRecord)
    } else {
      resetForm()
    }
  }
})

function handleClose() {
  emit('update:visible', false)
  formRef.value?.resetFields()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && props.editRecord) {
      const res = await updateRecord(props.editRecord.id, {
        transaction_type: form.transaction_type,
        category: form.category,
        amount: form.amount,
        note: form.note,
        transaction_date: form.transaction_date,
      })
      if (!res.success) throw new Error(res.message)
    } else {
      const res = await createRecord({
        transaction_type: form.transaction_type,
        category: form.category,
        amount: form.amount,
        note: form.note,
        transaction_date: form.transaction_date,
      })
      if (!res.success) throw new Error(res.message)
    }
    handleClose()
    emit('saved')
  } catch (e: any) {
    console.error('保存记录失败:', e)
  } finally {
    submitting.value = false
  }
}
</script>
