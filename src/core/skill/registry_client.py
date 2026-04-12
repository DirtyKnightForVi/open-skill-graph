# -*- coding: utf-8 -*-
"""
RegistryClient - 从 Django Skills Registry 获取技能元数据
"""

import asyncio
import traceback
from typing import Any, Dict, List, Optional

import aiohttp

from config.settings import Config
from logger.setup import logger


class RegistryClient:
    def __init__(self, base_url: str = None, timeout: int = 10):
        self.base_url = (base_url or Config.REGISTRY_BASE_URL or "").rstrip("/")
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        token = Config.REGISTRY_TOKEN
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    @staticmethod
    def _normalize_visibility(visibility: str) -> str:
        if visibility in ("common", "public"):
            return "common"
        return "user"

    async def get_skill_meta(self, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        if not self.base_url:
            logger.warning("Registry base url is not configured")
            return None

        url = f"{self.base_url}/api/v1/skills/resolve"
        params = {"owner_id": user_id, "skill_name": skill_name}

        try:
            async with self.session.get(url, params=params, headers=self._get_headers()) as resp:
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    logger.warning(f"Registry resolve failed: status={resp.status}, user_id={user_id}, skill={skill_name}")
                    return None

                payload = await resp.json()
                skill = payload.get("skill") or {}
                version = payload.get("version") or {}
                if not skill or not version:
                    return None

                owner_id = skill.get("owner_id", user_id)
                return {
                    "skill_name": skill.get("name", skill_name),
                    "skill_storage_id": f"SKILL_{owner_id}_{skill.get('name', skill_name)}",
                    "skill_description": skill.get("description", ""),
                    "owner_id": owner_id,
                    "type": self._normalize_visibility(skill.get("visibility", "private")),
                    "skill_version_id": version.get("id"),
                    "artifact_uri": version.get("artifact_uri", ""),
                    "artifact_sha256": version.get("artifact_sha256", ""),
                }
        except asyncio.TimeoutError:
            logger.warning(f"Registry request timeout: user_id={user_id}, skill={skill_name}")
            return None
        except Exception:
            logger.error(f"Registry request error: {traceback.format_exc()}")
            return None

    async def get_common_skills(self) -> List[Dict[str, Any]]:
        if not self.base_url:
            return []

        url = f"{self.base_url}/api/v1/skills/common/"
        try:
            async with self.session.get(url, headers=self._get_headers()) as resp:
                if resp.status != 200:
                    logger.warning(f"Registry common skills failed: status={resp.status}")
                    return []
                payload = await resp.json()

                result: List[Dict[str, Any]] = []
                for item in payload:
                    skill = item.get("skill") or {}
                    version = item.get("version") or {}
                    if not skill or not version:
                        continue
                    owner_id = skill.get("owner_id", "common")
                    skill_name = skill.get("name", "")
                    result.append(
                        {
                            "skill_name": skill_name,
                            "skill_storage_id": f"SKILL_{owner_id}_{skill_name}",
                            "skill_description": skill.get("description", ""),
                            "owner_id": owner_id,
                            "type": self._normalize_visibility(skill.get("visibility", "common")),
                            "skill_version_id": version.get("id"),
                            "artifact_uri": version.get("artifact_uri", ""),
                            "artifact_sha256": version.get("artifact_sha256", ""),
                        }
                    )
                return result
        except Exception:
            logger.error(f"Registry common skills error: {traceback.format_exc()}")
            return []
