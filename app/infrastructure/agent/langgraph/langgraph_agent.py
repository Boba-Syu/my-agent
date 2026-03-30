"""
LangGraph Agent 实现

将 LangGraph 框架适配到领域层的 AbstractAgent 抽象。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from app.domain.agent.abstract_agent import AbstractAgent
from app.domain.agent.agent_message import AgentMessage, MessageRole, ToolCall
from app.domain.agent.agent_response import (
    AgentChunk,
    AgentResponse,
    ChunkType,
    ToolResult,
    ToolUpdateResult,
)
from app.domain.agent.agent_tool import AgentTool
from app.infrastructure.agent.langgraph.tool_adapter import ToolAdapter
from app.infrastructure.llm.llm_provider import LLMConfig

logger = logging.getLogger(__name__)


class LangGraphAgent(AbstractAgent):
    """
    LangGraph 实现的 Agent
    
    将 LangGraph 框架适配到领域层的 AbstractAgent 抽象，
    实现底层框架与业务逻辑的解耦。
    
    Example:
        agent = LangGraphAgent(
            llm_config=LLMConfig(model="deepseek-v3"),
            system_prompt="你是一个记账助手",
            tool_adapters=[ToolAdapter(CalculatorTool())],
        )
        
        response = await agent.ainvoke("计算 100 + 50", "session-001")
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str,
        tool_adapters: list[ToolAdapter] | None = None,
        max_iterations: int = 10,
        timeout: int = 120,
    ):
        """
        初始化 LangGraph Agent
        
        Args:
            llm_config: LLM 配置
            system_prompt: 系统提示词
            tool_adapters: 工具适配器列表
            max_iterations: 最大迭代次数
            timeout: 超时时间（秒）
        """
        super().__init__(system_prompt, max_iterations, timeout)
        
        self._llm_config = llm_config
        self._tool_adapters = tool_adapters or []
        self._tools: list[AgentTool] = [
            adapter._domain_tool for adapter in self._tool_adapters
        ]
        
        # 初始化 LangGraph
        self._llm = self._create_llm()
        self._graph = self._build_graph()
        
        logger.info(
            f"LangGraphAgent 初始化完成: model={llm_config.model}, "
            f"tools={[t.name for t in self._tools]}"
        )

    def _create_llm(self) -> ChatOpenAI:
        """
        创建 LLM 实例
        
        Returns:
            LangChain ChatOpenAI 实例
        """
        return ChatOpenAI(
            model=self._llm_config.model,
            api_key=self._llm_config.api_key,
            base_url=self._llm_config.base_url,
            timeout=self._llm_config.timeout,
            max_tokens=self._llm_config.max_tokens,
            temperature=self._llm_config.temperature,
        )

    def _build_graph(self) -> CompiledStateGraph:
        """
        构建 LangGraph 状态图
        
        Returns:
            编译后的状态图
        """
        langchain_tools = [
            adapter.to_langchain_tool() for adapter in self._tool_adapters
        ]
        
        return create_react_agent(
            model=self._llm,
            tools=langchain_tools,
            prompt=self._system_prompt,
        )

    def _create_config(self, thread_id: str) -> dict[str, Any]:
        """
        创建调用配置
        
        Args:
            thread_id: 会话线程 ID
            
        Returns:
            LangGraph 配置字典
        """
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": self._max_iterations,
        }

    def _extract_reply(self, messages: list[Any]) -> str:
        """
        从消息列表中提取最终回复
        
        Args:
            messages: LangGraph 消息列表
            
        Returns:
            最终回复文本
        """
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                tool_calls = getattr(msg, "tool_calls", None) or []
                if not tool_calls:  # 没有工具调用的是最终回复
                    content = msg.content
                    if isinstance(content, list):
                        # 处理 deepseek-r1 等多内容格式
                        return "".join(
                            p.get("text", "")
                            for p in content
                            if isinstance(p, dict) and p.get("type") != "reasoning"
                        ).strip()
                    return str(content).strip()
        return "Agent 未能生成回复"

    def _extract_tool_calls(self, messages: list[Any]) -> list[ToolCall]:
        """
        提取工具调用信息
        
        Args:
            messages: 消息列表
            
        Returns:
            工具调用列表
        """
        tool_calls = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                calls = getattr(msg, "tool_calls", None) or []
                for tc in calls:
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {}),
                    ))
        return tool_calls

    def _convert_messages(self, messages: list[Any]) -> list[AgentMessage]:
        """
        将 LangGraph 消息转换为领域消息
        
        Args:
            messages: LangGraph 消息列表
            
        Returns:
            领域消息列表
        """
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = MessageRole.USER
                content = str(msg.content)
                tool_calls = None
            elif isinstance(msg, AIMessage):
                role = MessageRole.ASSISTANT
                content = str(msg.content) if isinstance(msg.content, str) else ""
                calls = getattr(msg, "tool_calls", None) or []
                tool_calls = [
                    ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {}),
                    )
                    for tc in calls
                ] or None
            elif isinstance(msg, ToolMessage):
                role = MessageRole.TOOL
                content = str(msg.content)
                tool_calls = None
            else:
                role = MessageRole.SYSTEM
                content = str(msg.content)
                tool_calls = None
            
            result.append(AgentMessage(
                role=role,
                content=content,
                tool_calls=tool_calls,
            ))
        return result

    # -------------------------------------------------------------------------
    # AbstractAgent 实现
    # -------------------------------------------------------------------------

    def invoke(self, message: str, thread_id: str) -> AgentResponse:
        """同步调用 Agent"""
        logger.info(f"LangGraphAgent.invoke: thread={thread_id}")
        
        config = self._create_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}
        
        try:
            result = self._graph.invoke(state, config=config)
            messages = result.get("messages", [])
            
            reply = self._extract_reply(messages)
            tool_calls = self._extract_tool_calls(messages)
            domain_messages = self._convert_messages(messages)
            
            return AgentResponse(
                content=reply,
                messages=domain_messages,
                tool_calls=tool_calls,
                metadata={
                    "model": self._llm_config.model,
                    "thread_id": thread_id,
                },
            )
        except Exception as e:
            logger.error(f"Agent 调用失败: {e}", exc_info=True)
            raise

    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """异步调用 Agent"""
        logger.info(f"LangGraphAgent.ainvoke: thread={thread_id}")
        
        config = self._create_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}
        
        try:
            result = await asyncio.wait_for(
                self._graph.ainvoke(state, config=config),
                timeout=self._timeout,
            )
            messages = result.get("messages", [])
            
            reply = self._extract_reply(messages)
            tool_calls = self._extract_tool_calls(messages)
            domain_messages = self._convert_messages(messages)
            
            return AgentResponse(
                content=reply,
                messages=domain_messages,
                tool_calls=tool_calls,
                metadata={
                    "model": self._llm_config.model,
                    "thread_id": thread_id,
                },
            )
        except asyncio.TimeoutError:
            logger.error(f"Agent 调用超时: {thread_id}")
            raise TimeoutError(f"处理时间超过 {self._timeout} 秒")
        except Exception as e:
            logger.error(f"Agent 调用失败: {e}", exc_info=True)
            raise

    def stream(self, message: str, thread_id: str) -> Iterator[AgentChunk]:
        """同步流式调用"""
        logger.info(f"LangGraphAgent.stream: thread={thread_id}")
        
        config = self._create_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}
        
        try:
            for chunk in self._graph.stream(state, config=config, stream_mode="values"):
                messages = chunk.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        tool_calls = getattr(last_msg, "tool_calls", None) or []
                        content = last_msg.content
                        
                        if isinstance(content, list):
                            content = "".join(
                                p.get("text", "")
                                for p in content
                                if isinstance(p, dict) and p.get("type") != "reasoning"
                            )
                        
                        if tool_calls:
                            for tc in tool_calls:
                                yield AgentChunk.tool_call_chunk(
                                    ToolCall(
                                        id=tc.get("id", ""),
                                        name=tc.get("name", ""),
                                        arguments=tc.get("args", {}),
                                    )
                                )
                        elif content:
                            yield AgentChunk.content_chunk(str(content))
            
            yield AgentChunk.done_chunk()
        except Exception as e:
            logger.error(f"流式调用失败: {e}", exc_info=True)
            yield AgentChunk.error_chunk(str(e))

    async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
        """异步流式调用"""
        logger.info(f"LangGraphAgent.astream: thread={thread_id}")
        
        config = self._create_config(thread_id)
        state = {"messages": [HumanMessage(content=message)]}
        
        try:
            async for chunk in self._graph.astream(state, config=config, stream_mode="values"):
                messages = chunk.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        tool_calls = getattr(last_msg, "tool_calls", None) or []
                        content = last_msg.content
                        
                        if isinstance(content, list):
                            content = "".join(
                                p.get("text", "")
                                for p in content
                                if isinstance(p, dict) and p.get("type") != "reasoning"
                            )
                        
                        if tool_calls:
                            for tc in tool_calls:
                                yield AgentChunk.tool_call_chunk(
                                    ToolCall(
                                        id=tc.get("id", ""),
                                        name=tc.get("name", ""),
                                        arguments=tc.get("args", {}),
                                    )
                                )
                        elif content:
                            yield AgentChunk.content_chunk(str(content))
            
            yield AgentChunk.done_chunk()
        except Exception as e:
            logger.error(f"异步流式调用失败: {e}", exc_info=True)
            yield AgentChunk.error_chunk(str(e))

    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """动态添加工具"""
        existing_names = {t.name for t in self._tools}
        added = []
        skipped = []
        
        for tool in tools:
            if tool.name not in existing_names:
                self._tools.append(tool)
                self._tool_adapters.append(ToolAdapter(tool))
                added.append(tool.name)
                existing_names.add(tool.name)
            else:
                skipped.append(tool.name)
        
        if added:
            # 重新构建图
            self._graph = self._build_graph()
            logger.info(f"已添加工具: {added}")
        
        return ToolUpdateResult(
            success=added,
            skipped=skipped,
            total=len(self._tools),
        )

    def remove_tools(self, tool_names: list[str]) -> ToolUpdateResult:
        """动态移除工具"""
        names_to_remove = set(tool_names)
        removed = []
        not_found = []
        
        new_tools = []
        new_adapters = []
        
        for tool, adapter in zip(self._tools, self._tool_adapters):
            if tool.name in names_to_remove:
                removed.append(tool.name)
                names_to_remove.discard(tool.name)
            else:
                new_tools.append(tool)
                new_adapters.append(adapter)
        
        not_found = list(names_to_remove)
        
        if removed:
            self._tools = new_tools
            self._tool_adapters = new_adapters
            self._graph = self._build_graph()
            logger.info(f"已移除工具: {removed}")
        
        return ToolUpdateResult(
            success=removed,
            skipped=not_found,
            total=len(self._tools),
        )

    def update_system_prompt(self, prompt: str) -> None:
        """更新系统提示词"""
        self._system_prompt = prompt
        self._graph = self._build_graph()
        logger.info("系统提示词已更新")

    @property
    def tools(self) -> list[AgentTool]:
        """当前工具列表"""
        return list(self._tools)
