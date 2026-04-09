"""
全局配置模块
读取项目根目录下的 application.toml，暴露全局 config 字典
"""

import sys
from pathlib import Path

# Python 3.11+ 内置 tomllib，低版本使用 tomli 兼容包
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

# 配置文件路径（固定为项目根目录下的 application.toml）
_CONFIG_PATH = Path(__file__).parent.parent / "application.toml"


def _load_config() -> dict:
    """从 application.toml 加载配置，返回配置字典"""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"配置文件未找到：{_CONFIG_PATH}\n"
            "请确保项目根目录下存在 application.toml 文件"
        )
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


# 全局配置对象，模块加载时一次性读取
config: dict = _load_config()


def get_llm_config() -> dict:
    """返回 LLM 相关配置"""
    return config.get("llm", {})


def get_embedding_config() -> dict:
    """返回 Embedding 相关配置"""
    return config.get("embedding", {})


def get_sqlite_config() -> dict:
    """返回 SQLite 数据库配置"""
    return config.get("database", {}).get("sqlite", {})


def get_milvus_config() -> dict:
    """返回 Milvus 数据库配置（已弃用，请使用 get_chroma_config）"""
    return config.get("database", {}).get("milvus", {})


def get_chroma_config() -> dict:
    """返回 Chroma 数据库配置"""
    return config.get("database", {}).get("chroma", {})


def get_server_config() -> dict:
    """返回 FastAPI 服务配置"""
    return config.get("server", {})


def get_agent_config() -> dict:
    """返回 Agent 行为配置"""
    return config.get("agent", {})


def get_config() -> dict:
    """返回完整配置字典"""
    return config
