# My Agent - 可扩展 Agent 框架

> 🚀 **由 AI Vibe Coding 生成** | Generated with AI assistance

基于 LangGraph ReAct 架构的可扩展 Agent 框架，提供标准化的 Agent 结构与工具扩展机制。

**本项目包含：**
- **核心框架**：标准化的 Agent 架构、工具系统、MCP/Skill 扩展机制
- **示例实现**：基于该框架的**智能记账 Agent**（收入/支出管理、数据可视化）

> 💡 此框架设计用于快速构建各类垂直领域 Agent，记账只是第一个示例，后续将实现更多专门的 Agent 应用。

## ✨ 框架特性

- **标准化架构**：基于 LangGraph ReAct 的标准 Agent 结构，易于扩展
- **多轮对话**：通过 thread_id 保持对话上下文
- **工具系统**：支持 Tool、MCP、Skill 三层扩展机制
- **流式输出**：SSE 实时响应
- **模型切换**：支持 deepseek-v3 / deepseek-r1 等模型
- **向量检索**：内置 Milvus 向量数据库支持

## 📊 记账 Agent 示例功能

- **智能对话**：自然语言记账查询与记录
- **记账管理**：收入/支出记录、分类统计
- **数据可视化**：收支图表、趋势分析
- **Excel 导出**：账单数据导出功能

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

## 📁 项目结构

### 核心框架（可复用）

```
my-agent/
├── app/
│   ├── config.py             # 配置读取模块
│   ├── llm/
│   │   └── llm_factory.py    # LLM/Embedding 工厂
│   ├── db/
│   │   ├── sqlite_client.py  # SQLite 客户端
│   │   └── milvus_client.py  # Milvus 向量数据库
│   ├── agent/
│   │   └── react_agent.py    # ReAct Agent 核心 ⭐
│   ├── tools/                # 基础工具集合
│   ├── mcp/                  # MCP 工具扩展
│   ├── skills/               # Skill 技能扩展
│   └── api/
│       └── routes.py         # 通用 API 路由
```

### 记账 Agent 示例实现

```
my-agent/
├── accounting-frontend/      # 记账前端界面
├── app/
│   ├── api/
│   │   └── accounting_routes.py  # 记账业务 API
│   └── tools/
│       └── accounting_tools.py   # 记账相关工具
└── data/                     # 记账数据库文件
```

### 配置文件

```
├── application.toml          # 全局配置文件（勿提交到 Git）
├── application.example.toml  # 配置示例文件
├── main.py                   # FastAPI 启动入口
├── pyproject.toml            # 项目依赖
└── tests/                    # 测试代码
```

## ⚙️ 配置说明

编辑 `application.toml` 配置以下关键项：

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `llm.api_key` | 阿里百炼 API Key | [百炼控制台](https://bailian.console.aliyun.com/) |
| `llm.base_url` | OpenAI 兼容接口 | 默认即可 |
| `llm.default_model` | 默认模型 | `deepseek-v3` / `deepseek-r1` |
| `embedding.base_url` | Ollama 地址 | 本地默认 `http://localhost:11434` |
| `database.sqlite.path` | SQLite 文件路径 | 默认 `./data/agent.db` |
| `server.port` | 服务端口 | 默认 `8000` |

## 🛠️ 开发指南

### 基于此框架开发新 Agent

1. **复用核心框架**：`app/agent/`, `app/llm/`, `app/db/` 可直接复用
2. **创建业务工具**：在 `app/tools/` 下新建业务相关工具
3. **创建 API 路由**：在 `app/api/` 下新建业务路由文件
4. **可选前端**：可配套开发专属前端界面

### 添加新工具

在 `app/tools/` 下创建新的工具文件：

```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """
    工具的用途描述。
    Args:
        param: 参数说明
    Returns:
        返回结果说明
    """
    return f"结果: {param}"
```

然后在 `app/tools/__init__.py` 中注册：

```python
from app.tools.my_tool import my_tool
ALL_TOOLS = [..., my_tool]
```

### 运行测试

```bash
uv run python tests/test_demo.py --mode local
```

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

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -am 'Add some feature'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## ⚠️ 安全提示

- **切勿将 `application.toml` 提交到 Git**，该文件包含敏感 API Key
- **不要将 `data/` 目录提交**，包含本地数据库文件
- 生产环境请关闭 `debug` 和 `reload` 模式

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

**许可范围：**
- ✅ 可自由使用、修改、分发
- ✅ 可用于商业用途
- ✅ 可闭源使用
- ✅ 无需支付费用
- ✅ 不承担任何责任

## 💬 联系方式

如有问题或建议，欢迎提交 Issue 或 PR。
