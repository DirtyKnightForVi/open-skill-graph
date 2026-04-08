# -*- coding: utf-8 -*-
import json
import os
from typing import Optional

from agentscope_runtime.sandbox import FilesystemSandbox
from agentscope_runtime.sandbox.enums import SandboxType
from agentscope_runtime.sandbox.registry import SandboxRegistry
from agentscope_runtime.sandbox.utils import build_image_uri

from core.sandbox.utils import FileSystemUtils

SANDBOXTYPE = "skill_scope"

@SandboxRegistry.register(
    build_image_uri(f"runtime-sandbox-{SANDBOXTYPE}"),
    sandbox_type=SANDBOXTYPE,
    security_level="medium",
    timeout=60,
    description="my sandbox",
    environment={
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "AMAP_MAPS_API_KEY": os.getenv("AMAP_MAPS_API_KEY", ""),
    }
)
class SkillScopeSandbox(FilesystemSandbox):
    def __init__(
            self,
            sandbox_id: Optional[str] = None,
            timeout: int = 3000,
            base_url: Optional[str] = None,
            bearer_token: Optional[str] = None,
    ):
        super().__init__(
            sandbox_id,
            base_url,
            bearer_token,
            SandboxType(SANDBOXTYPE),
        )

    def init_user_environment(self, user_id, session_id, utils: FileSystemUtils):
        utils.sync_workspace_from_remote(user_id, session_id, sandbox=self)

    def save_user_environment(self, user_id, session_id, utils: FileSystemUtils):
        utils.sync_workspace_to_remote(user_id, session_id, sandbox=self)
