# DDD 架构设计文档

## 1. 概述

本文档定义了 my-agent 项目的 DDD（领域驱动设计）架构规范，旨在实现核心业务逻辑与技术实现的解耦。

## 2. 架构分层

### 2.1 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    接口层 (Interface Layer)                  │
│         FastAPI Routes / CLI / WebSocket                     │
├─────────────────────────────────────────────────────────────┤
│                    应用层 (Application Layer)                │
│         应用服务 / 用例编排 / DTO 转换                        │
├─────────────────────────────────────────────────────────────┤
│                    领域层 (Domain Layer)                     │
│         实体 / 值对象 / 聚合根 / 领域服务 / 仓库接口          │
├─────────────────────────────────────────────────────────────┤
│                  基础设施层 (Infrastructure Layer)           │
│    LangGraph / SQLite / Milvus / HTTP Client / 外部服务      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 依赖规则

- 上层依赖下层
- 领域层不依赖任何其他层
- 基础设施层实现领域层定义的接口
- 依赖方向：**接口层 → 应用层 → 领域层 ← 基础设施层**

## 3. 领域层 (Domain Layer)

### 3.1 核心职责

- 定义业务概念和业务规则
- 独立于框架、UI 和数据库
- 包含核心业务逻辑

### 3.2 通用子域 (shared/)

#### Entity 实体基类
```python
class Entity(ABC):
    """领域实体基类"""
    
    def __init__(self, id: str | None = None):
        self._id = id
        self._events: list[DomainEvent] = []
    
    @property
    def id(self) -> str | None:
        return self._id
    
    def add_event(self, event: DomainEvent) -> None:
        self._events.append(event)
    
    def clear_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

#### Value Object 值对象基类
```python
@dataclass(frozen=True)
class ValueObject(ABC):
    """值对象基类 - 不可变、基于属性相等"""
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
```

#### Aggregate Root 聚合根基类
```python
class AggregateRoot(Entity, ABC):
    """聚合根 - 事务边界、一致性边界"""
    
    @property
    @abstractmethod
    def version(self) -> int:
        """乐观锁版本号"""
        pass
```

### 3.3 Agent 子域 (agent/)

#### Agent 抽象基类
```python
class AbstractAgent(ABC):
    """
    Agent 抽象基类 - 领域层核心抽象
    
    独立于任何底层框架（LangGraph、AutoGen 等）
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
    
    @abstractmethod
    def remove_tools(self, tool_names: list[str]) -> ToolUpdateResult:
        """动态移除工具"""
        pass
    
    @abstractmethod
    def update_system_prompt(self, prompt: str) -> None:
        """更新系统提示词"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> list[AgentTool]:
        """获取当前工具列表"""
        pass
```

#### AgentMessage 值对象
```python
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"

@dataclass(frozen=True)
class AgentMessage(ValueObject):
    """Agent 消息值对象"""
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)
```

#### AgentTool 领域接口
```python
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

### 3.4 记账子域 (accounting/)

#### Transaction 聚合根
```python
class Transaction(AggregateRoot):
    """
    记账交易聚合根
    
    聚合边界包含：
    - 交易类型（收入/支出）
    - 金额
    - 分类
    - 日期
    - 备注
    """
    
    def __init__(
        self,
        id: int | None,
        transaction_type: TransactionType,
        category: str,
        amount: Money,
        transaction_date: date,
        note: str = "",
        created_at: datetime | None = None,
    ):
        super().__init__(id)
        self._transaction_type = transaction_type
        self._category = category
        self._amount = amount
        self._transaction_date = transaction_date
        self._note = note
        self._created_at = created_at or datetime.now()
        self._version = 0
    
    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type
    
    @property
    def category(self) -> str:
        return self._category
    
    @property
    def amount(self) -> Money:
        return self._amount
    
    @property
    def transaction_date(self) -> date:
        return self._transaction_date
    
    @property
    def version(self) -> int:
        return self._version
    
    def update(
        self,
        category: str | None = None,
        amount: Money | None = None,
        transaction_date: date | None = None,
        note: str | None = None,
    ) -> None:
        """更新交易信息"""
        if category is not None:
            self._category = category
        if amount is not None:
            self._amount = amount
        if transaction_date is not None:
            self._transaction_date = transaction_date
        if note is not None:
            self._note = note
        self._version += 1
        self.add_event(TransactionUpdatedEvent(self.id))
    
    def to_snapshot(self) -> TransactionSnapshot:
        """生成快照"""
        return TransactionSnapshot(
            id=self._id,
            transaction_type=self._transaction_type.value,
            category=self._category,
            amount=self._amount.amount,
            transaction_date=self._transaction_date.isoformat(),
            note=self._note,
            created_at=self._created_at.isoformat() if self._created_at else None,
            version=self._version,
        )
```

