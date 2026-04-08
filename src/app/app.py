# -*- coding: utf-8 -*-
"""
重构后的Agent Skill应用 - 高内聚、低耦合架构（完全移除 meta_client 依赖）
"""
import traceback
import asyncio

import openai
from agentscope.message import Msg, TextBlock
# 基本依赖
from fastapi import UploadFile, Form
from typing import Annotated, List, Dict, Any, Optional, AsyncIterable
import re
import urllib
from copy import deepcopy

# agentscope runtime
import os

from starlette.responses import StreamingResponse

from config.settings import Config
from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest, RunStatus
import functools
# # 添加导入：runtime 1.1.0的新特性
from contextlib import asynccontextmanager
from agentscope.session import RedisSession
from agentscope_runtime.engine.services.sandbox import SandboxService
from fastapi import FastAPI
# # 沙箱
# from agentscope_runtime.adapters.agentscope.tool import sandbox_tool_adapter
from core.sandbox.utils import SkillFileSystemUtils

# 项目内部依赖
from logger.setup import TraceIDMiddleware, logger

# 导入统一技能服务（不依赖外部元数据服务）
from core.skill.manager import Manager
from core.skill.service import SkillService
from core.skill.toolkit import ToolkitBuilder
from core.prompt import PromptBuilder
from core.agent.builder import AgentBuilder
from core.agent.handler import QueryHandler
from app.endpoints.sandbox_handlers import SandboxEndpointHandlers
from app.process_logic import (
    get_session_state,
    setup_environment,
    build_system_prompt,
    build_toolkit,
    register_skills,
    create_agent,
    sandbox_load_local_skill
)
from core.agent.schemas import (
    SkillCreateRequest,
    GetUserSkillsRequest,
    SkillUseRequest,
    GeneralConversationRequest,
    FileListRequest,
    FileDownloadRequest,
    SkillListFilesRequest,
    EditFileContentRequest, BaseSkillRequest, SessionStartResponse
)

from core.sandbox import register_custom_sandbox
register_custom_sandbox()

# 配置日志
logger.info(f"Built LLM service using base URL: {Config.LLM_BASE_URL}")
logger.info(f"LLM Model Name: {Config.LLM_MODEL_NAME}")

# ==================== 应用初始化 ====================
import redis.asyncio as redis

# 创建Redis连接池
redis_pool = redis.ConnectionPool(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    password=Config.REDIS_PASSWORD,
    decode_responses=True,
    max_connections=10
)

core_session = RedisSession(
    connection_pool=redis_pool,
    key_ttl=Config.REDIS_KEY_TTL,
    key_prefix=Config.REDIS_KEY_PREFIX
)

# core_session.get_client().set()

skill_manager = None
skill_service = None
query_handler = QueryHandler(core_session)
endpoint_handlers = None

# ==================== 应用生命周期 ====================
# 测试连接是否正常
async def test_redis_connection(max_retries: int = 3, retry_delay: float = 1.0):
    """测试Redis连接，支持重试机制"""
    if Config.SESSION_TYPE != "redis":
        return True
    
    for attempt in range(max_retries):
        try:
            redis_client = core_session.get_client()
            await redis_client.ping()
            logger.info(f"✅ Redis connection test successful (attempt {attempt + 1}/{max_retries})")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                import asyncio
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ All Redis connection attempts failed. Last error: {e}")
                return False
    
    return False

async def init_services():
    """初始化所有服务（完全移除 meta_client 依赖）"""
    global skill_manager
    global skill_service
    global endpoint_handlers


    if not await test_redis_connection():
        raise ConnectionError("Cannot establish Redis connection after multiple attempts")
    

    # 初始化不依赖外部元数据服务的技能管理器和服务
    if skill_manager is None:
        # 使用不依赖外部元数据服务的管理器
        skill_manager = Manager(core_session)
        await skill_manager.__aenter__()  # 初始化管理器
        
        # 使用统一技能服务（不依赖外部元数据服务）
        skill_service = SkillService(skill_manager)
        logger.info("✅ Initialized Manager and SkillService (without meta_client)")
    else:
        # 如果已经初始化，确保服务正确引用
        if not isinstance(skill_service, SkillService):
            skill_service = SkillService(skill_manager)

    # 初始化端点处理器（使用统一技能服务）
    if endpoint_handlers is None:
        endpoint_handlers = SandboxEndpointHandlers(skill_service)
        logger.info("✅ Initialized EndpointHandlers with SkillService")

