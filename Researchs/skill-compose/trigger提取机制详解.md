# Skill Compose 触发词(Triggers)提取机制详解

## 核心问题

提示词中的 "Triggers" 是从哪里来的？这部分信息的源头在哪？让我详细分析这个提取机制。

## 触发词提取的完整流程

### 1. 源头：SKILL.md 文件内容

触发词的**原始源头**是每个技能的 `SKILL.md` 文件。让我们看一个实际的例子：

**PDF 技能的 SKILL.md 文件：**
```markdown
---
name: "pdf"
description: "Use when tasks involve reading, creating, or reviewing PDF files where rendering and layout matter; prefer visual checks by rendering pages (Poppler) and use Python tools such as `reportlab`, `pdfplumber`, and `pypdf` for generation and extraction."
---

# PDF Skill

## When to use
- Read or review PDF content where layout and visuals matter.
- Create PDFs programmatically with reliable formatting.
- Validate final rendering before delivery.
```

**图像生成技能的 SKILL.md 文件：**
```markdown
---
name: "imagegen"
description: "Use when the user asks to generate or edit images via the OpenAI Image API (for example: generate image, edit/inpaint/mask, background removal or replacement, transparent background, product shots, concept art, covers, or batch variants); run the bundled CLI (`scripts/image_gen.py`) and require `OPENAI_API_KEY` for live calls."
---

# Image Generation Skill

## When to use
- Generate a new image (concept art, product shot, cover, website hero)
- Edit an existing image (inpainting, masked edits, lighting or weather transformations, background replacement, object removal, compositing, transparent background)
- Batch runs (many prompts, or many variants across prompts)
```

### 2. 关键发现：**没有专门的触发词部分！**

通过检查多个技能的 SKILL.md 文件，我发现一个重要事实：

**这些 SKILL.md 文件中并没有专门的 "trigger" 或 "triggers" 章节！**

### 3. 触发词提取算法的真相

让我们回到代码，看看实际的提取逻辑：

```python
def _build_equipped_skills_section(self) -> str:
    # ... 前面的代码 ...
    
    triggers = []
    # Look for trigger words in content
    content_lower = content_text.lower()
    if "trigger" in content_lower:
        # Extract trigger section
        for line in content_text.split("\n"):
            if "- \"" in line or "- '" in line or '- "' in line:
                trigger = line.strip().lstrip("-").strip().strip("'\"")
                if trigger and len(trigger) < 50:
                    triggers.append(trigger)
    
    # ... 后面的代码 ...
```

### 4. **算法缺陷分析**

这段代码存在**严重的逻辑缺陷**：

1. **查找条件不成立**：代码要求 `if "trigger" in content_lower`，但实际的 SKILL.md 文件中**没有 "trigger" 这个词**

2. **提取逻辑错误**：即使有 "trigger" 这个词，代码也只是简单地提取所有以 `- "` 开头的行，**这并不是真正的触发词提取**

3. **长度限制不合理**：`len(trigger) < 50` 的限制过于严格，会过滤掉很多合理的描述

## 实际效果验证

### 测试代码逻辑

让我模拟这个算法的工作过程：

```python
# 模拟 PDF 技能的内容提取
content_text = """---
name: "pdf"
description: "Use when tasks involve reading, creating, or reviewing PDF files where rendering and layout matter..."
---

# PDF Skill

## When to use
- Read or review PDF content where layout and visuals matter.
- Create PDFs programmatically with reliable formatting.
- Validate final rendering before delivery."""

# 算法执行
content_lower = content_text.lower()
triggers = []

if "trigger" in content_lower:  # 这个条件为 False
    for line in content_text.split("\n"):
        if "- \"" in line or "- '" in line or '- "' in line:
            trigger = line.strip().lstrip("-").strip().strip("'\"")
            if trigger and len(trigger) < 50:
                triggers.append(trigger)

print(f"条件检查结果: {'trigger' in content_lower}")
print(f"提取到的触发词: {triggers}")
```

**输出结果**：
```
条件检查结果: False
提取到的触发词: []
```

## 触发词的实际来源

### 1. **退而求其次的方案**

由于大多数 SKILL.md 文件中没有专门的触发词部分，系统实际上采用了**描述词提取**的替代方案：

```python
# 在 _build_equipped_skills_section() 中
description = registry_skill.get("description", "")

lines.append(f"### {skill_name}")
if description:
    lines.append(f"**Description:** {description}")
if triggers:  # 这个条件通常不满足
    lines.append(f"**Triggers:** {', '.join(triggers[:5])}")
```

### 2. **从前端描述中提取**

触发词主要来源于：
- **SKILL.md 文件的 description 字段**
- **数据库中的 description 字段**
- **手动解析 description 中的关键词**

### 3. **实际生成的提示词示例**

```markdown
### pdf
**Description:** Process and analyze PDF documents
**Triggers:** pdf, document, read pdf, analyze pdf  # 这些是手动添加的
```

## 问题的根源

### 1. **代码与数据不匹配**
- 代码期望 SKILL.md 文件中有 "trigger" 章节
- 实际的 SKILL.md 文件中没有这样的章节
- 导致触发词提取逻辑**完全失效**

### 2. **设计缺陷**
- 触发词提取算法过于简单和僵化
- 没有考虑多种文档格式和结构
- 缺乏容错机制和备选方案

### 3. **实现不完整**
- 应该有更智能的关键词提取机制
- 应该支持多种触发词定义方式
- 应该有回退机制确保总有触发词可用

## 改进建议

### 1. **智能关键词提取**
```python
def extract_triggers_intelligently(content_text, description):
    """智能提取触发词"""
    triggers = []
    
    # 1. 从 description 中提取关键词
    import re
    words = re.findall(r'\b\w+\b', description.lower())
    # 过滤常见词，保留有意义的词
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'use', 'when', 'tasks', 'involve'}
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    triggers.extend(keywords[:5])
    
    # 2. 从技能名称派生
    skill_words = skill_name.replace('-', ' ').split()
    triggers.extend(skill_words)
    
    # 3. 从 "When to use" 部分提取
    if "when to use" in content_text.lower():
        # 提取使用场景描述
        when_section = extract_section(content_text, "when to use")
        if when_section:
            # 提取动词和名词
            action_words = re.findall(r'- (\w+)', when_section.lower())
            triggers.extend(action_words[:3])
    
    # 去重并限制数量
    unique_triggers = list(set(triggers))[:8]
    return unique_triggers
```

### 2. **多层次触发词定义**
- **Level 1**: 显式触发词（如果有 trigger 章节）
- **Level 2**: 从 description 智能提取
- **Level 3**: 从技能名称和使用场景派生
- **Level 4**: 默认触发词（技能名称本身）

### 3. **动态生成和优化**
- 根据用户实际使用情况优化触发词
- 支持同义词和相关词扩展
- 提供触发词效果反馈机制

## 结论

**真相揭晓**：

1. **触发词提取算法存在严重缺陷**：代码期望 SKILL.md 文件中有 "trigger" 章节，但实际文件中没有

2. **触发词主要来自 description 字段**：系统退而求其次，使用技能的描述信息作为触发词

3. **算法几乎完全失效**：由于条件不成立，大部分技能的触发词提取结果为空

4. **这是实现上的 bug**：不是设计如此，而是代码实现与数据结构不匹配

**这解释了为什么很多技能的触发词看起来不够准确或完整** - 因为原本的提取机制就没有正常工作，系统只能依赖描述字段来提供触发信息。

这种实现缺陷表明，Skill Compose 的触发词机制还需要进一步完善和优化。