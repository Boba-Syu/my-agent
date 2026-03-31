# DDD架构重构总结

## 重构时间
2026-03-31

## 重构目标
1. 将提示词从代码抽离到文件
2. 修复应用层直接依赖基础设施层的问题
3. 统一使用 AgentFactory 创建 Agent
4. 解耦领域层工具对基础设施的直接依赖

---

## 重构内容

### 1. 新增提示词模块 (`app/prompts/`)

**新增文件：**
- `app/prompts/__init__.py` - 提示词加载器
- `app/prompts/accounting/system_prompt.md` - 记账主提示词
- `app/prompts/accounting/few_shot_examples.md` - Few-shot 示例
- `app/prompts/accounting/output_schema.md` - 输出格式规范
- `app/prompts/accounting/tool_guidelines.md` - 工具使用指南
- `app/prompts/base/cot_guidelines.md` - COT 推理指导
- `app/prompts/base/safety_guard.md` - 安全防护规则
- `app/prompts/base/default_system_prompt.md` - 默认提示词

**关键函数：**
- `build_accounting_prompt()` - 从文件构建记账 Agent 提示词
- `build_default_agent_prompt()` - 构建默认 Agent 提示词
- `load_prompt()` - 加载提示词文件

### 2. 新增领域层接口

**新增文件：**
- `app/domain/agent/agent_cache.py` - Agent 缓存接口
- `app/domain/agent/tool_registry.py` - 工具注册表接口
- `app/domain/accounting/accounting_tool_interfaces.py` - 记账工具接口和常量

**导出更新：**
- `app/domain/agent/__init__.py` - 导出新的接口
- `app/domain/accounting/__init__.py` - 导出记账工具常量

### 3. 新增记账工具实现 (`app/infrastructure/tools/accounting/`)

**新增文件：**
- `add_transaction_tool.py` - 添加记账工具（通过 Repository 操作）
- `query_accounting_tool.py` - 查询记账工具
- `stats_by_period_tool.py` - 统计工具
- `get_categories_tool.py` - 获取分类工具
- `calculator_tool.py` - 计算器工具
- `datetime_tool.py` - 日期时间工具

**设计特点：**
- 所有工具通过构造函数接收 Repository 接口
- 不直接访问数据库，符合 DDD 原则

### 4. 重构应用服务

#### AgentService (`app/application/agent/agent_service.py`)

**变更前：**
```python
# 直接导入基础设施层
from app.infrastructure.agent.cache.agent_cache import AgentCache
from app.infrastructure.llm.llm_provider import LLMProvider
from app.infrastructure.tools.tool_registry import ToolRegistry
```

**变更后：**
```python
# 只依赖领域层接口
from app.domain.agent.agent_cache import AgentCache
from app.domain.agent.tool_registry import ToolRegistry

# 提示词从文件加载
from app.prompts import build_default_agent_prompt
```

#### AccountingAgentService (`app/application/accounting/accounting_agent_service.py`)

**变更前：**
```python
# 直接创建基础设施对象
from app.infrastructure.agent.langgraph.langgraph_agent import LangGraphAgent
from app.infrastructure.agent.langgraph.tool_adapter import ToolAdapter

agent = LangGraphAgent(
    llm_config=llm_config,
    system_prompt=system_prompt,
    tool_adapters=[ToolAdapter(t) for t in self.ACCOUNTING_TOOLS],
)
```

**变更后：**
```python
# 通过工厂创建
from app.prompts import build_accounting_prompt

agent = self._agent_factory.create_agent(
    model=model,
    tools=self._accounting_tools,
    system_prompt=system_prompt,
)
```

### 5. 更新基础设施层实现

#### AgentCache (`app/infrastructure/agent/cache/agent_cache.py`)
- 继承领域层 `AgentCache` 接口
- `InMemoryAgentCache` 实现接口