# 修改 lifespan 函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期钩子 — 初始化状态服务 & 沙箱"""
    # Session 管理器
    app.state.session = core_session
    # 浏览器沙箱服务
    app.state.sandbox_service = SandboxService(base_url=Config.SANDBOX_SERVICE_URL)
    await app.state.sandbox_service.start()
    # 初始化项目所需的其他服务
    await init_services()
    try:
        yield
    finally:
        await app.state.sandbox_service.stop()

class CustomAgentRequest(AgentRequest):
    query_type: Optional[str] = None

# 修改 AgentApp 初始化
app = AgentApp(
    app_name=Config.APP_NAME,
    app_description=Config.APP_DESCRIPTION,
    lifespan=lifespan,
    request_model=CustomAgentRequest,
)

app.add_middleware(TraceIDMiddleware)

# ==================== 查询接口 ====================
@app.query(framework="agentscope")
async def process_with_agent(self, msgs, request: AgentRequest, **kwargs):
    """
    处理消息的核心逻辑 - 重构版本（完全移除 meta_client 依赖）
    
    Args:
        msgs: 消息列表
        request: 代理请求
        **kwargs: 其他参数
    
    Yields:
        (消息, 是否为最后一条)
    """
    async with ProcessContext(request, msgs) as ctx:
        async for msg, last in ctx.process():
            yield msg, last
        logger.info(f'Process 流程结束: user_id={ctx.user_id}, session_id={ctx.session_id}')


class ProcessContext:
    def __init__(self, request: AgentRequest, msgs):
        self.request = request
        self.msgs = msgs
        self.user_id = request.user_id
        self.session_id = request.session_id
        self.sandbox_utils = SkillFileSystemUtils()
        self.sandbox_instance = None
        self.is_skill_creator_mode = False
        self.skill_to_upload_storage_list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 技能创建模式结束时保存沙箱技能到本地存储
        if self.is_skill_creator_mode and len(self.skill_to_upload_storage_list) > 0:
            self.sync_sandbox_skill_file_to_storage(self.skill_to_upload_storage_list)

        self.sandbox_utils.sync_workspace_to_remote(self.user_id, self.sandbox_instance, session_id=self.session_id)

    @property
    def sandbox_id(self):
        if self.sandbox_instance is not None:
            return self.sandbox_instance.sandbox_id
        return None

    def sync_sandbox_skill_file_to_storage(self, skill_info_list: List[Dict[str, Any]]):
        """ 上传沙箱内技能到本地技能仓库 """
        sandbox_skill_list = self.sandbox_instance.manager_api.fs_list(self.sandbox_id, 'skill', depth=2)
        sandbox_skill_info = {
            os.path.basename(item['path']): item
            for item in sandbox_skill_list
            if item['type'] == 'dir'
        }

        logger.info(f"Sandbox Skill Info: {sandbox_skill_info}")
        for skill_info in skill_info_list:
            owner_id = skill_info['owner_id']
            if owner_id != self.user_id:
                continue
            skill_name = skill_info['skill_name']
            storage_key = skill_info.get('skill_storage_id', f'SKILL_{self.user_id}_{skill_name}')
            if skill_name not in sandbox_skill_info:
                raise NotADirectoryError(f'技能[{skill_name}]目录不存在')

            logger.info(f'开始打包技能文件: {skill_name}')
            skill_dir = f'/workspace/skill/{storage_key}/{skill_name}'
            self.sandbox_utils.sandbox_make_archive(
                self.sandbox_instance,
                save_name=skill_name,
                archive_dir=skill_dir,
            )

            archive_name = f'{skill_name}.zip'
            sandbox_file_path = f'/workspace/{archive_name}'
            local_archive_path = self.sandbox_utils.get_storage_root() / f"{storage_key}.zip"
            archive_bytes = self.sandbox_instance.manager_api.fs_read(self.sandbox_id, sandbox_file_path, fmt='bytes')
            with open(local_archive_path, 'wb') as fp:
                fp.write(archive_bytes)

            logger.info(f'保存技能[{skill_name}]到本地仓库: {local_archive_path}')
            self.sandbox_utils.sandbox_delete_file(self.sandbox_instance, sandbox_file_path)

    async def process(self):
        try:
            user_id = self.user_id
            session_id = self.session_id
            # 步骤1: 获取当前会话的状态
            skills, is_skill_creator_mode, upload_dir = get_session_state(
                session_id, user_id, skill_manager
            )
            self.is_skill_creator_mode = True if getattr(self.request, 'query_type', None) == 'create' else False
            
            # 步骤2: 创建沙箱或本地环境
            sandbox_instance, env_info = setup_environment(
                session_id, user_id, app.state
            )
            self.sandbox_instance = sandbox_instance

            # 步骤3: 初始化提示词
            # 如果是"技能创建"模式，提示词是不一样的。
            to_do_list = skill_manager.get_session_to_do(session_id, user_id)
            system_prompt = build_system_prompt(
                skills, self.is_skill_creator_mode, upload_dir, to_do_list
            )
            self.skill_to_upload_storage_list = to_do_list if self.is_skill_creator_mode else skills
            

            # 步骤4: 构建工具箱
            toolkit = build_toolkit(
                skills, self.is_skill_creator_mode, sandbox_instance
            )

            # 步骤5: 加载技能
            await register_skills(
                toolkit, skills, core_session.get_client(), self.is_skill_creator_mode, sandbox_instance, to_do_list
            )

            # 步骤6: 创建智能体（异步调用）
            agent = await create_agent(system_prompt, toolkit, self.is_skill_creator_mode)

            # 添加调试钩子（保持原有功能）
            from app.process_logic import add_debug_hooks
            agent = add_debug_hooks(agent)

            # 处理查询，传递请求ID
            async for msg, last in query_handler.process_query(
                    agent, self.msgs, session_id, user_id
            ):
                yield msg, last

        except openai.APIError as e:
            logger.error(f'大模型接口异常: {e}')
            yield Msg('system', [TextBlock(type='text', text=f'{e}')], role='system'), True
        except Exception:
            logger.error(f"Error in process_with_agent: {traceback.format_exc()}")
            raise
        finally:
            pass


