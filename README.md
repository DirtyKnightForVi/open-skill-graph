# open-skill-graph

## 1. 项目定位

open-skill-graph 是一个面向技能化 Agent 执行的后端项目，目标是把“技能元数据管理、会话绑定、沙箱执行、审计追踪”串成完整可运行链路。

仓库包含两套服务：

- 主服务（main.py）：会话请求编排、技能装配、沙箱交互、对话处理。
- Django Registry（django_registry）：技能与版本元数据、会话绑定、审计、分发令牌。

## 2. 当前项目状态（2026-04）

已完成：

- 主服务支持 metadata source 切换（meta / registry / auto）。
- Django Registry 已落地核心模型和 API（Skill、SkillVersion、SessionSkillBinding、AuditLog）。
- 主服务在 registry 模式可写入绑定状态与审计日志。
- 本地技能包仓库（zip）与沙箱装载链路可用。

进行中：

- 分发闭环（下载令牌 + sha256 校验 + 失败审计细化）尚未全部接入主链路。

重点说明（启动依赖）：

- 当前主服务在生命周期里会创建 SandboxService 客户端并启动，因此 main.py 启动前必须先有可访问的 sandbox manager 服务。
- Django Registry 不是强制前置服务，仅当 SKILL_METADATA_SOURCE 使用 registry 或 auto 且配置了 REGISTRY_BASE_URL 时才是前置依赖。
- Redis 建议通过 Docker 启动，默认映射端口 6379；当 SESSION_TYPE=redis 时为前置依赖。

## 3. 代码结构（简版）

```text
.
├─ main.py                         # 主服务入口
├─ sandbox_service.py              # 沙箱管理服务入口
├─ src/
│  ├─ app/                         # AgentApp 应用层
│  ├─ core/
│  │  ├─ skill/                    # 技能管理、metadata client、toolkit
│  │  ├─ sandbox/                  # 沙箱文件与执行辅助
│  │  └─ agent/                    # Agent 构建与处理
│  ├─ config/                      # 环境配置
│  └─ logger/                      # 日志
└─ django_registry/                # Django Registry 服务
```

## 4. 运行要求

- Python >= 3.12
- uv（依赖与运行）
- Docker Desktop / Docker Engine（必须，用于 sandbox manager 后端）

## 5. main.py 启动前的服务顺序（重点）

推荐顺序：

1. 启动 Docker 引擎
2. 启动 sandbox manager（sandbox_service.py，默认 8000）
3. 按需启动 Redis（建议 Docker，默认 6379；SESSION_TYPE=redis 时必需）
4. 按需启动 Django Registry（registry 模式才需要，默认 8001）
5. 启动主服务 main.py（默认 3000）

### 5.1 一次性准备

在仓库根目录执行：

```bash
uv sync
```

建议先准备环境文件：

- 主服务：.env（可参考 .env.example）
- 沙箱服务：sandbox.env

最关键变量：

- ONLINE_BASE_URL / ONLINE_API_KEY / ONLINE_MODEL_NAME
- SANDBOX_SERVICE_URL（默认 http://127.0.0.1:8000）
- SKILL_METADATA_SOURCE（meta|registry|auto）
- REGISTRY_BASE_URL（registry 模式必填）

### 5.2 启动 sandbox manager（必须先于 main.py）

PowerShell（推荐）：

```powershell
uv run --env-file sandbox.env .\sandbox_service.py
```

说明：

- sandbox.env 中默认端口为 8000，CONTAINER_DEPLOYMENT=docker。
- 若服务启动失败，优先检查 Docker 是否可用、镜像是否可拉取/构建。

### 5.3 启动 Redis（建议 Docker）

当你准备使用 Redis 会话（SESSION_TYPE=redis）时，建议使用 Docker 启动：

```powershell
docker run -d --name open-skill-graph-redis -p 6379:6379 redis:7-alpine
```

验证 Redis 端口：

```powershell
Test-NetConnection 127.0.0.1 -Port 6379
```

主服务常见配套环境变量：

- SESSION_TYPE=redis
- REDIS_HOST=127.0.0.1
- REDIS_PORT=6379
- REDIS_DB=0
- REDIS_PASSWORD=（无密码可留空）

### 5.4 启动 Django Registry（按需）

当 SKILL_METADATA_SOURCE=registry（或 auto 且配置 REGISTRY_BASE_URL）时，先启动 Registry：

```powershell
uv run python .\django_registry\manage.py migrate
uv run python .\django_registry\manage.py runserver 0.0.0.0:8001
```

可选：导入 common 技能元数据

```powershell
uv run python .\django_registry\manage.py seed_skills --owner-id common
```

### 5.5 启动主服务 main.py

```powershell
uv run python .\main.py
```

主服务默认监听：3000。

## 6. 三种推荐启动模式

### 模式 A：本地最小可运行（默认）

- SKILL_METADATA_SOURCE=meta
- 可不启动 Django Registry
- SESSION_TYPE=json（可不启动 Redis）
- 必须启动 sandbox manager + main.py

适用：快速联调流程、接口调试、单机开发。

### 模式 B：Registry 集成模式

- SKILL_METADATA_SOURCE=registry
- REGISTRY_BASE_URL=http://127.0.0.1:8001
- SESSION_TYPE=json（可不启动 Redis）
- 需要启动 Django Registry + sandbox manager + main.py

适用：验证绑定状态、审计日志、分发令牌接口。

### 模式 C：Redis 会话模式

- SESSION_TYPE=redis
- 先启动 Redis（推荐 Docker，默认 6379）
- 然后启动 sandbox manager + main.py
- 若同时使用 registry，再加 Django Registry

适用：需要集中式会话状态或多实例共享会话。

## 7. 启动后自检

建议至少确认端口可达：

- 8000（sandbox manager）
- 8001（Django Registry，若启用）
- 3000（main.py）
- 6379（Redis，若启用）

可使用 PowerShell：

```powershell
Test-NetConnection 127.0.0.1 -Port 8000
Test-NetConnection 127.0.0.1 -Port 3000
```

若是 registry 模式，再检查：

```powershell
Test-NetConnection 127.0.0.1 -Port 8001
```

若使用 redis 会话模式，再检查：

```powershell
Test-NetConnection 127.0.0.1 -Port 6379
```

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

## 9. 常见问题

1) uv run .\sandbox_service.py 直接退出（Exit Code 1）

- 常见原因：Docker 未启动、镜像不可用、sandbox.env 未正确加载。
- 处理建议：先确认 Docker Desktop Running，再使用 --env-file 启动 sandbox_service。

2) main.py 启动后请求报沙箱连接错误

- 先确认 SANDBOX_SERVICE_URL 指向的服务可达（默认 127.0.0.1:8000）。

3) skill_use 在 registry 模式下失败

- 检查 REGISTRY_BASE_URL、REGISTRY_TOKEN、Django Registry 是否已启动并完成 migrate。

## 10. 项目文档

- 架构总蓝图：docs/plans/architecture-reset-master-plan.md
- Django 方案：docs/plans/django-skills-registry-plan.md
- 分发后续安排：docs/projects/distribution-followup.md

## 11. 已知限制

- 当前仓库以后端能力为主，不包含完整前端管理系统。
- 分发安全闭环尚未在主链路全部打通。
- 沙箱链路对运行环境（Docker、镜像、网络）依赖较强。
