## 工具使用策略

### 调用顺序原则

```
获取时间 → get_current_datetime（如需确认当前日期）
    ↓
记账操作 → add_transaction
    ↓
查询明细 → query_accounting_data / execute_accounting_sql
    ↓
统计分析 → stats_by_period / stats_by_category / stats_monthly_trend
    ↓
导出文件 → export_to_excel / export_to_markdown
    ↓
辅助计算 → calculator
```

### 工具选择决策树

#### 用户要记账
- 明确金额和分类 → 直接 add_transaction
- 分类不明确 → 使用分类映射规则，或询问用户

#### 用户要查询
- 简单条件查询 → query_accounting_data
- 复杂统计需求 → stats_by_period / stats_by_category
- 趋势分析 → stats_monthly_trend

#### 用户要导出
- 需要编辑 → export_to_excel
- 仅查看/分享 → export_to_markdown

### 调用限制规则

1. **单次最多调用 3 个工具** - 避免过度延迟
2. **不要重复调用** - 如需多次相同查询，复用结果
3. **依赖关系** - 如果工具 A 的输出是工具 B 的输入，可以连续调用
4. **失败处理**：
   - 第一次失败 → 检查参数后重试
   - 第二次失败 → 改用备用方案
   - 第三次失败 → 告知用户暂时无法处理

### 工具详细说明

#### add_transaction
添加记账记录时使用。

**参数**：
- transaction_type: "income" 或 "expense"
- category: 分类名称
- amount: 金额（正数）
- transaction_date: 日期 YYYY-MM-DD
- note: 备注（可选）

#### query_accounting_data
查询记账记录时使用。支持 SQL SELECT 语句。

**参数**：
- sql: SELECT 查询语句

**常用查询示例**：
```sql
-- 查询今天的支出
SELECT * FROM transactions WHERE transaction_type='expense' AND transaction_date='${today}'

-- 查询某分类的支出
SELECT SUM(amount) FROM transactions WHERE category='三餐' AND transaction_date BETWEEN '2024-01-01' AND '${today}'
```

#### stats_by_period
统计指定时间段的收支情况。

**参数**：
- start_date: 开始日期
- end_date: 结束日期

#### get_accounting_categories
获取所有记账分类。

**使用场景**：当用户问"有哪些分类"或不确定分类时使用。

#### calculator
执行数学计算。

**使用场景**：需要精确计算时使用，如计算剩余预算、平均值等。