#### 仓库接口
```python
class TransactionRepository(ABC):
    """交易仓库接口 - 由基础设施层实现"""
    
    @abstractmethod
    def get_by_id(self, id: int) -> Transaction | None:
        pass
    
    @abstractmethod
    def list(
        self,
        transaction_type: TransactionType | None = None,
        category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        pass
    
    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        pass
    
    @abstractmethod
    def get_statistics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionStatistics:
        pass
```

## 4. 应用层 (Application Layer)

### 4.1 核心职责

- 编排领域对象完成用例
- 事务管理
- 跨聚合协调
- DTO 转换

### 4.2 Agent 应用服务

```python
class AgentService:
    """
    Agent 应用服务
    
    协调领域层的 Agent 完成用户用例
    """
    
    def __init__(
        self,
        agent_factory: AgentFactory,
        agent_cache: AgentCache,
    ):
        self._agent_factory = agent_factory
        self._agent_cache = agent_cache
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """对话用例"""
        agent = self._get_or_create_agent(request.model)
        response = await agent.ainvoke(
            message=request.message,
            thread_id=request.thread_id,
        )
        return ChatResponse(
            reply=response.content,
            thread_id=request.thread_id,
            model=request.model,
        )
    
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[StreamChunk]:
        """流式对话用例"""
        agent = self._get_or_create_agent(request.model)
        async for chunk in agent.astream(
            message=request.message,
            thread_id=request.thread_id,
        ):
            yield chunk
    
    def _get_or_create_agent(self, model: str) -> AbstractAgent:
        """获取或创建 Agent 实例"""
        agent = self._agent_cache.get(model)
        if agent is None:
            agent = self._agent_factory.create(model)
            self._agent_cache.set(model, agent)
        return agent
```

### 4.3 记账应用服务

```python
class TransactionService:
    """交易应用服务"""
    
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        category_validator: CategoryValidator,
    ):
        self._repo = transaction_repo
        self._validator = category_validator
    
    def create_transaction(
        self,
        dto: CreateTransactionDTO,
    ) -> TransactionDTO:
        """创建交易用例"""
        # 验证分类
        if not self._validator.is_valid(dto.category, dto.transaction_type):
            raise InvalidCategoryError(dto.category)
        
        # 创建聚合根
        transaction = Transaction(
            id=None,
            transaction_type=TransactionType(dto.transaction_type),
            category=dto.category,
            amount=Money(dto.amount),
            transaction_date=date.fromisoformat(dto.transaction_date),
            note=dto.note,
        )
        
        # 保存
        saved = self._repo.save(transaction)
        return TransactionDTO.from_entity(saved)
    
    def list_transactions(
        self,
        query: TransactionQueryDTO,
    ) -> list[TransactionDTO]:
        """查询交易用例"""
        transactions = self._repo.list(
            transaction_type=TransactionType(query.type) if query.type else None,
            category=query.category,
            start_date=date.fromisoformat(query.start_date) if query.start_date else None,
            end_date=date.fromisoformat(query.end_date) if query.end_date else None,
            limit=query.limit,
        )
        return [TransactionDTO.from_entity(t) for t in transactions]
```

## 5. 基础设施层 (Infrastructure Layer)

### 5.1 核心职责

