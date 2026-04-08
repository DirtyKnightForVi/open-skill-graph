# -*- coding: utf-8 -*-
"""
查询处理器 - 处理智能体查询和多轮对话
"""

from typing import List, Dict, Any, AsyncGenerator, Tuple
from agentscope.agent import ReActAgent
from agentscope.pipeline import stream_printing_messages
from agentscope.session import JSONSession

from logger.setup import logger
import asyncio
from typing import AsyncGenerator, Tuple, Dict, Any

class QueryHandler:
    """查询处理器，处理智能体对话流程"""
    
    def __init__(self, state_service: JSONSession):
        """
        初始化查询处理器
        
        Args:
            state_service: 状态服务实例
        """
        self.state_service = state_service

    async def process_query(
        self,
        agent: ReActAgent,
        messages: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> AsyncGenerator[Tuple[Dict, bool], None]:
        """
        处理用户查询
        
        Args:
            agent: ReActAgent智能体实例
            messages: 消息列表
            session_id: 会话ID
            user_id: 用户ID
            
        Yields:
            (消息, 是否为最后一条) 元组
        """
        try:
            # 加载之前的状态（适配 JSONSession 新 API）
            await self.state_service.load_session_state(
                session_id=session_id,
                user_id=user_id,
                allow_not_exist=True,
                agent=agent
            )
            
            # logger.info(f"当前agent状态: {agent.state_dict()}")


            # 为写文件或者工具调用专门设计的流式返回。
            write_text_file_len = 0
            try:
                async for msg, last in stream_printing_messages(
                        agents=[agent],
                        coroutine_task=agent(messages),
                ):
                    if isinstance(msg.content, list):
                        for index, item in enumerate(msg.content):
                            if item.get("type", '') == 'tool_use' and item.get("name") == 'write_file':
                                tool_input = item.get("input", {})
                                content = tool_input.get("content", '')
                                if not content:
                                    continue

                                if write_text_file_len > 0:
                                    item['input']["content"] = content[write_text_file_len:]
                                write_text_file_len = len(content)

                                if last:
                                    write_text_file_len = 0

                    yield msg, last
            except asyncio.CancelledError:
                logger.warning(
                    f"Client disconnected, stream cancelled for "
                    f"session={session_id}, user_id={user_id}"
                )
            # 原始版本的流式返回
            # async for msg, last in stream_printing_messages(
            #     agents=[agent],
            #     coroutine_task=agent(messages),
            # ):
            #     yield msg, last
            
            # 保存状态（适配 JSONSession 新 API）
            await self.state_service.save_session_state(
                session_id=session_id,
                user_id=user_id,
                agent=agent
            )
            logger.info(f"Saved state for session {session_id}")
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise

