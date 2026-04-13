# -*- coding: utf-8 -*-
"""
应用入口点
启动 src 包下的应用
"""
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

# 添加 src 目录到 Python 路径（确保可以导入 src 下的模块）
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 导入配置用于启动前依赖检查
from src.config.settings import Config


def _check_tcp(host: str, port: int, timeout: float = 1.2) -> bool:
    """检查 TCP 端口是否可连通。"""
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port_from_url(raw_url: str, default_port: int) -> tuple[str, int]:
    """从 URL 提取 host/port，缺失时回退到默认值。"""
    if not raw_url:
        return "127.0.0.1", default_port
    parsed = urlparse(raw_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    return host, int(port)


def run_startup_preflight() -> None:
    """启动前依赖检查，根据配置判断哪些服务必须在线。"""
    checks: list[tuple[str, str, int, bool]] = []

    # 当前代码路径会在生命周期中连接 sandbox，因此将其视为必需依赖。
    sandbox_host, sandbox_port = _parse_host_port_from_url(Config.SANDBOX_SERVICE_URL, 8000)
    checks.append(("sandbox", sandbox_host, sandbox_port, True))

    session_type = str(Config.SESSION_TYPE).lower().strip()
    if session_type == "redis":
        checks.append(("redis", Config.REDIS_HOST or "127.0.0.1", int(Config.REDIS_PORT), True))

    metadata_source = str(Config.SKILL_METADATA_SOURCE).lower().strip()
    if metadata_source == "registry":
        registry_host, registry_port = _parse_host_port_from_url(Config.REGISTRY_BASE_URL, 8001)
        checks.append(("registry", registry_host, registry_port, True))
    elif metadata_source == "auto" and Config.REGISTRY_BASE_URL:
        registry_host, registry_port = _parse_host_port_from_url(Config.REGISTRY_BASE_URL, 8001)
        checks.append(("registry", registry_host, registry_port, False))

    if not checks:
        return

    print("[startup] Dependency preflight checks:")
    failed_required: list[str] = []
    for name, host, port, required in checks:
        ok = _check_tcp(host, port)
        status = "OK" if ok else "FAILED"
        req_label = "required" if required else "optional"
        print(f"[startup] - {name:<8} {host}:{port} [{req_label}] -> {status}")
        if required and not ok:
            failed_required.append(f"{name}({host}:{port})")

    if failed_required:
        failed_text = ", ".join(failed_required)
        raise RuntimeError(
            "Startup aborted because required dependencies are unavailable: "
            f"{failed_text}. Please start missing services or adjust .env configuration."
        )


# 导入并启动应用
from src.app.app import app

if __name__ == '__main__':
    run_startup_preflight()
    app.run(host="0.0.0.0", port=3000, debug=False)