- 实现领域层定义的接口
- 与外部系统交互（数据库、LLM、向量库）
- 技术细节封装

### 5.2 Agent 多实现支持

框架支持多种底层实现，目前提供：

| 实现 | 类名 | 路径 | 状态 |
|------|------|------|------|
| LangGraph | `LangGraphAgent` | `infrastructure/agent/langgraph/` | ✅ 主实现 |
| Agno | `AgnoAgent` | `infrastructure/agent/agno/` | ✅ 备选实现 |

通过 `AgentFactory` 可在不同实现间切换：

```python
# 使用 LangGraph 实现（默认）
factory = AgentFactory(implementation="langgraph")
agent = factory.create(model="deepseek-v3", ...)

# 使用 Agno 实现
factory = AgentFactory(implementation="agno")
agent = factory.create(model="deepseek-v3", ...)
```

### 5.3 LangGraph Agent 实现

```python
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
    
    def _create_llm(self) -> ChatOpenAI:
        """创建 LLM 实例"""
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self._llm_config.model,
            api_key=self._llm_config.api_key,
            base_url=self._llm_config.base_url,
            timeout=self._llm_config.timeout,
            max_tokens=self._llm_config.max_tokens,
        )
    
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
    
    def _extract_reply(self, messages: list) -> str:
        """从 LangGraph 消息中提取回复"""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                content = msg.content
                if isinstance(content, list):
                    return "".join(
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") != "reasoning"
                    ).strip()
                return str(content).strip()
        return "Agent 未能生成回复"
    
    def _convert_messages(self, messages: list) -> list[AgentMessage]:
        """将 LangGraph 消息转换为领域消息"""
        # ... 转换逻辑
        pass
```

### 5.4 Agno Agent 实现

```python
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
                    "implementation": "agno",
                },
            )
        except asyncio.TimeoutError:
            return AgentResponse(
                content="处理时间过长，请稍后再试或简化您的问题",
                is_error=True,
            )
```

### 5.5 SQLite 交易仓库实现

```python
class SQLiteTransactionRepository(TransactionRepository):
    """
    SQLite 交易仓库实现
    
    实现领域层的 TransactionRepository 接口
    """
    
    def __init__(self, client: SQLiteClient):
        self._client = client
    
    def get_by_id(self, id: int) -> Transaction | None:
        rows = self._client.query(
            "SELECT * FROM transactions WHERE id = :id",
            {"id": id},
        )
        if not rows:
            return None
        return self._row_to_entity(rows[0])
    
    def save(self, transaction: Transaction) -> Transaction:
        if transaction.id is None:
            # 插入
            result = self._client.execute(
                """
                INSERT INTO transactions 
                (transaction_type, category, amount, transaction_date, note)
                VALUES (:type, :category, :amount, :date, :note)
                """,
                {
                    "type": transaction.transaction_type.value,
                    "category": transaction.category,
                    "amount": transaction.amount.amount,
                    "date": transaction.transaction_date.isoformat(),
                    "note": transaction.note,
                },
            )
            # 重新加载获取完整数据
            return self.get_by_id(result.lastrowid)
        else:
            # 更新
            self._client.execute(
                """
                UPDATE transactions 
                SET transaction_type = :type,
                    category = :category,
                    amount = :amount,
                    transaction_date = :date,
                    note = :note
                WHERE id = :id
                """,
                {
                    "id": transaction.id,
                    "type": transaction.transaction_type.value,
                    "category": transaction.category,
                    "amount": transaction.amount.amount,
                    "date": transaction.transaction_date.isoformat(),
                    "note": transaction.note,
                },
            )
            return transaction
    
    def _row_to_entity(self, row: dict) -> Transaction:
        """数据库行转换为领域实体"""
        return Transaction(
            id=row["id"],
            transaction_type=TransactionType(row["transaction_type"]),
            category=row["category"],
            amount=Money(row["amount"]),
            transaction_date=date.fromisoformat(row["transaction_date"]),
            note=row.get("note", ""),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
        )
```

## 6. 接口层 (Interface Layer)

