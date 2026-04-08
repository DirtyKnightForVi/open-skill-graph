# -*- coding: utf-8 -*-
"""
日志配置模块 - 统一的日志设置
"""

import logging
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.settings import Config

trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 从请求头获取 trace_id（例如从 X-Request-ID），如果没有则生成新的
        trace_id = request.headers.get('X-Request-ID', uuid.uuid4().hex)
        # 将 trace_id 设置到上下文变量中
        token = trace_id_var.set(trace_id)
        try:
            response = await call_next(request)
            # 可将 trace_id 也写入响应头，方便客户端查看
            response.headers['X-Request-ID'] = trace_id
            return response
        finally:
            # 清理上下文变量，避免内存泄漏
            trace_id_var.reset(token)



class TraceIDFilter(logging.Filter):
    def filter(self, record):
        # 将 trace_id 添加到日志记录中
        record.trace_id = trace_id_var.get() or uuid.uuid4().hex
        return True


def setup_logging(name):
    """配置应用日志"""
    # logging.basicConfig(
    #     level=Config.LOG_LEVEL,
    #     filename=Config.LOG_FILE,
    #     filemode='a',
    #     format=Config.LOG_FORMAT
    # )
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    handler = RotatingFileHandler(Config.LOG_FILE, maxBytes=1024 * 1024 * 20, backupCount=10, encoding="utf-8")
    formatter = logging.Formatter(Config.LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(Config.LOG_LEVEL)
    logger.addFilter(TraceIDFilter())
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的logger"""
    return logging.getLogger(name)


logger = setup_logging('agent_skill_app')
