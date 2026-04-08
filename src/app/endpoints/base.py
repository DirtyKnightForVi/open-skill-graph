# -*- coding: utf-8 -*-
"""
基础端点处理器 - 提供通用功能和基础架构
"""

from typing import Dict, Any
from core.skill.service import SkillService
from logger.setup import logger


class BaseEndpointHandlers:
    """基础端点处理器，提供通用功能和错误处理"""
    
    def __init__(self, skill_service: SkillService):
        """
        初始化基础端点处理器
        
        Args:
            skill_service: 技能服务实例
        """
        self.skill_service = skill_service
    
    def _handle_error(self, operation: str, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        统一的错误处理机制
        
        Args:
            operation: 操作名称
            error: 异常对象
            context: 额外的上下文信息
            
        Returns:
            错误响应
        """
        error_msg = str(error)
        logger.error(f"Error in {operation}: {error_msg}", extra=context or {})
        
        return {
            "status": "error",
            "error": error_msg
        }
    
    def _log_operation(self, operation: str, user_id: str, **kwargs):
        """
        记录操作日志
        
        Args:
            operation: 操作名称
            user_id: 用户ID
            **kwargs: 其他日志参数
        """
        log_msg = f"{operation} endpoint called for user {user_id}"
        if kwargs:
            log_msg += f" with params: {kwargs}"
        logger.info(log_msg)