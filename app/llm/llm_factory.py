"""
LLM 工厂模块
统一管理阿里百炼 LLM 和 Ollama Embedding 实例的创建与配置
"""

from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaEmbeddings

from app.config import get_llm_config, get_embedding_config


class LLMFactory:
    """
    LLM 与 Embedding 工厂类

    使用示例:
        llm = LLMFactory.create_llm()                    # 使用默认模型 deepseek-v3
        llm_r1 = LLMFactory.create_llm("deepseek-r1")   # 使用 deepseek-r1
        embedding = LLMFactory.create_embedding()         # 获取 Ollama Embedding
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
    def create_embedding() -> OllamaEmbeddings:
        """
        创建 Ollama 本地 Embedding 实例

        Returns:
            OllamaEmbeddings 实例（默认使用 bge-m3:latest）
        """
        emb_cfg = get_embedding_config()

        return OllamaEmbeddings(
            model=emb_cfg.get("model", "bge-m3:latest"),
            base_url=emb_cfg.get("base_url", "http://localhost:11434"),
        )
