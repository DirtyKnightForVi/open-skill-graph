# -*- coding: utf-8 -*-
"""
应用入口点
启动 src 包下的应用
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

import functools
import os
import traceback

# 添加 src 目录到 Python 路径（确保可以导入 src 下的模块）
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from agentscope_runtime.sandbox.manager.server import app
from agentscope_runtime.common.container_clients import DockerClient

# 自定义沙箱导入注册
from src.core.sandbox import register_custom_sandbox

register_custom_sandbox()


def docker_in_docker_wrapper(func):
    """ DockerInDocker启动沙箱服务, 对应的沙箱ip需要改成沙箱服务所在宿主机ip """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _id, ports, ip = func(
            *args, **kwargs,
        )
        if not _id:
            raise RuntimeError("Sandbox container creation failed: container id is empty. Check image availability and registry access.")
        real_ip = os.getenv("SANDBOX_IP", "localhost")
        app.logger.info(f'容器启动成功: 容器id={_id}, 端口={ports}, ip={ip}, 实际调用ip={real_ip}')
        return _id, ports, real_ip

    return wrapper


runtime_config_file = 'sandbox_runtime_config.json'
runtime_config = {}
if os.path.exists(runtime_config_file) and os.path.isfile(runtime_config_file):
    with open(runtime_config_file, 'r') as f:
        runtime_config = json.load(f)


def extract_image_name(image_tag):
    # 去掉tag部分
    if ':' in image_tag:
        image_tag = image_tag.split(':', 1)[0]
    # 按/分割，取最后一部分
    last_part = image_tag.split('/')[-1]
    # 按-分割，取最后一部分
    skill_scope = last_part.split('-')[-1]
    return skill_scope


def merge_volumes(func):
    """ 合并SandboxManger创建容器和默认volumes """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            image = args[1]
            image_name = extract_image_name(image)
            # 自定义容器启动配置
            custom_runtime_config = deepcopy(runtime_config.get(image_name)) or {}
            app.logger.info(f'image_name={image_name}, image={image}')
            _runtime_config = kwargs.get('runtime_config') or {}

            # 替换volumes
            if "volumes" in custom_runtime_config:
                kwargs['volumes'] = custom_runtime_config.pop('volumes')

            environment = kwargs.get('environment') or {}
            environment.update(_runtime_config.get('environment') or {})
            environment.update(custom_runtime_config.pop('environment', None) or {})

            kwargs['runtime_config'] = custom_runtime_config
            app.logger.info(f'容器启动配置: {kwargs}')
        except:
            app.logger.error(f'{traceback.format_exc()}')
        return func(*args, **kwargs)

    return wrapper


DockerClient.create = merge_volumes(docker_in_docker_wrapper(DockerClient.create))

if __name__ == '__main__':
    app.main()
