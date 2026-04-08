# Agent Skill App - 智能体技能应用平台

## 项目概述

Agent Skill App 是一个基于 AgentScope 框架构建的智能体技能管理平台，支持用户创建、管理、使用和分享自定义技能。该应用提供了一个完整的技能生态系统，允许用户通过技能扩展智能体的能力，实现专业化的任务处理。

### 核心特性

- **技能创建与管理**: 提供完整的技能创建、编辑、打包和分发流程
- **多用户支持**: 支持用户隔离的技能管理，每个用户可以拥有自己的技能库
- **智能体集成**: 基于 AgentScope 框架，支持 ReActAgent 智能体
- **文件操作**: 支持文件上传、下载和管理功能
- **沙箱环境**: 提供安全的代码执行环境
- **离线/在线模式**: 支持内网和外网 LLM 调用
- **技能模板**: 提供标准化的技能模板和创建指南

## 项目架构

### 目录结构

```
agent_skill_app/
├── main.py                         # 应用入口（启动器）
├── src/                            # 源代码包
│   ├── app/                        # 应用层
│   │   ├── app.py                  # FastAPI 应用主体
│   │   └── endpoints/              # API 端点定义
│   ├── config/                     # 配置管理层
│   │   └── settings.py             # 环境配置和常量
│   ├── core/                       # 核心业务逻辑层
│   │   ├── agent/                  # 智能体模块
│   │   ├── skill/                  # 技能管理模块
│   │   └── sandbox/                # 沙箱环境模块
│   ├── logger/                     # 日志管理层
│   └── utils/                      # 工具函数层
├── Agent_Work_Dir/                 # 运行时工作目录
│   ├── Skills/                     # 技能存储目录
│   │   ├── common_skills/          # 公共技能（所有用户可用）
│   │   ├── user_skills/            # 用户自定义技能
│   │   └── SkillTemplete/          # 技能模板
│   ├── cache/                      # 技能缓存
│   ├── Files/                      # 用户文件存储
│   └── Uploaded_Skills/            # 上传的技能包
├── logs/                           # 应用日志目录
├── docs/                           # 文档目录
├── pyproject.toml                  # Python 项目配置
├── Dockerfile                      # Docker 容器配置
└── .env.example                    # 环境变量模板
```

### 技术栈

- **后端框架**: FastAPI + AgentScope
- **智能体框架**: AgentScope Runtime
- **依赖管理**: uv + pyproject.toml
- **容器化**: Docker
- **日志系统**: Python logging + RotatingFileHandler
- **文件处理**: aiofiles, python-pptx, pypdf, Pillow 等

## 快速开始

### 环境要求

- Python 3.12+
- uv (Python 包管理器)
- Docker (可选，用于容器化部署)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd agent_skill_app
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置 LLM API 密钥和其他参数
   ```

3. **安装依赖**
   ```bash
   uv sync
   ```

4. **运行应用**
   ```bash
   python main.py
   ```

5. **访问应用**
   - 应用将在 `http://localhost:3000` 启动
   - API 文档: `http://localhost:3000/docs`

### Docker 部署

```bash
# 构建镜像
docker build -t agent-skill-app .

# 运行容器
docker run -p 3000:3000 --env-file .env agent-skill-app
```

## 核心功能

### 1. 技能管理

#### 技能结构
每个技能包含以下结构：
```
skill-name/
├── SKILL.md (必需)
│   ├── YAML frontmatter (元数据)
│   └── Markdown 说明文档
├── scripts/      (可选) - 可执行脚本
├── references/   (可选) - 参考资料
└── assets/       (可选) - 输出资源文件
```

#### 技能创建流程
1. **理解需求**: 分析用户需求，确定技能功能
2. **规划资源**: 确定需要的脚本、参考资料和资源文件
3. **初始化技能**: 使用技能模板创建基础结构
4. **编辑技能**: 编写 SKILL.md 和添加资源文件
5. **打包技能**: 验证并打包为 .skill 文件
6. **迭代优化**: 根据使用反馈进行改进

### 2. 智能体集成

应用基于 AgentScope 框架构建 ReActAgent 智能体，支持：
- **工具调用**: 动态加载技能提供的工具
- **上下文管理**: 智能的上下文压缩和记忆管理
- **多轮对话**: 支持复杂的多轮交互
- **流式响应**: 支持实时流式输出

### 3. 文件管理

- **文件上传**: 支持用户文件上传到个人空间
- **文件下载**: 支持文件下载和技能包下载
- **目录浏览**: 树形结构展示用户文件和技能文件
- **权限控制**: 用户隔离的文件访问权限

### 4. API 接口

#### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/skill_create` | POST | 创建新技能 |
| `/get_user_skills` | GET | 获取用户技能列表 |
| `/skill_use` | POST | 使用指定技能 |
| `/general_conversation` | POST | 一般对话接口 |
| `/upload` | POST | 上传用户文件 |
| `/upload_skill` | POST | 上传技能包 |
| `/download_skill` | GET | 下载技能包 |
| `/get_skill_content` | GET | 获取技能内容 |
| `/list_files` | GET | 列出用户文件 |
| `/list_skill_skeleton` | GET | 列出技能文件结构 |

