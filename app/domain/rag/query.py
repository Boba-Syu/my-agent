"""
查询值对象

表示RAG检索查询。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.shared.value_object import ValueObject
from app.domain.rag.knowledge_base_type import KnowledgeBaseType


@dataclass(frozen=True)
class SubQuery(ValueObject):
    """
    子查询值对象
    
    表示问题分解后的一个子查询。
    
    Example:
        sub = SubQuery(
            query="如何申请退款",
            kb_types=[KnowledgeBaseType.FAQ],
            weight=1.0
        )
    """
    
    query: str
    """子查询文本"""
    
    kb_types: list[KnowledgeBaseType] = field(default_factory=list)
    """建议检索的知识库类型"""
    
    weight: float = 1.0
    """权重（用于结果融合）"""
    
    def __post_init__(self):
        """初始化后验证"""
        if not self.query or not self.query.strip():
            raise ValueError("子查询不能为空")
        if self.weight <= 0:
            raise ValueError("权重必须大于0")


@dataclass(frozen=True)
class Query(ValueObject):
    """
    查询值对象
    
    表示用户的RAG检索请求。
    
    Example:
        query = Query(
            original_query="我想退货，该怎么操作？",
            sub_queries=[
                SubQuery("退货流程", [KnowledgeBaseType.FAQ]),
                SubQuery("退款政策", [KnowledgeBaseType.FAQ]),
            ]
        )
    """
    
    original_query: str
    """原始查询文本"""
    
    sub_queries: list[SubQuery] = field(default_factory=list)
    """分解后的子查询列表"""
    
    filters: dict[str, Any] = field(default_factory=dict)
    """元数据过滤条件"""
    
    top_k: int = 10
    """返回结果数量"""
    
    def __post_init__(self):
        """初始化后验证"""
        if not self.original_query or not self.original_query.strip():
            raise ValueError("原始查询不能为空")
        if self.top_k <= 0:
            raise ValueError("top_k必须大于0")
    
    @property
    def all_kb_types(self) -> list[KnowledgeBaseType]:
        """
        获取所有涉及的知识库类型
        
        Returns:
            去重后的知识库类型列表
        """
        types = set()
        for sub in self.sub_queries:
            types.update(sub.kb_types)
        return list(types)
    
    @property
    def has_sub_queries(self) -> bool:
        """是否有子查询"""
        return len(self.sub_queries) > 0
    
    def get_queries_for_kb(self, kb_type: KnowledgeBaseType) -> list[str]:
        """
        获取指定知识库类型的所有查询
        
        Args:
            kb_type: 知识库类型
            
        Returns:
            查询文本列表
        """
        queries = []
        for sub in self.sub_queries:
            if kb_type in sub.kb_types:
                queries.append(sub.query)
        return queries if queries else [self.original_query]
