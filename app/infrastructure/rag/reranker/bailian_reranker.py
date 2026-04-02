"""
百炼 Reranker 实现

使用阿里百炼 qwen3-vl-rerank 模型对检索结果重排序。
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from app.config import get_embedding_config, get_llm_config
from app.domain.rag.reranker import Reranker
from app.domain.rag.search_result import RankedResult, SearchResult

logger = logging.getLogger(__name__)


class BailianReranker(Reranker):
    """
    阿里百炼 Reranker 实现
    
    使用百炼 qwen3-vl-rerank 模型对候选文档进行相关性重排序。
    通过 OpenAI 兼容 API 调用。
    
    注意：如果百炼没有专门的 rerank API，可以使用 LLM 实现简单的相关性打分。
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "qwen3-vl-rerank",
    ):
        """
        初始化百炼Reranker
        
        Args:
            api_key: API密钥，None时从配置读取
            base_url: API基础URL，None时从配置读取
            model: 重排序模型名称
        """
        # 优先使用embedding配置，fallback到llm配置
        emb_cfg = get_embedding_config()
        llm_cfg = get_llm_config()
        
        self._api_key = api_key or emb_cfg.get("api_key") or llm_cfg.get("api_key", "")
        self._base_url = base_url or emb_cfg.get("base_url") or llm_cfg.get(
            "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self._model = model
        
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        
        logger.info(f"BailianReranker初始化: model={model}")
    
    @property
    def name(self) -> str:
        """重排序器名称"""
        return f"bailian_{self._model}"
    
    @property
    def batch_size(self) -> int:
        """批量处理大小"""
        return 20
    
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """
        重排序检索结果
        
        使用百炼API对文档进行相关性打分，然后排序。
        如果API不支持直接rerank，使用LLM打分实现。
        
        Args:
            query: 原始查询
            results: 待排序的检索结果
            top_k: 返回前K个结果
            
        Returns:
            重排序后的结果列表
        """
        if not results:
            return []
        
        try:
            # 使用LLM对每个文档进行相关性打分
            scored_results = []
            
            for result in results:
                score = self._score_document(query, result.content)
                scored_results.append((result, score))
            
            # 按分数降序排序
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 生成RankedResult
            ranked = []
            for rank, (result, score) in enumerate(scored_results[:top_k], 1):
                ranked.append(RankedResult(
                    search_result=result,
                    rerank_score=score,
                    rank=rank,
                ))
            
            logger.debug(f"重排序完成: 输入{len(results)}条，输出{len(ranked)}条")
            return ranked
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 失败时返回原始排序
            return [
                RankedResult(search_result=r, rerank_score=r.score, rank=i + 1)
                for i, r in enumerate(results[:top_k])
            ]
    
    def _score_document(self, query: str, document: str) -> float:
        """
        对单个文档进行相关性打分
        
        Args:
            query: 查询
            document: 文档内容
            
        Returns:
            相关性分数 (0-1)
        """
        try:
            prompt = f"""请评估以下文档与用户查询的相关性。

用户查询: {query}

文档内容: {document[:500]}...

请只返回一个0-100的整数分数，100表示高度相关，0表示完全不相关。
只返回数字，不要其他内容。"""
            
            response = self._client.chat.completions.create(
                model="deepseek-v3",  # 使用通用模型打分
                messages=[
                    {"role": "system", "content": "你是一个文档相关性评估专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=10,
            )
            
            content = response.choices[0].message.content.strip()
            # 提取数字
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                score = int(numbers[0])
                return min(max(score / 100, 0), 1)  # 归一化到0-1
            
            return 0.5  # 默认中等相关
            
        except Exception as e:
            logger.warning(f"文档打分失败: {e}")
            return 0.5