## 配置说明

### 环境变量

关键配置参数：

```env
# 外网 LLM 配置
ONLINE_BASE_URL="https://api.deepseek.com/v1"
ONLINE_API_KEY="your-api-key"
ONLINE_MODEL_NAME="deepseek-chat"

# 路径配置
SKILLS_PATH="Agent_Work_Dir/Skills"
UPLOAD_PATH="uploads"
SKILLS_CACHE_PATH="Agent_Work_Dir/cache"

# 技能配置
SKILL_CREATOR_NAME="skill-creator"

# 性能配置
STREAM_CHUNK_SIZE=128
REQUEST_TIMEOUT_SECONDS=30
COMPRESS_LIMIT=45
```

### 技能配置

- **公共技能**: 存储在 `common_skills/` 目录，所有用户可用
- **用户技能**: 存储在 `user_skills/<user_id>/` 目录，用户隔离
- **技能模板**: 存储在 `SkillTemplete/` 目录，用于新技能创建

## 使用示例

### 创建新技能

```python
import requests

# 创建技能请求
response = requests.post("http://localhost:3000/skill_create", json={
    "user_id": "user123",
    "session_id": "session456",
    "skill_name": "excel-analyzer",
    "skill_description": "Excel 数据分析技能"
})

print(response.json())
```

### 使用技能

```python
# 使用技能进行对话
response = requests.post("http://localhost:3000/skill_use", json={
    "user_id": "user123",
    "session_id": "session456",
    "skill_name": "excel-analyzer",
    "query": "分析这个Excel文件的数据"
})

print(response.json())
```

### 上传文件

```python
import requests

files = {'file': open('data.xlsx', 'rb')}
data = {
    'user_id': 'user123',
    'session_id': 'session456'
}

response = requests.post("http://localhost:3000/upload", files=files, data=data)
print(response.json())
```

## 开发指南

### 项目结构说明

- **src/app/**: 应用层，包含 FastAPI 应用和端点定义
- **src/config/**: 配置管理，集中管理所有环境变量和常量
- **src/core/**: 核心业务逻辑，包含智能体、技能、沙箱等模块
- **src/logger/**: 日志系统，提供统一的日志记录功能
- **src/utils/**: 工具函数，提供通用的文件操作等工具

### 添加新功能

1. **添加新端点**:
   - 在 `src/app/endpoints/` 下创建新的处理器
   - 在 `src/app/app.py` 中注册端点
   - 更新 `src/app/endpoints/handlers.py` 中的统一处理器

2. **添加新技能**:
   - 参考 `SkillTemplete/` 创建技能结构
   - 编写详细的 SKILL.md 文档
   - 添加必要的脚本和资源文件

3. **扩展智能体功能**:
   - 在 `src/core/agent/` 下添加新的构建器或处理器
   - 在 `src/core/skill/toolkit.py` 中添加新工具

### 测试

```bash
# 运行单元测试
uv run pytest tests/

# 运行集成测试
uv run python tests/integration_test.py
```

## 部署指南

### 生产环境部署

1. **使用 Gunicorn**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:3000 src.app.app:app
   ```

2. **使用 Docker Compose**:
   ```yaml
   version: '3.8'
   services:
     app:
       build: .
       ports:
         - "3000:3000"
       environment:
         - ONLINE_API_KEY=${ONLINE_API_KEY}
       volumes:
         - ./logs:/workspace/logs
         - ./Agent_Work_Dir:/workspace/Agent_Work_Dir
   ```

### 监控和日志

- **日志文件**: `logs/agent_service.log`
- **日志轮转**: 自动轮转，最大 10MB，保留 1 个备份
- **监控指标**: 可通过 `/metrics` 端点获取应用状态

## 常见问题

### Q: 如何调试技能创建问题？
A: 检查日志文件 `logs/agent_service.log`，查看详细的错误信息。确保技能目录结构正确，SKILL.md 文件格式正确。

### Q: 如何配置 LLM？
A: 设置 `ONLINE_BASE_URL`、`ONLINE_API_KEY` 和 `ONLINE_MODEL_NAME`。
### Q: 技能上传失败怎么办？
A: 检查文件名格式，必须为 `SKILL_技能英文名.zip` 格式。确保 zip 文件包含正确的技能目录结构。

### Q: 如何扩展工具集？
A: 在 `src/core/skill/toolkit.py` 中添加新工具，并在 `ToolkitBuilder` 类中注册。

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目基于 MIT 许可证开源。详见 LICENSE 文件。

## 联系方式

- 项目维护者: [维护者姓名]
- 问题反馈: [GitHub Issues]
- 文档更新: [项目 Wiki]

---

**最后更新**: 2026年2月8日  
**版本**: 0.1.0  
**状态**: 开发中