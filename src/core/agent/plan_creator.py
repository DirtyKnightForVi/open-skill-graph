# -*- coding: utf-8 -*-
"""
计划创建器 - 为技能创建模式生成7步流程计划
"""

from agentscope.plan import PlanNotebook, Plan, SubTask
from typing import Optional
import asyncio


def plan_change_logging_hook(plan_notebook: PlanNotebook, plan: Plan) -> None:
    """
    计划变化钩子函数 - 控制台日志版
    
    Args:
        plan_notebook (PlanNotebook): PlanNotebook实例
        plan (Plan): 当前计划实例（变化后）
    """
    if plan is None:
        print(f"📋 [计划变更] 当前计划: 无")
        return
    
    # 统计各状态子任务数量
    states = {"todo": 0, "in_progress": 0, "done": 0, "abandoned": 0}
    for subtask in plan.subtasks:
        if subtask.state in states:
            states[subtask.state] += 1
    
    print(f"📋 [计划变更] 计划: {plan.name}")
    print(f"   📝 描述: {plan.description[:80]}...")
    print(f"   📊 状态: {plan.state}")
    print(f"   📈 子任务统计: todo={states['todo']}, in_progress={states['in_progress']}, "
          f"done={states['done']}, abandoned={states['abandoned']}")
    
    # 找出当前正在进行的任务
    in_progress_tasks = [(i, t.name) for i, t in enumerate(plan.subtasks) if t.state == "in_progress"]
    if in_progress_tasks:
        for idx, name in in_progress_tasks:
            print(f"   🔄 进行中任务[{idx}]: {name}")


