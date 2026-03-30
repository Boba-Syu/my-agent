"""
交易应用服务

协调交易领域对象完成用户用例。
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from app.application.accounting.dto import (
    CreateTransactionDTO,
    TransactionDTO,
    TransactionQueryDTO,
    StatisticsDTO,
)
from app.domain.accounting.money import Money
from app.domain.accounting.transaction import Transaction, TransactionType
from app.domain.accounting.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class TransactionService:
    """
    交易应用服务
    
    协调交易聚合根完成用户用例，包括：
    - 创建交易
    - 查询交易
    - 更新交易
    - 删除交易
    - 统计查询
    
    Example:
        service = TransactionService(transaction_repository)
        
        # 创建交易
        transaction = service.create_transaction(CreateTransactionDTO(...))
        
        # 查询交易
        transactions = service.list_transactions(TransactionQueryDTO(...))
    """

    def __init__(self, repository: TransactionRepository):
        """
        初始化应用服务
        
        Args:
            repository: 交易仓库
        """
        self._repository = repository

    def create_transaction(self, dto: CreateTransactionDTO) -> TransactionDTO:
        """
        创建交易用例
        
        Args:
            dto: 创建交易请求
            
        Returns:
            创建的交易 DTO
        """
        logger.info(f"创建交易: {dto.category} {dto.amount}")
        
        # 创建领域实体
        transaction = Transaction(
            id=None,
            transaction_type=TransactionType(dto.transaction_type),
            category=dto.category,
            amount=Money(Decimal(str(dto.amount))),
            transaction_date=date.fromisoformat(dto.transaction_date),
            note=dto.note,
        )
        
        # 保存
        saved = self._repository.save(transaction)
        
        return TransactionDTO.from_entity(saved)

    def list_transactions(self, query: TransactionQueryDTO) -> list[TransactionDTO]:
        """
        查询交易用例
        
        Args:
            query: 查询条件
            
        Returns:
            交易 DTO 列表
        """
        transactions = self._repository.list(
            transaction_type=TransactionType(query.transaction_type) if query.transaction_type else None,
            category=query.category,
            start_date=date.fromisoformat(query.start_date) if query.start_date else None,
            end_date=date.fromisoformat(query.end_date) if query.end_date else None,
            limit=query.limit,
        )
        
        return [TransactionDTO.from_entity(t) for t in transactions]

    def get_transaction(self, transaction_id: str) -> TransactionDTO | None:
        """
        获取单个交易
        
        Args:
            transaction_id: 交易 ID
            
        Returns:
            交易 DTO，不存在返回 None
        """
        transaction = self._repository.get(transaction_id)
        if transaction:
            return TransactionDTO.from_entity(transaction)
        return None

    def update_transaction(
        self,
        transaction_id: str,
        dto: CreateTransactionDTO,
    ) -> TransactionDTO | None:
        """
        更新交易用例
        
        Args:
            transaction_id: 交易 ID
            dto: 更新数据
            
        Returns:
            更新后的交易 DTO，不存在返回 None
        """
        transaction = self._repository.get(transaction_id)
        if not transaction:
            return None
        
        # 更新实体
        transaction.update(
            category=dto.category,
            amount=Money(Decimal(str(dto.amount))),
            transaction_date=date.fromisoformat(dto.transaction_date),
            note=dto.note,
        )
        
        # 保存
        saved = self._repository.save(transaction)
        
        return TransactionDTO.from_entity(saved)

    def delete_transaction(self, transaction_id: str) -> bool:
        """
        删除交易用例
        
        Args:
            transaction_id: 交易 ID
            
        Returns:
            是否成功删除
        """
        return self._repository.delete(transaction_id)

    def get_statistics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> StatisticsDTO:
        """
        获取统计数据用例
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计数据 DTO
        """
        stats = self._repository.get_statistics(
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
        )
        
        return StatisticsDTO.from_domain(stats)

    def get_categories_summary(
        self,
        transaction_type: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """
        获取分类汇总
        
        Args:
            transaction_type: 交易类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            分类汇总列表
        """
        return self._repository.get_categories_summary(
            transaction_type=TransactionType(transaction_type),
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
        )

    def get_daily_summary(
        self,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """
        获取每日汇总
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            每日汇总列表
        """
        return self._repository.get_daily_summary(
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
        )
