# -*- coding: utf-8 -*-
"""
技能元数据客户端 - 通过接口访问技能元数据
"""
import logging
import traceback

import aiohttp
import asyncio
from typing import Dict, Optional, Any, List
from config.settings import Config
from utils.mock import mock_get_skill_meta, mock_common_skills

from logger.setup import logger

# logger = logging.getLogger(__name__)


class SkillMetaClient:
    """技能元数据客户端 - 通过 REST API 获取技能信息"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        初始化技能元数据客户端
        
        Args:
            base_url: 接口基础URL，如 http://ip:port
            timeout: 接口超时时间（秒）
        """
        self.base_url = base_url or Config.SKILL_META_API_URL
        self.timeout = timeout
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    @mock_get_skill_meta
    async def get_skill_meta(self, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能元数据
        
        Args:
            user_id: 用户ID，支持 \"common\" 表示公共技能
            skill_name: 技能名称（英文）
            
        Returns:
            dict: 标准化后的技能信息，None 表示技能不存在或接口错误
        """
        if not self.base_url:
            logger.warning("Skill meta API URL not configured")
            return None
            
        url = f"{self.base_url}/skill/getSkillMetaData.htm"
        params = {
            "userId": user_id,
            "skillName": skill_name
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 404:
                    logger.info(f"Skill not found: {user_id}/{skill_name}")
                    return None
                elif response.status != 200:
                    logger.warning(f"API error: {response.status} for {user_id}/{skill_name}")
                    return None
                
                data = await response.json()
                if not data:
                    logger.info(f"Empty response for {user_id}/{skill_name}")
                    return None
                
                # 标准化响应格式
                return self._normalize_skill_info(data, user_id, skill_name)
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting skill meta for {user_id}/{skill_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting skill meta for {user_id}/{skill_name}: {traceback.format_exc()}")
            return None
    
    def _normalize_skill_info(self, data: Dict[str, Any], user_id: str, skill_name: str) -> Dict[str, Any]:
        """
        标准化技能信息格式
        
        Args:
            data: 原始接口响应数据
            user_id: 用户ID
            skill_name: 技能名称
            
        Returns:
            dict: 标准化后的技能信息
        """
        # 确定技能类型
        skill_type = "common" if user_id == "common" else "user"
        
        # 生成本地技能存储 key
        storage_key = self._generate_storage_key(user_id, skill_name, skill_type)
        
        return {
            "skill_name": skill_name,
            "skill_storage_id": storage_key,
            "skill_description": data.get("skill_desc", ""),
            "owner_id": user_id
        }
    
    def _generate_storage_key(self, user_id: str, skill_name: str, skill_type: str) -> str:
        """
        生成本地技能存储 key
        
        Args:
            user_id: 用户ID
            skill_name: 技能名称
            skill_type: 技能类型
            
        Returns:
            str: 技能存储 key
        """
        if user_id == "common":
            return f"SKILL_common_{skill_name}"
        else:
            return f"SKILL_{user_id}_{skill_name}"
    
    @mock_common_skills
    async def get_common_skills(self) -> List[Dict[str, Any]]:
        """
        获取所有公共技能（通过接口）
        
        注意：由于接口不支持批量查询，这里返回预设的公共技能列表
        后续可以优化为调用专门的公共技能接口
        
        Returns:
            list: 公共技能列表
        """
        # 预设的公共技能列表
        common_skill_names = [
            "File-Read-Skill",
            "File-Write-Skill", 
            "Text-Processing-Skill",
            "HTTP-Request-Skill",
            "Data-Format-Convert-Skill",
            "skill-creator"
        ]
        
        common_skills = []
        for skill_name in common_skill_names:
            skill_info = await self.get_skill_meta("common", skill_name)
            if skill_info:
                common_skills.append(skill_info)
                
        logger.info(f"Retrieved {len(common_skills)} common skills via API")
        return common_skills