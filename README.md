# open-skill-graph

## 1. 项目定位

open-skill-graph 是一个面向技能化 Agent 执行的后端项目，目标是把“技能元数据管理、会话绑定、沙箱执行、审计追踪”串成可运行链路。

当前仓库同时包含两部分：

- 主服务：负责会话请求编排、技能装配、沙箱交互与对话处理。
- Django Registry：负责技能与版本元数据、会话绑定、审计与分发令牌接口。

## 2. 当前状态（2026-04）

已完成：

- 主服务已支持 metadata source 切换（meta/registry/auto）。
- Django Registry 已具备基础模型与 API（Skill、SkillVersion、SessionSkillBinding、AuditLog）。
- 主服务在 registry 模式下已接入绑定与审计的基础回写。
- 仓库已去除对历史内网脚本挂载的默认依赖。

进行中：

- 技能分发闭环（下载令牌 + sha256 校验 + 失败审计细化）尚未全量接入主流程。

## 3. 核心能力范围

- 会话级技能装配与卸载。
- 本地技能包（zip）存储、装载与沙箱内注册。
- 基础多用户隔离（session_id + user_id 维度）。
- Registry 中心化管理：
  - 技能与版本查询。
  - 会话绑定状态（pending/mounted/failed/unmounted）。
  - 审计日志写入。
  - 分发下载令牌签发与解析。

## 4. 代码结构（简版）

```text
.
├─ main.py                         # 主服务入口
├─ src/
│  ├─ app/                         # FastAPI/AgentApp 应用层
│  ├─ core/
│  │  ├─ skill/                    # 技能管理、metadata client、toolkit
│  │  ├─ sandbox/                  # 沙箱文件与执行辅助
│  │  └─ agent/                    # Agent 构建与处理
│  ├─ config/                      # 环境配置
│  └─ logger/                      # trace_id 与日志
└─ django_registry/                # Django Registry 服务
   ├─ apps/skills/                 # 模型、序列化、视图、管理命令
   └─ registry_service/            # Django settings/urls
```

## 5. 运行要求

- Python >= 3.12
- uv（依赖与运行命令统一入口）
- Docker（可选，用于沙箱相关镜像和部署）

## 6. 快速启动

### 6.1 安装依赖

```bash
uv sync
```

### 6.2 启动主服务

```bash
uv run python main.py
```

默认端口：3000

### 6.3 启动 Django Registry

```bash
uv run python django_registry/manage.py migrate
uv run python django_registry/manage.py runserver 0.0.0.0:8001
```

### 6.4 可选：初始化技能元数据

```bash
uv run python django_registry/manage.py seed_skills --owner-id common
```

提示：如果本地仓库没有 SKILL_*.zip，会输出提示并退出，不会写库。

## 7. 关键配置

主服务配置位于环境变量（由 src/config/settings.py 读取），常用项如下：

- ONLINE_BASE_URL / ONLINE_API_KEY / ONLINE_MODEL_NAME
- IF_SANDBOX / SANDBOX_TYPE / SANDBOX_SERVICE_URL
- SKILL_METADATA_SOURCE（meta|registry|auto）
- REGISTRY_BASE_URL / REGISTRY_TIMEOUT / REGISTRY_TOKEN
- SKILL_STORAGE_PATH / WORKSPACE_STORAGE_PATH

Registry 配置见 django_registry/registry_service/settings.py，常用项：

- REGISTRY_DB_ENGINE（sqlite|postgres）
- REGISTRY_DB_NAME / REGISTRY_DB_USER / REGISTRY_DB_PASSWORD / REGISTRY_DB_HOST / REGISTRY_DB_PORT
- DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS

## 8. API 概览

主服务（节选）：

- POST /skill_create
- POST /skill_use
- GET /get_user_skills
- POST /general_conversation
- POST /session/start
- POST /process

Django Registry（节选）：

- GET /api/v1/skills/resolve?owner_id=<id>&skill_name=<name>
- GET /api/v1/skills/common/
- POST /api/v1/session-bindings/
- PATCH /api/v1/session-bindings/{id}/
- POST /api/v1/audit/
- POST /api/v1/distribution/issue-download-token
- POST /api/v1/distribution/resolve-download-token

## 9. 项目文档

- 架构总蓝图：docs/plans/architecture-reset-master-plan.md
- Django 方案：docs/plans/django-skills-registry-plan.md
- 分发后续安排（暂缓记录）：docs/projects/distribution-followup.md

## 10. 已知限制

- 当前仓库以后端能力为主，不包含完整前端管理系统。
- 分发安全闭环尚未在主链路全部打通（已完成接口与部分回写基础）。
- 沙箱相关能力依赖运行环境中的对应镜像与服务可达性。
