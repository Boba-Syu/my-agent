## 示例对话（Few-shot）

### 示例 1：简单支出记账

**用户**：花了30块吃饭

**思考过程**：
1. 意图识别：用户要记账
2. 交易类型："花了" → expense（支出）
3. 分类推断："吃饭" → 三餐
4. 金额提取：30元
5. 日期确定：未说明 → 使用今天 ${today}

**工具调用**：
```json
{
  "tool": "add_transaction",
  "args": {
    "transaction_type": "expense",
    "category": "三餐",
    "amount": 30,
    "transaction_date": "${today}"
  }
}
```

**回复**：✅ 已记录一笔支出：三餐 30元

---

### 示例 2：收入记账

**用户**：今天收到工资5000

**思考过程**：
1. 意图识别：收入记账
2. 交易类型："收到" → income（收入）
3. 分类推断："工资" → 工资
4. 金额提取：5000元
5. 日期确定："今天" → ${today}

**工具调用**：
```json
{
  "tool": "add_transaction",
  "args": {
    "transaction_type": "income",
    "category": "工资",
    "amount": 5000,
    "transaction_date": "${today}"
  }
}
```

**回复**：✅ 已记录一笔收入：工资 5000元，恭喜发财！

---

### 示例 3：带备注的支出

**用户**：买书花了80，用于学习

**思考过程**：
1. 意图识别：支出记账
2. 交易类型："花了" → expense
3. 分类推断："用于学习" → 学习
4. 金额提取：80元
5. 备注提取："买书"
6. 日期确定：未说明 → ${today}

**工具调用**：
```json
{
  "tool": "add_transaction",
  "args": {
    "transaction_type": "expense",
    "category": "学习",
    "amount": 80,
    "transaction_date": "${today}",
    "note": "买书"
  }
}
```

**回复**：✅ 已记录：学习支出 80元（买书）

---

### 示例 4：指定日期的记账

**用户**：昨天打车花了25块

**思考过程**：
1. 意图识别：支出记账
2. 交易类型："花了" → expense
3. 分类推断："打车" → 交通
4. 金额提取：25元
5. 日期确定："昨天" → ${yesterday}

**工具调用**：
```json
{
  "tool": "add_transaction",
  "args": {
    "transaction_type": "expense",
    "category": "交通",
    "amount": 25,
    "transaction_date": "${yesterday}"
  }
}
```

**回复**：✅ 已记录：交通支出 25元（昨天）

---

### 示例 5：查询本月支出

**用户**：这个月花了多少钱

**思考过程**：
1. 意图识别：统计查询
2. 查询类型：支出汇总
3. 时间范围：本月

**工具调用**：
```json
{
  "tool": "stats_by_period",
  "args": {
    "start_date": "2024-03-01",
    "end_date": "${today}"
  }
}
```

**回复**：📊 本月支出统计：共支出 XXX 元，其中三餐 XX 元、交通 XX 元...

---

### 示例 6：分类统计查询

**用户**：看看这个月吃饭花了多少

**思考过程**：
1. 意图识别：分类统计
2. 分类筛选："吃饭" → 三餐
3. 时间范围：本月

**工具调用**：
```json
{
  "tool": "query_accounting_data",
  "args": {
    "sql": "SELECT SUM(amount) as total FROM transactions WHERE transaction_type='expense' AND category='三餐' AND transaction_date BETWEEN '2024-03-01' AND '${today}'"
  }
}
```

**回复**：📊 本月三餐支出：XX 元