# ==================== API端点 ====================
def covert_to_sse_response(message, status: str):
    event = SessionStartResponse(message=message, status=status)
    return f"data: {event.model_dump_json()}\n\n"


@app.post('/session/start')
async def start_session(request: BaseSkillRequest):
    """
    启动session, 沙箱
    """

    async def start_session_method() -> AsyncIterable[str]:
        # 返回提示信息和状态, 状态在最后完成后返回completed
        user_id = request.user_id
        session_id = request.session_id
        try:
            # 步骤1: 获取当前会话的状态
            skills, is_skill_creator_mode, _ = get_session_state(
                session_id, user_id, skill_manager
            )
            to_do_list = skill_manager.get_session_to_do(session_id, user_id)
            sandbox_instance, _ = setup_environment(
                session_id, user_id, app.state
            )
            yield covert_to_sse_response(message='初始化沙箱环境成功', status=RunStatus.InProgress)

            logger.info(f"[SANDBOX START] - got sandbox id is {sandbox_instance.sandbox_id}")
            logger.info(f"[SANDBOX START] - start loading user({user_id})'s skills for {session_id}")
            yield covert_to_sse_response(message='初始化技能信息', status=RunStatus.InProgress)
            task = sandbox_load_local_skill(
                sandbox_instance, skills, is_skill_creator_mode, to_do_list, core_session.get_client())

            logger.info(f"[SANDBOX START] - start loadding user({user_id})'s files for {session_id}")
            yield covert_to_sse_response(message='初始化工作空间', status=RunStatus.InProgress)
            SkillFileSystemUtils().sync_workspace_from_remote(user_id, sandbox_instance, session_id=session_id)
            yield covert_to_sse_response(message='初始化工作空间成功', status=RunStatus.InProgress)
            await task
            yield covert_to_sse_response(message='初始化技能信息成功', status=RunStatus.InProgress)
            yield covert_to_sse_response(message='沙箱创建成功', status=RunStatus.Completed)
            logger.info("[SANDBOX START COMPLETE] - ALL CLEAR")
        except Exception as e:
            logger.error(f"Error in start_session: {traceback.format_exc()}")
            yield covert_to_sse_response(message=f'沙箱创建失败: {e}', status=RunStatus.Failed)

    return StreamingResponse(
        start_session_method(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )



@app.post('/session/heartbeat')
def heartbeat(request: BaseSkillRequest):
    """心跳检测沙箱容器是否存活"""
    user_id = request.user_id
    session_id = request.session_id
    sandbox_service: SandboxService = app.state.sandbox_service
    session_ctx_id = sandbox_service._create_session_ctx_id(session_id, user_id)
    env_ids = sandbox_service.manager_api.get_session_mapping(session_ctx_id)
    logger.info(f'获取用户沙箱列表: user_id={user_id}, session_id={session_id}, env_ids={env_ids}')
    container_name_list = list(env_ids)
    sandbox_alive = False
    if not container_name_list:
        message = f'Sandbox not started'
    else:
        container_name = container_name_list[0]
        # info = ContainerModel(**sandbox_service.manager_api.get_info(container_name))
        if sandbox_service.manager_api.check_health(container_name):
            sandbox_alive = True
            message = f'Sandbox alive'
        else:
            message = f"Sandbox deactivated"

    return {
        'isAlive': sandbox_alive,
        'message': message
    }




@app.post("/stop")
async def stop_task(request: AgentRequest):
    """
    向正在运行的会话发送中断信号
    """
    # 检查 AgentApp 是否有 stop_chat 方法
    if hasattr(app, 'stop_chat'):
        await app.stop_chat(
            user_id=request.user_id,
            session_id=request.session_id,
        )
    else:
        logger.warning("AgentApp does not have stop_chat method, skipping interrupt")
    
    return {
        "status": "success",
        "message": "Interrupt signal broadcasted.",
    }


@app.endpoint("/skill_use")
async def skill_use(request: SkillUseRequest):
    """使用用户已注册的技能"""
    return await endpoint_handlers.skill_use(request)

@app.endpoint("/skill_create")
async def skill_create(request: SkillCreateRequest):
    """创建并注册用户自定义技能"""
    return await endpoint_handlers.skill_create(request)


@app.endpoint("/general_conversation")
async def general_conversation(request: GeneralConversationRequest):
    """一般对话接口"""
    return await endpoint_handlers.general_conversation(request)

@app.endpoint('/upload', methods=['POST'])
async def upload_to_sandbox(
        file: UploadFile,
        user_id: Annotated[str, Form()],
        session_id: Annotated[str, Form()]
):
    """
    上传用户文件到沙箱空间
    
    请求参数:
        - file: 要上传的文件
        - user_id: 用户唯一标识符
        - session_id: 会话唯一标识符
    
    响应参数:
        - status: 请求状态（success 或 error）
        - filename: 上传的文件名
        - file_path: 文件在沙箱中的存储路径
        - size: 文件大小（字节）
        - message: 操作结果消息
        - error: 错误信息（仅当 status=error 时存在）
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 调用端点处理器处理文件上传到沙箱
        result = await endpoint_handlers.upload_file_to_sandbox(user_id, session_id, file.filename, file_content, app.state.sandbox_service)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in upload_to_sandbox endpoint: {str(e)}")
        return {
            "status": "error",
            "error": f"文件上传到沙箱失败: {str(e)}"
        }

@app.endpoint("/list_files")
async def list_files(request: FileListRequest):
    """获取沙箱工作空间文件列表（树形结构）"""
    return await endpoint_handlers.list_user_files(request, app.state.sandbox_service)

# 让java后端传对应SKILL_{user_id}_{skill_name}的路径,复用接口返回
@app.endpoint("/list_skill_skeleton")
async def list_skill_skeleton(request: SkillListFilesRequest):
    """获取技能目录的文件列表（树形结构）"""
    return await endpoint_handlers.list_skill_files(request, app.state.sandbox_service)


@app.endpoint("/download_file")
async def download_file(request: FileDownloadRequest):
    """从沙箱下载用户文件或技能内容"""
    try:
        sandbox, env_ids = setup_environment(request.session_id, request.user_id, app.state)
        file_content = sandbox.manager_api.fs_read(sandbox.sandbox_id, request.file_path, fmt='bytes')
        filename = os.path.basename(request.file_path)
        import tempfile
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        try:
            # 使用FastAPI的FileResponse返回文件
            from fastapi.responses import FileResponse

            # 设置适当的Content-Disposition头
            encoded_filename = urllib.parse.quote(filename)
            headers = {
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
            }

            return FileResponse(
                tmp_file_path,
                filename=filename,
                headers=headers
            )
        except Exception as e:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
            logger.error(f"Error creating file response: {str(e)}")
            return {
                "status": "error",
                "error": f"创建文件响应失败: {str(e)}"
            }
    except Exception as e:
        logger.error(f"Error in download_file endpoint: {str(e)}")
        return {
            "status": "error",
            "error": f"下载文件失败: {str(e)}"
        }

@app.endpoint('/edit_file')
async def edit_file(request: EditFileContentRequest):
    """在沙箱中编辑用户文件或技能文件内容"""
    return await endpoint_handlers.edit_file_in_sandbox(request, app.state.sandbox_service)




if __name__ == "__main__":
    logger.info("✅ Agent Skill Application configured successfully (without meta_client dependency)")