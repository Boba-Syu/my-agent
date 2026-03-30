"""
LLM 配置与提供器

定义 LLM 配置数据类和提供器。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMConfig:
    """
    LLM 配置值对象
    
    包含创建 LLM 实例所需的所有配置。
    
    Example:
        config = LLMConfig(
            model="deepseek-v3",
            api_key="sk-xxx",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    """
    
    model: str
    """模型名称"""
    
    api_key: str
    """API 密钥"""
    
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """API 基础 URL"""
    
    timeout: int = 60
    """请求超时（秒）"""
    
    max_tokens: int = 4096
    """最大 token 数"""
    
    temperature: float = 0.7
    """温度参数"""


class LLMProvider:
    """
    LLM 提供器
    
    从应用配置创建 LLM 配置。
    
    Example:
        provider = LLMProvider()
        config = provider.get_config("deepseek-v3")
    """

    def __init__(self, config_source: dict | None = None):
        """
        初始化提供器
        
        Args:
            config_source: 配置源字典，None 时使用 app.config
        """
        self._config_source = config_source

    def get_config(self, model_name: str | None = None) -> LLMConfig:
        """
        获取 LLM 配置
        
        Args:
            model_name: 模型名称，None 使用默认
            
        Returns:
            LLM 配置
        """
        if self._config_source:
            cfg = self._config_source
        else:
            from app.config import get_llm_config
            cfg = get_llm_config()
        
        model = model_name or cfg.get("default_model", "deepseek-v3")
        
        return LLMConfig(
            model=model,
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            timeout=cfg.get("timeout", 60),
            max_tokens=cfg.get("max_tokens", 4096),
            temperature=cfg.get("temperature", 0.7),
        )

    @staticmethod
    def from_app_config() -> LLMProvider:
        """从应用配置创建提供器"""
        return LLMProvider()
