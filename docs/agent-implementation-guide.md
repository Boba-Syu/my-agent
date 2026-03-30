# Agent 实现指南

> 本文档详细说明如何基于 DDD 架构实现新的 Agent 底层框架，以及如何扩展现有实现。

---

## 目录

1. [架构概述](#架构概述)
2. [核心抽象](#核心抽象)
3. [现有实现](#现有实现)
4. [新增实现步骤](#新增实现步骤)
5. [工具开发指南](#工具开发指南)
6. [最佳实践](#最佳实践)

---

## 架构概述

### DDD 分层架构

```
┌─────────────────────────────────────────────┐
│              接口层 (Interface Layer)        │
│     FastAPI Routes / CLI / WebSocket        │
├─────────────────────────────────────────────┤
│             应用层 (Application Layer)       │
│   AgentService / AccountingAgentService     │
│   用例编排 / DTO 转换 / 事务管理             │
├─────────────────────────────────────────────┤
│             领域层 (Domain Layer)            │
│   AbstractAgent (核心抽象)                  │
│   AgentTool / AgentMessage / AgentResponse  │
│   Transaction / Money / Repository 接口     │
├─────────────────────────────────────────────┤
│           基础设施层 (Infrastructure)        │
│   LangGraphAgent / AgnoAgent                │
│   SQLiteTransactionRepository               │
│   ToolAdapter / LLMProvider                 │
└─────────────────────────────────────────────┘
```

### 依赖方向

```
接口层 ────────► 应用层 ────────► 领域层 ◄─────── 基础设施层
     (依赖)        (依赖)        (抽象)         (实现)
```

---

## 核心抽象

### AbstractAgent (领域层)

```python
# app/domain/agent/abstract_agent.py

class AbstractAgent(ABC):
    """
    Agent 抽象基类 - 领域层核心抽象
    
    独立于任何底层框架（LangGraph、AutoGen、Agno 等）
    定义 Agent 的核心能力边界
    """
    
    @abstractmethod
    def invoke(self, message: str, thread_id: str) -> AgentResponse:
        """同步调用 Agent"""
        pass
    
    @abstractmethod
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """异步调用 Agent"""
        pass
    
    @abstractmethod
    def stream(self, message: str, thread_id: str) -> Iterator[AgentChunk]:
        """同步流式调用"""
        pass
    
    @abstractmethod
    async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
        """异步流式调用"""
        pass
    
    @abstractmethod
    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """动态添加工具"""
        pass
```

### AgentTool (领域层)

```python
# app/domain/agent/agent_tool.py

class AgentTool(ABC):
    """
    领域工具接口
    
    定义工具在领域层的契约，与具体实现框架无关
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具唯一名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（供 LLM 理解）"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """工具参数 JSON Schema"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
```

---

## 现有实现

### 1. LangGraphAgent

```python
# app/infrastructure/agent/langgraph/langgraph_agent.py

class LangGraphAgent(AbstractAgent):
    """
    LangGraph 实现的 Agent
    
    将 LangGraph 框架适配到领域层的 Agent 抽象
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str,
        tool_adapters: list[ToolAdapter],
        max_iterations: int = 10,
        timeout: int = 120,
    ):
        self._llm_config = llm_config
        self._system_prompt = system_prompt
        self._tool_adapters = tool_adapters
        self._max_iterations = max_iterations
        self._timeout = timeout
        
        # 初始化 LangGraph
        self._llm = self._create_llm()
        self._graph = self._build_graph()
    
    def _build_graph(self) -> CompiledStateGraph:
        """构建 LangGraph 状态图"""
        from langgraph.prebuilt import create_react_agent
        
        tools = [adapter.to_langchain_tool() for adapter in self._tool_adapters]
        return create_react_agent(
            model=self._llm,
            tools=tools,
            prompt=self._system_prompt,
        )
    
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """实现领域层定义的异步调用接口"""
        from langchain_core.messages import HumanMessage
        
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": self._max_iterations,
        }
        state = {"messages": [HumanMessage(content=message)]}
        
        # 调用 LangGraph
        result = await self._graph.ainvoke(state, config=config)
        
        # 转换为领域模型
        messages = result.get("messages", [])
        reply = self._extract_reply(messages)
        
        return AgentResponse(
            content=reply,
            messages=self._convert_messages(messages),
            metadata={"model": self._llm_config.model},
        )
```

### 2. AgnoAgent

```python
# app/infrastructure/agent/agno/agno_agent.py

class AgnoAgent(AbstractAgent):
    """
    Agno 框架实现的 Agent
    
    展示如何基于相同的领域抽象实现不同的底层框架
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str,
        tool_adapters: list[ToolAdapter],
        max_iterations: int = 10,
        timeout: int = 120,
    ):
        self._llm_config = llm_config
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._timeout = timeout
        
        # 初始化 Agno Agent
        self._agno_agent = self._build_agent(tool_adapters)
    
    def _build_agent(self, tool_adapters: list[ToolAdapter]) -> Any:
        """构建 Agno Agent"""
        from agno import Agent as AgnoAgent
        from agno.models.openai import OpenAIChat
        
        # 转换工具
        agno_tools = [adapter.to_agno_tool() for adapter in tool_adapters]
        
        return AgnoAgent(
            model=OpenAIChat(
                id=self._llm_config.model,
                api_key=self._llm_config.api_key,
                base_url=self._llm_config.base_url,
            ),
            description=self._system_prompt,
            tools=agno_tools,
            show_tool_calls=True,
            markdown=True,
        )
    
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """实现领域层定义的异步调用接口"""
        try:
            response = await asyncio.wait_for(
                self._run_agent(message),
                timeout=self._timeout,
            )
            
            return AgentResponse(
                content=response.content if hasattr(response, "content") else str(response),
                metadata={
                    "model": self._llm_config.model,
                    "thread_id": thread_id,
                    "tools_used": self._extract_tool_calls(response),
                },
            )
        except asyncio.TimeoutError:
            return AgentResponse(
                content="处理时间过长，请稍后再试或简化您的问题",
                is_error=True,
            )
```

---

## 新增实现步骤

### 步骤 1: 创建新实现目录

```bash
mkdir -p app/infrastructure/agent/{new_framework}
touch app/infrastructure/agent/{new_framework}/__init__.py
touch app/infrastructure/agent/{new_framework}/{new_framework}_agent.py
```

### 步骤 2: 实现 AbstractAgent 接口

```python
# app/infrastructure/agent/new_framework/new_framework_agent.py

from __future__ import annotations

import logging
from typing import Any

from app.domain.agent import AbstractAgent, AgentResponse, AgentChunk, AgentTool, ToolUpdateResult
from app.infrastructure.llm import LLMConfig
from app.infrastructure.agent.langgraph.tool_adapter import ToolAdapter

logger = logging.getLogger(__name__)


class NewFrameworkAgent(AbstractAgent):
    """
    [New Framework] 实现的 Agent
    
    实现说明：
    - 继承 AbstractAgent 基类
    - 在内部使用 [New Framework]
    - 对外隐藏实现细节
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str,
        tool_adapters: list[ToolAdapter],
        max_iterations: int = 10,
        timeout: int = 120,
    ):
        self._llm_config = llm_config
        self._system_prompt = system_prompt
        self._tool_adapters = tool_adapters
        self._max_iterations = max_iterations
        self._timeout = timeout
        
        # 初始化 [New Framework]
        self._agent = self._build_agent()
    
    def _build_agent(self) -> Any:
        """构建 [New Framework] Agent"""
        # TODO: 实现具体的 Agent 构建逻辑
        pass
    
    def invoke(self, message: str, thread_id: str) -> AgentResponse:
        """同步调用 Agent"""
        # TODO: 实现同步调用
        pass
    
    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """异步调用 Agent"""
        # TODO: 实现异步调用
        pass
    
    def stream(self, message: str, thread_id: str) -> Iterator[AgentChunk]:
        """同步流式调用"""
        # TODO: 实现同步流式调用
        pass
    
    async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
        """异步流式调用"""
        # TODO: 实现异步流式调用
        pass
    
    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """动态添加工具"""
        # TODO: 实现工具添加
        pass
    
    def remove_tools(self, tool_names: list[str]) -> ToolUpdateResult:
        """动态移除工具"""
        # TODO: 实现工具移除
        pass
```

### 步骤 3: 实现工具适配器

```python
# app/infrastructure/agent/new_framework/tool_adapter.py

class ToolAdapter:
    """
    工具适配器 - 将领域层 AgentTool 适配为 [New Framework] 工具
    """
    
    def __init__(self, domain_tool: AgentTool):
        self._domain_tool = domain_tool
    
    def to_new_framework_tool(self) -> Any:
        """转换为 [New Framework] 工具格式"""
        # TODO: 实现工具转换
        pass
    
    @property
    def domain_tool(self) -> AgentTool:
        return self._domain_tool
```

### 步骤 4: 更新工厂

```python
# app/application/agent/agent_factory.py

class AgentFactory:
    """Agent 工厂 - 支持多种底层实现"""
    
    def __init__(self, implementation: str = "langgraph"):
        self._implementation = implementation
    
    def create(
        self,
        model: str,
        system_prompt: str,
        tools: list[AgentTool],
    ) -> AbstractAgent:
        """创建 Agent 实例"""
        llm_config = LLMProvider().get_config(model)
        tool_adapters = [ToolAdapter(t) for t in tools]
        
        if self._implementation == "langgraph":
            from app.infrastructure.agent import LangGraphAgent
            return LangGraphAgent(
                llm_config=llm_config,
                system_prompt=system_prompt,
                tool_adapters=tool_adapters,
            )
        elif self._implementation == "agno":
            from app.infrastructure.agent import AgnoAgent
            return AgnoAgent(
                llm_config=llm_config,
                system_prompt=system_prompt,
                tool_adapters=tool_adapters,
            )
        elif self._implementation == "new_framework":
            from app.infrastructure.agent.new_framework import NewFrameworkAgent
            return NewFrameworkAgent(
                llm_config=llm_config,
                system_prompt=system_prompt,
                tool_adapters=tool_adapters,
            )
        else:
            raise ValueError(f"Unknown implementation: {self._implementation}")
```

### 步骤 5: 注册导出

```python
# app/infrastructure/__init__.py

from app.infrastructure.agent.langgraph.langgraph_agent import LangGraphAgent
from app.infrastructure.agent.agno.agno_agent import AgnoAgent
from app.infrastructure.agent.new_framework.new_framework_agent import NewFrameworkAgent

__all__ = [
    "LangGraphAgent",
    "AgnoAgent",
    "NewFrameworkAgent",
    # ...
]
```

---

## 工具开发指南

### 创建新的领域工具

```python
# app/infrastructure/tools/calculator_tool.py

from __future__ import annotations

import ast
import logging
import operator
from typing import Any

from app.domain.agent import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class CalculatorTool(AgentTool):
    """
    计算器工具
    
    安全地执行数学计算表达式
    """
    
    # 支持的操作符
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """
        执行数学计算。支持 +, -, *, /, ** 等运算符。
        
        Args:
            expression: 数学表达式字符串，如 "100 * 1.08 + 50"
        
        Returns:
            计算结果
        """
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '100 + 50'",
                }
            },
            "required": ["expression"],
        }
    
    def execute(self, expression: str) -> ToolResult:
        """执行计算"""
        try:
            result = self._safe_eval(expression)
            return ToolResult.success_result(
                content=str(result),
                data={"expression": expression, "result": result},
            )
        except Exception as e:
            logger.error(f"计算错误: {e}")
            return ToolResult.error_result(
                message=f"计算失败: {str(e)}",
            )
    
    def _safe_eval(self, expression: str) -> float:
        """安全地评估数学表达式"""
        tree = ast.parse(expression.strip(), mode='eval')
        return self._eval_node(tree.body)
    
    def _eval_node(self, node: ast.AST) -> float:
        """递归计算 AST 节点"""
        if isinstance(node, ast.Num):
            return float(node.n)
        elif isinstance(node, ast.Constant):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self._OPERATORS[op_type](operand)
        else:
            raise ValueError(f"不支持的表达式类型: {type(node).__name__}")
```

### 注册工具

```python
# app/infrastructure/tools/tool_registry.py

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: dict[str, AgentTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """注册默认工具"""
        # 记账工具
        self.register(AddTransactionTool())
        self.register(QueryTransactionsTool())
        self.register(StatsByPeriodTool())
        self.register(StatsByCategoryTool())
        self.register(ExportToExcelTool())
        self.register(ExportToMarkdownTool())
        
        # 通用工具
        self.register(CalculatorTool())
        self.register(GetCurrentDatetimeTool())
    
    def register(self, tool: AgentTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name}")
    
    def get(self, name: str) -> AgentTool | None:
        """获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> list[AgentTool]:
        """获取所有工具"""
        return list(self._tools.values())
```

---

## 最佳实践

### 1. 错误处理

```python
async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
    """统一的错误处理"""
    try:
        result = await asyncio.wait_for(
            self._do_invoke(message, thread_id),
            timeout=self._timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Agent 调用超时: {thread_id}")
        return AgentResponse(
            content="处理时间过长，请稍后再试或简化您的问题",
            is_error=True,
            error_type="timeout",
        )
    except Exception as e:
        logger.error(f"Agent 调用失败: {e}", exc_info=True)
        return AgentResponse(
            content=f"处理过程中出现了问题: {str(e)}",
            is_error=True,
            error_type="unknown",
        )
```

### 2. 流式输出

```python
async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
    """流式输出处理"""
    try:
        async for chunk in self._agent.astream(...):
            # 提取内容
            content = self._extract_content(chunk)
            
            # 检测工具调用
            if self._is_tool_call(chunk):
                yield AgentChunk(
                    content="",
                    chunk_type=ChunkType.TOOL_CALL,
                    metadata=self._extract_tool_call(chunk),
                )
            else:
                yield AgentChunk(
                    content=content,
                    chunk_type=ChunkType.TEXT,
                )
    except Exception as e:
        yield AgentChunk(
            content=f"[ERROR] {str(e)}",
            chunk_type=ChunkType.ERROR,
        )
```

### 3. 缓存策略

```python
# 使用缓存避免重复创建
class AgentCache:
    """Agent 缓存接口"""
    
    @abstractmethod
    def get(self, key: str) -> AbstractAgent | None:
        pass
    
    @abstractmethod
    def set(self, key: str, agent: AbstractAgent) -> None:
        pass
    
    @abstractmethod
    def clear(self) -> None:
        pass


class InMemoryAgentCache(AgentCache):
    """内存中的 Agent 缓存"""
    
    def __init__(self, max_size: int = 100):
        self._cache: dict[str, AbstractAgent] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> AbstractAgent | None:
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, agent: AbstractAgent) -> None:
        with self._lock:
            if len(self._cache) >= self._max_size:
                # LRU 淘汰
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[key] = agent
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
```

### 4. 测试策略

```python
# tests/test_langgraph_agent.py

import pytest
from app.infrastructure.agent import LangGraphAgent
from app.infrastructure.llm import LLMConfig


@pytest.fixture
def agent():
    """创建测试 Agent"""
    return LangGraphAgent(
        llm_config=LLMConfig(
            model="deepseek-chat",
            api_key="test-key",
            base_url="https://api.example.com",
        ),
        system_prompt="你是一个测试助手",
        tool_adapters=[],
    )


@pytest.mark.asyncio
async def test_agent_invoke(agent):
    """测试同步调用"""
    response = await agent.ainvoke("你好", "test-thread")
    
    assert response is not None
    assert response.content is not None
    assert not response.is_error


@pytest.mark.asyncio
async def test_agent_stream(agent):
    """测试流式调用"""
    chunks = []
    async for chunk in agent.astream("你好", "test-thread"):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert all(isinstance(c, AgentChunk) for c in chunks)
```

---

## 附录

### 参考实现对比

| 特性 | LangGraphAgent | AgnoAgent |
|------|---------------|-----------|
| 流式输出 | ✅ | ✅ |
| 工具调用 | ✅ | ✅ |
| 多轮对话 | ✅ | ✅ |
| 异步支持 | ✅ | ✅ |
| 超时控制 | ✅ | ✅ |
| 错误处理 | ✅ | ✅ |

### 相关文件

```
app/
├── domain/agent/
│   ├── abstract_agent.py       # 核心抽象
│   ├── agent_tool.py           # 工具接口
│   └── agent_response.py       # 响应模型
├── infrastructure/agent/
│   ├── langgraph/
│   │   ├── langgraph_agent.py  # LangGraph 实现
│   │   └── tool_adapter.py     # 工具适配器
│   ├── agno/
│   │   ├── agno_agent.py       # Agno 实现
│   │   └── tool_adapter.py
│   └── cache/
│       └── agent_cache.py      # 缓存实现
└── application/agent/
    ├── agent_service.py        # 应用服务
    └── agent_factory.py        # 工厂
```

---

*文档版本: 1.0.0*
*最后更新: 2025-03-30*
