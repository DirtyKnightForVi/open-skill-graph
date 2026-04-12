# -*- coding: utf-8 -*-
"""
处理逻辑模块 - 将 process_with_agent 方法分解为清晰的步骤
"""
import asyncio
import json
import os
from copy import deepcopy
from typing import Tuple, List, Dict, Any, Optional
from agentscope.tool import Toolkit
from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter

from core.sandbox.utils import SkillFileSystemUtils
from core.skill.registry_client import RegistryClient
from src.core.skill.toolkit import SandboxToolkit, ToolkitBuilder
from core.agent.builder import AgentBuilder
from core.prompt import PromptBuilder
from logger.setup import logger
from config.settings import Config


def get_session_state(session_id: str, user_id: str, skill_manager) -> Tuple[List[Dict[str, Any]], bool, str]:
    """
    步骤1: 获取当前会话的状态
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        skill_manager: 技能管理器实例
    
    Returns:
        Tuple: (技能列表, 是否是技能创建模式, 用户上传目录路径)
    """
    # 获取当前会话的技能
    skills = skill_manager.get_session_skills(session_id, user_id)
    
    # 直接从session的state中获取创建模式
    is_skill_creator_mode = skill_manager.get_creator_mode(session_id, user_id)
    
    upload_dir = "/workspace"
    logger.info(f"Session state - skills: {len(skills)}, creator mode: {is_skill_creator_mode}, user upload dir is on sandbox.")
    
    return skills, is_skill_creator_mode, upload_dir


