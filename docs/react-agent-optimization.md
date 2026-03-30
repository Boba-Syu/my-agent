# ReactAgent 优化说明文档

本文档详细记录了 `ReactAgent` 核心模块的优化内容，包括性能改进、功能增强和架构优化。

---

## 一、优化概览

| 优先级 | 优化项 | 文件 | 状态 |
|--------|--------|------|------|
| P0 | Agent 实例缓存 | `accounting_agent.py` | ✅ 已完成 |
| P0 | 异步流式调用 | `react_agent.py` | ✅ 已完成 |
| P0 | recursion_limit 配置 | `react_agent.py` | ✅ 已完成 |
| P1 | 错误处理与超时 | `react_agent.py` | ✅ 已完成 |
| P1 | 工具调用状态推送 | `accounting_routes.py` | ✅ 已完成 |
| P1 | 系统提示词动态刷新 | `accounting_agent.py` | ✅ 已完成 |
| P2 | 工具管理完善 | `react_agent.py` | ✅ 已完成 |
| P2 | reasoning_content 过滤 | `react_agent.py` | ✅ 已完成 |

---

## 二、详细优化说明

### 2.1 Agent 实例缓存（P0）

#### 问题
每次 HTTP 请求都重新调用 `create_accounting_agent()`，导致：
- 重新编译 LangGraph 状态图（耗时）
- 重新初始化数据库表
- 高并发下性能瓶颈

#### 解决方案
在 `accounting_agent.py` 中实现按 `(model, date)` 的缓存机制：

```python
# 全局缓存
_agent_cache: dict[tuple[str, date], ReactAgent] = {}
_cache_lock = threading.Lock()

def create_accounting_agent(model: str = "deepseek-v3") -> ReactAgent:
    cache_key = _get_cache_key(model)  # (model, date.today())

    if cache_key in _agent_cache:
        return _agent_cache[cache_key]  # 命中缓存

    with _cache_lock:
        # 创建新实例并缓存
        agent = _create_agent_instance(model)
        _agent_cache[cache_key] = agent
        return agent
```

#### 优势
- **同一天内复用 Agent**：同一 model 在同一天内只创建一次
- **自动日期刷新**：每天首次请求自动创建新 Agent（更新提示词中的日期）
- **线程安全**：使用 `threading.Lock()` 保证并发安全
- **自动清理**：保留最近 7 天缓存，防止内存泄漏

#### 缓存管理接口
```python
# 获取缓存状态
GET /api/v1/accounting/admin/cache

# 清空缓存（热更新用）
POST /api/v1/accounting/admin/cache/clear
```

---

### 2.2 异步流式调用 `astream()`（P0）

#### 问题
原 `stream()` 方法是同步生成器：

```python
# 问题代码
for chunk in agent.stream(...):  # 同步迭代会阻塞 asyncio 事件循环！
    yield chunk
```

在 FastAPI 的 async 路由中，同步的 `for` 循环会阻塞整个事件循环，**导致其他并发请求被挂起**。

#### 解决方案
添加异步流式方法 `astream()`：

```python
async def astream(self, message: str, thread_id: str = "default"):
    """异步流式调用，适用于 FastAPI SSE 场景"""
    async for chunk in self._graph.astream(state, config=config, stream_mode="values"):
        yield chunk
```

路由层使用 `async for`：

```python
async for chunk in agent.astream(...):  # 不阻塞事件循环
    yield chunk
```

#### 优势
- **非阻塞 I/O**：不阻塞 asyncio 事件循环
- **高并发友好**：多个 SSE 连接可同时处理
- **错误处理**：内置异常捕获，返回 `[ERROR]` 标记

---

### 2.3 recursion_limit 配置（P0）

#### 问题
原代码从配置读取了 `max_iterations`，但未实际传递给 LangGraph：

```python
self._max_iterations = agent_cfg.get("max_iterations", 10)
# ... 但 _build_graph() 中没有使用
```

#### 解决方案
在每次调用时通过 `config` 传入 `recursion_limit`：

```python
def _get_config(self, thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": self._max_iterations,
    }

def invoke(self, message: str, thread_id: str = "default") -> str:
    config = self._get_config(thread_id)  # 包含 recursion_limit
    result = self._graph.invoke(state, config=config)
```

#### 配置
在 `application.toml` 中设置：

```toml
[agent]
max_iterations = 10  # ReAct 循环最大步数
timeout = 120        # 整体调用超时（秒）
```

---

### 2.4 错误处理与超时控制（P1）

#### 新增功能
1. **整体超时控制**：`asyncio.wait_for()` 包装调用
2. **优雅降级**：异常时返回用户友好的错误信息
3. **分类错误处理**：针对超时、限流、内容过滤等场景

```python
async def ainvoke(self, message: str, thread_id: str = "default") -> str:
    try:
        result = await asyncio.wait_for(
            self._graph.ainvoke(state, config=config),
            timeout=self._timeout
        )
        reply = self._extract_reply(result)
    except asyncio.TimeoutError as e:
        reply = self._handle_exception(e, "ainvoke")  # "处理时间过长，请稍后再试"
    except Exception as e:
        reply = self._handle_exception(e, "ainvoke")  # 统一处理
```

#### 错误类型映射
| 异常类型 | 用户提示 |
|----------|----------|
| TimeoutError | "处理时间过长，请稍后再试或简化您的问题" |
| Rate Limit | "服务繁忙，请稍后再试" |
| Content Filter | "您的输入可能包含敏感内容，请修改后重试" |
| 其他 | "处理过程中出现了问题，请重试" |

---

### 2.5 工具调用状态推送（P1）