async def create_skill_generation_plan() -> PlanNotebook:
    """
    创建技能生成计划 - 7步完整流程版本
    
    Returns:
        PlanNotebook: 配置好的计划笔记本
    """
    plan_notebook = PlanNotebook()
    
    # 注册计划变化钩子函数
    plan_notebook.register_plan_change_hook(
        hook_name="console_logging_hook",
        hook=plan_change_logging_hook,
    )
    
    await plan_notebook.create_plan(
        name="SkillForge Agent Skill生成",
        description="基于7步生成引擎自动构建生产级Agent技能，遵循简洁性、渐进式披露、代码优先等核心设计原则，输出符合行业最佳实践的完整Skill包。",
        expected_outcome="一个完整的Agent Skill项目，包含SKILL.md（YAML前置元数据：name、description）、可选资源：scripts/（可执行代码）、references/（参考资料）、templates/（模板文件）。项目遵循SkillForge质量标准：简洁性（<500行）、描述触发器优化、代码示例完整、反面案例必备、祈使语气一致。",
        subtasks=[
            SubTask(
                name="Step 1: 需求深度挖掘",
                description=(
                    "基于用户一句话需求，进行5维框架深度分析：核心定位（名称、价值主张）、功能边界（输入→处理→输出三元组）、"
                    "使用场景（≥5个具体案例）、知识缺口分析（AI已知/未知/易错）、依赖约束。输出结构化需求文档（2000-5000字），"
                    "为后续步骤提供完整的设计依据，特别关注AI模型在此领域的知识盲点。"
                ),
                expected_outcome=(
                    "一份Markdown格式的《技能需求规格说明书》，包含：\n"
                    "1. 核心定位（hyphen-case名称、20字内摘要、目标用户、价值主张）\n"
                    "2. 功能边界（3-7个核心功能三元组、扩展功能、明确排除项）\n"
                    "3. 使用场景（≥5个，每个含用户请求、期望行为、输出格式）\n"
                    "4. 知识缺口分析（AI已知内容排除、AI未知核心内容、AI易错模式）\n"
                    "5. 依赖约束（外部工具/API、平台兼容性、性能/安全要求）"
                ),
            ),
            SubTask(
                name="Step 2: 架构决策引擎",
                description=(
                    "基于需求分析做出5个关键架构决策：结构模式选择（工作流型/任务型/指南型/能力型）、"
                    "自由度级别确定（高/中/低）、资源文件规划（scripts/references/templates详细清单）、"
                    "渐进式披露策略（SKILL.md vs 配套文件的内容分配）、质量保证方案（验证清单、常见错误、质量标准）。"
                    "输出完整目录结构树，为后续步骤提供明确的实现蓝图。"
                ),
                expected_outcome=(
                    "一份架构决策文档，包含：\n"
                    "1. 结构模式选择及理由（适配需求特点）\n"
                    "2. 自由度级别及约束规则（创意型vs精确型）\n"
                    "3. 资源文件规划表（路径、类型、用途、行数估算）\n"
                    "4. 渐进式披露策略（<500行控制、加载触发条件）\n"
                    "5. 质量保证方案（验证清单、错误模式、质量标准）\n"
                    "6. 完整目录结构树（skill-name/及其子目录）"
                ),
            ),
            SubTask(
                name="Step 3: 元数据精炼",
                description=(
                    "生成并优化SKILL.md的YAML前置元数据。首先生成3个候选description，"
                    "从触发精准度（用户说什么会触发）、能力覆盖度（是否完整描述核心能力）、"
                    "信息密度（每个词的价值）三个维度进行自评打分（1-5分）。"
                    "选择最高分候选作为最终description，确保30-80词、客观描述性语气、"
                    "包含WHAT+WHEN触发关键词。"
                ),
                expected_outcome=(
                    "最优YAML frontmatter，格式：\n"
                    "```yaml\n"
                    "---\n"
                    "name: skill-name\n"
                    "description: |\n"
                    "  30-80词的优化描述，包含做什么和何时用\n"
                    "---\n"
                    "```\n"
                    "附带3候选description的评分对比表"
                ),
            ),
            SubTask(
                name="Step 4: SKILL.md主体生成",
                description=(
                    "基于架构决策和元数据，生成SKILL.md完整正文（不含frontmatter）。"
                    "严格遵循核心原则：简洁性（只含AI未知内容）、长度控制（150-450行）、"
                    "祈使语气、代码示例优先、反面案例必备。内容结构包括：概述、核心工作流程、"
                    "详细规则指令、代码示例（❌Bad/✅Good对比）、边界情况处理、输出格式规范、验证检查清单。"
                ),
                expected_outcome=(
                    "一份完整的SKILL.md正文（Markdown格式），特点：\n"
                    "1. 150-450行，不含AI已知通用知识\n"
                    "2. 全程祈使语气，无重复description内容\n"
                    "3. 完整可运行的代码示例，使用对比格式\n"
                    "4. 清晰的结构层次和验证检查清单\n"
                    "5. 超过100行的章节引用至references/"
                ),
            ),
            SubTask(
                name="Step 5: 质量审计与优化",
                description=(
                    "对生成的SKILL.md进行10维度严格质量审计：描述触发精准度、知识增量、代码示例质量、"
                    "反面案例覆盖、结构清晰度、渐进式披露、语气一致性、边界处理、可操作性、完整性。"
                    "每个维度1-10分评分，对低于8分的维度进行自动修复。输出评分报告和优化后的完整SKILL.md。"
                ),
                expected_outcome=(
                    "两部分输出：\n"
                    "## PART A：评分卡（10维度评分表，问题说明）\n"
                    "## PART B：优化后的完整SKILL.md\n"
                    "优化版本必须通过所有质量维度（≥8分），包含YAML frontmatter和修复后的正文"
                ),
            ),
            SubTask(
                name="Step 6: 配套资源生成",
                description=(
                    "严格按照Step 2架构决策中的资源文件规划，生成所有配套资源文件。"
                    "包括可执行脚本（含shebang行）、参考文档、模板文件等。"
                    "每个文件必须完整可用，无省略号或TODO占位符。遵循自动化提取格式要求。"
                ),
                expected_outcome=(
                    "所有规划的资源文件，格式：\n"
                    "### FILE: `scripts/xxx.py`\n"
                    "```python\n"
                    "#!/usr/bin/env python3\n"
                    "# 完整可执行代码\n"
                    "```\n"
                    "### FILE: `references/xxx.md`\n"
                    "```markdown\n"
                    "# 完整参考文档\n"
                    "```\n"
                    "严格按规划清单，无遗漏或额外文件"
                ),
            ),
            SubTask(
                name="Step 7: 最终组装与交付",
                description=(
                    "生成使用说明文档并完成最终质量验证。使用说明包含：安装说明（1-3句话）、"
                    "触发示例（≥5个自然语言请求）、迭代建议（3-5条具体改进方向）、"
                    "验证清单（SKILL.md完整性检查）。同时进行质量门验证："
                    "YAML frontmatter有效性、描述包含WHAT+WHEN、行数控制、代码完整性等。"
                ),
                expected_outcome=(
                    "完整交付包，包含：\n"
                    "1. 使用说明文档（4个标准部分）\n"
                    "2. 最终目录结构树\n"
                    "3. 质量验证通过证明\n"
                    "4. 所有文件打包就绪，可直接部署到AI平台\n"
                    "验证清单全部勾选，确保生产级质量"
                ),
            ),
        ],
    )
    return plan_notebook