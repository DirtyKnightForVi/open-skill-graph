# -*- coding: utf-8 -*-
"""
沙箱端点处理器 - 整合沙箱相关的功能模块
"""

from typing import Dict, Any
from core.skill.service import SkillService
from .base import BaseEndpointHandlers
from .skill import SkillEndpointHandlers
from .sandbox_file import SandboxFileEndpointHandlers


class SandboxEndpointHandlers(BaseEndpointHandlers):
    """沙箱端点处理器，整合沙箱相关的功能模块"""
    
    def __init__(self, skill_service: SkillService):
        """
        初始化沙箱端点处理器
        
        Args:
            skill_service: 技能服务实例
        """
        super().__init__(skill_service)
        
        # 初始化各个子模块
        self.skill_handlers = SkillEndpointHandlers(skill_service)
        self.sandbox_file_handlers = SandboxFileEndpointHandlers(skill_service)
    
    # 技能相关端点 - 代理到 SkillEndpointHandlers
    async def skill_create(self, request) -> Dict[str, Any]:
        """创建技能"""
        return await self.skill_handlers.skill_create(request)
    
    # 暂时先保留，等待java后端给我一个新的接口。
    def get_user_skills(self, request) -> Dict[str, Any]:
        """获取用户技能列表"""
        return self.skill_handlers.get_user_skills(request)
    
    async def skill_use(self, request) -> Dict[str, Any]:
        """使用技能"""
        return await self.skill_handlers.skill_use(request)
    
    async def general_conversation(self, request) -> Dict[str, Any]:
        """一般对话"""
        return await self.skill_handlers.general_conversation(request)
    
    # 沙箱文件相关端点 - 代理到 SandboxFileEndpointHandlers
    async def upload_file_to_sandbox(self, user_id: str, session_id: str, filename: str, file_content: bytes, sandbox_service) -> Dict[str, Any]:
        """上传用户文件到沙箱空间"""
        return await self.sandbox_file_handlers.upload_file_to_sandbox(user_id, session_id, filename, file_content, sandbox_service)
    
    async def list_user_files(self, request, sandbox_service) -> Dict[str, Any]:
        """获取沙箱工作空间文件列表"""
        return await self.sandbox_file_handlers.list_files_in_sandbox(request.user_id, request.session_id, sandbox_service)

    async def list_skill_files(self, request, sandbox_service) -> Dict[str, Any]:
        """获取特定技能下的文件结构"""
        
        return await self.sandbox_file_handlers.list_skill_files_in_sandbox(request.user_id, request.session_id, request.skill_name, sandbox_service)
    
    async def download_file_from_sandbox(self, user_id: str, session_id: str, file_path: str, sandbox_service, skill_name: str = "") -> Dict[str, Any]:
        """从沙箱下载用户文件"""
        return await self.sandbox_file_handlers.download_file_from_sandbox(user_id, session_id, file_path, sandbox_service, skill_name)
    
    async def edit_file_in_sandbox(self, request, sandbox_service) -> Dict[str, Any]:
        """在沙箱中编辑用户文件或技能文件内容"""
        return await self.sandbox_file_handlers.edit_file_in_sandbox(
            request.user_id, 
            request.session_id,
            request.skill_name or "",  # 处理 None 值
            request.file_path,
            request.file_content,
            sandbox_service
        )