### 6.1 核心职责

- 接收外部请求
- 输入验证
- 调用应用服务
- 返回响应

### 6.2 FastAPI 路由示例

```python
router = APIRouter(prefix="/api/v1/accounting", tags=["记账"])

@router.post("/chat", response_model=ChatResponse)
async def accounting_chat(
    request: AccountingChatRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> ChatResponse:
    """记账对话接口"""
    return await service.chat(ChatRequest(
        message=request.message,
        model=request.model,
        thread_id=request.thread_id,
    ))

@router.get("/records", response_model=list[TransactionRecord])
async def get_records(
    transaction_type: str | None = Query(default=None),
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> list[TransactionRecord]:
    """查询记账记录"""
    transactions = service.list_transactions(TransactionQueryDTO(
        type=transaction_type,
    ))
    return [TransactionRecord.from_dto(t) for t in transactions]
```

### 6.3 依赖注入配置

```python
def get_agent_service() -> AgentService:
    """获取 Agent 应用服务"""
    factory = LangGraphAgentFactory(
        llm_config=get_llm_config(),
        tool_registry=get_tool_registry(),
    )
    cache = InMemoryAgentCache()
    return AgentService(factory, cache)

def get_transaction_service() -> TransactionService:
    """获取交易应用服务"""
    repo = SQLiteTransactionRepository(SQLiteClient())
    validator = CategoryValidator()
    return TransactionService(repo, validator)
```

## 7. 目录结构

```
app/
├── domain/                      # 领域层
│   ├── __init__.py
│   ├── shared/                  # 通用子域
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── value_object.py
│   │   ├── aggregate_root.py
│   │   ├── repository.py
│   │   └── domain_event.py
│   ├── agent/                   # Agent 子域
│   │   ├── __init__.py
│   │   ├── abstract_agent.py
│   │   ├── agent_message.py
│   │   ├── agent_tool.py
│   │   ├── agent_response.py
│   │   └── session.py
│   └── accounting/              # 记账子域
│       ├── __init__.py
│       ├── transaction.py
│       ├── transaction_category.py
│       ├── money.py
│       ├── transaction_repository.py
│       └── transaction_statistics.py
│
├── application/                 # 应用层
│   ├── __init__.py
│   ├── agent/                   # Agent 应用服务
│   │   ├── __init__.py
│   │   ├── agent_service.py
│   │   ├── agent_factory.py
│   │   └── dto.py
│   └── accounting/              # 记账应用服务
│       ├── __init__.py
│       ├── transaction_service.py
│       ├── transaction_dto.py
│       └── transaction_factory.py
│
├── infrastructure/              # 基础设施层
│   ├── __init__.py
│   ├── agent/                   # Agent 实现
│   │   ├── __init__.py
│   │   ├── langgraph/
│   │   │   ├── __init__.py
│   │   │   ├── langgraph_agent.py
│   │   │   ├── tool_adapter.py
│   │   │   └── message_adapter.py
│   │   └── cache/
│   │       ├── __init__.py
│   │       └── agent_cache.py
│   ├── llm/                     # LLM 基础设施
│   │   ├── __init__.py
│   │   ├── llm_factory.py
│   │   └── llm_config.py
│   ├── persistence/             # 持久化
│   │   ├── __init__.py
│   │   ├── sqlite/
│   │   │   ├── __init__.py
│   │   │   ├── sqlite_transaction_repo.py
│   │   │   └── sqlite_client.py
│   │   └── milvus/
│   │       ├── __init__.py
│   │       └── milvus_client.py
│   └── tools/                   # 工具实现
│       ├── __init__.py
│       ├── base_tool.py
│       ├── calculator_tool.py
│       ├── search_tool.py
│       └── tool_registry.py
│
├── interfaces/                  # 接口层
│   ├── __init__.py
│   ├── http/                    # HTTP 接口
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── agent_routes.py
│   │   │   └── accounting_routes.py
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── agent_schemas.py
│   │       └── accounting_schemas.py
│   └── websocket/               # WebSocket 接口（可选）
│
└── config/                      # 配置
    ├── __init__.py
    └── settings.py
```

