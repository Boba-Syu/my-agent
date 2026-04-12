"""
RAG 提示词模块

定义RAG系统使用的各种提示词模板。
"""

from __future__ import annotations

import os


def _load_prompt_file(filename: str) -> str:
    """从文件加载提示词"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def build_coze_agent_system_prompt() -> str:
    """
    构建Coze客服智能体系统提示词

    Returns:
        Coze客服人设提示词
    """
    return _load_prompt_file("coze_agent_system_prompt.md")


def build_react_guidelines() -> str:
    """
    构建ReAct模式指导

    Returns:
        ReAct模式指导文档
    """
    return _load_prompt_file("react_guidelines.md")


def build_agentic_rag_prompt() -> str:
    """
    构建Agentic RAG完整提示词

    组合Coze人设 + ReAct指导

    Returns:
        完整的Agentic RAG系统提示词
    """
    system_prompt = build_coze_agent_system_prompt()
    react_guidelines = build_react_guidelines()

    return f"""{system_prompt}

---

## ReAct模式参考

{react_guidelines}

---

## 当前任务

现在请根据用户的输入，按照上述ReAct模式进行思考和行动。
请显式输出你的思考过程（Thought），然后决定行动（Action）。
"""


def build_query_decomposition_prompt(query: str) -> str:
    """
    构建查询分解提示词
    
    Args:
        query: 用户查询
        
    Returns:
        提示词
    """
    return f"""你是一个智能查询分析助手。请将用户的问题分解为多个子问题，并判断每个子问题属于哪种知识库类型。

支持的知识库类型：
- faq: 常见问题，面向客户的FAQ
- regulation: 规章制度，面向员工的企业内部文档

用户问题: {query}

请按以下JSON格式输出分析结果：
{{
    "sub_queries": [
        {{
            "query": "子问题1",
            "kb_types": ["faq"],
            "weight": 1.0
        }},
        {{
            "query": "子问题2",
            "kb_types": ["regulation"],
            "weight": 0.8
        }}
    ]
}}

注意：
1. 将复杂问题分解为2-3个更具体的子问题
2. 每个子问题标注可能的知识库类型（可以多个）
3. weight表示子问题的重要性（0-1之间）
4. 只输出JSON，不要有其他内容"""


def build_answer_generation_prompt(query: str, context: str) -> str:
    """
    构建答案生成提示词
    
    Args:
        query: 用户查询
        context: 检索上下文
        
    Returns:
        提示词
    """
    return f"""你是一个专业的知识库问答助手。请基于提供的参考文档回答用户的问题。

用户问题: {query}

参考文档:
{context}

回答要求：
1. 基于参考文档内容回答问题
2. 如果文档中没有相关信息，明确告知用户
3. 回答要准确、简洁、有条理
4. 可以适当引用文档中的关键信息
5. 如果涉及多个方面，请分点说明

请直接输出答案："""


def build_kb_classification_prompt(query: str) -> str:
    """
    构建知识库分类提示词
    
    Args:
        query: 用户查询
        
    Returns:
        提示词
    """
    return f"""请判断以下用户问题属于哪种知识库类型：

用户问题: {query}

知识库类型：
- faq: 常见问题，面向客户的FAQ（如产品使用、售后服务等）
- regulation: 规章制度，面向员工的企业内部文档（如考勤、报销、流程等）

请只输出类型名称（faq或regulation），不要其他内容。"""
