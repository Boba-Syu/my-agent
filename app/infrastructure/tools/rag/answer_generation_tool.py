"""
答案生成工具

基于上下文生成最终答案的AgentTool。
供ReAct Agent在获取上下文后调用。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from app.domain.agent.agent_tool import AgentTool, ToolResult
from app.config import get_llm_config
from app.prompts.rag import build_answer_generation_prompt

logger = logging.getLogger(__name__)


class AnswerGenerationTool(AgentTool):
    """
    答案生成工具

    基于检索到的上下文，生成对用户问题的最终答案。
    通常在get_context之后调用。

    Example:
        tool = AnswerGenerationTool()
        result = tool.execute(
            query="如何创建Bot",
            context="[文档1] ...",
        )
    """

    def __init__(self, llm: ChatOpenAI | None = None):
        """
        初始化答案生成工具

        Args:
            llm: LLM实例，None时从配置创建
        """
        self._llm = llm or self._create_llm()

    def _create_llm(self) -> ChatOpenAI:
        """创建LLM实例"""
        config = get_llm_config()
        return ChatOpenAI(
            model=config.get("model", "deepseek-v3"),
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            temperature=0.3,
            max_tokens=2000,
        )

    @property
    def name(self) -> str:
        """工具名称"""
        return "generate_answer"

    @property
    def description(self) -> str:
        """工具描述"""
        return (
            "基于上下文生成对用户问题的最终答案。\n"
            "适用于：已获取相关上下文，需要生成完整回答时\n"
            "参数：\n"
            "- query: 用户原始问题\n"
            "- context: 检索到的上下文内容"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """参数Schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户原始问题",
                },
                "context": {
                    "type": "string",
                    "description": "检索到的上下文内容",
                },
            },
            "required": ["query", "context"],
        }

    def execute(
        self,
        query: str,
        context: str,
    ) -> ToolResult:
        """
        执行答案生成

        Args:
            query: 用户问题
            context: 上下文内容

        Returns:
            工具执行结果
        """
        logger.info(f"[AnswerGen] 开始生成答案 | query={query[:50]}... | context长度={len(context)}")

        try:
            if not context.strip():
                logger.warning("[AnswerGen] 上下文为空，无法生成答案")
                return ToolResult.success_result(
                    "抱歉，我在知识库中没有找到相关信息，无法回答您的问题。",
                    has_context=False,
                )

            # 构建提示词
            logger.debug("[AnswerGen] 构建生成提示词...")
            prompt = build_answer_generation_prompt(query, context)
            logger.debug(f"[AnswerGen] 提示词长度: {len(prompt)}")

            # 生成答案 - 使用同步调用
            logger.info("[AnswerGen] 调用LLM生成答案...")
            response = self._llm.invoke(prompt)
            answer = response.content.strip()
            logger.info(f"[AnswerGen] 答案生成完成 | 长度={len(answer)}")

            return ToolResult.success_result(
                answer,
                answer=answer,
                has_context=True,
            )

        except Exception as e:
            logger.error(f"[AnswerGen] 答案生成失败: {e}", exc_info=True)
            return ToolResult.error_result(f"答案生成失败: {str(e)}")
