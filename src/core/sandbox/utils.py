import json
import os
import shutil
import tempfile
import traceback

from agentscope_runtime.sandbox import FilesystemSandbox
from mcp.types import CallToolResult, TextContent
from pathlib import Path

from config import Config
from errors.errors import SandBoxRunCommendError
from logger import logger

WORKDIR_DIR = '/workspace'

class RunShellCommandResponse(CallToolResult):
    """ 沙箱执行shell命令返回数据 """
    @property
    def stdout(self):
        return self.get_content_by_type('stdout')

    @property
    def stderr(self):
        return self.get_content_by_type('stderr')

    @property
    def return_code(self):
        return self.get_content_by_type('returncode')

    def get_content_by_type(self, content_type):
        for item in self.content:
            if not isinstance(item, TextContent):
                continue

            description = item.model_extra.get('description')
            if description == content_type:
                return item.text
        return ''


class FileSystemUtils:
    def __init__(self):
        self.sandbox_script_dir = '/scripts'

    def sync_workspace_from_remote(self, user_id, sandbox: FilesystemSandbox = None, *args, **kwargs):
        """从远端同步工作空间"""
        raise NotImplementedError()

    def sync_workspace_to_remote(self, user_id, sandbox: FilesystemSandbox = None, *args, **kwargs):
        """同步工作空间到远端"""
        raise NotImplementedError()

    @staticmethod
    def sandbox_file_exists(sandbox: FilesystemSandbox, sandbox_file_path):
        """判断沙箱中文件是否存在
            Args:
                sandbox (FilesystemSandbox): 沙箱对象
                sandbox_file_path (str): 沙箱内文件路径
        """
        resp = sandbox.run_ipython_cell(f'import os\nprint(os.path.exists("{sandbox_file_path}"))')
        if resp.get('isError'):
            raise Exception(f"判断沙箱文件是否存在异常: {resp}")
        if resp.get('content', [])[0].get("text").strip('\n') == 'True':
            return True
        else:
            return False

    @staticmethod
    def sandbox_delete_file(sandbox: FilesystemSandbox, file_path: str):
        sandbox.manager_api.fs_remove(sandbox.sandbox_id, file_path)

    def sandbox_make_archive(
            self, sandbox: FilesystemSandbox, save_name, archive_dir, exclude_dirs=None, save_dir=None):
        """沙箱内打包

            Args:
                sandbox (FilesystemSandbox): 沙箱对象
                save_name (str): 保存文件名称
                archive_dir (str): 打包目录
                exclude_dirs (List[str]): 需要忽略的目录列表
                save_dir str: 压缩文件保存目录, 不传默认在/workspace
        """
        save_dir = save_dir or WORKDIR_DIR
        exclude_dirs = exclude_dirs or []
        cmd = (f'python {self.sandbox_script_dir}/file.py make_archive --archive_name {save_name} '
               f'--archive_dir {archive_dir} --save_dir {save_dir}')
        if exclude_dirs:
            exclude_dirs_str = ','.join(exclude_dirs)
            cmd += f' --exclude="{exclude_dirs_str}"'

        self.run_shell_command_in_sandbox(sandbox, cmd)

    def sandbox_unpack_archive(self, sandbox: FilesystemSandbox, archive_path, save_dir):
        cmd = f'python {self.sandbox_script_dir}/file.py unpack_archive --archive_path {archive_path} --save_dir {save_dir}'
        return self.run_shell_command_in_sandbox(sandbox, cmd)

    @staticmethod
    def _run_shell_command_in_sandbox(sandbox_instance, cmd, resp_parse_func=None):
        """在沙箱内执行脚本

            Args:
                sandbox_instance (FilesystemSandbox): 沙箱实例
                cmd (str): 需要执行的脚本
                resp_parse_func (callable): 自定义结果解析函数 def resp_parse_func(cmd_output)
        """
        raw_resp = sandbox_instance.run_shell_command(cmd)

        # 自定义返回解析
        if callable(resp_parse_func):
            return resp_parse_func(raw_resp)
        resp = RunShellCommandResponse(**raw_resp)
        if resp.isError:
            raise SandBoxRunCommendError(f'沙箱执行命令失败: {resp.stderr}')
        return resp

    @classmethod
    def run_shell_command_in_sandbox(cls, sandbox_instance, cmd, resp_parse_func=None):
        """在沙箱内执行脚本

            Args:
                sandbox_instance (FilesystemSandbox): 沙箱实例
                cmd (str): 需要执行的脚本
                resp_parse_func (callable): 自定义结果解析函数 def resp_parse_func(cmd_output)
        """
        resp = cls._run_shell_command_in_sandbox(sandbox_instance, cmd, resp_parse_func)
        output = json.loads(resp.stdout)
        if output['status'] != 'success':
            raise SandBoxRunCommendError(f'沙箱执行脚本异常: cmd={cmd}, output={resp.stdout}')
        return output.get('data', {})


