"""
Skill（技能）示例扩展模块

Skill 是比 Tool 更高层次的封装，通常代表一个完整的业务能力，
内部可以组合多个 Tool、调用 LLM、访问数据库等。

扩展方式：
1. 复制此文件，重命名为 xxx_skill.py
2. 继承 BaseSkill，实现 name/description 和 execute 方法
3. 在 Agent 层或业务层直接调用 skill.execute()，
   或通过 to_langchain_tool() 作为工具传入 Agent
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """
    Skill 基类
    所有 Skill 应继承此类并实现抽象方法
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill 名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Skill 描述"""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """
        执行 Skill

        Args:
            **kwargs: Skill 所需输入参数

        Returns:
            执行结果字符串
        """
        ...

    def to_langchain_tool(self) -> StructuredTool:
        """
        将 Skill 转换为 LangChain StructuredTool，
        使其可以直接传入 ReactAgent 的 tools 列表

        Returns:
            LangChain StructuredTool 实例
        """
        _self = self

        def _run(**kwargs: Any) -> str:
            return _self.execute(**kwargs)

        return StructuredTool.from_function(
            func=_run,
            name=self.name,
            description=self.description,
        )


class SummarizeSkill(BaseSkill):
    """
    文本摘要 Skill 示例

    接收一段较长文本，调用 LLM 生成简洁摘要。
    这是典型的"Skill = LLM 能力 + 业务逻辑"封装模式。
    """

    @property
    def name(self) -> str:
        return "summarize_text"

    @property
    def description(self) -> str:
        return (
            "对给定的长文本进行摘要提炼，返回简洁的核心内容。"
            "适用于文章总结、文档摘要等场景。"
            "参数：text（需要摘要的原始文本，字符串）"
        )

    def execute(self, text: str = "") -> str:
        """
        生成文本摘要

        Args:
            text: 需要摘要的原始文本

        Returns:
            摘要内容字符串
        """
        if not text.strip():
            return "错误：输入文本为空，无法生成摘要"

        # -------------------------------------------------------
        # TODO：替换为真实 LLM 调用
        # 示例：
        #   from app.llm.llm_factory import LLMFactory
        #   llm = LLMFactory.create_llm()
        #   from langchain_core.messages import HumanMessage
        #   response = llm.invoke([HumanMessage(content=f"请对以下文本生成摘要：\n\n{text}")])
        #   return response.content
        # -------------------------------------------------------
        logger.debug(f"SummarizeSkill 执行，文本长度：{len(text)}")

        # 简单截断模拟（实际应调用 LLM）
        preview = text[:100] + "..." if len(text) > 100 else text
        return (
            f"【摘要（模拟）】\n"
            f"原文长度：{len(text)} 字\n"
            f"内容预览：{preview}\n"
            f"提示：将 execute 方法中的模拟实现替换为真实 LLM 调用以获得真实摘要。"
        )


# 导出可用的 Skill 实例
summarize_skill = SummarizeSkill()

# 转换为 LangChain 工具（可直接加入 Agent 工具列表）
summarize_text = summarize_skill.to_langchain_tool()
