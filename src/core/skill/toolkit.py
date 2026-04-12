# -*- coding: utf-8 -*-
"""
工具箱构建器 - 动态构建和管理工具箱
"""

from logger.setup import logger
from typing import List, Dict, Optional, Any
from agentscope.tool import Toolkit, execute_python_code, execute_shell_command, view_text_file
from agentscope.tool import write_text_file
from agentscope.tool import _types

class ToolkitBuilder:
    """工具箱构建器，用于动态装配工具和技能"""
    
    # 基础工具 为 非沙箱环境 准备
    BASIC_TOOLS = ["view_text_file"]
    WRITE_TOOLS = ["write_text_file", "insert_text_file"]
    EXECUTE_TOOLS = ["execute_python_code", "execute_shell_command"]
    
    @staticmethod
    def build_basic_toolkit() -> Toolkit:
        """构建基础工具箱"""
        toolkit = Toolkit()
        toolkit.register_tool_function(execute_shell_command)
        # 测试用
        # toolkit.register_tool_function(write_text_file)
        toolkit.register_tool_function(view_text_file)
        logger.info("Built BASIC toolkit with `execute_shell_command` and `view_text_file`.")
        return toolkit
    
    @staticmethod
    def build_full_toolkit() -> Toolkit:
        """构建完整工具箱"""
        toolkit = Toolkit()
        toolkit.register_tool_function(execute_shell_command)
        toolkit.register_tool_function(view_text_file)
        toolkit.register_tool_function(execute_python_code)
        logger.info("Built FULL toolkit with `execute_shell_command`, `view_text_file` and `execute_python_code`.")
        return toolkit
    
    @classmethod
    def build_creator_toolkit(cls) -> Toolkit:
        """为skill-creator构建工具箱"""
        toolkit = ToolkitBuilder.build_full_toolkit()
        toolkit.register_tool_function(write_text_file)
        logger.info("Built CREATOR toolkit with `execute_shell_command`, `view_text_file`, `execute_python_code` and `write_text_file`.")
        return toolkit
    
    @staticmethod
    def register_skills(toolkit: Toolkit, skill_dirs: List[str]) -> None:
        """为工具箱注册技能"""
        for skill_dir in skill_dirs:
            try:
                toolkit.register_agent_skill(skill_dir)

                logger.info(f"Registered skill from: {skill_dir}")
            except Exception as e:
                logger.error(f"Failed to register skill from {skill_dir}: {str(e)}")
    
    @staticmethod
    def build_toolkit_for_skills(
        skills: List[Dict[str, Any]],
        include_write_tools: bool = False
    ) -> Toolkit:
        """
        根据技能列表构建工具箱
        
        Args:
            skills: 技能列表，每个技能包含name和skill_dir
            include_write_tools: 是否包含文件写入工具
            
        Returns:
            配置好的Toolkit对象
        """
        if include_write_tools:
            toolkit = ToolkitBuilder.build_creator_toolkit()
        else:
            toolkit = ToolkitBuilder.build_full_toolkit()
        # 注册技能
        skill_dirs = [
            skill.get("skill_dir", "") if isinstance(skill, dict) else getattr(skill, "skill_dir", "")
            for skill in skills
        ]
        ToolkitBuilder.register_skills(toolkit, skill_dirs)
        
        return toolkit
    
    @staticmethod
    def build_toolkit_for_sandbox(target_sandbox) -> 'Toolkit':
        """
        为沙箱环境构建工具箱
        
        Args:
            target_sandbox: 沙箱实例
            
        Returns:
            配置好的Toolkit对象
        """
        from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter
        
        # 创建 SandboxToolkit 实例以支持在线技能注册
        toolkit = SandboxToolkit(sandbox=target_sandbox)
        
        # 注册沙箱中的工具
        tools = target_sandbox.list_tools()
        if not isinstance(tools, dict):
            raise RuntimeError(
                f"Invalid list_tools response type: {type(tools).__name__}, value={tools}"
            )
        for name in tools:
            if not isinstance(tools[name], (list, tuple)):
                raise RuntimeError(
                    f"Invalid tools payload for namespace '{name}': {tools[name]}"
                )
            for tool_name in tools[name]:
                toolkit.register_tool_function(sandbox_tool_adapter(getattr(target_sandbox, tool_name)))
        
        logger.info(f"Built sandbox toolkit with {len(toolkit.tools)} tools")
        return toolkit


class SandboxToolkit(Toolkit):
    """扩展的 Toolkit 类，支持在线技能注册"""
    
    def __init__(self, sandbox=None, agent_skill_instruction=None, agent_skill_template=None):
        super().__init__(agent_skill_instruction, agent_skill_template)
        self.sandbox = sandbox

    def register_agent_skill_from_online_data(self, skill_name, skill_desc, skill_storage_id=None):
        """从在线数据源注册一个agent skill的元信息
        
        Args:
            skill_name (str): 技能名称
            skill_desc (str): 技能描述
            skill_storage_id (str, optional): 技能的本地存储 key，用于确定沙箱内目录
        """
        if skill_name in self.skills:
            raise ValueError(
                f"An agent skill with name '{skill_name}' is already registered "
                "in the toolkit.",
            )
        
        # 确保参数类型正确，与原始方法保持一致
        skill_name, skill_desc = str(skill_name), str(skill_desc)
        
        # 使用skill_storage_id作为目录名，如果没有提供则使用skill_name
        skill_dir = f'/workspace/skill/{skill_storage_id}/{skill_name}' if skill_storage_id else f'/workspace/skill/{skill_name}'
        
        self.skills[skill_name] = _types.AgentSkill(
            name=skill_name,
            description=skill_desc,
            dir=skill_dir,  # 使用skill_storage_id作为目录名，避免技能名冲突
        )
        
        # 添加日志记录，与原始方法保持一致
        logger.info(
            "Registered agent skill '%s' from online data source with dir '%s'.",
            skill_name,
            skill_dir,
        )
