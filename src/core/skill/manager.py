# -*- coding: utf-8 -*-
"""
技能管理器 - 基于本地存储与元信息接口的技能管理
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
import traceback
from typing import Dict, List, Optional, Any
from agentscope.module import StateModule
# from agentscope.session import JSONSession, RedisSession
from config.settings import Config
from core.skill.storage_ops import StorageOperations
from core.skill.meta_client import SkillMetaClient
from core.skill.registry_client import RegistryClient
from logger.setup import logger

# logger = logging.getLogger(__name__)


class Manager(StateModule):
    """
    技能管理器 - 基于本地存储与元信息接口的轻量级实现
    
    核心职责：
    1. 管理会话与技能的关联关系
    2. 通过接口获取技能信息（不再依赖本地缓存）
    3. 与本地技能存储集成进行技能文件操作
    4. 处理 skill-creator 的 to_do 逻辑
    
    所有技能信息都通过元信息接口动态获取
    """
    
    def __init__(self, core_session):
        """
        初始化技能管理器
        
        Args:
            core_session: JSONSession 实例，或这Redis
        """
        super().__init__()
        self.core_session = core_session
        self.storage_ops = StorageOperations()
        
        # 会话技能关联：{session_id -> {user_id -> {skills: [...], to_do: [...], created_at: ..., updated_at: ...}}}
        self.session_skills: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.register_state('session_skills')
        
        # 元信息客户端（可切换: meta / registry / auto）
        source = str(Config.SKILL_METADATA_SOURCE).lower().strip()
        if source == "registry":
            self.meta_client = RegistryClient(
                base_url=Config.REGISTRY_BASE_URL,
                timeout=Config.REGISTRY_TIMEOUT,
            )
        elif source == "auto":
            if Config.REGISTRY_BASE_URL:
                self.meta_client = RegistryClient(
                    base_url=Config.REGISTRY_BASE_URL,
                    timeout=Config.REGISTRY_TIMEOUT,
                )
            else:
                self.meta_client = SkillMetaClient()
        else:
            self.meta_client = SkillMetaClient()
        
        self._state_flag = "skillManager"
        self._state_flag_session = "skillManagerSession"
        
        logger.info(f"✅ Manager initialized with metadata source={source}, client={self.meta_client.__class__.__name__}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._load_session_skills()
        await self.meta_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._save_session_skills()
        await self.meta_client.__aexit__(exc_type, exc_val, exc_tb)
    
    # ==================== 会话管理 ====================
    
    async def _load_session_skills(self):
        """从 JSONSession 加载会话技能数据"""
        try:
            await self.core_session.load_session_state(
                session_id=self._state_flag_session,
                user_id=self._state_flag,
                allow_not_exist=True,
                skillManager=self
            )
            logger.info("Loaded session skills from JSONSession")
        except Exception as e:
            logger.info(f"No previous session skills found, initializing empty: {str(e)}")
            self.session_skills = {}
    
    async def _save_session_skills(self):
        """将会话技能数据保存到 JSONSession"""
        await self.core_session.save_session_state(
            session_id=self._state_flag_session,
            user_id=self._state_flag,
            skillManager=self
        )
    
    def create_session(self, session_id: str, user_id: str) -> bool:
        """
        创建会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 创建是否成功
        """
        try:
            if session_id not in self.session_skills:
                self.session_skills[session_id] = {}
            
            if user_id not in self.session_skills[session_id]:
                self.session_skills[session_id][user_id] = {
                    "skills": [],
                    "to_do": [],
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "is_creator_mode": False
                }
                logger.info(f"Created session: {session_id}/{user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to create session {session_id}/{user_id}: {str(e)}")
            return False
    
    async def cleanup_session(self, session_id: str, user_id: str) -> bool:
        """
        清理会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 清理是否成功
        """
        try:
            if session_id in self.session_skills and user_id in self.session_skills[session_id]:
                del self.session_skills[session_id][user_id]
                logger.info(f"Cleaned up session: {session_id}/{user_id}")
                
                # 如果会话没有任何用户了，删除会话
                if not self.session_skills[session_id]:
                    del self.session_skills[session_id]
                
                await self._save_session_skills()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}/{user_id}: {str(e)}")
            return False
    
    # ==================== 技能装配 ====================
    
    async def attach_skills(
            self, 
            session_id: str, 
            user_id: str, 
            skill_names: List[str], 
            skill_owner_id: str) -> Dict[str, List[str]]:
        """
        为会话装配技能（支持使用来自特定用户的技能）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（当前使用者）
            skill_names: 要装配的技能名称列表
            skill_owner_id: 技能归属用户ID
            
        Returns:
            dict: {
                "attached": [...],  # 成功装配的技能列表
                "failed": [...]     # 失败的技能列表
            }
        """
        try:
            # 确保会话存在
            self.create_session(session_id, user_id)
            
            attached_skills = []
            failed_skills = []
            current_time = int(time.time())
            
            for skill_name in skill_names:
                # 获取技能信息（通过接口）
                skill_info = await self._get_skill_info(skill_owner_id, skill_name)
                
                if skill_info is None:
                    failed_skills.append(skill_name)
                    logger.warning(f"Skill {skill_name} not found for user {skill_owner_id}")
                else:
                    # 技能信息已经包含owner_id字段，直接使用
                    skill_info_with_owner = skill_info.copy()
                    
                    # 装配技能到会话（避免重复）
                    existing_names = [s["skill_name"] for s in self.session_skills[session_id][user_id]["skills"]]
                    if skill_name not in existing_names:
                        self.session_skills[session_id][user_id]["skills"].append(skill_info_with_owner)
                        attached_skills.append(skill_name)
                        logger.info(f"Attached skill {skill_name} (owner: {skill_owner_id}) to session {session_id}/{user_id}")
            
            # 更新修改时间
            self.session_skills[session_id][user_id]["updated_at"] = current_time
            
            # 保存到文件
            await self._save_session_skills()
            
            result = {
                "attached": attached_skills,
                "failed": failed_skills
            }
            
            logger.info(f"Attached skills to session {session_id}/{user_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to attach skills to session {session_id}/{user_id}: {str(e)}")
            return {"attached": [], "failed": skill_names}
    
    async def detach_skills(self, session_id: str, user_id: str, skill_names: Optional[List[str]] = None) -> bool:
        """
        从会话卸载技能
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            skill_names: 要卸载的技能名称列表（如果为None，则卸载所有技能）
            
        Returns:
            bool: 卸载是否成功
        """
        try:
            if session_id not in self.session_skills or user_id not in self.session_skills[session_id]:
                logger.warning(f"Session {session_id}/{user_id} not found")
                return False
            
            if skill_names is None:
                # 卸载所有技能
                self.session_skills[session_id][user_id]["skills"] = []
                self.session_skills[session_id][user_id]["to_do"] = []
                logger.info(f"Detached all skills from session {session_id}/{user_id}")
            else:
                # 卸载指定技能
                current_skills = self.session_skills[session_id][user_id]["skills"]
                self.session_skills[session_id][user_id]["skills"] = [
                    skill for skill in current_skills if skill["skill_name"] not in skill_names
                ]
                
                # 同时从 to_do 中移除
                current_todos = self.session_skills[session_id][user_id].get("to_do", [])
                self.session_skills[session_id][user_id]["to_do"] = [
                    todo for todo in current_todos if todo["skill_name"] not in skill_names
                ]
                logger.info(f"Detached skills {skill_names} from session {session_id}/{user_id}")
            
            # 更新修改时间
            self.session_skills[session_id][user_id]["updated_at"] = int(time.time())
            
            # 保存到文件
            await self._save_session_skills()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to detach skills from session {session_id}/{user_id}: {str(e)}")
            return False
    
    # ==================== 技能查询 ====================
    
    async def _get_skill_info(self, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能信息（通过元信息接口，不再依赖本地缓存）
        
        Args:
            user_id: 用户ID
            skill_name: 技能名称
            
        Returns:
            dict: 技能信息，包含name、type、skill_storage_id、skill_description
            返回 None 表示技能不存在
        """
        try:
            # 通过接口获取技能元数据
            skill_info = await self.meta_client.get_skill_meta(user_id, skill_name)
            return skill_info
            
        except Exception as e:
            logger.error(f"Error getting skill info for {user_id}/{skill_name}: {e}")
            return None
    
    def get_session_skills(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的所有装配技能
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            list: 会话的技能列表
        """
        if session_id not in self.session_skills or user_id not in self.session_skills[session_id]:
            return []
        
        return self.session_skills[session_id][user_id]["skills"]
    
    def has_skill(self, session_id: str, user_id: str, skill_name: str) -> bool:
        """
        检查会话是否装配了指定技能
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            skill_name: 技能名称
            
        Returns:
            bool: 是否装配了该技能
        """
        skills = self.get_session_skills(session_id, user_id)
        return any(skill["skill_name"] == skill_name for skill in skills)
    
    def get_session_info(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话的详细信息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            dict: 会话信息，包括创建时间、修改时间、技能列表
        """
        if session_id not in self.session_skills or user_id not in self.session_skills[session_id]:
            return None
        
        return self.session_skills[session_id][user_id]
    
    # ==================== 技能创建 ====================
    
    async def create_skill_with_to_do(self, session_id: str, user_id: str, skill_name: str, skill_desc: str) -> Dict[str, Any]:
        """
        创建新技能的完整工作流（与 STORAGE 集成）
        
        步骤：
        1. 从模板复制文件到临时目录
        2. 更新 SKILL.md 中的 name 和 description
        3. 打包目录为 tar 文件
        4. 上传到 STORAGE
        5. 在 session_skills 中添加 to_do 字段
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            skill_name: 新技能的名称
            skill_desc: 新技能的描述
            
        Returns:
            dict: {
                "success": bool,
                "skill_storage_id": str,  # STORAGE key
                "message": str
            }
        """
        try:
            # 步骤1：检查会话是否已初始化，且只有 skill-creator
            if session_id not in self.session_skills:
                logger.error(f"Session {session_id} not found")
                return {"success": False, "message": f"Session {session_id} not found"}
            
            if user_id not in self.session_skills[session_id]:
                logger.error(f"User {user_id} not found in session {session_id}")
                return {"success": False, "message": f"User {user_id} not found in session {session_id}"}
            
            # 检查是否只有 skill-creator
            skills = self.session_skills[session_id][user_id].get("skills", [])
            skill_names = [s.get("skill_name") for s in skills]
            
            if len(skills) != 1 or skill_names[0] != Config.SKILL_CREATOR_NAME:
                logger.error("Session must have only 'skill-creator' skill to create new skill")
                return {"success": False, "message": "Session must have only 'skill-creator' skill to create new skill"}
            
            # 步骤2：创建临时技能目录
            import tempfile
            import shutil
            from pathlib import Path
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_skill_dir = Path(temp_dir) / skill_name
                temp_skill_dir.mkdir(exist_ok=True)
                
                logger.info(f"Created temporary skill directory: {temp_skill_dir}")
                
                # 步骤3：从模板复制文件
                template_dir = Path(Config.SKILLS_CREATE_TEMPLATE)
                if not template_dir.exists():
                    logger.error(f"Template directory not found: {template_dir}")
                    return {"success": False, "message": f"Template directory not found: {template_dir}"}
                
                # 复制模板文件
                for item in template_dir.iterdir():
                    if item.name == 'SKILL.md':
                        # 特殊处理 SKILL.md，更新 name 和 description
                        with open(item, "r", encoding='utf-8') as template:
                            content = template.read()
                            # 简单的字符串替换（实际使用时可能需要更复杂的模板处理）
                            skill_content = content.replace('{{skill_name}}', skill_name)
                            skill_content = skill_content.replace('{{skill_description}}', skill_desc)
                        
                        with open(temp_skill_dir / item.name, 'w', encoding='utf-8') as skill_file:
                            skill_file.write(skill_content)
                        continue
                    
                    if item.is_dir():
                        shutil.copytree(item, temp_skill_dir / item.name, dirs_exist_ok=True)
                    elif item.is_file() and item.name != ".gitkeep":
                        shutil.copy2(item, temp_skill_dir / item.name)
                
                logger.info(f"Copied template files to {temp_skill_dir}")
                
                # 步骤4：保存到本地技能仓库
                storage_key = self.storage_ops.save_skill_package(temp_skill_dir, user_id, skill_name)
                
                # 步骤5：在 session_skills 中添加 to_do 字段
                to_do_item = {
                    "skill_name": skill_name,
                    "skill_storage_id": storage_key,
                    "skill_description": skill_desc,
                    "owner_id": user_id  # 因为是to_do，说明是自己的技能
                }


                if "to_do" not in self.session_skills[session_id][user_id]:
                    self.session_skills[session_id][user_id]["to_do"] = []
                
                # 检查是否已存在，避免重复
                current_todo_skill_names = [item["skill_name"] for item in self.session_skills[session_id][user_id]["to_do"]]
                if skill_name not in current_todo_skill_names:
                    self.session_skills[session_id][user_id]["to_do"].append(to_do_item)
                else:
                    # 更新现有项
                    todo_skill_index = current_todo_skill_names.index(skill_name)
                    self.session_skills[session_id][user_id]["to_do"][todo_skill_index] = to_do_item
                
                # 更新修改时间并设置创建模式
                self.session_skills[session_id][user_id]["updated_at"] = int(time.time())
                self.session_skills[session_id][user_id]["is_creator_mode"] = True
                
                # 保存到文件
                await self._save_session_skills()
                
                logger.info(f"Added to_do item for skill {skill_name} in session {session_id}/{user_id}")
                
                # 注意：不再更新本地缓存，技能信息通过接口实时获取
                logger.info(f"Skill {skill_name} created for user {user_id}")
                
                return {
                    "success": True,
                    "skill_storage_id": storage_key,
                    "message": f"技能 {skill_name} 创建并保存到本地仓库成功"
                }
                
        except Exception as e:
            logger.error(f"Error creating skill: {str(e)}")
            return {"success": False, "message": f"创建技能失败: {str(e)}"}
    
    def get_session_to_do(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        """
        获取会话的 to_do 列表
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            list: to_do 项列表
        """
        if session_id in self.session_skills and user_id in self.session_skills[session_id]:
            return self.session_skills[session_id][user_id].get("to_do", [])
        return []
    
    def _update_creator_mode_from_todos(self, session_id: str, user_id: str) -> bool:
        """
        根据to_do列表状态更新创建模式
        当to_do列表为空时，自动设置is_creator_mode为False
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 是否进行了更新
        """
        try:
            if session_id not in self.session_skills or user_id not in self.session_skills[session_id]:
                return False
            
            to_do_list = self.session_skills[session_id][user_id].get("to_do", [])
            current_mode = self.session_skills[session_id][user_id].get("is_creator_mode", False)
            
            # 如果to_do列表为空但is_creator_mode为True，则重置为False
            if not to_do_list and current_mode:
                self.session_skills[session_id][user_id]["is_creator_mode"] = False
                self.session_skills[session_id][user_id]["updated_at"] = int(time.time())
                logger.info(f"[AUTO RESET] Set is_creator_mode to False for session {session_id}/{user_id} because to_do list is empty")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating creator mode based on todos: {str(e)}")
            return False
    
    def set_creator_mode(self, session_id: str, user_id: str, mode: bool) -> bool:
        """
        设置会话的创建模式
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            mode: 创建模式状态
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if session_id not in self.session_skills or user_id not in self.session_skills[session_id]:
                logger.warning(f"Session {session_id}/{user_id} not found")
                return False
            
            self.session_skills[session_id][user_id]["is_creator_mode"] = mode
            self.session_skills[session_id][user_id]["updated_at"] = int(time.time())
            
            # 保存到文件
            asyncio.create_task(self._save_session_skills())
            
            logger.info(f"Set creator mode to {mode} for session {session_id}/{user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set creator mode for session {session_id}/{user_id}: {str(e)}")
            return False
    
    def get_creator_mode(self, session_id: str, user_id: str) -> bool:
        """
        获取会话的创建模式
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 创建模式状态，默认为False
        """
        if session_id in self.session_skills and user_id in self.session_skills[session_id]:
            # 自动检查是否需要重置创建模式
            self._update_creator_mode_from_todos(session_id, user_id)
            return self.session_skills[session_id][user_id].get("is_creator_mode", False)
        return False
    
    async def add_skill_to_todo(self, session_id: str, user_id: str, skill_name: str, skill_desc: str, owner_id: str) -> Dict[str, Any]:
        """
        将已有技能添加到to_do列表中，用于二次优化
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            skill_name: 技能名称
            skill_desc: 技能描述
            owner_id: 技能归属用户ID
            
        Returns:
            dict: {
                "success": bool,
                "skill_storage_id": str,
                "message": str
            }
        """
        try:
            # 确保会话存在
            self.create_session(session_id, user_id)
            
            # 生成本地技能存储 key
            skill_storage_id = f"SKILL_{owner_id}_{skill_name}"
            
            # 创建to_do项
            to_do_item = {
                "skill_name": skill_name,
                "skill_storage_id": skill_storage_id,
                "skill_description": skill_desc,
                "owner_id": owner_id
            }
            
            # 初始化to_do列表（如果不存在）
            if "to_do" not in self.session_skills[session_id][user_id]:
                self.session_skills[session_id][user_id]["to_do"] = []
            
            # 检查是否已存在，避免重复
            current_todo_skill_names = [item["skill_name"] for item in self.session_skills[session_id][user_id]["to_do"]]
            if skill_name not in current_todo_skill_names:
                self.session_skills[session_id][user_id]["to_do"].append(to_do_item)
            else:
                # 更新现有项
                todo_skill_index = current_todo_skill_names.index(skill_name)
                self.session_skills[session_id][user_id]["to_do"][todo_skill_index] = to_do_item
            
            # 更新修改时间并设置创建模式
            self.session_skills[session_id][user_id]["updated_at"] = int(time.time())
            self.session_skills[session_id][user_id]["is_creator_mode"] = True
            
            # 保存到文件
            await self._save_session_skills()
            
            logger.info(f"Added skill {skill_name} to to_do list for session {session_id}/{user_id}")
            
            return {
                "success": True,
                "skill_storage_id": skill_storage_id,
                "message": f"技能 {skill_name} 已添加到待优化列表"
            }
            
        except Exception as e:
            logger.error(f"Error adding skill to to_do: {str(e)}")
            return {"success": False, "message": f"添加技能到待优化列表失败: {str(e)}"}
    
    async def clear_session_skills(self, session_id: str, user_id: str) -> bool:
        """清空当前会话的所有技能"""
        try:
            if session_id in self.session_skills and user_id in self.session_skills[session_id]:
                self.session_skills[session_id][user_id]["skills"] = []
                self.session_skills[session_id][user_id]["to_do"] = []
                await self._save_session_skills()
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing session skills: {e}")
            return False
    
    # ==================== 统计和调试 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取管理器的统计信息
        
        Returns:
            dict: 包含会话数、用户会话对数、技能数等统计数据
        """
        session_count = len(self.session_skills)
        user_session_count = sum(len(users) for users in self.session_skills.values())
        
        return {
            "sessions_count": session_count,
            "user_session_pairs_count": user_session_count,
            "total_skills_in_sessions": sum(
                len(data["skills"])
                for session in self.session_skills.values()
                for data in session.values()
            ),
            "total_todos_in_sessions": sum(
                len(data.get("to_do", []))
                for session in self.session_skills.values()
                for data in session.values()
            )
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info(f"Manager Stats: {stats}")