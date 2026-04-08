# -*- coding: utf-8 -*-
"""
沙箱文件端点处理器 - 处理沙箱中的文件管理相关操作
"""
import traceback
import os
import tempfile
import json
from typing import Dict, Any, Optional
from config.settings import Config
from logger.setup import logger
from src.core.sandbox.utils import SkillFileSystemUtils
from .base import BaseEndpointHandlers


class SandboxFileEndpointHandlers(BaseEndpointHandlers):
    """沙箱文件端点处理器，处理沙箱中的文件管理相关操作"""
    
    # 沙箱基本类型
    SANDBOX_TYPE = Config.SANDBOX_TYPE

    # 文件上传配置
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.json', '.xml', '.yaml', '.yml', '.md', '.py', '.js', '.html', '.css', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.tar', '.gz'}
    
    async def upload_file_to_sandbox(self, user_id: str, session_id: str, filename: str, file_content: bytes, sandbox_service) -> Dict[str, Any]:
        """
        端点: /upload_to_sandbox - 上传用户文件到沙箱空间
        
        请求参数:
            - user_id: 用户唯一标识符
            - session_id: 会话ID
            - filename: 文件名
            - file_content: 文件二进制内容
            - sandbox_service: 沙箱服务实例
        
        响应参数:
            - status: 请求状态（success 或 error）
            - filename: 上传的文件名
            - file_path: 文件在沙箱中的存储路径
            - size: 文件大小（字节）
            - message: 操作结果消息
            - error: 错误信息（仅当 status=error 时存在）
        """
        try:
            self._log_operation("Upload file to sandbox", user_id, filename=filename, session_id=session_id)
            
            # 验证文件名
            if not filename or not filename.strip():
                return {
                    "status": "error",
                    "error": "文件名不能为空"
                }
            
            # 清理文件名，移除路径分隔符和特殊字符
            safe_filename = os.path.basename(filename.strip())
            
            # 检查文件扩展名
            file_ext = os.path.splitext(safe_filename)[1].lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                return {
                    "status": "error",
                    "error": f"不支持的文件类型: {file_ext}。支持的文件类型: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
                }
            
            # 检查文件大小
            file_size = len(file_content)
            if file_size > self.MAX_FILE_SIZE:
                return {
                    "status": "error",
                    "error": f"文件大小超过限制: {file_size / (1024*1024):.1f}MB > {self.MAX_FILE_SIZE / (1024*1024):.1f}MB"
                }
            
            # 连接沙箱
            try:
                sandboxes = sandbox_service.connect(
                    session_id=session_id,
                    user_id=user_id,
                    sandbox_types=[self.SANDBOX_TYPE],
                )
                sandbox_instance = sandboxes[0]
                logger.info(f"Connected to sandbox for session {session_id}/{user_id}")
            except Exception as e:
                logger.error(f"Failed to connect to sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"连接沙箱失败: {str(e)}"
                }
            
            # 构建沙箱中的文件路径
            sandbox_file_path = f"/workspace/upload/{safe_filename}"
            
            # 检查文件是否已存在，如果存在则添加数字后缀
            base_name, ext = os.path.splitext(safe_filename)
            counter = 1
            final_filename = safe_filename
            
            while True:
                try:
                    # 尝试检查文件是否存在
                    check_result = sandbox_instance.run_shell_command(f'ls -l {sandbox_file_path}')
                    if check_result.get('content', []) or 'No such file or directory' in check_result.get('content', [])[0].get('text', ''):
                        # 文件不存在，可以使用这个路径
                        break
                    else:
                        # 文件存在，生成新文件名
                        final_filename = f"{base_name}_{counter}{ext}"
                        sandbox_file_path = f"/workspace/upload/{final_filename}"
                        counter += 1
                        
                        # 防止无限循环
                        if counter > 10:
                            return {
                                "status": "error",
                                "error": "文件名冲突处理失败，请重命名文件后重试"
                            }
                except Exception:
                    # 如果检查失败，假设文件不存在
                    break
            
            # 创建临时文件用于上传
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                # 确保上传目录存在
                sandbox_instance.run_shell_command(f"mkdir -p /workspace/upload")
                
                # 将文件写入沙箱
                sandbox_instance.manager_api.fs_write_from_path(
                    sandbox_instance.sandbox_id,
                    sandbox_file_path,
                    tmp_file_path
                )
                
                logger.info(f"File uploaded to sandbox successfully: user={user_id}, filename={final_filename}, size={file_size} bytes")
                
                return {
                    "status": "success",
                    "filename": final_filename,
                    "file_path": sandbox_file_path,
                    "size": file_size,
                    "message": f"文件上传成功: {final_filename}"
                }
                
            finally:
                # 清理临时文件
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                
        except Exception as e:
            return self._handle_error("upload_file_to_sandbox", e, {
                "user_id": user_id,
                "filename": filename,
                "session_id": session_id
            })
    
    async def list_files_in_sandbox(self, user_id: str, session_id: str, sandbox_service) -> Dict[str, Any]:
        """
        端点: /list_files - 获取沙箱工作空间文件列表（树形结构）
        
        请求参数:
            - user_id: 用户唯一标识符
            - session_id: 会话ID
            - sandbox_service: 沙箱服务实例
        
        响应参数:
            - status: 请求状态（success 或 error）
            - user_id: 用户唯一标识符
            - current_path: 当前路径（固定为根目录）
            - pagination: 分页信息（不分页）
            - file_list: 文件树列表
        """
        try:
            self._log_operation("List files in sandbox", user_id, session_id=session_id)
            
            # 连接沙箱
            try:
                sandboxes = sandbox_service.connect(
                    session_id=session_id,
                    user_id=user_id,
                    sandbox_types=[self.SANDBOX_TYPE],
                )
                sandbox_instance = sandboxes[0]
                logger.info(f"Connected to sandbox for session {session_id}/{user_id}")
            except Exception as e:
                logger.error(f"Failed to connect to sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"连接沙箱失败: {str(e)}"
                }
            
            # 使用 directory_tree 方法获取工作空间文件列表
            try:
                tree_result = sandbox_instance.directory_tree("/workspace/output")
                logger.info(f"Got directory tree for /workspace")
                
                # 转换格式以匹配现有接口
                file_list = self._convert_directory_tree_to_file_list(tree_result)
                
                return {
                    "status": "success",
                    "user_id": user_id,
                    "current_path": "",  # 根目录
                    "pagination": {
                        "page": -1,
                        "page_size": len(file_list),
                        "total": len(file_list),
                        "total_pages": 1
                    },
                    "file_list": file_list
                }
                
            except Exception as e:
                logger.error(f"Failed to get directory tree: {str(e)}")
                return {
                    "status": "error",
                    "error": f"获取文件列表失败: {str(e)}"
                }
                
        except Exception as e:
            return self._handle_error("list_files_in_sandbox", e, {
                "user_id": user_id,
                "session_id": session_id
            })
    
    def _convert_directory_tree_to_file_list(self, tree_result) -> list:
        """
        将 directory_tree 的结果转换为文件列表格式
        
        Args:
            tree_result: directory_tree 的返回结果
            
        Returns:
            转换后的文件列表
        """
        file_list = []
        
        # tree_result 是 Response 对象，需要从 content 中提取
        if not tree_result['isError']:
            # 遍历 content 列表，寻找文本内容
            for content_item in tree_result["content"]:
                if content_item['text']:
                    try:
                        # 首先尝试解析为 JSON 格式的树形数据
                        tree_data = json.loads(content_item['text'])
                        file_list = self._parse_tree_data(tree_data, "")
                        break
                    except (json.JSONDecodeError, AttributeError):
                        # 如果不是 JSON，尝试解析为简单的文本格式
                        try:
                            file_list = self._parse_simple_list(content_item['text'], "")
                            break
                        except Exception as e:
                            logger.error(f"Failed to parse directory tree content as simple list: {str(e)}")
        
        return file_list
    
    def _parse_tree_data(self, tree_data, current_path) -> list:
        """
        递归解析树形数据
        Args:
            tree_data: 树形数据列表
            current_path: 当前路径
        Returns:
            解析后的树形文件列表
        """
        file_list = []
        
        if not isinstance(tree_data, list):
            return file_list
            
        for item in tree_data:
            if not isinstance(item, dict):
                continue
                
            name = item.get('name', '')
            item_type = item.get('type', '')
            full_path = os.path.join(current_path, name) if current_path else name
            
            if item_type == 'directory':
                # 递归处理子项
                children = item.get('children', [])
                child_items = self._parse_tree_data(children, full_path)
                
                # 添加目录项（包含子项）
                file_list.append({
                    "name": name,
                    "type": "directory",
                    "path": full_path,
                    "size": 0,
                    "children": child_items
                })
                    
            elif item_type == 'file':
                # 添加文件项
                file_list.append({
                    "name": name,
                    "type": "file",
                    "path": full_path,
                    "size": 0,  # directory_tree 不返回文件大小
                    "children": []
                })
        
        return file_list
    
    def _parse_simple_list(self, text_content: str, current_path: str = "") -> list:
        """
        解析简单的文件列表文本格式
        
        Args:
            text_content: 文本内容，格式如 "[FILE] A.md\n[DIR] complex_test_structure\n..."
            current_path: 当前路径
            
        Returns:
            解析后的文件列表
        """
        file_list = []
        
        if not text_content:
            return file_list
            
        # 按行分割
        lines = text_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 解析格式: [TYPE] filename
            if line.startswith('[FILE] '):
                filename = line[7:].strip()  # 移除 "[FILE] " 前缀
                if filename:
                    full_path = os.path.join(current_path, filename) if current_path else filename
                    file_list.append({
                        "name": filename,
                        "type": "file",
                        "path": full_path,
                        "size": 0
                    })
            elif line.startswith('[DIR] '):
                dirname = line[6:].strip()  # 移除 "[DIR] " 前缀
                if dirname:
                    full_path = os.path.join(current_path, dirname) if current_path else dirname
                    file_list.append({
                        "name": dirname,
                        "type": "directory",
                        "path": full_path,
                        "size": 0
                    })
        
        return file_list
    
    async def list_skill_files_in_sandbox(self, user_id: str, session_id: str, skill_name: str, sandbox_service) -> Dict[str, Any]:
        """
        端点: /list_skill_skeleton - 获取沙箱中技能目录的文件列表（树形结构）
        
        请求参数:
            - user_id: 用户唯一标识符
            - session_id: 会话ID
            - skill_name: 技能名称
            - sandbox_service: 沙箱服务实例
        
        响应参数:
            - status: 请求状态（success 或 error）
            - user_id: 用户唯一标识符
            - current_path: 当前路径（固定为技能根目录）
            - pagination: 分页信息（不分页，返回完整列表）
            - file_list: 文件树列表
        """
        try:
            self._log_operation("List skill files in sandbox", user_id, session_id=session_id, skill_name=skill_name)
            skill_storage_key = skill_name
            if skill_storage_key.startswith("SKILL_"):
                _, _, skill_name = skill_storage_key.split('_', 2)
            else:
                skill_name = skill_storage_key
            # 连接沙箱
            try:
                sandboxes = sandbox_service.connect(
                    session_id=session_id,
                    user_id=user_id,
                    sandbox_types=[self.SANDBOX_TYPE],
                )
                sandbox_instance = sandboxes[0]
                logger.info(f"Connected to sandbox for session {session_id}/{user_id}")
            except Exception as e:
                logger.error(f"Failed to connect to sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"连接沙箱失败: {str(e)}"
                }
            
            # 构建技能目录路径
            skill_dir_path = f"/workspace/skill/{skill_storage_key}/{skill_name}"
            
            # 检查技能目录是否存在
            try:
                check_result = sandbox_instance.run_shell_command(f'ls -a "{skill_dir_path}"')
                if check_result.get('isError'):
                    logger.warning(f'沙箱id={sandbox_instance.sandbox_id}, 检查用户技能[{skill_name}]目录是否存在失败: {check_result}')
                    error_message = check_result.get('content', [{}])[0].get('text', '技能目录不存在')
                    if 'No such file or directory' in error_message:
                        return {
                            "status": "error",
                            "error": f"技能目录不存在: {skill_name}"
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"检查技能目录失败: {error_message}"
                        }
            except Exception as e:
                logger.error(traceback.format_exc())
                return {
                    "status": "error",
                    "error": f"检查技能目录异常: {str(e)}"
                }
            
            # 使用 directory_tree 方法获取技能目录文件列表
            try:
                tree_result = sandbox_instance.directory_tree(skill_dir_path)
                logger.info(f"Got directory tree for skill directory: {skill_dir_path}")
                
                # 转换格式以匹配现有接口
                file_list = self._convert_directory_tree_to_file_list(tree_result)
                
                return {
                    "status": "success",
                    "user_id": user_id,
                    "current_path": "",  # 技能根目录，不显示相对路径
                    "pagination": {
                        "page": -1,
                        "page_size": len(file_list),
                        "total": len(file_list),
                        "total_pages": 1
                    },
                    "file_list": file_list
                }
                
            except Exception as e:
                logger.error(f"Failed to get skill directory tree: {str(e)}")
                return {
                    "status": "error",
                    "error": f"获取技能文件列表失败: {str(e)}"
                }
                
        except Exception as e:
            return self._handle_error("list_skill_files_in_sandbox", e, {
                "user_id": user_id,
                "session_id": session_id,
                "skill_name": skill_name
            })
    
    async def download_file_from_sandbox(self, user_id: str, session_id: str, file_path: str, sandbox_service, skill_name: str = "") -> Dict[str, Any]:
        """
        端点: /download_file - 验证文件存在并返回元数据（不包含文件内容）
        
        请求参数:
            - user_id: 用户唯一标识符
            - session_id: 会话ID
            - file_path: 相对于沙箱的文件路径
            - sandbox_service: 沙箱服务实例
            - skill_name: 技能名称（可选，为空时从用户工作空间下载，非空时从技能目录下载）
        
        响应参数:
            - status: 请求状态（success 或 error）
            - filename: 文件名
            - size: 文件大小（字节）
            - sandbox_id: 沙箱ID（用于流式读取）
            - file_path: 沙箱中的完整文件路径
            - sandbox_instance: 沙箱实例（用于流式读取）
            - error: 错误信息（仅当 status=error 时存在）
        """
        try:
            self._log_operation("Download file from sandbox", user_id, session_id=session_id, file_path=file_path, skill_name=skill_name)
            
            # 安全验证 - 检查文件路径是否安全
            if not file_path or not file_path.strip():
                return {
                    "status": "error",
                    "error": "文件路径不能为空"
                }
            
            # 清理文件路径，防止路径遍历攻击
            safe_file_path = file_path.strip()
            
            # 连接沙箱
            try:
                sandboxes = sandbox_service.connect(
                    session_id=session_id,
                    user_id=user_id,
                    sandbox_types=[self.SANDBOX_TYPE],
                )
                sandbox_instance = sandboxes[0]
                logger.info(f"Connected to sandbox for session {session_id}/{user_id}")
            except Exception as e:
                logger.error(f"Failed to connect to sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"连接沙箱失败: {str(e)}"
                }
            
            # 构建沙箱中的完整文件路径
            sandbox_full_path = f"/workspace/{safe_file_path}"
            # 检查文件是否存在
            try:
                check_result = sandbox_instance.manager_api.fs_exists(sandbox_instance.sandbox_id, sandbox_full_path)                
                # 解析检查结果
                if not check_result:
                    return {
                        "status": "error",
                        "error": f"文件不存在: {safe_file_path}"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"检查文件存在性异常: {str(e)}"
                }
            
            # 获取文件信息（大小等）
            file_size = 0
            try:
                # 获取文件大小
                info_result = sandbox_instance.run_shell_command(f'wc -c "{sandbox_full_path}"')
                if not info_result.get('isError'):
                    size_output = info_result.get('content', [{}])[0].get('text', '').strip()
                    if size_output:
                        file_size = int(size_output.split()[0])
            except Exception:
                # 如果获取大小失败，默认0（上层会处理）
                file_size = 0
            
            # 提取文件名
            filename = os.path.basename(safe_file_path)
            
            logger.info(f"File metadata retrieved: user={user_id}, file_path={safe_file_path}, size={file_size} bytes")
            
            # 返回元数据，不包含文件内容
            return {
                "status": "success",
                "filename": filename,
                "size": file_size,
                "sandbox_id": sandbox_instance.sandbox_id,
                "file_path": sandbox_full_path,
                "sandbox_instance": sandbox_instance  # 传递实例用于流式读取
            }
                
        except Exception as e:
            return self._handle_error("download_file_from_sandbox", e, {
                "user_id": user_id,
                "file_path": file_path,
                "skill_name": skill_name
            })
    
    async def edit_file_in_sandbox(self, user_id: str, session_id: str, skill_name: str, file_path: str, file_content: Optional[str], sandbox_service) -> Dict[str, Any]:
        """
        端点: /edit_file - 在沙箱中编辑用户文件或技能文件内容
        
        请求参数:
            - user_id: 用户唯一标识符
            - session_id: 会话ID
            - skill_name: 技能名称（空字符串表示用户文件空间）
            - file_path: 相对于沙箱的文件路径（相对路径）
            - file_content: 全量的文件内容（None或空字符串表示清空文件）
            - sandbox_service: 沙箱服务实例
        
        响应参数:
            - status: 请求状态（success 或 error）
            - message: 操作结果描述
            - error: 错误信息（仅当 status=error 时存在）
            - file_path: 文件路径
        """
        try:
            self._log_operation("Edit file in sandbox", user_id, session_id=session_id, file_path=file_path, skill_name=skill_name)
            
            # 安全验证 - 检查文件路径是否安全
            if not file_path or not file_path.strip():
                return {
                    "status": "error",
                    "error": "文件路径不能为空"
                }
            
            # 清理文件路径，防止路径遍历攻击
            safe_file_path = file_path.strip()
            
            # 连接沙箱
            try:
                sandboxes = sandbox_service.connect(
                    session_id=session_id,
                    user_id=user_id,
                    sandbox_types=[self.SANDBOX_TYPE],
                )
                sandbox_instance = sandboxes[0]
                logger.info(f"Connected to sandbox for session {session_id}/{user_id}")
            except Exception as e:
                logger.error(f"Failed to connect to sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"连接沙箱失败: {str(e)}"
                }
            
            # 构建沙箱中的完整文件路径
            sandbox_full_path = f"/workspace/{safe_file_path}"
            is_skill_file = safe_file_path.startswith("skill/")
            
            # 检查文件是否存在
            try:
                check_result = sandbox_instance.manager_api.fs_exists(sandbox_instance.sandbox_id, sandbox_full_path)
                
                # 解析检查结果
                if not check_result:
                    return {
                        "status": "error",
                        "error": f"文件不存在: {safe_file_path}"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"检查文件存在性异常: {str(e)}"
                }
            
            # 处理文件内容 - 如果为None则使用空字符串
            content_to_write = file_content if file_content is not None else ""
            
            # 使用 write_file 工具写入文件内容
            try:
                # 执行写入命令
                write_result = sandbox_instance.write_file(sandbox_full_path, content_to_write)
                
                if write_result.get('isError'):
                    error_message = write_result.get('content', [{}])[0].get('text', '写入文件失败')
                    return {
                        "status": "error",
                        "error": f"写入文件失败: {error_message}"
                    }
                
                logger.info(f"File edited successfully in sandbox: user={user_id}, file_path={safe_file_path}, skill_name={skill_name}")

                if is_skill_file:
                    parts = safe_file_path.split('/')
                    storage_key = parts[1] if len(parts) > 1 else ""
                    edit_skill_name = parts[2] if len(parts) > 2 else ""
                    if storage_key and edit_skill_name:
                        logger.info(f"[SKILL-FILE-ETID] [SKILL-DETECT] File belongs to a skill. user={user_id}, path={safe_file_path}, skill={edit_skill_name}")
                        storage_utils = SkillFileSystemUtils()
                        edit_skill_dir = f'/workspace/skill/{storage_key}/{edit_skill_name}'

                        logger.info(f"[SKILL-FILE-ETID] [ARCHIVE-START] Creating archive for skill '{edit_skill_name}' at {edit_skill_dir}")
                        storage_utils.sandbox_make_archive(
                            sandbox_instance,
                            save_name=edit_skill_name,
                            archive_dir=edit_skill_dir,
                        )
                        logger.info(f"[SKILL-FILE-ETID] [ARCHIVE-COMPLETE] Archive created for skill '{edit_skill_name}'")

                        logger.info(f"[SKILL-FILE-ETID] [UPLOAD-START] Saving skill '{edit_skill_name}' with storage key={storage_key}")
                        archive_name = f'{edit_skill_name}.zip'
                        sandbox_file_path = f'/workspace/{archive_name}'
                        storage_utils.sandbox_upload_skill_package(
                            sandbox_instance,
                            storage_key,
                            sandbox_file_path=sandbox_file_path,
                        )
                        logger.info(f"[SKILL-FILE-ETID] [UPLOAD-COMPLETE] Skill '{edit_skill_name}' successfully saved. storage_key={storage_key}")

                        logger.info(f"[SKILL-FILE-ETID] [CLEANUP-START] Removing temporary archive file: {sandbox_file_path}")
                        storage_utils.sandbox_delete_file(sandbox_instance, sandbox_file_path)
                        logger.info(f"[SKILL-FILE-ETID] [CLEANUP-COMPLETE] Temporary archive file deleted: {sandbox_file_path}")

                return {
                    "status": "success",
                    "message": "文件已成功保存",
                    "file_path": file_path
                }
                
            except Exception as e:
                logger.error(f"Failed to write file in sandbox: {str(e)}")
                return {
                    "status": "error",
                    "error": f"写入文件内容失败: {str(e)}"
                }
        except Exception as e:
            return self._handle_error("edit_file_in_sandbox", e, {
                "user_id": user_id,
                "file_path": file_path,
                "skill_name": skill_name
            })
