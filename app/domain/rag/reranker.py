"""
重排序接口

定义检索结果重排序的领域层契约。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.domain.rag.search_result import SearchResult, RankedResult

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """
    重排序接口
    
    定义检索结果重排序的领域层契约，由基础设施层实现。
    
    使用场景：
    - 对混合检索的结果进行精排序
    - 提高检索结果的相关性
    
    Example:
        class BailianReranker(Reranker):
            def rerank(self, query, results, top_k):
                # 调用百炼qwen3-vl-rerank API
                pass
    """
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """
        重排序检索结果
        
        Args:
            query: 原始查询
            results: 待排序的检索结果
            top_k: 返回前K个结果
            
        Returns:
            重排序后的结果列表
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """重排序器名称"""
        pass
    
    @property
    @abstractmethod
    def batch_size(self) -> int:
        """批量处理大小（0表示不限制）"""
        pass
