# -*- coding: utf-8 -*-
"""
请求模型 - 为不同的endpoint定义专门的请求类
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BaseSkillRequest(BaseModel):
    """所有请求的基类，包含公共字段"""
    # model_config = ConfigDict(extra='forbid')  # 禁止额外字段，避免拼写错误
    
    session_id: str = Field(..., min_length=1, description="会话唯一标识符")
    user_id: str = Field(..., min_length=1, description="用户唯一标识符")

class GetUserSkillsRequest(BaseModel):
    """获取用户技能列表的请求"""
    # model_config = ConfigDict(extra='forbid')
    user_id: str = Field(..., min_length=1, description="用户唯一标识符")

class SkillCreateRequest(BaseSkillRequest):
    """创建技能的请求"""
    skill_name: Optional[str] = Field(None, min_length=1, description="技能名称（可选）")
    skill_name_cn: Optional[str] = Field(None, min_length=1, description="技能中文名称（可选）")
    skill_desc: Optional[str] = Field(None, description="技能描述（可选）")
    need_creat_skill_file: Optional[str] = Field(None, description="是否需要创建技能文件（可选，值为'yes'时创建新技能）")

class SkillUseRequest(BaseSkillRequest):
    """使用技能的请求"""
    # 数据示例：
    # [
    #     {
    #         "user_id":"001321877", "skill_name":"skill-A"
    #     },{
    #         "user_id":"001321878", "skill_name":"skill-B"
    #     },{
    #         "user_id":"001321879", "skill_name":"skill-C"
    #     }
    # ]
    skills_list: List[dict] = Field(..., min_length=1, description="要使用的技能列表")
    
    # target_user_id: Optional[str] = Field(None, min_length=1, description="技能归属用户ID（可选，默认使用当前用户）")

class GetSkillContentRequest(BaseSkillRequest):
    """获取技能内容的请求"""
    skill_name: str = Field(..., min_length=1, description="技能名称")

class GeneralConversationRequest(BaseSkillRequest):
    """一般对话的请求"""
    pass


class SkillUploadRequest(BaseSkillRequest):
    """技能文件上传的请求"""
    pass

# 文件操作相关请求类
class FileListRequest(BaseSkillRequest):
    """文件列表请求"""
    path: Optional[str] = Field("", description="相对路径（可选），默认为根目录")
    page: Optional[int] = Field(1, ge=-1, description="页码，从1开始，默认1")
    page_size: Optional[int] = Field(20, ge=1, le=100, description="每页大小，默认20，最大100")


class FileDownloadRequest(BaseSkillRequest):
    """文件下载请求"""
    file_path: str = Field(..., min_length=1, description="相对于用户目录的文件路径")
    skill_name: Optional[str] = Field(None, description="技能名称（可选）")
    


class SkillDownloadRequest(BaseSkillRequest):
    """技能下载请求"""
    skill_name: str = Field(..., min_length=1, description="技能名称")
    target_user_id: Optional[str] = Field(None, description="技能归属用户ID（可选，默认使用当前用户）")


class SkillListFilesRequest(BaseSkillRequest):
    """技能文件列表请求"""
    skill_name: str = Field(..., min_length=1, description="技能名称.-java后端当前传的是skill-storage-id")
    page: Optional[int] = Field(1, ge=-1, description="页码，从1开始，默认1")
    page_size: Optional[int] = Field(20, ge=-1, le=100, description="每页大小，默认20，最大100")

class EditFileContentRequest(BaseSkillRequest):
    """用户修改任意文件的内容并保存"""
    skill_name: Optional[str] = Field("", description="技能名称（空字符串表示用户文件空间）")
    file_path: str = Field(..., min_length=1, description="相对于用户目录的文件路径")
    file_content: Optional[str] = Field(None, description="全量的文件内容（None或空字符串表示清空文件）")


class SessionStartResponse(BaseModel):
    message: str
    status: str
