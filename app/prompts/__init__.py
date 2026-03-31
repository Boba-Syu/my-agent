"""
提示词加载与管理模块

职责：
- 从文件加载提示词模板
- 渲染提示词变量
- 构建完整的系统提示词

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from pathlib import Path
from string import Template
from typing import Any

logger = logging.getLogger(__name__)

# 提示词根目录
PROMPT_DIR = Path(__file__).parent

# 提示词版本注册表
PROMPT_VERSIONS = {
    "v1.0.0": "基础版本",
    "v1.1.0": "增加 Few-shot 示例",
    "v1.2.0": "结构化输出 + COT 优化",
}


def load_prompt(name: str) -> str:
    """加载指定名称的提示词文件
    
    Args:
        name: 提示词文件路径，相对于 prompts 目录，如 "accounting/system_prompt"
        
    Returns:
        提示词文件内容
        
    Raises:
        FileNotFoundError: 文件不存在
    """
    file_path = PROMPT_DIR / f"{name}.md"
    if not file_path.exists():
        logger.error(f"提示词文件不存在: {file_path}")
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    content = file_path.read_text(encoding="utf-8")
    logger.debug(f"已加载提示词: {name} ({len(content)} 字符)")
    return content


def render_template(template: str, variables: dict[str, Any]) -> str:
    """渲染提示词模板，替换变量
    
    Args:
        template: 模板字符串
        variables: 变量字典
        
    Returns:
        渲染后的字符串
    """
    return Template(template).safe_substitute(variables)


def build_accounting_prompt(
    today: str,
    weekday: str,
    yesterday: str,
    version: str = "v1.2.0",
) -> str:
    """构建记账 Agent 系统提示词
    
    按照模块化结构组合各个提示词组件：
    1. 主提示词模板
    2. COT 推理指导
    3. Few-shot 示例
    4. 输出格式规范
    5. 工具使用指南
    6. 安全防护规则
    
    Args:
        today: 今天日期 YYYY-MM-DD
        weekday: 星期几
        yesterday: 昨天日期 YYYY-MM-DD
        version: 提示词版本
        
    Returns:
        完整的系统提示词
    """
    components = [
        load_prompt("accounting/system_prompt"),
        load_prompt("base/cot_guidelines"),
        load_prompt("accounting/few_shot_examples"),
        load_prompt("accounting/output_schema"),
        load_prompt("accounting/tool_guidelines"),
        load_prompt("base/safety_guard"),
    ]
    
    base_prompt = "\n\n".join(components)
    
    variables = {
        "today": today,
        "weekday": weekday,
        "yesterday": yesterday,
        "version": version,
    }
    
    return render_template(base_prompt, variables)


def build_default_agent_prompt() -> str:
    """构建默认 Agent 系统提示词
    
    Returns:
        默认系统提示词
    """
    return load_prompt("base/default_system_prompt")


__all__ = [
    "load_prompt",
    "render_template",
    "build_accounting_prompt",
    "build_default_agent_prompt",
    "PROMPT_VERSIONS",
]
