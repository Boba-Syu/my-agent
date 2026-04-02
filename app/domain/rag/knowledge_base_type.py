"""
知识库类型枚举

定义支持的知识库分类。
"""

from __future__ import annotations

from enum import Enum


class KnowledgeBaseType(Enum):
    """
    知识库类型
    
    支持的知识库分类：
    - FAQ: 面向客户的常见问题
    - REGULATION: 面向员工的企业规章制度
    """
    
    FAQ = "faq"
    """FAQ知识库 - 面向客户的常见问题解答"""
    
    REGULATION = "regulation"
    """规章制度知识库 - 面向员工的企业内部文档"""
    
    @classmethod
    def from_string(cls, value: str) -> KnowledgeBaseType:
        """
        从字符串创建枚举
        
        Args:
            value: 字符串值
            
        Returns:
            对应的枚举值
            
        Raises:
            ValueError: 如果字符串不匹配任何枚举值
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = [e.value for e in cls]
            raise ValueError(f"无效的知识库类型: {value}，有效值: {valid}")
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        names = {
            KnowledgeBaseType.FAQ: "常见问题",
            KnowledgeBaseType.REGULATION: "规章制度",
        }
        return names.get(self, self.value)