class SkillFileSystemUtils(FileSystemUtils):
    @staticmethod
    def get_storage_root() -> Path:
        root = Path(Config.SKILL_STORAGE_PATH)
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def get_workspace_storage_root() -> Path:
        root = Path(Config.WORKSPACE_STORAGE_PATH)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def get_skill_archive_path(self, storage_key: str) -> Path:
        return self.get_storage_root() / f"{storage_key}.zip"

    def sandbox_download_skill_packages(self, sandbox_instance, storage_key_list):
        """从本地技能仓库向沙箱复制技能包并解压"""
        for storage_key in storage_key_list:
            archive_path = self.get_skill_archive_path(storage_key)
            if not archive_path.exists():
                raise FileNotFoundError(f"Skill archive not found: {archive_path}")

            sandbox_path = f"/workspace/skill/{storage_key}.zip"
            sandbox_instance.manager_api.fs_write_from_path(
                sandbox_instance.sandbox_id,
                sandbox_path,
                str(archive_path)
            )
            self.run_shell_command_in_sandbox(
                sandbox_instance,
                f"mkdir -p /workspace/skill/{storage_key} && unzip -o {sandbox_path} -d /workspace/skill/{storage_key} && rm -rf {sandbox_path}"
            )

    def sandbox_upload_skill_package(self, sandbox_instance, storage_key: str, sandbox_file_path: str):
        """将沙箱内技能包保存到本地技能仓库"""
        archive_bytes = sandbox_instance.manager_api.fs_read(sandbox_instance.sandbox_id, sandbox_file_path, fmt='bytes')
        archive_path = self.get_storage_root() / f"{storage_key}.zip"
        with open(archive_path, 'wb') as fp:
            fp.write(archive_bytes)
        return str(archive_path)

    def sync_workspace_from_remote(self, user_id, sandbox: FilesystemSandbox = None, *args, **kwargs):
        """从本地工作空间备份恢复到沙箱"""
        if sandbox is None:
            return

        session_id = kwargs.get('session_id')
        workspace_archive = 'workspace.zip'
        local_workspace_path = self.get_workspace_storage_root() / f"{user_id}_{session_id}_{workspace_archive}"

        if not local_workspace_path.exists():
            logger.info(f"No local workspace backup found: {local_workspace_path}")
            return

        sandbox_save_path = os.path.join(WORKDIR_DIR, workspace_archive)
        sandbox_instance.manager_api.fs_write_from_path(
            sandbox_instance.sandbox_id,
            sandbox_save_path,
            str(local_workspace_path)
        )
        self.sandbox_unpack_archive(sandbox, sandbox_save_path, save_dir=WORKDIR_DIR)
        sandbox_instance.manager_api.fs_remove(sandbox_instance.sandbox_id, sandbox_save_path)

    def sync_workspace_to_remote(self, user_id, sandbox: FilesystemSandbox = None, *args, **kwargs):
        """将沙箱工作空间备份到本地存储"""
        if sandbox is None:
            return

        session_id = kwargs.get('session_id')
        workspace_archive_name = 'workspace'
        workspace_archive_file_name = f'{workspace_archive_name}.zip'
        exclude_dirs = ['skill', 'workspace.zip']
        logger.info(f'Packaging workspace for local backup: user={user_id}, session={session_id}')
        self.sandbox_make_archive(sandbox, workspace_archive_name, WORKDIR_DIR, exclude_dirs=exclude_dirs)
        sandbox_file_path = os.path.join(WORKDIR_DIR, workspace_archive_file_name)

        try:
            archive_bytes = sandbox.manager_api.fs_read(sandbox.sandbox_id, sandbox_file_path, fmt='bytes')
            local_workspace_path = self.get_workspace_storage_root() / f"{user_id}_{session_id}_{workspace_archive_file_name}"
            with open(local_workspace_path, 'wb') as fp:
                fp.write(archive_bytes)
            logger.info(f"Saved sandbox workspace backup to local storage: {local_workspace_path}")
        finally:
            sandbox.manager_api.fs_remove(sandbox.sandbox_id, sandbox_file_path)
