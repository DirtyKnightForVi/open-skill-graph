# -*- coding: utf-8 -*-
"""
端点工具函数 - 通用的辅助功能
"""

import os
import zipfile
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from config.settings import Config
from logger.setup import logger


def is_safe_path(user_id: str, skill_name:str, requested_path: str) -> bool:
    """
    验证路径安全性，防止目录遍历攻击
    
    Args:
        user_id: 用户ID
        requested_path: 请求的路径
        
    Returns:
        是否安全
    """
    # 防止路径遍历攻击
    if ".." in requested_path or requested_path.startswith("/"):
        return False
    
    # 构建完整路径并检查是否在用户目录内
    if skill_name == "":
        user_dir = os.path.join(Config.UPLOAD_PATH, user_id)
    else:
        if user_id == "common":
            user_dir = os.path.join(Config.SKILLS_PATH, "common_skills", skill_name)
        else:
            user_dir = os.path.join(Config.SKILLS_PATH, "user_skills", user_id, skill_name)
    full_path = os.path.abspath(os.path.join(user_dir, requested_path))
    user_dir_abs = os.path.abspath(user_dir)
    
    return full_path.startswith(user_dir_abs)


def package_skill_to_zip(skill_dir: str, output_path: str) -> bool:
    """
    将技能目录打包成zip文件，文件直接放在zip根目录
    
    Args:
        skill_dir: 技能目录路径
        output_path: 输出的zip文件路径
        
    Returns:
        是否成功
    """
    try:
        skill_path = Path(skill_dir)
        if not skill_path.exists() or not skill_path.is_dir():
            logger.error(f"Skill directory not found or invalid: {skill_dir}")
            return False
        
        # 确保输出目录存在
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建zip文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历技能目录下的所有文件
            for file_path in skill_path.rglob('*'):
                if file_path.is_file():
                    # 计算在zip中的相对路径（相对于技能目录根）
                    arcname = file_path.relative_to(skill_path)
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added to zip: {arcname}")
        
        logger.info(f"Successfully packaged skill {skill_path.name} to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error packaging skill to zip: {str(e)}")
        return False


def get_skill_info_for_download(skill_service, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
    """
    获取技能信息用于下载（支持用户技能和公共技能）
    
    Args:
        skill_service: 技能服务实例
        user_id: 请求用户ID
        skill_name: 技能名称
        
    Returns:
        技能信息或None
    """
    try:
        # 首先检查用户的技能
        user_skills = skill_service.get_user_skills_formatted(user_id)
        for skill in user_skills:
            if skill.get("skill_name") == skill_name:
                return {
                    "skill_dir": skill.get("skill_dir", ""),
                    "skill_type": "user",
                    "source_user": user_id
                }
        
        logger.warning(f"Skill {skill_name} not found for user {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting skill info for download: {str(e)}")
        return None


def build_file_tree(dir_path: str, user_dir: str) -> list:
    """
    递归构建文件树结构
    
    Args:
        dir_path: 当前目录路径
        user_dir: 用户根目录路径
            
    Returns:
        文件树列表
    """
    file_tree = []
    
    try:
        # 获取目录下的所有条目
        entries = os.listdir(dir_path)
        
        # 过滤隐藏文件（不以.开头）
        entries = [entry for entry in entries if not entry.startswith('.')]
        
        # 分离文件和目录
        files = []
        directories = []
        
        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            if os.path.isfile(full_path):
                files.append(entry)
            elif os.path.isdir(full_path):
                directories.append(entry)
        
        # 按名称排序，目录优先于文件
        directories.sort()
        files.sort()
        sorted_entries = directories + files
        
        # 构建文件树
        for entry in sorted_entries:
            full_path = os.path.join(dir_path, entry)
            relative_path = os.path.relpath(full_path, user_dir)
            
            # 判断是否为文件
            is_file = os.path.isfile(full_path)
            
            item = {
                "name": entry,
                "type": "file" if is_file else "directory",
                "path": relative_path,
                "children": []
            }
            
            # 文件大小
            if is_file:
                try:
                    item["size"] = os.path.getsize(full_path)
                except (OSError, IOError):
                    item["size"] = 0
            else:
                item["size"] = None
            
            # 时间信息
            try:
                # 修改时间 (mtime)
                mtime = os.path.getmtime(full_path)
                item["modified_time"] = datetime.fromtimestamp(mtime).isoformat()
                
                # 创建时间 (ctime)
                ctime = os.path.getctime(full_path)
                item["created_time"] = datetime.fromtimestamp(ctime).isoformat()
            except (OSError, IOError):
                item["modified_time"] = None
                item["created_time"] = None
            
            # 递归处理子目录
            if not is_file:
                item["children"] = build_file_tree(full_path, user_dir)
            
            file_tree.append(item)
            
    except (OSError, IOError) as e:
        logger.error(f"Error building file tree for {dir_path}: {str(e)}")
        
    return file_tree