#### 功能
SSE 流式输出不仅返回最终回复，还推送中间工具调用状态，前端可展示"正在记录..."等加载状态。

#### SSE 消息格式
```
data: 你好！我来帮您
data: 记录这笔支出。

data: [TOOL_CALL] {"name": "add_transaction", "args": {...}}
data: [TOOL_RESULT] {"name": "add_transaction", "result": "✅ 记账成功"}
data: 已为您记录支出...

data: [DONE]
```

#### 前端处理示例
```javascript
eventSource.onmessage = (event) => {
    const data = event.data;

    if (data.startsWith('[TOOL_CALL]')) {
        showLoadingState('正在处理...');
    } else if (data.startsWith('[TOOL_RESULT]')) {
        updateLoadingState(JSON.parse(data.slice(13)));
    } else if (data === '[DONE]') {
        hideLoadingState();
    } else if (data.startsWith('[ERROR]')) {
        showError(data.slice(7));
    } else {
        appendMessage(data);  // 正常内容
    }
};
```

---

### 2.6 系统提示词动态刷新（P1）

#### 问题
原提示词中的日期在 Agent 创建时硬编码：

```python
def _build_system_prompt() -> str:
    today_str = datetime.now().strftime("%Y-%m-%d")
    return f"...今天日期：{today_str}..."
```

如果缓存 Agent，跨天后提示词中的"今天"就过期了。

#### 解决方案
按 `(model, date)` 缓存，每天自动创建新 Agent：

```python
def _get_cache_key(model: str) -> tuple[str, date]:
    return (model, date.today())  # 按天缓存

def create_accounting_agent(model: str = "deepseek-v3") -> ReactAgent:
    cache_key = _get_cache_key(model)
    # 今天第一次调用 → 创建新 Agent（最新日期）
    # 今天后续调用 → 复用缓存 Agent
```

---

### 2.7 工具管理完善（P2）

#### 改进点
1. **`add_tools()` 返回结果**：
   ```python
   result = agent.add_tools([new_tool1, new_tool2])
   # result = {"added": ["tool1"], "skipped": ["tool2"], "total": 11}
   ```

2. **新增 `remove_tools()` 方法**：
   ```python
   result = agent.remove_tools(["tool_name"])
   # result = {"removed": ["tool_name"], "not_found": [], "total": 10}
   ```

3. **工具列表副本保护**：
   ```python
   self._tools = list(tools)  # 创建副本，避免外部修改影响内部状态
   ```

---

### 2.8 reasoning_content 过滤（P2）

#### 问题
deepseek-r1 模型返回的 content 可能包含推理过程：

```python
[
    {"type": "reasoning", "text": "用户说要记账，我需要..."},
    {"type": "text", "text": "已为您记录支出..."}
]
```

原代码会把两者都拼接，导致回复中包含推理过程。

#### 解决方案
在 `_extract_reply` 和 `_log_messages` 中过滤 `type: reasoning`：

```python
text_parts = [
    part.get("text", "")
    for part in msg.content
    if isinstance(part, dict) and part.get("type") != "reasoning"
]
return "".join(text_parts).strip()
```

---

## 三、新增配置项

在 `application.toml` 的 `[agent]` 节中新增：

```toml
[agent]
default_system_prompt = "You are a helpful assistant."
max_iterations = 10      # ReAct 循环最大步数（防止无限循环）
timeout = 120            # 异步调用整体超时（秒）
```

---

## 四、API 变更

### 4.1 新增接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/accounting/admin/cache` | GET | 获取 Agent 缓存状态 |
| `/api/v1/accounting/admin/cache/clear` | POST | 清空 Agent 缓存 |

### 4.2 SSE 消息格式扩展

| 消息类型 | 格式 | 说明 |
|----------|------|------|
| 正常内容 | `data: 内容\n\n` | 普通回复文本 |
| 工具调用 | `data: [TOOL_CALL] {"name": "..."}\n\n` | 开始调用工具 |
| 工具结果 | `data: [TOOL_RESULT] {"name": "..."}\n\n` | 工具返回结果 |
| 完成 | `data: [DONE]\n\n` | 流式输出结束 |
| 错误 | `data: [ERROR] 错误信息\n\n` | 发生错误 |

---

## 五、使用建议

### 5.1 Agent 缓存策略
- 正常情况无需干预，缓存自动按天刷新
- 修改工具或提示词后，调用 `POST /admin/cache/clear` 热更新
- 监控缓存状态：调用 `GET /admin/cache`

### 5.2 流式输出
- 优先使用异步 `astream()` 而非 `stream()`
- 前端应处理 `[TOOL_CALL]` / `[TOOL_RESULT]` 展示加载状态
- 超时时间可在配置中调整，默认为 120 秒

### 5.3 错误处理
- 无需额外 try-except，Agent 层已统一处理
- 如需自定义错误处理，可在路由层捕获后二次处理

---

## 六、性能对比

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 首次请求 | 建表 + 编译图 + LLM 调用 | 相同 | - |
| 同日复用 | 建表 + 编译图 + LLM 调用 | LLM 调用 | ~50-100ms |
| 并发 SSE | 阻塞事件循环 | 非阻塞 | 并发能力大幅提升 |

---

## 七、注意事项

1. **缓存过期**：缓存按天刷新，跨天后的首次请求会创建新 Agent
2. **内存占用**：缓存保留最近 7 天的 Agent，每天每个 model 约占用 50-100MB
3. **配置热加载**：修改 `max_iterations` / `timeout` 后需清空缓存生效
4. **向后兼容**：`stream()` 方法仍保留，但不推荐在 FastAPI async 路由中使用
