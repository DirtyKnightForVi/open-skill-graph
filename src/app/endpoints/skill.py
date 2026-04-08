# -*- coding: utf-8 -*-
"""
技能端点处理器 - 处理技能相关的CRUD操作
"""

from typing import Dict, Any
from core.agent.schemas import (
    SkillCreateRequest,
    GetUserSkillsRequest,
    SkillUseRequest,
    GeneralConversationRequest
)
from logger.setup import logger
from .base import BaseEndpointHandlers


class SkillEndpointHandlers(BaseEndpointHandlers):
    """技能端点处理器，处理技能相关的所有操作"""
    
    async def skill_create(self, request: SkillCreateRequest) -> Dict[str, Any]:
        """
        端点: /skill_create - 创建并注册用户自定义技能
        
        请求参数:
            - session_id: 会话唯一标识符
            - user_id: 用户唯一标识符
            - skill_name: 用户要新建的技能名称
            - skill_desc: 用户要新建的技能描述
            - need_creat_skill_file: 是否需要创建技能文件（可选，值为'yes'时创建新技能）
        
        响应参数:
            - status: 请求状态（success 或 error）
            - create_user_id: 用户唯一标识符
            - create_start_time: 技能创建时间戳
            - skill_storage_id: 新建技能的skill_storage_id
        """
        try:
            session_id = request.session_id
            user_id = request.user_id
            skill_name = getattr(request, 'skill_name', None)
            skill_desc = getattr(request, 'skill_desc', None)
            need_creat_skill_file = getattr(request, 'need_creat_skill_file', None)
            
            self._log_operation("[SKILL CREATION]", user_id, skill_name=skill_name, need_creat_skill_file=need_creat_skill_file)
            
            # 根据参数决定逻辑分支
            if need_creat_skill_file == "yes":
                # 原有逻辑：创建新技能
                result = await self.skill_service.create_session_with_skill_creator(
                    session_id, user_id, skill_name, skill_desc
                )
            else:
                # 新逻辑：二次优化已有技能
                result = await self.skill_service.add_existing_skill_to_todo(
                    session_id, user_id, skill_name, skill_desc
                )
            
            return result
        
        except Exception as e:
            return self._handle_error("skill_create", e, {"user_id": request.user_id})
    
    def get_user_skills(self, request: GetUserSkillsRequest) -> Dict[str, Any]:
        """
        端点: /get_user_skills - 获取用户已注册的技能列表
        
        请求参数:
            - user_id: 用户唯一标识符
        
        响应参数:
            - status: 请求状态（success 或 error）
            - user_id: 用户唯一标识符
            - skills: 用户已注册技能列表
        """
        try:
            user_id = request.user_id
            skills = self.skill_service.get_user_skills_formatted(user_id)
            
            self._log_operation("Get user skills", user_id, skill_count=len(skills))
            
            return {
                "status": "success",
                "user_id": user_id,
                "skills": skills
            }
        
        except Exception as e:
            return self._handle_error("get_user_skills", e, {"user_id": request.user_id})
    
    async def skill_use(self, request: SkillUseRequest) -> Dict[str, Any]:
        """
        端点: /skill_use - 使用用户已注册的、且当前想调用的技能
        
        请求参数:
            - session_id: 会话唯一标识符
            - user_id: 用户唯一标识符
            - skills_list: 用户想调用的技能列表（每个技能包含user_id和skill_name）
        
        响应参数:
            - status: 请求状态（success 或 error）
            - data: 操作结果消息
        """
        try:
            session_id = request.session_id
            user_id = request.user_id
            skills_list = request.skills_list
            
            # 记录技能来源日志 - 显示每个技能的来源用户
            skill_sources = [f"{skill['skill_name']}({skill['user_id']})" for skill in skills_list]
            logger.info(f"User {user_id} requesting to use skills from multiple sources: {skill_sources}")
            
            self._log_operation("Skill use", user_id, skills_list=skills_list)
                        
            result = await self.skill_service.attach_skills_to_session(
                session_id, user_id, skills_list
            )
            
            return result
        
        except Exception as e:
            return {
                "status": "error",
                "data": f"技能调用失败: {str(e)}"
            }
    
    async def general_conversation(self, request: GeneralConversationRequest) -> Dict[str, Any]:
        """
        端点: /general_conversation - 一般对话接口，支持多轮对话
        
        请求参数:
            - session_id: 会话唯一标识符
            - user_id: 用户唯一标识符
        
        响应参数:
            - status: 请求状态（success 或 error）
            - response: 操作结果消息
        """
        try:
            session_id = request.session_id
            user_id = request.user_id
            
            self._log_operation("General conversation", user_id)
            
            result = await self.skill_service.detach_session_skills(session_id, user_id)
            
            return result
        
        except Exception as e:
            return {
                "status": "error",
                "response": "当前对话技能工具已卸载"
            }