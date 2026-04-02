"""
Agno Agent 实现

将 Agno 框架适配到领域层的 AbstractAgent 抽象。

Agno 是一个轻量级、高性能的 Agent 框架，
此实现展示了如何轻松替换底层 Agent 框架。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

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
from app.infrastructure.llm.llm_provider import LLMConfig

logger = logging.getLogger(__name__)


class AgnoAgent(AbstractAgent):
    """
    Agno 实现的 Agent
    
    将 Agno 框架适配到领域层的 AbstractAgent 抽象，
    展示如何轻松替换底层 Agent 框架。
    
    Agno 特点：
    - 轻量级，高性能
    - 原生支持流式输出
    - 简洁的工具定义方式
    - 支持多种 LLM 后端
    
    Example:
        agent = AgnoAgent(
            llm_config=LLMConfig(model="deepseek-v3"),
            system_prompt="你是一个记账助手",
            tools=[CalculatorTool()],
        )
        
        response = await agent.ainvoke("计算 100 + 50", "session-001")
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str,
        tools: list[AgentTool] | None = None,
        max_iterations: int = 10,
        timeout: int = 120,
    ):
        """
        初始化 Agno Agent
        
        Args:
            llm_config: LLM 配置
            system_prompt: 系统提示词
            tools: 工具列表
            max_iterations: 最大迭代次数
            timeout: 超时时间（秒）
        """
        super().__init__(system_prompt, max_iterations, timeout)
        
        self._llm_config = llm_config
        self._tools: list[AgentTool] = tools or []
        self._agent = self._create_agent()
        
        logger.info(
            f"AgnoAgent 初始化完成: model={llm_config.model}, "
            f"tools={[t.name for t in self._tools]}"
        )

    def _create_agent(self) -> Any:
        """
        创建 Agno Agent 实例
        
        Returns:
            Agno Agent 实例
        """
        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
        except ImportError:
            logger.error("Agno 未安装，请运行: uv add agno")
            raise

        # 创建 Agno 工具
        agno_tools = self._convert_tools_to_agno()

        # 创建 Agno Agent
        # 注意：阿里百炼 API 不支持 developer 角色，需要覆盖 role_map
        # OpenAIChat 默认将 "system" 映射为 "developer"，我们需要改回 "system"
        return Agent(
            model=OpenAIChat(
                id=self._llm_config.model,
                api_key=self._llm_config.api_key,
                base_url=self._llm_config.base_url,
                # 覆盖 role_map，将 system 角色保持为 system，而不是 developer
                role_map={
                    "system": "system",
                    "user": "user",
                    "assistant": "assistant",
                    "tool": "tool",
                    "model": "assistant",
                },
            ),
            tools=agno_tools,
            description=self._system_prompt,
            markdown=True,
        )

    def _convert_tools_to_agno(self) -> list[Any]:
        """
        将领域层工具转换为 Agno 工具
        
        Returns:
            Agno 工具列表
        """
        try:
            from agno.tools import Toolkit
        except ImportError:
            return []

        agno_tools = []
        
        for tool in self._tools:
            # 创建 Agno 工具包装器
            agno_tool = self._wrap_tool_for_agno(tool)
            if agno_tool:
                agno_tools.append(agno_tool)
        
        return agno_tools

    def _wrap_tool_for_agno(self, tool: AgentTool) -> Any:
        """
        包装领域工具为 Agno 工具
        
        Args:
            tool: 领域层工具
            
        Returns:
            Agno 工具函数
        """
        import inspect

        # 获取工具的 execute 方法签名
        sig = inspect.signature(tool.execute)
        params = list(sig.parameters.values())
        # 移除 'self' 参数
        if params and params[0].name == 'self':
            params = params[1:]
        
        # 检查是否有 **kwargs 参数
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params
        )
        # 获取具体的参数名（非 **kwargs）
        concrete_params = [
            p.name for p in params 
            if p.kind != inspect.Parameter.VAR_KEYWORD
        ]

        def _to_snake_case(name: str) -> str:
            """将驼峰命名转换为下划线命名"""
            import re
            # 处理边界情况
            if not name:
                return name
            # 先处理首字母大写的情况（如 StartDate -> start_date）
            s1 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
            s2 = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s1)
            return s2.lower()

        def tool_func(*args, **kwargs) -> str:
            """Agno 工具函数包装"""
            try:
                # Agno 可能传递嵌套结构: {'args': {}, 'kwargs': {...}} 或 {'args': {...}}
                # 需要提取真正的参数
                actual_args = args
                actual_kwargs = kwargs
                
                # 检测 Agno 的嵌套参数结构
                # 情况1: {'args': {}, 'kwargs': {...}}
                # 情况2: {'args': {'start_date': 'xxx', 'end_date': 'yyy'}} 只有args
                if 'args' in kwargs and isinstance(kwargs.get('args'), dict):
                    args_dict = kwargs.get('args', {})
                    # 如果有 'kwargs' 键，提取它
                    if 'kwargs' in kwargs and isinstance(kwargs.get('kwargs'), dict):
                        actual_kwargs = kwargs.get('kwargs', {})
                    else:
                        actual_kwargs = {}
                    
                    # 将 args dict 的值作为位置参数或关键字参数
                    # 如果 args_dict 的键是参数名，也加入 actual_kwargs
                    if args_dict:
                        actual_kwargs.update(args_dict)
                    actual_args = ()
                
                # 调试：记录提取后的参数
                logger.info(f"[DEBUG] 工具 [{tool.name}] 被调用")
                logger.info(f"[DEBUG]   原始 args={args}, kwargs={kwargs}")
                logger.info(f"[DEBUG]   提取后 actual_args={actual_args}, actual_kwargs={actual_kwargs}")
                logger.info(f"[DEBUG]   期望参数: {concrete_params}")
                
                # 构建参数：将参数名转换为 snake_case 并匹配工具期望的参数
                tool_args = {}
                
                # 处理位置参数：将 args 映射到 concrete_params
                for i, arg in enumerate(actual_args):
                    if i < len(concrete_params):
                        param_name = concrete_params[i]
                        tool_args[param_name] = arg
                    elif has_var_keyword:
                        logger.warning(f"[DEBUG] 工具 [{tool.name}] 收到额外的位置参数: {arg}")
                
                # 创建参数名映射（snake_case -> 原始值）处理关键字参数
                normalized_kwargs = {}
                for key, value in actual_kwargs.items():
                    normalized_key = _to_snake_case(key)
                    normalized_kwargs[normalized_key] = value
                
                logger.info(f"[DEBUG]   normalized_kwargs={normalized_kwargs}")
                
                # 提取工具定义的具体参数（关键字参数优先覆盖位置参数）
                for param_name in concrete_params:
                    if param_name in normalized_kwargs:
                        tool_args[param_name] = normalized_kwargs.pop(param_name)
                
                logger.info(f"[DEBUG]   匹配后的 tool_args={tool_args}")
                
                # 检查必需参数是否缺失
                missing_params = [p for p in concrete_params if p not in tool_args]
                if missing_params:
                    return f"参数错误: 缺少必需参数 {missing_params}。请提供: {', '.join(missing_params)}"
                
                # 如果工具接受 **kwargs，将剩余参数也传入（使用 snake_case 键）
                if has_var_keyword and normalized_kwargs:
                    tool_args.update(normalized_kwargs)
                
                result = tool.execute(**tool_args)
                
                if result.success:
                    return result.content
                else:
                    return f"工具执行错误: {result.error_message}"
            except Exception as e:
                logger.error(f"工具执行异常 [{tool.name}]: {e}", exc_info=True)
                return f"工具执行异常: {str(e)}"

        # 设置函数元数据
        tool_func.__name__ = tool.name
        tool_func.__doc__ = tool.description

        return tool_func

    def _recreate_agent(self) -> None:
        """重新创建 Agent（配置变更后）"""
        self._agent = self._create_agent()

    # -------------------------------------------------------------------------
    # AbstractAgent 实现
    # -------------------------------------------------------------------------

    def invoke(self, message: str, thread_id: str) -> AgentResponse:
        """
        同步调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Returns:
            Agent 响应
        """
        logger.info(f"AgnoAgent.invoke: thread={thread_id}")
        
        try:
            # Agno 的 run 方法
            result = self._agent.run(message)
            
            # 提取回复内容
            content = self._extract_content(result)
            
            return AgentResponse(
                content=content,
                messages=[AgentMessage.user_message(message)],
                metadata={
                    "model": self._llm_config.model,
                    "thread_id": thread_id,
                    "framework": "agno",
                },
            )
        except Exception as e:
            logger.error(f"Agno Agent 调用失败: {e}", exc_info=True)
            raise

    async def ainvoke(self, message: str, thread_id: str) -> AgentResponse:
        """
        异步调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Returns:
            Agent 响应
        """
        logger.info(f"AgnoAgent.ainvoke: thread={thread_id}")
        
        try:
            # Agno 的 arun 方法（异步）
            import asyncio
            
            # Agno 可能没有原生异步，使用线程池
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._agent.run(message)),
                timeout=self._timeout,
            )
            
            content = self._extract_content(result)
            
            return AgentResponse(
                content=content,
                messages=[AgentMessage.user_message(message)],
                metadata={
                    "model": self._llm_config.model,
                    "thread_id": thread_id,
                    "framework": "agno",
                },
            )
        except asyncio.TimeoutError:
            logger.error(f"Agno Agent 调用超时: {thread_id}")
            raise TimeoutError(f"处理时间超过 {self._timeout} 秒")
        except Exception as e:
            logger.error(f"Agno Agent 调用失败: {e}", exc_info=True)
            raise

    def stream(self, message: str, thread_id: str) -> Iterator[AgentChunk]:
        """
        同步流式调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Yields:
            流式响应块
        """
        logger.info(f"AgnoAgent.stream: thread={thread_id}")
        
        try:
            # Agno 的 run 方法支持流式
            for chunk in self._agent.run(message, stream=True):
                content = self._extract_chunk_content(chunk)
                if content:
                    yield AgentChunk.content_chunk(content)
            
            yield AgentChunk.done_chunk()
        except Exception as e:
            logger.error(f"Agno Agent 流式调用失败: {e}", exc_info=True)
            yield AgentChunk.error_chunk(str(e))

    async def astream(self, message: str, thread_id: str) -> AsyncIterator[AgentChunk]:
        """
        异步流式调用 Agent
        
        Args:
            message: 用户输入消息
            thread_id: 会话线程 ID
            
        Yields:
            流式响应块
        """
        logger.info(f"AgnoAgent.astream: thread={thread_id}")
        
        try:
            # Agno 可能不支持原生异步流式，使用同步流式包装
            import asyncio
            
            loop = asyncio.get_event_loop()
            
            def sync_stream():
                for chunk in self._agent.run(message, stream=True):
                    yield chunk
            
            # 在异步生成器中迭代同步生成器
            for chunk in sync_stream():
                content = self._extract_chunk_content(chunk)
                if content:
                    yield AgentChunk.content_chunk(content)
                # 让出控制权
                await asyncio.sleep(0)
            
            yield AgentChunk.done_chunk()
        except Exception as e:
            logger.error(f"Agno Agent 异步流式调用失败: {e}", exc_info=True)
            yield AgentChunk.error_chunk(str(e))

    def add_tools(self, tools: list[AgentTool]) -> ToolUpdateResult:
        """
        动态添加工具
        
        Args:
            tools: 要添加的工具列表
            
        Returns:
            更新结果
        """
        existing_names = {t.name for t in self._tools}
        added = []
        skipped = []
        
        for tool in tools:
            if tool.name not in existing_names:
                self._tools.append(tool)
                added.append(tool.name)
                existing_names.add(tool.name)
            else:
                skipped.append(tool.name)
        
        if added:
            # 重新创建 Agent 以应用新工具
            self._recreate_agent()
            logger.info(f"AgnoAgent 已添加工具: {added}")
        
        return ToolUpdateResult(
            success=added,
            skipped=skipped,
            total=len(self._tools),
        )

    def remove_tools(self, tool_names: list[str]) -> ToolUpdateResult:
        """
        动态移除工具
        
        Args:
            tool_names: 要移除的工具名称列表
            
        Returns:
            更新结果
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
        
        not_found = list(names_to_remove)
        
        if removed:
            self._tools = new_tools
            self._recreate_agent()
            logger.info(f"AgnoAgent 已移除工具: {removed}")
        
        return ToolUpdateResult(
            success=removed,
            skipped=not_found,
            total=len(self._tools),
        )

    def update_system_prompt(self, prompt: str) -> None:
        """
        更新系统提示词
        
        Args:
            prompt: 新的系统提示词
        """
        self._system_prompt = prompt
        self._recreate_agent()
        logger.info("AgnoAgent 系统提示词已更新")

    @property
    def tools(self) -> list[AgentTool]:
        """当前工具列表"""
        return list(self._tools)

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    def _extract_content(self, result: Any) -> str:
        """
        从 Agno 结果中提取内容
        
        Args:
            result: Agno 返回结果
            
        Returns:
            提取的文本内容
        """
        if result is None:
            return ""
        
        # Agno 返回的是 RunResponse 对象
        if hasattr(result, 'content'):
            return str(result.content)
        elif hasattr(result, 'messages') and result.messages:
            # 从消息中提取最后一条 AI 消息
            for msg in reversed(result.messages):
                if hasattr(msg, 'role') and msg.role == 'assistant':
                    return str(getattr(msg, 'content', ''))
        
        return str(result)

    def _extract_chunk_content(self, chunk: Any) -> str:
        """
        从流式块中提取内容
        
        Args:
            chunk: Agno 流式块
            
        Returns:
            提取的文本内容
        """
        if chunk is None:
            return ""
        
        if isinstance(chunk, str):
            return chunk
        
        if hasattr(chunk, 'content'):
            return str(chunk.content)
        
        if hasattr(chunk, 'delta'):
            return str(chunk.delta)
        
        return str(chunk)

    def __repr__(self) -> str:
        return (
            f"AgnoAgent("
            f"model={self._llm_config.model}, "
            f"tools_count={len(self._tools)}, "
            f"max_iterations={self._max_iterations}"
            f")"
        )