def setup_environment(
        session_id: str, 
        user_id: str, 
        app_state
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
    """
    步骤2: 创建沙箱或本地环境
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        if_sandbox: 是否使用沙箱 (1: 使用, 0: 不使用)
        app_state: 应用状态对象
    
    Returns:
        Tuple: (沙箱实例或None, 环境信息字典)
    """
    # 使用沙箱，若自定义类型失败则回退 base
    sandbox_types = [Config.SANDBOX_TYPE]
    if Config.SANDBOX_TYPE != "base":
        sandbox_types.append("base")

    last_error = None
    for sandbox_type in sandbox_types:
        try:
            sandboxes = app_state.sandbox_service.connect(
                session_id=session_id,
                user_id=user_id,
                sandbox_types=[sandbox_type],
            )
            target_box = sandboxes[0] if sandboxes else None
            sandbox_id = getattr(target_box, "sandbox_id", None)
            if not target_box or not sandbox_id:
                raise RuntimeError(
                    f"Sandbox created with invalid identity (sandbox_type={sandbox_type}, sandbox_id={sandbox_id})."
                )

            logger.info(
                f"Connected to sandbox for session {session_id}/{user_id} with type={sandbox_type}, sandbox_id={sandbox_id}."
            )
            return target_box, {"type": "sandbox", "sandbox": target_box, "sandbox_type": sandbox_type}
        except Exception as e:
            last_error = e
            logger.warning(f"Failed to connect sandbox type={sandbox_type}: {e}")

    raise RuntimeError(
        f"Failed to initialize sandbox for session {session_id}/{user_id}. "
        f"Please ensure the sandbox image exists and can be pulled. Last error: {last_error}"
    )


def build_system_prompt(
        skills: List[Dict[str, Any]], 
        is_skill_creator_mode: bool, 
        upload_dir: str, 
        to_do_list: List[Dict[str, str]] = None
    ) -> str:
    """
    步骤3: 初始化提示词
    
    Args:
        skills: 技能列表
        is_skill_creator_mode: 是否是技能创建模式
        upload_dir: 用户上传目录
        to_do_list: 待完善技能列表（技能创建模式时使用）
    
    Returns:
        完整的系统提示词
    """
    # 初始化系统提示词，告知用户的上传目录
    system_prompt = PromptBuilder.build_base_prompt()
    system_prompt += f"\n# 用户的文件空间\n1. 注意：用户的工作空间位于：`/workspace`。\n2. 你可以使用安全的工具查看。\n3. 你首先应该考虑查看文件，而不是修改文件。修改前应该询问用户是否继续。\n\n"
    
    if is_skill_creator_mode:
        # 技能创建模式
        system_prompt += PromptBuilder.build_skill_creator_prompt(to_do_list)
        logger.info(f"Built skill-creator prompt with {len(to_do_list) if to_do_list else 0} to-do items")
    elif skills and len(skills) > 0:
        # 普通技能模式
        skill_names = [
            skill.get("skill_name", "") if isinstance(skill, dict) else getattr(skill, "skill_name", "")
            for skill in skills
        ]
        system_prompt += PromptBuilder.build_agent_prompt(skill_names)
    
    
    logger.info(f"Built system prompt - creator mode: {is_skill_creator_mode}, skills count: {len(skills)}")
    
    return system_prompt


def build_toolkit(
        skills: List[Dict[str, Any]], 
        is_skill_creator_mode: bool, 
        sandbox_instance: Optional[Any]
    ) -> Toolkit:
    """
    步骤4: 构建工具箱
    
    Args:
        skills: 技能列表
        is_skill_creator_mode: 是否是技能创建模式
        sandbox_instance: 沙箱实例（如果有）
        if_sandbox: 是否使用沙箱 (1: 使用, 0: 不使用)
    
    Returns:
        配置好的Toolkit对象
    """
    if sandbox_instance is not None:
        # 使用沙箱模式， 默认使用沙箱内的全部工具（暂定）
        toolkit = ToolkitBuilder.build_toolkit_for_sandbox(sandbox_instance)
        logger.info("Built toolkit for sandbox mode")
        return toolkit


def copy_local_skill_to_sandbox(sandbox_instance, skills, toolkit=None, is_skill_creator_mode=False, to_do_list=None):
    for skill in skills:
        skill_name = skill.get("skill_name", "") if isinstance(skill, dict) else getattr(skill, "skill_name", "")
        skill_desc = skill.get("skill_description", "") if isinstance(skill, dict) else getattr(skill,
                                                                                                "skill_description", "")
        skill_storage_key = skill.get("skill_storage_id", "") if isinstance(skill, dict) else getattr(skill,
                                                                                                  "skill_storage_id", "")
        if skill_name and skill_desc:
            if toolkit is not None:
                toolkit.register_agent_skill_from_online_data(skill_name, skill_desc)
                logger.info(f"Registered online skill: {skill_name}")
            sandbox_instance.manager_api.fs_write_from_path(
                sandbox_instance.sandbox_id,
                f"/workspace/skill/{skill_storage_key}.zip",
                f"Agent_Work_Dir/Files/Download_Skills/{skill_storage_key}.zip"
            )
            sandbox_instance.run_shell_command(f"mkdir -p /workspace/skill/{skill_name}")
            sandbox_instance.run_shell_command(
                f"unzip -o /workspace/skill/{skill_storage_key}.zip -d /workspace/skill/{skill_name}")
            sandbox_instance.run_shell_command(f"rm -rf /workspace/skill/{skill_storage_key}.zip")

            if is_skill_creator_mode and to_do_list:
                todo_item = to_do_list[0]
                sandbox_instance.manager_api.fs_write_from_path(
                    sandbox_instance.sandbox_id,
                    f"/workspace/skill/{todo_item['skill_storage_id']}.zip",
                    f"Agent_Work_Dir/Files/Download_Skills/{todo_item['skill_storage_id']}.zip"
                )
                sandbox_instance.run_shell_command(f"mkdir -p /workspace/skill/{todo_item['skill_name']}")
                sandbox_instance.run_shell_command(
                    f"unzip -o /workspace/skill/{todo_item['skill_storage_id']}.zip -d /workspace/skill/{todo_item['skill_name']}")
                sandbox_instance.run_shell_command(f"rm -rf /workspace/skill/{todo_item['skill_storage_id']}.zip")

async def sandbox_load_local_skill(sandbox_instance, skills, is_skill_creator_mode, to_do_list, redis_client):
    """沙箱内加载本地技能包"""
    async def sync_binding_status(target_skills: List[Dict[str, Any]], status: str):
        source = str(Config.SKILL_METADATA_SOURCE).lower().strip()
        if source not in {"registry", "auto"} or not Config.REGISTRY_BASE_URL:
            return

        bindings = [skill for skill in target_skills if skill.get("registry_binding_id")]
        if not bindings:
            return

        async with RegistryClient(base_url=Config.REGISTRY_BASE_URL, timeout=Config.REGISTRY_TIMEOUT) as client:
            tasks = []
            for skill in bindings:
                storage_id = skill.get("skill_storage_id", "")
                mounted_path = f"/workspace/skill/{storage_id}".rstrip("/")
                tasks.append(
                    client.update_session_binding(
                        binding_id=skill.get("registry_binding_id"),
                        status=status,
                        sandbox_id=sandbox_instance.sandbox_id,
                        mounted_path=mounted_path,
                    )
                )
            results = await asyncio.gather(*tasks, return_exceptions=True)

        failed = [item for item in results if item is not True]
        if failed:
            logger.warning(f"Registry binding status sync incomplete: status={status}, failed_count={len(failed)}")

    logger.info(f"开始从本地技能仓库加载技能到沙箱，沙箱ID: {sandbox_instance.sandbox_id}")
    logger.info(f"技能数量: {len(skills)}，技能名称列表: {[skill.get('skill_name') for skill in skills]}")
    logger.info(f"技能创建模式: {is_skill_creator_mode}")

    storage_keys = [skill['skill_storage_id'] for skill in skills if skill.get('skill_storage_id')]
    loaded_skills = [skill for skill in skills if skill.get('skill_storage_id')]
    try:
        if storage_keys:
            logger.info(f"开始从本地技能仓库复制技能，storage_keys: {storage_keys}")
            SkillFileSystemUtils().sandbox_download_skill_packages(sandbox_instance, storage_keys)

            await redis_client.set(
                f"{sandbox_instance.sandbox_id}_download_skills",
                json.dumps(skills),
                ex=12*3600
            )
            logger.debug(f"技能信息已存储到Redis")
            await sync_binding_status(loaded_skills, "mounted")

        if is_skill_creator_mode and to_do_list:
            logger.info(f"技能创建模式，额外加载待完善技能: {to_do_list[0]['skill_storage_id']}")
            SkillFileSystemUtils().sandbox_download_skill_packages(
                sandbox_instance,
                [to_do_list[0]["skill_storage_id"]]
            )
    except Exception:
        await sync_binding_status(loaded_skills, "failed")
        raise


async def register_skills(
        toolkit: SandboxToolkit, 
        skills: List[Dict[str, Any]], 
        redis_client,
        is_skill_creator_mode: bool,
        sandbox_instance: Optional[Any],
        to_do_list: List[Dict[str, str]] = None
    ) -> None:
    """
    步骤5: 加载技能
    
    Args:
        toolkit: 工具箱实例
        skills: 技能列表
        is_skill_creator_mode: 是否是技能创建模式
        sandbox_instance: 沙箱实例（如果有）
        to_do_list: 待完善技能列表（技能创建模式时使用）
    """
    if sandbox_instance is not None:
        # 使用沙箱：使用远端注册技能的方法
        if skills and len(skills) > 0:
            # 转换为 SandboxToolkit 以便使用在线技能注册
            if isinstance(toolkit, SandboxToolkit):
                # 在沙箱内准备技能文件
                redis_key = f"{sandbox_instance.sandbox_id}_download_skills"
                if not await redis_client.exists(redis_key):
                    # 启动沙箱时未加载本地技能包
                    await sandbox_load_local_skill(sandbox_instance, skills, is_skill_creator_mode, to_do_list, redis_client)

                need_to_registed_skills = json.loads(await redis_client.get(redis_key))
                for skill in need_to_registed_skills:
                    toolkit.register_agent_skill_from_online_data(
                        skill['skill_name'],
                        skill['skill_description'],
                        skill.get('skill_storage_id')
                    )
            else:
                logger.warning("Toolkit is not SandboxToolkit, skipping online skill registration")


async def create_agent(system_prompt: str, toolkit: Toolkit, is_skill_creator_mode: bool) -> Any:
    """
    步骤6: 创建智能体（异步版本）
    
    Args:
        system_prompt: 系统提示词
        toolkit: 工具箱实例
        is_skill_creator_mode: 是否是技能创建模式
    
    Returns:
        配置好的智能体对象
    """
    if is_skill_creator_mode:
        # 技能创建模式：使用带计划的智能体
        agent = await AgentBuilder.build_skill_creator_agent(system_prompt, toolkit)
        logger.info("Created skill-creator agent with plan notebook")
        # agent = AgentBuilder.build_default_agent(system_prompt, toolkit)
        # logger.info(f"Created skill-creator agent with {Config.SKILL_CREATOR_NAME} skill to build a new Skill.")
    else:
        # 普通模式：使用默认智能体
        agent = AgentBuilder.build_default_agent(system_prompt, toolkit)
        logger.info("Created default agent")
    
    return agent


def add_debug_hooks(agent: Any) -> Any:
    """
    添加调试钩子到智能体
    
    Args:
        agent: 智能体实例
    
    Returns:
        添加了调试钩子的智能体
    """
    import functools
    
    def out_put_kwargs(func):
        @functools.wraps(func)
        def wrapper(**kwargs):
            logger.info(f"Agent called with: {kwargs}")
            response = func(**kwargs)
            logger.info(f"Agent responsed with: {response}")
            return response
        return wrapper
    
    # 添加调试钩子
    agent.model.client.chat.completions.create = out_put_kwargs(agent.model.client.chat.completions.create)
    
    logger.info("Added debug hooks to agent")
    return agent
