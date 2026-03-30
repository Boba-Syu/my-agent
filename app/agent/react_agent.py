"""
ReAct Agent 核心模块

基于 LangGraph 的 create_react_agent 实现，封装为可配置类。
支持自定义系统提示词、工具列表、LLM 实例，提供同步/异步调用接口。

ReAct 推理流程：
    用户输入 → [推理] → [选择工具] → [执行工具] → [观察结果] → [继续推理/输出最终答案]
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

from app.config import get_agent_config
from app.utils.logging_utils import get_trace_id

logger = logging.getLogger(__name__)


class ReactAgent:
    """
    ReAct 架构 Agent 类

    封装 LangGraph create_react_agent，提供：
    - 可配置的系统提示词
    - 可配置的工具列表（支持 LangChain tool / MCP tool / Skill tool）
    - 同步 invoke / 异步 ainvoke / 流式 stream / 异步流式 astream 多种调用方式
    - 多轮对话支持（通过 thread_id 区分会话）
    - 完善的错误处理和超时控制
    - 动态工具管理（添加/移除）

    使用示例:
        from app.llm.llm_factory import LLMFactory
        from app.tools import ALL_TOOLS

        llm = LLMFactory.create_llm("deepseek-v3")
        agent = ReactAgent(llm=llm, tools=ALL_TOOLS)

        # 单轮对话
        reply = agent.invoke("计算 123 * 456 等于多少？")
        print(reply)

        # 多轮对话（使用相同 thread_id）
        reply1 = agent.invoke("我叫张三", thread_id="user-001")
        reply2 = agent.invoke("我叫什么名字？", thread_id="user-001")

        # 异步流式调用（FastAPI SSE 推荐）
        async for chunk in agent.astream("查询我的记录", thread_id="user-001"):
            yield chunk
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        tools: list,
        system_prompt: str | None = None,
    ) -> None:
        """
        初始化 ReAct Agent

        Args:
            llm:           LLM 实例（ChatOpenAI，兼容阿里百炼）
            tools:         工具列表（LangChain @tool / StructuredTool 等）
            system_prompt: 系统提示词，为 None 时使用配置文件默认值
        """
        agent_cfg = get_agent_config()

        self._llm = llm
        self._tools = list(tools)  # 创建副本，避免外部修改影响内部状态
        self._system_prompt = system_prompt or agent_cfg.get(
            "default_system_prompt", "You are a helpful assistant."
        )
        self._max_iterations = agent_cfg.get("max_iterations", 10)
        self._timeout = agent_cfg.get("timeout", 120)  # 默认整体超时 120 秒

        # 编译 LangGraph ReAct 图
        self._graph: CompiledStateGraph = self._build_graph()

        logger.info(
            f"ReactAgent 初始化完成：model={llm.model_name}, "
            f"tools={[t.name for t in tools]}, "
            f"max_iterations={self._max_iterations}, timeout={self._timeout}s"
        )

    def _build_graph(self) -> CompiledStateGraph:
        """
        构建并编译 LangGraph ReAct 状态图

        Returns:
            已编译的 CompiledGraph，可直接调用 invoke/stream
        """
        return create_react_agent(
            model=self._llm,
            tools=self._tools,
            prompt=self._system_prompt,
        )

    def _get_config(self, thread_id: str) -> dict[str, Any]:
        """
        构建调用配置，包含 thread_id 和 recursion_limit

        Args:
            thread_id: 会话线程 ID

        Returns:
            LangGraph 调用配置字典
        """
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": self._max_iterations,
        }

    def _extract_reply(self, result: dict[str, Any]) -> str:
        """
        从 LangGraph 输出中提取最终回复文本

        Args:
            result: LangGraph invoke 返回的状态字典

        Returns:
            AI 最终回复的文本内容
        """
        messages: list[BaseMessage] = result.get("messages", [])
        # 从后往前找最后一条 AI 消息
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # 处理 content 为列表的情况（如 deepseek-r1 包含推理过程）
                if isinstance(msg.content, list):
                    # 过滤掉 reasoning 类型的内容块，只保留 text 类型
                    text_parts = [
                        part.get("text", "")
                        for part in msg.content
                        if isinstance(part, dict) and part.get("type") != "reasoning"
                    ]
                    return "".join(text_parts).strip()
                return str(msg.content).strip()
        return "Agent 未能生成回复"

    def _log_messages(self, messages: list[BaseMessage]) -> None:
        """
        遍历消息列表，只打印工具调用过程和最终 AI 回复，不输出中间推理流。

        - AIMessage 带 tool_calls → 打印工具名称和入参（中间推理步骤）
        - ToolMessage             → 打印工具返回结果
        - AIMessage 无 tool_calls → 打印最终完整输出
        """
        tid = get_trace_id()
        for msg in messages:
            if isinstance(msg, AIMessage):
                tool_calls = getattr(msg, "tool_calls", None) or []
                if tool_calls:
                    for tc in tool_calls:
                        logger.info(
                            "[tid=%s] 🔧 调用工具: %s | 入参: %s",
                            tid, tc.get("name", "?"), tc.get("args", {}),
                        )
                else:
                    # 最终完整回复
                    content = msg.content
                    if isinstance(content, list):
                        # 过滤 reasoning 类型
                        content = "".join(
                            p.get("text", "")
                            for p in content
                            if isinstance(p, dict) and p.get("type") != "reasoning"
                        ).strip()
                    if content:
                        logger.info("[tid=%s] 🤖 LLM最终输出: %s", tid, content)
            elif isinstance(msg, ToolMessage):
                result_preview = str(msg.content)[:200]
                logger.info(
                    "[tid=%s] 📦 工具返回 [%s]: %s%s",
                    tid, msg.name, result_preview,
                    "..." if len(str(msg.content)) > 200 else "",
                )

    def _handle_exception(self, e: Exception, operation: str) -> str:
        """
        统一处理异常，返回用户友好的错误信息

        Args:
            e: 捕获的异常
            operation: 当前操作名称

        Returns:
            用户友好的错误提示
        """
        tid = get_trace_id()
        error_msg = str(e)

        if isinstance(e, asyncio.TimeoutError):
            logger.error("[tid=%s] ❌ %s 超时", tid, operation)
            return "抱歉，处理时间过长，请稍后再试或简化您的问题。"
        elif "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
            logger.error("[tid=%s] ❌ %s 触发限流: %s", tid, operation, error_msg[:200])
            return "服务繁忙，请稍后再试。"
        elif "content filter" in error_msg.lower():
            logger.error("[tid=%s] ❌ %s 内容被过滤", tid, operation)
            return "您的输入可能包含敏感内容，请修改后重试。"
        else:
            logger.error("[tid=%s] ❌ %s 异常: %s", tid, operation, error_msg, exc_info=True)
            return f"处理过程中出现了问题，请重试。错误: {error_msg[:100]}"

    def invoke(self, message: str, thread_id: str = "default") -> str:
        """
        同步调用 Agent（阻塞）

        Args:
            message:   用户输入的消息
            thread_id: 会话线程 ID，相同 ID 的对话共享上下文

        Returns:
            Agent 最终回复的文本
        """
        tid = get_trace_id()
        logger.info("[tid=%s] ▶ invoke 开始 | thread=%s | input: %s", tid, thread_id, message[:200])
        t0 = time.monotonic()

        config = self._get_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}

        try:
            result = self._graph.invoke(state, config=config)
            reply = self._extract_reply(result)
            self._log_messages(result.get("messages", []))
        except Exception as e:
            reply = self._handle_exception(e, "invoke")

        elapsed = time.monotonic() - t0
        logger.info("[tid=%s] ✅ invoke 完成 | thread=%s | 耗时=%.2fs | 回复长度=%d字",
                    tid, thread_id, elapsed, len(reply))
        return reply

    async def ainvoke(self, message: str, thread_id: str = "default") -> str:
        """
        异步调用 Agent（非阻塞，适用于 FastAPI async 路由）

        Args:
            message:   用户输入的消息
            thread_id: 会话线程 ID

        Returns:
            Agent 最终回复的文本
        """
        tid = get_trace_id()
        logger.info("[tid=%s] ▶ ainvoke 开始 | thread=%s | input: %s", tid, thread_id, message[:200])
        t0 = time.monotonic()

        config = self._get_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}

        try:
            result = await asyncio.wait_for(
                self._graph.ainvoke(state, config=config),
                timeout=self._timeout
            )
            reply = self._extract_reply(result)
            self._log_messages(result.get("messages", []))
        except asyncio.TimeoutError as e:
            reply = self._handle_exception(e, "ainvoke")
        except Exception as e:
            reply = self._handle_exception(e, "ainvoke")

        elapsed = time.monotonic() - t0
        logger.info("[tid=%s] ✅ ainvoke 完成 | thread=%s | 耗时=%.2fs | 回复长度=%d字",
                    tid, thread_id, elapsed, len(reply))
        return reply

    def stream(self, message: str, thread_id: str = "default"):
        """
        流式调用 Agent，逐步返回中间步骤和最终结果

        Args:
            message:   用户输入的消息
            thread_id: 会话线程 ID

        Yields:
            每个中间步骤的状态字典

        Note:
            此方法为同步生成器，在 FastAPI async 路由中请使用 astream()
        """
        tid = get_trace_id()
        logger.info("[tid=%s] ▶ stream 开始 | thread=%s | input: %s", tid, thread_id, message[:200])
        t0 = time.monotonic()

        config = self._get_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}

        last_messages: list[BaseMessage] = []
        try:
            for chunk in self._graph.stream(state, config=config, stream_mode="values"):
                last_messages = chunk.get("messages", [])
                yield chunk
        except Exception as e:
            logger.error("[tid=%s] ❌ stream 异常: %s", tid, str(e), exc_info=True)
            raise  # 流式错误需要上游处理

        # 流结束后统一打印工具调用 + 最终输出
        self._log_messages(last_messages)
        elapsed = time.monotonic() - t0
        logger.info("[tid=%s] ✅ stream 完成 | thread=%s | 耗时=%.2fs", tid, thread_id, elapsed)

    async def astream(self, message: str, thread_id: str = "default"):
        """
        异步流式调用 Agent，逐步返回中间步骤和最终结果（推荐用于 FastAPI SSE）

        Args:
            message:   用户输入的消息
            thread_id: 会话线程 ID

        Yields:
            每个中间步骤的状态字典

        Example:
            async for chunk in agent.astream("查询记录", thread_id="user-001"):
                msg = chunk.get("messages", [])[-1] if chunk.get("messages") else None
                if isinstance(msg, AIMessage):
                    print(msg.content)
        """
        tid = get_trace_id()
        logger.info("[tid=%s] ▶ astream 开始 | thread=%s | input: %s", tid, thread_id, message[:200])
        t0 = time.monotonic()

        config = self._get_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}

        last_messages: list[BaseMessage] = []
        try:
            async for chunk in self._graph.astream(state, config=config, stream_mode="values"):
                last_messages = chunk.get("messages", [])
                yield chunk
        except Exception as e:
            logger.error("[tid=%s] ❌ astream 异常: %s", tid, str(e), exc_info=True)
            # 生成一个错误标记，上游可以识别
            yield {"__error__": self._handle_exception(e, "astream")}
            return

        # 流结束后统一打印工具调用 + 最终输出
        self._log_messages(last_messages)
        elapsed = time.monotonic() - t0
        logger.info("[tid=%s] ✅ astream 完成 | thread=%s | 耗时=%.2fs", tid, thread_id, elapsed)

    def update_system_prompt(self, new_prompt: str) -> None:
        """
        动态更新系统提示词并重新编译 Agent 图

        Args:
            new_prompt: 新的系统提示词
        """
        self._system_prompt = new_prompt
        self._graph = self._build_graph()
        logger.info("系统提示词已更新，Agent 图已重新编译")

    def add_tools(self, new_tools: list) -> dict[str, Any]:
        """
        动态添加工具并重新编译 Agent 图

        Args:
            new_tools: 需要添加的工具列表

        Returns:
            添加结果字典，包含 added（成功添加的工具名列表）和 skipped（因重名跳过的工具名列表）
        """
        existing_names = {t.name for t in self._tools}
        added = []
        skipped = []

        for tool in new_tools:
            if tool.name not in existing_names:
                self._tools.append(tool)
                added.append(tool.name)
                existing_names.add(tool.name)  # 防止同一批内有重复
            else:
                skipped.append(tool.name)

        if added:
            self._graph = self._build_graph()
            logger.info(f"已添加工具：{added}，Agent 图已重新编译")
        if skipped:
            logger.warning(f"跳过重名工具：{skipped}")

        return {"added": added, "skipped": skipped, "total": len(self._tools)}

    def remove_tools(self, tool_names: list[str]) -> dict[str, Any]:
        """
        动态移除工具并重新编译 Agent 图

        Args:
            tool_names: 需要移除的工具名称列表

        Returns:
            移除结果字典，包含 removed（成功移除的工具名列表）和 not_found（未找到的工具名列表）
        """
        names_to_remove = set(tool_names)
        removed = []
        not_found = []

        new_tools = []
        for tool in self._tools:
            if tool.name in names_to_remove:
                removed.append(tool.name)
                names_to_remove.discard(tool.name)
            else:
                new_tools.append(tool)

        # 记录未找到的工具
        not_found = list(names_to_remove)

        if removed:
            self._tools = new_tools
            self._graph = self._build_graph()
            logger.info(f"已移除工具：{removed}，Agent 图已重新编译")
        if not_found:
            logger.warning(f"未找到工具：{not_found}")

        return {"removed": removed, "not_found": not_found, "total": len(self._tools)}

    @property
    def tools(self) -> list:
        """返回当前工具列表副本"""
        return list(self._tools)

    @property
    def system_prompt(self) -> str:
        """返回当前系统提示词"""
        return self._system_prompt

    @property
    def max_iterations(self) -> int:
        """返回当前最大迭代次数"""
        return self._max_iterations

    @property
    def timeout(self) -> int:
        """返回当前超时时间（秒）"""
        return self._timeout