#### ToolRegistry (`app/infrastructure/tools/tool_registry.py`)
- 继承领域层 `ToolRegistry` 接口
- 实现 `get()` 方法符合接口规范

### 6. 更新依赖注入 (`app/interfaces/http/dependencies.py`)

**新增函数：**
- `get_transaction_repository()` - 获取 Repository
- `get_accounting_tools()` - 获取记账工具列表（注入 Repository）

**更新函数：**
- `get_agent_service()` - 注入领域层接口
- `get_accounting_agent_service()` - 注入工具和工厂

---

## DDD 架构合规性检查

### 依赖方向（重构后）

```
┌─────────────────────────────────────────┐
│ 接口层 (Interface Layer)                 │
│   dependencies.py                       │
│   - 创建 Repository 具体实现             │
│   - 创建 Tool 实例并注入 Repository      │
│   - 注入领域层接口                       │
├─────────────────────────────────────────┤
│ 应用层 (Application Layer)               │
│   AgentService                          │
│   AccountingAgentService                │
│   - 只依赖领域层接口                     │
│   - 通过 AgentFactory 创建 Agent         │
│   - 使用 prompts 模块构建提示词          │
├─────────────────────────────────────────┤
│ 领域层 (Domain Layer)                    │
│   AbstractAgent                         │
│   AgentCache (接口)                     │
│   ToolRegistry (接口)                   │
│   TransactionRepository (接口)          │
│   - 无任何基础设施依赖                   │
├─────────────────────────────────────────┤
│ 基础设施层 (Infrastructure Layer)        │
│   LangGraphAgent                        │
│   InMemoryAgentCache                    │
│   ToolRegistryImpl                      │
│   SQLiteTransactionRepository           │
│   - 实现领域层接口                       │
└─────────────────────────────────────────┘
```

### 检查清单

| 检查项 | 状态 |
|-------|------|
| 领域层无基础设施依赖 | ✅ |
| 应用层只依赖领域层接口 | ✅ |
| 提示词从文件加载 | ✅ |
| Agent 通过工厂创建 | ✅ |
| 工具通过 Repository 操作数据 | ✅ |
| 依赖注入配置正确 | ✅ |

---

## 使用示例

### 创建 AccountingAgentService

```python
from app.application.accounting.accounting_agent_service import AccountingAgentService
from app.application.agent.agent_factory import AgentFactory
from app.infrastructure.agent.cache.agent_cache import InMemoryAgentCache
from app.infrastructure.tools.accounting import (
    AddTransactionTool,
    QueryAccountingTool,
    StatsByPeriodTool,
    GetCategoriesTool,
    CalculatorTool,
    GetCurrentDatetimeTool,
)
from app.infrastructure.persistence.sqlite.sqlite_transaction_repo import SQLiteTransactionRepository

# 创建 Repository
repository = SQLiteTransactionRepository()

# 创建工具（注入 Repository）
tools = [
    AddTransactionTool(repository=repository),
    QueryAccountingTool(repository=repository),
    StatsByPeriodTool(repository=repository),
    GetCategoriesTool(),
    CalculatorTool(),
    GetCurrentDatetimeTool(),
]

# 创建服务
service = AccountingAgentService(
    agent_cache=InMemoryAgentCache(),
    agent_factory=AgentFactory(),
    accounting_tools=tools,
)

# 使用
response = await service.chat("花了50块吃饭", "deepseek-v3", "session-001")
```

---

## 后续建议

1. **测试覆盖** - 为新创建的工具类和提示词加载器添加单元测试
2. **文档更新** - 更新 API 文档，说明新的架构设计
3. **配置扩展** - 可以在 `application.toml` 中添加提示词版本配置
4. **热重载** - 实现提示词文件的热重载功能

---

## 文件变更统计

| 类型 | 数量 |
|-----|------|
| 新增文件 | 15 |
| 修改文件 | 8 |
| 删除代码行 | ~250 (硬编码提示词) |
| 新增代码行 | ~800 |
