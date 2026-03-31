"""
日期时间工具实现

职责：
- 获取当前日期时间信息

作者: AI Assistant
日期: 2026-03-31
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.domain.agent.agent_tool import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class GetCurrentDatetimeTool(AgentTool):
    """获取当前时间工具
    
    返回当前日期、时间和星期信息。
    """
    
    @property
    def name(self) -> str:
        return "get_current_datetime"
    
    @property
    def description(self) -> str:
        return "获取当前日期、时间和星期信息"
    
    @property
    def parameters(self) -> dict:
        return {}  # 无参数
    
    def execute(self) -> ToolResult:
        """执行获取时间操作
        
        Returns:
            工具执行结果
        """
        try:
            now = datetime.now()
            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            
            result = {
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": weekday_names[now.weekday()],
                "datetime": now.isoformat(),
                "year": now.year,
                "month": now.month,
                "day": now.day,
            }
            
            content = f"📅 当前时间：{result['date']} {result['time']} {result['weekday']}"
            
            return ToolResult.success_result(content=content, data=result)
            
        except Exception as e:
            logger.error(f"获取时间失败: {e}", exc_info=True)
            return ToolResult.error_result(f"获取时间失败: {str(e)}")
