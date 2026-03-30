# My Agent - DDD 可扩展 Agent 框架

> 🚀 **由 AI Vibe Coding 生成** | Generated with AI assistance

基于 **DDD（领域驱动设计）架构** 的可扩展 Agent 框架，提供清晰的领域边界和可替换的基础设施层。

**核心设计理念：**
- **领域层独立**：核心业务逻辑与框架无关
- **基础设施可替换**：LangGraph、AutoGen、自研框架均可接入
- **清晰的架构边界**：四层架构（领域层/应用层/基础设施层/接口层）

---

## ✨ 框架特性

### DDD 架构特性
- **分层架构**：领域层、应用层、基础设施层、接口层职责清晰
- **领域层独立**：核心业务逻辑不依赖任何第三方框架
- **Agent 抽象**：`AbstractAgent` 支持多种底层实现
- **工具抽象**：`AgentTool` 统一工具接口，框架无关

### 功能特性
- **多轮对话**：通过 thread_id 保持对话上下文
- **工具系统**：Tool、MCP、Skill 三层扩展机制
- **流式输出**：SSE 实时响应
- **模型切换**：支持 deepseek-v3 / deepseek-r1 等模型
- **向量检索**：内置 Milvus 向量数据库支持

---

## 📁 项目结构（DDD 架构）

```
my-agent/
├── app/
│   ├── domain/                      # 领域层 - 核心业务逻辑
│   │   ├── shared/                  # 通用子域
│   │   │   ├── entity.py            # 实体基类
│   │   │   ├── value_object.py      # 值对象基类
│   │   │   ├── aggregate_root.py    # 聚合根基类
│   │   │   ├── repository.py        # 仓库接口基类
│   │   │   └── domain_event.py      # 领域事件基类
│   │   ├── agent/                   # Agent 子域
│   │   │   ├── abstract_agent.py    # Agent 抽象基类 ⭐
│   │   │   ├── agent_message.py     # 消息值对象
│   │   │   ├── agent_tool.py        # 工具领域接口
│   │   │   └── agent_response.py    # 响应模型
│   │   └── accounting/              # 记账子域
│   │       ├── transaction.py       # 交易聚合根
│   │       ├── money.py             # 金额值对象
│   │       └── transaction_repository.py # 仓库接口
│   │
│   ├── application/                 # 应用层 - 用例编排
│   │   ├── agent/                   # Agent 应用服务
│   │   │   └── agent_service.py
│   │   └── accounting/              # 记账应用服务
│   │       └── transaction_service.py
│   │
│   ├── infrastructure/              # 基础设施层 - 技术实现
│   │   ├── agent/                   # Agent 实现
│   │   │   ├── langgraph/           # LangGraph 实现
│   │   │   │   ├── langgraph_agent.py ⭐
│   │   │   │   └── tool_adapter.py  # 工具适配器
│   │   │   └── cache/
│   │   │       └── agent_cache.py   # Agent 缓存
│   │   ├── llm/                     # LLM 基础设施
│   │   │   └── llm_provider.py
│   │   └── persistence/             # 持久化实现
│   │       ├── sqlite/
│   │       │   └── sqlite_transaction_repo.py
│   │       └── milvus/
│   │
│   ├── interfaces/                  # 接口层 - API 适配
│   │   └── http/                    # HTTP 接口
│   │       ├── routes/
│   │       │   ├── agent_routes.py
│   │       │   └── accounting_routes.py
│   │       └── schemas/             # Pydantic DTO
│   │
│   └── config.py                    # 配置读取
│
├── docs/
│   └── ddd-architecture.md          # DDD 架构设计文档 ⭐
│
├── application.toml                 # 全局配置（勿提交到 Git）
├── application.example.toml         # 配置示例文件
├── main.py                          # FastAPI 启动入口
└── pyproject.toml                   # 项目依赖
```

### 架构依赖关系

```
接口层 (interfaces/) → 应用层 (application/) → 领域层 (domain/)
                                          ↖
                                            基础设施层 (infrastructure/)
```

- **领域层**：不依赖任何其他层，包含核心业务逻辑
- **应用层**：编排领域对象完成用例
- **基础设施层**：实现领域层定义的接口
- **接口层**：接收外部请求，调用应用服务

---

## 🚀 快速开始

### 环境要求

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- Ollama（用于本地 Embedding）
- Node.js ≥ 18（如需运行记账前端）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd my-agent
```

### 2. 安装依赖

```bash
# 安装 Python 依赖
uv sync

# 安装记账前端依赖（可选）
cd accounting-frontend
npm install
```

### 3. 配置环境

```bash
# 复制示例配置文件
cp application.example.toml application.toml

# 编辑 application.toml，填入你的阿里百炼 API Key
# 从 https://bailian.console.aliyun.com/ 获取
```

### 4. 启动服务

```bash
# 启动 Agent 服务（后台）
uv run python main.py

# 服务启动后访问：
# - API 文档：http://localhost:8000/docs
# - ReDoc：http://localhost:8000/redoc
```

### 5. 启动记账前端（可选）

```bash
cd accounting-frontend
npm run dev

# 前端访问：http://localhost:5173
```

---

## 🏗️ DDD 架构详解

### 1. 领域层 (Domain Layer)

**核心抽象，与框架无关**

```python
# app/domain/agent/abstract_agent.py
class AbstractAgent(ABC):
    """Agent 抽象基类 - 领域层"""
    
    @abstractmethod
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """异步调用 Agent"""
        pass
    
    @abstractmethod
    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """动态添加工具"""
        pass
```

### 2. 基础设施层 (Infrastructure Layer)

**实现领域层接口，框架相关**

```python
# app/infrastructure/agent/langgraph/langgraph_agent.py
class LangGraphAgent(AbstractAgent):
    """LangGraph 实现的 Agent"""
    
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        # 使用 LangGraph 实现
        result = await self._graph.ainvoke(...)
        # 转换为领域模型
        return AgentResponse(...)
```

**未来可以轻松切换底层框架：**

```python
# 添加 AutoGen 实现
class AutoGenAgent(AbstractAgent):
    """AutoGen 实现的 Agent"""
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        # 使用 AutoGen 实现
        ...
```

### 3. 应用层 (Application Layer)

**编排用例，协调领域对象**

```python
# app/application/agent/agent_service.py
class AgentService:
    """Agent 应用服务"""
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        agent = self._get_or_create_agent(request.model)
        response = await agent.ainvoke(
            message=request.message,
            thread_id=request.thread_id,
        )
        return ChatResponse(content=response.content)
```

### 4. 接口层 (Interface Layer)

**接收请求，调用应用服务**

```python
# app/interfaces/http/routes/agent_routes.py
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    service = get_agent_service()
    return await service.chat(request)
```

---

## 🛠️ 开发指南

### 添加新的 Agent 实现

1. 继承 `AbstractAgent` 抽象基类
2. 实现所有抽象方法
3. 在应用层使用新的实现

```python
# my_custom_agent.py
from app.domain.agent.abstract_agent import AbstractAgent

class MyCustomAgent(AbstractAgent):
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        # 你的实现
        pass
    
    # ... 其他方法
```

### 添加新工具

1. 实现 `AgentTool` 接口
2. 注册到工具注册表

```python
# app/infrastructure/tools/calculator_tool.py
from app.domain.agent.agent_tool import AgentTool, ToolResult

class CalculatorTool(AgentTool):
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "执行数学计算"
    
    def execute(self, expression: str) -> ToolResult:
        try:
            result = safe_eval(expression)
            return ToolResult.success_result(str(result))
        except Exception as e:
            return ToolResult.error_result(str(e))
```

### 运行测试

```bash
uv run python tests/test_demo.py --mode local
```

---

## 📊 记账 Agent 示例

本项目包含一个完整的**记账 Agent** 示例，演示 DDD 架构的实际应用：

### 功能
- **智能对话**：自然语言记账查询与记录
- **记账管理**：收入/支出记录、分类统计
- **数据可视化**：收支图表、趋势分析
- **Excel 导出**：账单数据导出功能

### 领域模型
```python
# 交易聚合根
class Transaction(AggregateRoot):
    def __init__(self, type, category, amount: Money, date):
        self._transaction_type = type
        self._category = category
        self._amount = amount
        self._transaction_date = date
```

---

## 📝 常用命令

```bash
# 安装新依赖
uv add <package>

# 更新依赖
uv sync

# 运行开发服务器
uv run python main.py

# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check .
```

---

## ⚙️ 配置说明

编辑 `application.toml` 配置以下关键项：

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `llm.api_key` | 阿里百炼 API Key | [百炼控制台](https://bailian.console.aliyun.com/) |
| `llm.default_model` | 默认模型 | `deepseek-v3` / `deepseek-r1` |
| `embedding.base_url` | Ollama 地址 | 本地默认 `http://localhost:11434` |
| `database.sqlite.path` | SQLite 文件路径 | 默认 `./data/agent.db` |
| `server.port` | 服务端口 | 默认 `8000` |

---

## 📚 文档

- [DDD 架构设计文档](docs/ddd-architecture.md) - 详细的架构规范和设计原则
- [API 文档](http://localhost:8000/docs) - FastAPI 自动生成的 Swagger 文档

---

## ⚠️ 安全提示

- **切勿将 `application.toml` 提交到 Git**，该文件包含敏感 API Key
- **不要将 `data/` 目录提交**，包含本地数据库文件
- 生产环境请关闭 `debug` 和 `reload` 模式

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

**许可范围：**
- ✅ 可自由使用、修改、分发
- ✅ 可用于商业用途
- ✅ 可闭源使用
- ✅ 无需支付费用
- ✅ 不承担任何责任

---

## 💬 联系方式

如有问题或建议，欢迎提交 Issue 或 PR。
