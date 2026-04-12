# -*- coding: utf-8 -*-
"""
配置模块 - 集中管理所有配置参数
"""

import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any
import datetime

load_dotenv()


class Config:
    """应用配置类"""

    # 工作空间路径设置
    WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", '/workspace')

    # Session配置
    # session类型
    SESSION_TYPE = os.environ.get("SESSION_TYPE", 'json')
    if SESSION_TYPE == 'json':
        SESSION_CONNNECT_INFO = "./session_cache"
    # # else:
    # #     # 为redis做的占位符
    # #     SESSION_CONNNECT_INFO = "./session_cache"
    # Redis配置
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
    REDIS_KEY_TTL = int(os.environ.get("REDIS_KEY_TTL", "86400"))  # 默认24小时过期
    REDIS_KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "")
    
    # 应用基础配置
    APP_NAME = "SKILL_AGENT_APP"
    APP_DESCRIPTION = "创建智能体技能、使用智能体技能的示例应用。"
    
    # 日志配置
    now = datetime.datetime.now()
    log_file_name = f"Agent_Service_{now.strftime('%Y%m%d_%H%M%S')}.log"
    LOG_PATH = os.environ.get("LOG_PATH", "logs")
    os.makedirs(LOG_PATH, exist_ok=True)
    LOG_FILE = os.path.join(LOG_PATH, log_file_name)
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(trace_id)s - %(message)s'
    
    # 根据配置设置LLM服务地址和凭证
    LLM_BASE_URL = os.environ.get("ONLINE_BASE_URL")
    LLM_API_KEY = os.environ.get("ONLINE_API_KEY")
    LLM_MODEL_NAME = os.environ.get("ONLINE_MODEL_NAME")
    LLM_MODEL_NAME_FOR_COMPRESS = os.environ.get("LLM_MODEL_NAME_FOR_COMPRESS", None)
    LLM_TOKEN_FOR_COMPRESS = os.environ.get("LLM_TOKEN_FOR_COMPRESS", None)
    
    # 技能路径配置
    SKILLS_PATH = os.environ.get("SKILLS_PATH", "Agent_Work_Dir/Skills")
    SKILLS_CREATE_TEMPLATE = os.environ.get("SKILLS_CREATE_TEMPLATE", "Agent_Work_Dir/Skills/SkillTemplete")

    # 技能缓存配置
    SKILLS_CACHE_PATH = os.environ.get("SKILLS_CACHE_PATH", "Agent_Work_Dir/cache")

    UPLOAD_PATH = os.environ.get("UPLOAD_PATH", "Agent_Work_Dir/Files/User_Files")

    # 技能上传配置
    UPLOADED_SKILL_PATH = os.environ.get("UPLOADED_SKILL_PATH", "Agent_Work_Dir/Uploaded_Skills")

    # 本地技能仓库路径（替代 STORAGE 存储）
    SKILL_STORAGE_PATH = os.environ.get("SKILL_STORAGE_PATH", "Agent_Work_Dir/Files/Download_Skills")
    WORKSPACE_STORAGE_PATH = os.environ.get("WORKSPACE_STORAGE_PATH", "Agent_Work_Dir/Files/Workspace_Backup")

    # 技能生成配置
    SKILL_CREATOR_NAME = os.environ.get("SKILL_CREATOR_NAME", "skill-creator")
    
    # 模型生成配置
    MODEL_CONTEXT_LIMIT = int(os.environ.get("MODEL_CONTEXT_LIMIT", 64*1024))
    MODEL_MAX_TOKENS = int(os.environ.get("MODEL_MAX_TOKENS", 4096))
    STREAM_CHUNK_SIZE = int(os.environ.get("STREAM_CHUNK_SIZE", 5))
    REACT_MAX_ITERS = int(os.environ.get("REACT_MAX_ITERS", 31))
    
    # 系统提示词
    prompt_file = "System_Prompt.md"
    if prompt_file and os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            SYSTEM_PROMPT_BASE = f.read()
    else:
        SYSTEM_PROMPT_BASE = "你是工银智涌。\nIf writing fails, wait for 5 seconds before retrying.\n"

    # 请求超时配置
    REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "300.0"))

    # 上下文压缩阈值
    COMPRESS_LIMIT = int(os.environ.get("COMPRESS_LIMIT", 45))

    # 是否启用沙箱服务
    IF_SANDBOX = int(os.environ.get("IF_SANDBOX", 0))
    # 沙箱类型
    SANDBOX_TYPE = os.getenv("SANDBOX_TYPE", "base")

    # 沙箱环境只读目录挂载: localPath1:sandboxPath1,localPath2:sandboxPath2
    SANDBOX_READONLY_MOUNTS = os.getenv("SANDBOX_READONLY_MOUNTS", "")
    # 沙箱服务url
    SANDBOX_SERVICE_URL = os.getenv("SANDBOX_SERVICE_URL", "")

    # 技能下载配置
    DOWNLOAD_SKILL_PATH = os.environ.get("DOWNLOAD_SKILL_PATH", "downloads/skills")

    # 技能元数据接口配置
    SKILL_METADATA_SOURCE = os.environ.get("SKILL_METADATA_SOURCE", "meta")
    REGISTRY_BASE_URL = os.environ.get("REGISTRY_BASE_URL", "")
    REGISTRY_TIMEOUT = int(os.environ.get("REGISTRY_TIMEOUT", "10"))
    REGISTRY_TOKEN = os.environ.get("REGISTRY_TOKEN", "")

    # 旧元数据接口配置（兼容保留）
    SKILL_META_API_URL = os.environ.get("SKILL_META_API_URL", "")
    SKILL_META_API_TIMEOUT = int(os.environ.get("SKILL_META_API_TIMEOUT", "10"))
    SKILL_META_API_MAX_RETRIES = int(os.environ.get("SKILL_META_API_MAX_RETRIES", "2"))

    # 内部请求代理接口url
    INNER_PROXY_URL = os.environ.get("INNER_PROXY_URL", "")

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置字典"""
        return {
            "model_name": cls.LLM_MODEL_NAME,
            "api_key": cls.LLM_API_KEY,
            "base_url": cls.LLM_BASE_URL,
            "stream": True,
            "client_kwargs": {
                "base_url": cls.LLM_BASE_URL,
                "timeout": 100.0,
            },
            "generate_kwargs": {
                "max_tokens": cls.MODEL_MAX_TOKENS,
            }
        }