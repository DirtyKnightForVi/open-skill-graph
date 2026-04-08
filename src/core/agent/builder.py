# -*- coding: utf-8 -*-
"""
智能体构建器 - 创建和配置ReActAgent
"""

from typing import Optional, Dict, Any
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit
from agentscope.token import CharTokenCounter
from agentscope.plan import PlanNotebook, Plan, SubTask
from logger.enhanced import create_enhanced_model
from config.settings import Config
from logger.setup import logger
import asyncio


class AgentBuilder:
    """智能体构建器"""

    @staticmethod
    def build_agent(
            name: str,
            sys_prompt: str,
            toolkit: Toolkit,
            model_config: Optional[Dict[str, Any]] = None,
            plan_notebook: Optional[PlanNotebook] = None
    ) -> ReActAgent:
        """
        构建ReActAgent智能体
        
        Args:
            name: 智能体名称
            sys_prompt: 系统提示词
            toolkit: 工具箱
            model_config: 模型配置，如果为None则使用默认配置
            plan: 计划对象，如果为None则不使用计划功能

        Returns:
            配置好的ReActAgent对象
        """
        if model_config is None:
            model_config = Config.get_llm_config()

        model = create_enhanced_model(**model_config)

        # 压缩模型配置（可选）
        compression_model = None
        if Config.LLM_MODEL_NAME_FOR_COMPRESS:
            compression_model = OpenAIChatModel(
                model_name=Config.LLM_MODEL_NAME_FOR_COMPRESS,
                api_key=Config.LLM_API_KEY,
                client_kwargs={
                    'base_url': Config.LLM_BASE_URL,
                },
                stream=True,
                extra_body={'enable_thinking': False}
            )

        agent = ReActAgent(
            name=name,
            model=model,
            sys_prompt=sys_prompt,
            toolkit=toolkit,
            memory=InMemoryMemory(),
            formatter=OpenAIChatFormatter(max_tokens=Config.MODEL_CONTEXT_LIMIT - Config.MODEL_MAX_TOKENS),
            max_iters=Config.REACT_MAX_ITERS,
            compression_config=CompressionConfig(
                enable=True,
                agent_token_counter=CharTokenCounter(),  # 智能体的 token 计数器
                trigger_threshold=Config.COMPRESS_LIMIT * 1024,  # 超过 512 个 token 时触发压缩
                keep_recent=3,  # 保持最近 3 条消息不被压缩
                compression_model=compression_model,
            ),
            plan_notebook=plan_notebook  # 将计划对象传递给智能体构建函数
        )

        agent.set_console_output_enabled(enabled=False)

        logger.info(f"Built agent '{name}' with toolkit")
        return agent

    @staticmethod
    def build_default_agent(
            sys_prompt: str,
            toolkit: Toolkit
    ) -> ReActAgent:
        """
        构建默认配置的智能体（名称为Friday）
        
        Args:
            sys_prompt: 系统提示词
            toolkit: 工具箱
            
        Returns:
            配置好的ReActAgent对象
        """
        return AgentBuilder.build_agent(
            name=Config.APP_NAME,
            sys_prompt=sys_prompt,
            toolkit=toolkit
        )

    @staticmethod
    async def build_skill_creator_agent(
            sys_prompt: str,
            toolkit: Toolkit
    ) -> ReActAgent:
        """
        构建技能创建智能体（带计划功能）
        
        Args:
            sys_prompt: 系统提示词
            toolkit: 工具箱
            
        Returns:
            配置好的ReActAgent对象（带PlanNotebook）
        """
        # 从plan_creator导入创建计划的函数
        from src.core.agent.plan_creator import create_skill_generation_plan

        # 创建计划笔记本
        plan_notebook = await create_skill_generation_plan()

        # 创建智能体并添加计划笔记本
        agent = AgentBuilder.build_agent(
            name=f"{Config.APP_NAME}_SkillCreator",
            sys_prompt=sys_prompt,
            toolkit=toolkit,
            plan_notebook=plan_notebook  # 将计划笔记本传递给智能体构建函数
        )

        # 添加计划功能
        # agent.plan_notebook = plan_notebook

        logger.info(f"Built skill-creator agent with plan notebook")
        return agent


class CompressionConfig(ReActAgent.CompressionConfig):
    summary_schema: Optional[dict] = None
