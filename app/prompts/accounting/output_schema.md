## 输出格式要求

所有回复必须严格遵循以下 JSON 结构：

```json
{
  "thinking": "你的思考过程（可选，用于调试）",
  "response": "给用户的中文回复（必填，支持 Markdown）",
  "data": {
    "transaction_id": "记录ID",
    "amount": 100,
    "category": "分类",
    "date": "2024-01-01"
  },
  "suggested_actions": [
    "建议用户的下一步操作1",
    "建议用户的下一步操作2"
  ],
  "requires_follow_up": false
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| thinking | string | 否 | 内部推理过程，用户看不到 |
| response | string | 是 | 展示给用户的消息 |
| data | object | 否 | 结构化数据，前端可解析展示 |
| suggested_actions | array | 否 | 建议的下一步操作（最多3个） |
| requires_follow_up | boolean | 否 | 是否需要用户补充信息 |

### 输出示例

**记账成功时**：
```json
{
  "thinking": "用户要记账，类型为支出，分类三餐，金额50元",
  "response": "✅ 已记录一笔支出：三餐 50元",
  "data": {
    "transaction_type": "expense",
    "category": "三餐",
    "amount": 50,
    "date": "${today}"
  },
  "suggested_actions": ["继续记账", "查看今日收支"]
}
```

**查询结果时**：
```json
{
  "thinking": "用户查询本月支出，通过stats_by_period工具获取数据",
  "response": "📊 本月支出统计\n\n总支出：1,250元\n- 三餐：500元\n- 交通：300元\n- 日用品：200元\n- 其他：250元",
  "data": {
    "total_expense": 1250,
    "breakdown": {
      "三餐": 500,
      "交通": 300,
      "日用品": 200,
      "其他": 250
    }
  }
}
```

**信息不足时**：
```json
{
  "thinking": "用户说要记账，但没有提供金额",
  "response": "请问这笔记录的金额是多少呢？",
  "requires_follow_up": true
}
```
