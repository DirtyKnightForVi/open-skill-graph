# -*- coding: utf-8 -*-
"""
??????? - ?????????????????
"""

# import traceback
# import os
# import shutil
# import tempfile
# import zipfile
# import tarfile
# from pathlib import Path
import logging
import re
from typing import List, Dict, Any, Optional

from logger.setup import logger
import time
from config.settings import Config
from core.skill.manager import Manager
from core.skill.storage_ops import StorageOperations

# logger = logging.getLogger(__name__)


class SkillService:
    """????????????????????????????????"""
    
    def __init__(self, skill_manager: Manager):
        """
        ???????
        
        Args:
            skill_manager: ???????????????????
        """
        self.skill_manager = skill_manager
        self.storage_ops = StorageOperations()
    
    def get_skill_creator(self) -> List[str]:
        """
        ?? skill-creator ??
        
        Returns:
            ?? skill-creator ???
        """
        return [Config.SKILL_CREATOR_NAME]
    
    async def add_existing_skill_to_todo(
        self,
        session_id: str,
        user_id: str,
        skill_name: Optional[str] = None,
        skill_desc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ????????to_do?????????
        
        Args:
            session_id: ??ID
            user_id: ??ID
            skill_name: ????
            skill_desc: ????
            
        Returns:
            ?????????
        """
        try:
            # 1. ???????skill-creator?????????
            self.skill_manager.create_session(session_id, user_id)
            logger.info(f"[SKILL OPTIMIZATION] Created session {session_id} for user {user_id}")
            
            # ?? skill-creator
            skill_creator = self.get_skill_creator()
            if not skill_creator:
                logger.error("[SKILL OPTIMIZATION] skill-creator is not available")
                return {
                    "status": "error",
                    "error": "skill-creator not available"
                }
            
            # ?? skill-creator
            attach_result = await self.skill_manager.attach_skills(session_id, user_id, skill_creator, "common")
            if attach_result["failed"]:
                logger.error(f"[SKILL OPTIMIZATION] Failed to attach skill-creator: {attach_result['failed']}")
                return {
                    "status": "error",
                    "error": "skill-creator attachment failed"
                }
            
            response_data = {
                "status": "success",
                "create_user_id": user_id,
                "create_start_time": int(time.time() * 1000),
                "skill_storage_id": ""
            }
            
            # 2. ??????to_do???????
            if skill_name:
                add_result = await self.skill_manager.add_skill_to_todo(
                    session_id, user_id, skill_name, skill_desc, user_id
                )
                if add_result["success"]:
                    skill_storage_id = add_result["skill_storage_id"]
                    logger.info(f"[SKILL OPTIMIZATION] Added skill '{skill_name}' to to_do with STORAGE key: {skill_storage_id}")
                    response_data["skill_storage_id"] = skill_storage_id
                else:
                    logger.error(f"[SKILL OPTIMIZATION] Failed to add skill to to_do: {add_result['message']}")
                    return {
                        "status": "error",
                        "error": add_result["message"]
                    }
            
            return response_data
        
        except Exception as e:
            logger.error(f"[SKILL OPTIMIZATION] Error in add_existing_skill_to_todo: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_session_with_skill_creator(
        self,
        session_id: str,
        user_id: str,
        skill_name: Optional[str] = None,
        skill_desc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ??????? skill-creator ???????????
        
        Args:
            session_id: ??ID
            user_id: ??ID
            skill_name: ????????
            skill_desc: ????????
            
        Returns:
            ?? status?user_id?start_time ??????
        """
        try:
            # ????
            self.skill_manager.create_session(session_id, user_id)
            logger.info(f"[SKILL CREATION] Created session {session_id} for user {user_id}")
            
            # ?? skill-creator
            skill_creator = self.get_skill_creator()
            if not skill_creator:
                logger.error("[SKILL CREATION] skill-creator is not available")
                return {
                    "status": "error",
                    "error": "skill-creator not available"
                }
            
            # ?? skill-creator
            attach_result = await self.skill_manager.attach_skills(session_id, user_id, skill_creator, "common")
            if attach_result["failed"]:
                logger.error(f"[SKILL CREATION] Failed to attach skill-creator: {attach_result['failed']}")
                return {
                    "status": "error",
                    "error": "skill-creator attachment failed"
                }
            
            response_data = {
                "status": "success",
                "create_user_id": user_id,
                "create_start_time": int(time.time() * 1000),
                "skill_storage_id": ""
            }
            
            # ????????????????
            if skill_name:
                create_result = await self.skill_manager.create_skill_with_to_do(
                    session_id, user_id, skill_name, skill_desc
                )
                if create_result["success"]:
                    skill_storage_id = create_result["skill_storage_id"]
                    logger.info(f"[SKILL CREATION] Created skill '{skill_name}' with STORAGE key: {skill_storage_id}")
                    response_data["skill_storage_id"] = skill_storage_id
                else:
                    logger.error(f"[SKILL CREATION] Failed to create skill: {create_result['message']}")
                    return {
                        "status": "error",
                        "error": create_result["message"]
                    }
            
            return response_data
        
        except Exception as e:
            logger.error(f"[SKILL CREATION] Error in create_session_with_skill_creator: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def attach_skills_to_session(
        self,
        session_id: str,
        user_id: str,
        skills_list: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        ???????????????????????????
        
        Args:
            session_id: ??ID
            user_id: ??ID???????
            skills_list: ???????????user_id?skill_name
            
        Returns:
            ??status?message???
        """
        try:
            # ??/?????
            self.skill_manager.create_session(session_id, user_id)
            
            # ??????????????
            skills_by_owner: Dict[str, List[str]] = {}
            for skill_item in skills_list:
                skill_owner_id = skill_item.get("user_id")
                skill_name = skill_item.get("skill_name")
                
                if skill_owner_id not in skills_by_owner:
                    skills_by_owner[skill_owner_id] = []
                skills_by_owner[skill_owner_id].append(skill_name)
            
            # ????????????????????
            unavailable_skills = []
            for skill_owner_id, skill_names in skills_by_owner.items():
                for skill_name in skill_names:
                    skill_info = await self.skill_manager._get_skill_info(skill_owner_id, skill_name)
                    print(skill_info)
                    if skill_info is None:
                        unavailable_skills.append({
                            "user_id": skill_owner_id,
                            "skill_name": skill_name
                        })
            
            if unavailable_skills:
                # ????????????
                error_msg = ""
                for unavailable_skill in unavailable_skills:
                    error_skill = unavailable_skill
                    error_msg += f"{error_skill['skill_name']}??????????{error_skill['user_id']}?"
                    logger.warning(f"Unavailable skills for user {user_id}: {unavailable_skills}")
                return {
                    "status": "error",
                    "data": error_msg
                }
            
            # ?????????????
            all_attached = []
            all_failed = []
            
            for skill_owner_id, skill_names in skills_by_owner.items():
                # ????????????????
                attach_result = await self.skill_manager.attach_skills(session_id, user_id, skill_names, skill_owner_id)
                all_attached.extend(attach_result["attached"])
                all_failed.extend(attach_result["failed"])
            
            if all_failed:
                # ?????????????
                error_msg = f"{all_failed[0]}??????"
                logger.warning(f"Failed to attach skills: {all_failed}")
                return {
                    "status": "error",
                    "data": error_msg
                }
            
            # ????????
            success_msg = "???????"
            logger.info(f"User {user_id} successfully attached skills from multiple sources: {all_attached}")
            
            return {
                "status": "success",
                "data": success_msg
            }
        
        except Exception as e:
            logger.error(f"Error attaching skills: {str(e)}")
            return {
                "status": "error",
                "data": f"??????: {str(e)}"
            }
    
    async def detach_session_skills(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        ??????????
        
        Args:
            session_id: ??ID
            user_id: ??ID
            
        Returns:
            ??status?response???
        """
        try:
            # ??/?????
            self.skill_manager.create_session(session_id, user_id)
            
            # ?????????
            skills = self.skill_manager.get_session_skills(session_id, user_id)
            
            if skills and len(skills) > 0:
                skill_names = [skill.get("skill_name", "") for skill in skills]
                await self.skill_manager.detach_skills(session_id, user_id, skill_names)
                logger.info(f"Detached {len(skill_names)} skills from session {session_id}")
            
            return {
                "status": "success",
                "response": "???????????"
            }
        
        except Exception as e:
            logger.error(f"Error detaching skills: {str(e)}")
            return {
                "status": "error",
                "response": "???????????"
            }
    
    async def get_skill_content(self, user_id: str, skill_name: str) -> Dict[str, Any]:
        """
        ????????? SKILL.md ????
        
        ????????????????????????????????
        
        Args:
            user_id: ??ID
            skill_name: ????
            
        Returns:
            ?????????
        """
        try:
            # ??????
            skill_info = await self.skill_manager._get_skill_info(user_id, skill_name)
            if skill_info is None:
                logger.warning(f"Skill not found: {skill_name} for user {user_id}")
                return {
                    "status": "error",
                    "skill_name": skill_name,
                    "message": f"??'{skill_name}' ???"
                }
            
            # ?????????????
            skill_storage_key = skill_info["skill_storage_id"]
            
            try:
                content = self.storage_ops.read_skill_md(skill_storage_key, skill_name)
                skill_md_path = None
                if content is None:
                    raise FileNotFoundError(f"SKILL.md not found in local package: {skill_storage_key}")
                
                # ???????? SKILL.md ??
                skill_content = content
            except Exception as download_error:
                logger.error(f"Failed to load skill {skill_name} from local storage: {download_error}")
                return {
                    "status": "error",
                    "skill_name": skill_name,
                    "message": f"???????????????: {str(download_error)}"
                }
            
            # ????????? YAML frontmatter?
            import re
            match = re.match(r'^---\n.*?\n---\n(.*)', skill_content, re.DOTALL)
            if match:
                skill_content = match.group(1).strip()
            else:
                skill_content = skill_content.strip()
            
            logger.info(f"Successfully retrieved skill content for {skill_name} (owner_id: {skill_info['owner_id']})")
            return {
                "status": "success",
                "skill_name": skill_name,
                "skill_content": skill_content,
                "skill_type": skill_info["type"],
                "message": "????????"
            }
        
        except Exception as e:
            logger.error(f"Error getting skill content for {skill_name}: {str(e)}")
            return {
                "status": "error",
                "skill_name": skill_name,
                "message": f"????????: {str(e)}"
            }
    
    async def get_user_skills_formatted(self, user_id: str) -> List[Dict[str, str]]:
        """
        ?????????????? - ???????
        
        Args:
            user_id: ??ID??????\"common\" ??????
            
        Returns:
            ????????
        """
        try:
            # ?????user_id?\"common\"???????
            if user_id == "common":
                # ??????????
                common_skills = await self.skill_manager.meta_client.get_common_skills()
                
                # ????????
                formatted_common_skills = []
                for skill_info in common_skills:
                    formatted_common_skills.append({
                        "skill_name": skill_info["skill_name"],
                        "skill_storage_id": skill_info["skill_storage_id"],
                        "skill_description": skill_info["skill_description"]
                    })
                
                logger.info(f"Retrieved {len(formatted_common_skills)} common skills via API")
                return formatted_common_skills
            
            # ??????????????????????????
            # ??????????????????
            logger.info(f"No batch API available for user {user_id}, returning empty skill list")
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving user skills: {str(e)}")
            return []
    
    async def upload_skill(self, user_id: str, session_id: str, file_path: str, filename: str) -> Dict[str, Any]:
        """
        ????????????????????????????
        
        Args:
            user_id: ??ID
            session_id: ??ID
            file_path: ???zip????
            filename: ???????SKILL_?????.zip?
            
        Returns:
            ?????????
        """
        import zipfile
        import tempfile
        from pathlib import Path
        
        temp_extract_dir = None
        
        try:
            # 1. ???????
            match = re.match(r'^SKILL_([a-zA-Z0-9_-]+)\.zip$', filename)
            if not match:
                return {
                    "status": "error",
                    "skill_name": "",
                    "skill_dir": "",
                    "is_overwritten": False,
                    "message": f"???????????SKILL_?????.zip?????????{filename}"
                }
            
            skill_name_from_filename = match.group(1)
            logger.info(f"Uploading skill with name: {skill_name_from_filename}, user: {user_id}, session: {session_id}")
            
            # 2. ?????????
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_extract_dir = Path(temp_dir) / skill_name_from_filename
                temp_extract_dir.mkdir(exist_ok=True)
                
                # ??zip??
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                logger.info(f"Extracted skill files to: {temp_extract_dir}")
                
                # 3. ??SKILL.md????
                skill_md_path = temp_extract_dir / "SKILL.md"
                if not skill_md_path.exists():
                    return {
                        "status": "error",
                        "skill_name": skill_name_from_filename,
                        "skill_dir": "",
                        "is_overwritten": False,
                        "message": "??????SKILL.md??"
                    }
                
                # 4. ??SKILL.md?????
                try:
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # ??YAML frontmatter
                    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                    if not match:
                        return {
                            "status": "error",
                            "skill_name": skill_name_from_filename,
                            "skill_dir": "",
                            "is_overwritten": False,
                            "message": "SKILL.md?????????YAML frontmatter"
                        }
                    
                    frontmatter = match.group(1)
                    
                    # ??name??
                    name_match = re.search(r'^name:\s*(.+?)$', frontmatter, re.MULTILINE)
                    if not name_match:
                        return {
                            "status": "error",
                            "skill_name": skill_name_from_filename,
                            "skill_dir": "",
                            "is_overwritten": False,
                            "message": "SKILL.md???name??"
                        }
                    
                    skill_name_from_metadata = name_match.group(1).strip()
                    
                    # ??description??
                    desc_match = re.search(r'^description:\s*(.+?)$', frontmatter, re.MULTILINE)
                    skill_description = desc_match.group(1).strip() if desc_match else ""
                    
                except Exception as e:
                    return {
                        "status": "error",
                        "skill_name": skill_name_from_filename,
                        "skill_dir": "",
                        "is_overwritten": False,
                        "message": f"??SKILL.md????: {str(e)}"
                    }
                
                # 5. ???????????SKILL.md??name??
                if skill_name_from_filename != skill_name_from_metadata:
                    return {
                        "status": "error",
                        "skill_name": skill_name_from_filename,
                        "skill_dir": "",
                        "is_overwritten": False,
                        "message": f"?????????SKILL.md??name???????={skill_name_from_filename}, SKILL.md={skill_name_from_metadata}"
                    }
                
                # 6. ?????????
                try:
                    storage_key = self.storage_ops.save_skill_package(temp_extract_dir, user_id, skill_name_from_filename)
                    logger.info(f"Successfully saved skill {skill_name_from_filename} to local storage with key: {storage_key}")
                    
                    return {
                        "status": "success",
                        "skill_name": skill_name_from_filename,
                        "skill_dir": str(temp_extract_dir),
                        "is_overwritten": False,
                        "skill_storage_key": storage_key,
                        "message": skill_description
                    }
                    
                except Exception as upload_error:
                    logger.error(f"Local storage save failed for skill {skill_name_from_filename}: {upload_error}")
                    return {
                        "status": "error",
                        "skill_name": skill_name_from_filename,
                        "skill_dir": "",
                        "is_overwritten": False,
                        "message": f"???????????: {str(upload_error)}"
                    }
        
        except Exception as e:
            logger.error(f"Error in upload_skill: {str(e)}")
            return {
                "status": "error",
                "skill_name": "",
                "skill_dir": "",
                "is_overwritten": False,
                "message": f"??????: {str(e)}"
            }