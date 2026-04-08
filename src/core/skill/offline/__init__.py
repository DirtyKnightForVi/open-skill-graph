# -*- coding: utf-8 -*-
"""
技能管理模块 - 基于本地存储与元信息接口的轻量级实现
文件已移动到上层目录，此文件保留用于向后兼容
"""
# 从上层目录导入
from ..manager import Manager
from ..meta_client import SkillMetaClient
from ..storage_ops import StorageOperations

__all__ = [
    'Manager',
    'SkillMetaClient',
    'StorageOperations'
]