## 8. 防腐层设计

### 8.1 工具适配器

```python
class ToolAdapter:
    """
    工具适配器
    
    将领域层的 AgentTool 适配为 LangChain 工具
    """
    
    def __init__(self, domain_tool: AgentTool):
        self._domain_tool = domain_tool
    
    def to_langchain_tool(self) -> StructuredTool:
        """转换为 LangChain 工具"""
        from langchain_core.tools import StructuredTool
        
        def _run(**kwargs):
            result = self._domain_tool.execute(**kwargs)
            return result.content
        
        return StructuredTool.from_function(
            func=_run,
            name=self._domain_tool.name,
            description=self._domain_tool.description,
        )
```

### 8.2 消息适配器

```python
class MessageAdapter:
    """
    消息适配器
    
    在 LangGraph 消息和领域消息之间转换
    """
    
    @staticmethod
    def to_domain(message: BaseMessage) -> AgentMessage:
        """转换为领域消息"""
        if isinstance(message, HumanMessage):
            role = MessageRole.USER
        elif isinstance(message, AIMessage):
            role = MessageRole.ASSISTANT
        elif isinstance(message, ToolMessage):
            role = MessageRole.TOOL
        else:
            role = MessageRole.SYSTEM
        
        return AgentMessage(
            role=role,
            content=str(message.content),
        )
    
    @staticmethod
    def from_domain(message: AgentMessage) -> BaseMessage:
        """从领域消息转换"""
        # ... 反向转换逻辑
        pass
```

## 9. 编码规范

### 9.1 文件头模板

```python
"""
模块名称

职责描述...

作者:
日期:
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)
```

### 9.2 命名规范

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 模块 | 小写下划线 | `transaction_repository.py` |
| 类 | 大驼峰 | `TransactionRepository` |
| 函数/方法 | 小写下划线 | `get_by_id` |
| 常量 | 大写下划线 | `MAX_RETRY_COUNT` |
| 私有成员 | 单下划线前缀 | `_id`, `_calculate` |
| 抽象类 | 前缀 `Abstract` | `AbstractAgent` |

### 9.3 导入顺序

```python
# 1. 标准库
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any

# 2. 第三方库
from pydantic import BaseModel

# 3. 应用内部
from app.domain.shared import Entity
from app.domain.agent import AgentTool
```

## 10. 演进策略

### 10.1 增量重构步骤

1. **阶段一：建立领域层抽象**
   - 创建 `domain/shared/` 基础类
   - 创建 `domain/agent/` 抽象
   - 保持现有代码继续运行

2. **阶段二：基础设施层实现**
   - 创建 `infrastructure/agent/langgraph/`
   - 将现有 `ReactAgent` 适配到 `LangGraphAgent`
   - 验证功能等价

3. **阶段三：应用层服务**
   - 创建应用服务编排用例
   - 定义 DTO

4. **阶段四：接口层迁移**
   - 路由使用应用服务
   - 添加依赖注入

5. **阶段五：领域建模**
   - 建立记账领域模型
   - 替换现有的直接数据库操作

### 10.2 回滚策略

- 每个阶段保持向后兼容
- 通过特性开关控制新旧实现切换
- 保留原有代码直到新实现稳定

---

## 附录 A：术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 实体 | Entity | 有唯一标识的对象 |
| 值对象 | Value Object | 基于属性值相等的不可变对象 |
| 聚合根 | Aggregate Root | 聚合的入口实体，事务边界 |
| 仓库 | Repository | 聚合的持久化接口 |
| 领域事件 | Domain Event | 领域内发生的有意义事件 |
| 应用服务 | Application Service | 编排用例的无状态服务 |
| 防腐层 | Anti-Corruption Layer | 隔离外部系统的适配层 |

## 附录 B：参考资料

1. 《领域驱动设计》Eric Evans
2. 《实现领域驱动设计》Vaughn Vernon
3. [Microsoft DDD 架构指南](https://docs.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice)
4. [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
