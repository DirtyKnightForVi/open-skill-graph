# -*- coding: utf-8 -*-
"""
本地技能存储操作 - 替代 STORAGE 服务的本地技能包管理
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from config.settings import Config
from logger.setup import logger


class StorageOperations:
    """本地技能包存储操作"""

    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or Config.SKILL_STORAGE_PATH)
        self.root_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized StorageOperations with root_path: {self.root_path}")

    def get_skill_key(self, user_id: str, skill_name: str, skill_type: str = "user") -> str:
        if skill_type == "common":
            return f"SKILL_common_{skill_name}"
        elif skill_type == "public":
            return f"SKILL_public_{skill_name}"
        return f"SKILL_{user_id}_{skill_name}"

    def get_skill_archive_path(self, skill_key: str) -> Path:
        return self.root_path / f"{skill_key}.zip"

    def save_skill_package(self, skill_dir: Path, user_id: str, skill_name: str) -> str:
        """将技能目录打包并保存到本地技能仓库"""
        skill_key = self.get_skill_key(user_id, skill_name)
        archive_path = self.get_skill_archive_path(skill_key)
        base_name = str(archive_path.with_suffix(''))

        shutil.make_archive(base_name, 'zip', root_dir=skill_dir)

        logger.info(f"Saved skill package {skill_name} to local storage: {archive_path}")
        return skill_key

    def extract_skill_package(self, skill_key: str, target_dir: Path) -> Path:
        archive_path = self.get_skill_archive_path(skill_key)
        if not archive_path.exists():
            raise FileNotFoundError(f"Skill archive not found: {archive_path}")

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(archive_path), str(target_dir))

        logger.info(f"Extracted skill package {skill_key} to {target_dir}")
        return target_dir

    def read_skill_md(self, skill_key: str, skill_name: str) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            self.extract_skill_package(skill_key, temp_dir_path)
            candidate = temp_dir_path / "SKILL.md"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")

            nested = temp_dir_path / skill_name / "SKILL.md"
            if nested.exists():
                return nested.read_text(encoding="utf-8")

            raise FileNotFoundError(f"SKILL.md not found for skill {skill_name} in package {skill_key}")

    def has_skill_package(self, skill_key: str) -> bool:
        return self.get_skill_archive_path(skill_key).exists()
