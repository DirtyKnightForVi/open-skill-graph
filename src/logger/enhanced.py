# -*- coding: utf-8 -*-
"""
增强日志记录模块
提供详细的大模型调用日志记录功能
"""
import functools
import json
import time
from typing import Any, Type, AsyncGenerator

import httpx
from agentscope.model import ChatResponse
from agentscope.model import OpenAIChatModel
from pydantic import BaseModel

from logger.setup import logger


class ModelError(Exception):
    """ 模型异常 """
    pass

def post_response(func):
    """ 处理返回数据 """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async for item in func(*args, **kwargs):
            logger.debug(f'response chunk: {item}')
            try:
                item_str = item.decode()
                item_json = json.loads(item_str)
                if "code" in item_json:
                    raise ModelError(item_json.get('msg') or item_str)
            except Exception:
                pass
            yield item
    return wrapper

httpx.Response.aiter_bytes = post_response(httpx.Response.aiter_bytes)


class EnhancedOpenAIChatModel(OpenAIChatModel):
    """
    增强的OpenAI聊天模型，提供详细的调用日志记录
    """
    
    def __init__(self, *args, **kwargs):
        """
        初始化增强的OpenAI聊天模型
        
        Args:
            *args: OpenAIChatModel的初始化参数
            **kwargs: OpenAIChatModel的初始化关键字参数
        """
        super().__init__(*args, **kwargs)
        self.model_name = kwargs.get('model_name', 'unknown')
        self.logger = logger
    
    # @trace_llm
    async def __call__(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        structured_model: Type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        调用大模型并记录详细的日志
        
        Args:
            messages: 消息列表
            tools: 工具列表
            tool_choice: 工具选择
            structured_model: 结构化模型
            **kwargs: 其他参数
            
        Returns:
            ChatResponse: 聊天响应
        """
        start_time = time.time()
        
        # 记录请求信息
        request_info = {
            "model": self.model_name,
            "messages_count": len(messages),
            "has_tools": tools is not None and len(tools) > 0,
            "tool_count": len(tools) if tools else 0,
            "structured_model": structured_model.__name__ if structured_model else None,
            "timestamp": start_time
        }
        
        # 提取用户消息内容（如果有）
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if user_messages:
            last_user_message = user_messages[-1].get('content', '')
            # 处理content可能是list的情况
            if isinstance(last_user_message, list):
                # 如果是列表，提取第一个元素中的文本
                last_user_message = str(last_user_message)
            # 截取前100个字符作为摘要
            message_preview = str(last_user_message)[:100]
            request_info["user_message_preview"] = message_preview + ("..." if len(str(last_user_message)) > 100 else "")
        
        self.logger.info(f"LLM Request Start: {request_info}")
        
        try:
            # 调用父类方法
            response = await super().__call__(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                structured_model=structured_model,
                **kwargs
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录响应信息
            response_info = {
                "model": self.model_name,
                "duration_seconds": round(duration, 3),
                "response_id": getattr(response, 'id', 'unknown'),
                "finish_reason": getattr(response, 'finish_reason', 'unknown'),
                "timestamp": end_time
            }
            
            # 提取响应内容
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message'):
                    message = choice.message
                    if hasattr(message, 'content') and message.content:
                        content = message.content
                        # 处理content可能是list的情况
                        if isinstance(content, list):
                            content = str(content)
                        content_str = str(content)
                        response_info["response_preview"] = content_str[:100] + ("..." if len(content_str) > 100 else "")
                    
                    # 检查是否有工具调用
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        response_info["has_tool_calls"] = True
                        response_info["tool_calls_count"] = len(message.tool_calls)
            
            # 提取使用情况统计
            if hasattr(response, 'usage'):
                usage = response.usage
                response_info.update({
                    "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(usage, 'completion_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                })
            
            self.logger.info(f"LLM Request Complete: {response_info}")
            
            return response
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            error_info = {
                "model": self.model_name,
                "duration_seconds": round(duration, 3),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": end_time
            }
            
            self.logger.error(f"LLM Request Failed: {error_info}")
            raise

def create_enhanced_model(
    model_name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    stream: bool = True,
    **kwargs
) -> EnhancedOpenAIChatModel:
    """
    创建增强的OpenAI聊天模型
    
    Args:
        model_name: 模型名称
        api_key: API密钥
        base_url: API基础URL
        stream: 是否使用流式输出
        **kwargs: 其他参数
        
    Returns:
        EnhancedOpenAIChatModel: 增强的模型实例
    """
    client_kwargs = kwargs.get('client_kwargs', {})
    if base_url:
        client_kwargs['base_url'] = base_url
    
    generate_kwargs = kwargs.get('generate_kwargs', {})
    
    return EnhancedOpenAIChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=stream,
        client_kwargs=client_kwargs,
        generate_kwargs=generate_kwargs,
        **{k: v for k, v in kwargs.items() if k not in ['client_kwargs', 'generate_kwargs']}
    )
