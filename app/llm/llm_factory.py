"""
LLM 工厂模块
统一管理阿里百炼 LLM 和 Embedding 实例的创建与配置
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings

from app.config import get_llm_config, get_embedding_config


class LLMFactory:
    """
    LLM 与 Embedding 工厂类

    使用示例:
        llm = LLMFactory.create_llm()                    # 使用默认模型 deepseek-v3
        llm_r1 = LLMFactory.create_llm("deepseek-r1")   # 使用 deepseek-r1
        embedding = LLMFactory.create_embedding()        # 获取 Embedding（Ollama 或百炼）
    """

    @staticmethod
    def create_llm(model_name: str | None = None) -> ChatOpenAI:
        """
        创建阿里百炼 LLM 实例（兼容 OpenAI 协议）

        Args:
            model_name: 模型名称，为 None 时使用配置文件中的 default_model

        Returns:
            ChatOpenAI 实例
        """
        llm_cfg = get_llm_config()
        model = model_name or llm_cfg.get("default_model", "deepseek-v3")

        return ChatOpenAI(
            model=model,
            api_key=llm_cfg.get("api_key", ""),
            base_url=llm_cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            timeout=llm_cfg.get("timeout", 60),
            max_tokens=llm_cfg.get("max_tokens", 4096),
        )

    @staticmethod
    def create_embedding() -> OpenAIEmbeddings | OllamaEmbeddings:
        """
        创建 Embedding 实例

        根据配置文件自动选择：
        - 如果配置了 Ollama base_url (localhost:11434)，使用 OllamaEmbeddings
        - 否则使用阿里百炼 OpenAIEmbeddings

        Returns:
            OpenAIEmbeddings 或 OllamaEmbeddings 实例
        """
        emb_cfg = get_embedding_config()
        base_url = emb_cfg.get("base_url", "")
        model = emb_cfg.get("model", "bge-m3:latest")

        # 检测是否为 Ollama 本地服务
        if "localhost:11434" in base_url or "127.0.0.1:11434" in base_url:
            return OllamaEmbeddings(
                model=model,
                base_url=base_url,
            )
        else:
            # 使用阿里百炼或其他 OpenAI 兼容服务
            return OpenAIEmbeddings(
                model=model,
                api_key=emb_cfg.get("api_key"),
                base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                dimensions=emb_cfg.get("dimensions", 1024),
            )
