# -*- coding: utf-8 -*-
"""
提示词构建器 - 动态生成系统提示词
"""

from typing import List, Dict, Any
from config.settings import Config

from logger.setup import logger



class PromptBuilder:
    """系统提示词构建器"""
    
    @staticmethod
    def build_base_prompt() -> str:
        """获取基础提示词"""
        import datetime
        
        base_prompt = Config.SYSTEM_PROMPT_BASE
        
        now = datetime.datetime.now()
        time_str = now.strftime('%Y年%m月%d日 %H:%M:%S')
        weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        
        time_zone = f"\n## 时间信息\n+ 当前时间：{time_str} ({weekday})\n+ 时区：北京时间 (UTC+8)"
        
        return base_prompt + time_zone

    
    @staticmethod
    def build_skill_creator_prompt(to_do_list: List[Dict[str, str]] = None) -> str:
        """
        为skill-creator构建提示词
        
        Args:
            to_do_list: 待完善的技能列表，每项包含skill_name和skill_dir
            
        Returns:
            完整的系统提示词
        """
        # prompt = PromptBuilder.build_base_prompt()
        prompt = ""
        
        if to_do_list and len(to_do_list) == 1:
            to_do_skills_info = "\n".join(
                [f"待完善技能信息：\n    - 技能名称：{item['skill_name']}\n    - 路径: /workspace/skill/{item['skill_storage_id']}/{item['skill_name']}" for item in to_do_list]
            )
            prompt += f"\n# 你当前的任务：完善用户已经创建的技能\n1. **重要** ：你需要使用`{Config.SKILL_CREATOR_NAME}`技能中的指导，来完善技能；\n2. {to_do_skills_info}\n3. 在完善技能时，你所有的新建的文件、所有要修改的文件，都只能在`/workspace/skill/{to_do_list[0]['skill_storage_id']}/{to_do_list[0]['skill_name']}`路径下创建或修改，**绝对不能越界**。\n4. 你可以使用文件写入工具来创建或修改文件。\n5. 技能完善结束后，用```markdown```格式（不写文件）来简短分点总结你完善了哪些内容，总结一定要非常简短才行。\n"
            logger.info(f"Built skill-creator prompt with {len(to_do_list)} to-do skills")
        
        return prompt
    
    @staticmethod
    def build_agent_prompt(skill_names: List[str] = None) -> str:
        """
        为普通智能体构建提示词
        
        Args:
            skill_names: 装配的技能名称列表
            
        Returns:
            完整的系统提示词
        """
        prompt = ""
        
        if skill_names and len(skill_names) > 0:
            skills_info = "、".join(skill_names)
            prompt += f"\n1. 当前会话已装配技能：{skills_info}；\n2. 你使用技能时生成的**任何结果文件**都应不重复的放在用户的文件空间（`/workspace/output`）内；\n3. 尽量不修改`/workspace/skill`和`/workspace/upload`路径下的内容。"
        
        return prompt
