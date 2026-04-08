import functools
import json
from pathlib import Path

from config import Config
from logger import logger


# 加载测试数据配置文件
def load_mock_skill_data():
    """加载技能元数据测试数据"""
    try:
        mock_data_file = Path("skill_meta_service_test.json")
        if mock_data_file.exists():
            with open(mock_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"加载mock技能数据失败: {e}")
    return {}


# 全局mock数据缓存
MOCK_SKILL_DATA = load_mock_skill_data()


def mock_get_skill_meta(func):
    @functools.wraps(func)
    async def wrapper(self, user_id: str, skill_name: str):
        # 从测试数据中查找技能信息
        skill_data = find_skill_in_mock_data(user_id, skill_name)
        if skill_data:
            # 使用测试数据中的完整信息
            skill_type = "common" if user_id == "common" else "user"
            skill_storage_id = skill_data.get("skill_storage_id", f"SKILL_{user_id}_{skill_name}")
            
            skill_info = {
                "name": skill_data.get("name", skill_name),
                "type": skill_type,
                "skill_storage_id": skill_storage_id,
                "skill_description": skill_data.get("skill_description", ""),
                "skill_name_cn": skill_data.get("skill_name_cn", ""),
                "skill_path": skill_data.get("skill_path", ""),
                "skill_example": skill_data.get("skill_example", ""),
                "cluster_type": skill_data.get("cluster_type", ""),
                "create_time": skill_data.get("create_time", ""),
                "update_time": skill_data.get("update_time", ""),
                "user_id": user_id,
                # 原始数据备用
                "raw_data": skill_data
            }
            logger.info(f"使用mock数据返回技能信息: {user_id}/{skill_name}")
            return skill_info

        # 如果没有找到测试数据，使用默认的mock逻辑
        skill_type = "common" if user_id == "common" else "user"
        if skill_type == 'user':
            default_skill_name = 'Excel-Analy-Skill'
            data = {
                'skill_desc': '可以模板化生成Excel分析文件的技能',
                'skill_name_cn': '',
                "skill_path": "",
                "skill_example": "",
                "cluster_type": "",
                "create_time": "",
                "update_time": "",
            }
        else:
            data = {
                'skill_desc': 'This skill provides guidance for creating effective skills.',
                'skill_name_cn': '',
                "skill_path": "",
                "skill_example": "",
                "cluster_type": "",
                "create_time": "",
                "update_time": "",
            }

        skill_storage_id = f"SKILL_{user_id}_{skill_name}"
        skill_info = {
            "name": skill_name,
            "type": skill_type,
            "skill_storage_id": skill_storage_id,
            "skill_description": data.get("skill_desc", ""),
            "skill_name_cn": data.get("skill_name_cn", ""),
            "skill_path": data.get("skill_path", ""),
            "skill_example": data.get("skill_example", ""),
            "cluster_type": data.get("cluster_type", ""),
            "create_time": data.get("create_time", ""),
            "update_time": data.get("update_time", ""),
            "user_id": user_id,
            # 原始数据备用
            "raw_data": data
        }
        logger.info(f"使用默认mock数据返回技能信息: {user_id}/{skill_name}")
        return skill_info
    return wrapper


def find_skill_in_mock_data(user_id: str, skill_name: str) -> dict:
    """在mock数据中查找技能信息"""
    try:
        # 标准化用户ID
        if user_id == "common":
            user_key = "common"
        elif user_id == "public":
            user_key = "public"
        else:
            # 对于其他用户ID，检查是否有对应的测试数据
            if user_id in MOCK_SKILL_DATA:
                user_key = user_id
            else:
                # 如果没有找到特定用户，尝试使用001321877作为默认测试用户
                user_key = "001321877"
        
        # 查找用户数据
        user_data = MOCK_SKILL_DATA.get(user_key, {})
        if not user_data or "skill" not in user_data:
            return None
        
        # 查找具体技能
        for skill in user_data["skill"]:
            if skill.get("name") == skill_name:
                return skill
        
        # 如果没有找到精确匹配，可以尝试部分匹配
        for skill in user_data["skill"]:
            if skill_name.lower() in skill.get("name", "").lower():
                return skill
        
        return None
        
    except Exception as e:
        logger.error(f"查找mock技能数据时出错: {e}")
        return None


def mock_common_skills(func):
    """为获取公共技能列表提供mock数据"""
    @functools.wraps(func)
    async def wrapper(self):
        logger.info("使用mock数据返回公共技能列表")
        # 从测试数据中获取公共技能
        public_skills = []

        # 获取common用户的技能
        common_data = MOCK_SKILL_DATA.get("common", {})
        if "skill" in common_data:
            for skill in common_data["skill"]:
                skill_type = "common"
                skill_storage_id = skill.get("skill_storage_id", f"SKILL_common_{skill.get('name', 'unknown')}")
                skill_info = {
                    "name": skill.get("name", ""),
                    "type": skill_type,
                    "skill_storage_id": skill_storage_id,
                    "skill_description": skill.get("skill_description", ""),
                    "skill_name_cn": skill.get("skill_name_cn", ""),
                    "skill_path": skill.get("skill_path", ""),
                    "skill_example": skill.get("skill_example", ""),
                    "cluster_type": skill.get("cluster_type", ""),
                    "create_time": skill.get("create_time", ""),
                    "update_time": skill.get("update_time", ""),
                    "user_id": "common",
                    "raw_data": skill
                }
                public_skills.append(skill_info)

        # 获取public用户的技能
        public_data = MOCK_SKILL_DATA.get("public", {})
        if "skill" in public_data:
            for skill in public_data["skill"]:
                skill_type = "common"
                skill_storage_id = skill.get("skill_storage_id", f"SKILL_public_{skill.get('name', 'unknown')}")
                skill_info = {
                    "name": skill.get("name", ""),
                    "type": skill_type,
                    "skill_storage_id": skill_storage_id,
                    "skill_description": skill.get("skill_description", ""),
                    "skill_name_cn": skill.get("skill_name_cn", ""),
                    "skill_path": skill.get("skill_path", ""),
                    "skill_example": skill.get("skill_example", ""),
                    "cluster_type": skill.get("cluster_type", ""),
                    "create_time": skill.get("create_time", ""),
                    "update_time": skill.get("update_time", ""),
                    "user_id": "public",
                    "raw_data": skill
                }
                public_skills.append(skill_info)

        return public_skills
    return wrapper