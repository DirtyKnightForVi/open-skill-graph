# open-skill-graph 产品化差距分析

> 分析日期：2026-05-13
> 视角：架构师 + 产品经理
> 状态：仅分析，不修改源码

---

## 一、项目现状画像

```mermaid
graph TB
    subgraph "当前已具备"
        A[主服务 main.py :3000] --> B[技能装配]
        A --> C[沙箱编排]
        A --> D[对话处理]
        E[(Django Registry :8001)] --> F[技能元数据CRUD]
        E --> G[版本管理]
        E --> H[会话绑定]
        E --> I[审计日志]
        E --> J[下载令牌]
        K[Sandbox Manager :8000] --> L[Docker容器管理]
        K --> M[文件系统操作]
        K --> N[Shell/Python执行]
        O[Redis :6379] --> P[会话状态存储]
        Q[LLM API] --> A
        R[本地技能包仓库 zip] --> A
    end
```

**已具备的核心能力：**
- 技能元数据的注册、版本化管理（Django Registry）
- 会话绑定与审计追踪
- Docker 沙箱隔离执行
- ReActAgent 计划型智能体（含 7 步技能创建流水线）
- 多模式运行（meta/registry/auto，json/redis 会话）
- 技能文件的上传、下载、编辑、列表
- 启动前依赖检查（preflight check）

---

## 二、目标产品画像（应达到的状态）

```mermaid
graph TB
    subgraph "接入层"
        GW[API Gateway]
        SDK[多语言 SDK]
        WEB[管理控制台 Web UI]
    end
    subgraph "核心服务层"
        MAIN[主服务]
        REGISTRY[元数据注册中心]
        SANDBOX[沙箱管理]
    end
    subgraph "平台能力层"
        AUTH[统一认证 OAuth2/JWT/RBAC]
        BILLING[用量计量 计费/配额]
        MARKET[技能市场 发现/评价/协作]
        GOVERN[治理中心 审批/合规/策略]
        ANALYTICS[分析平台 使用统计/质量监控]
        NOTIFY[通知中心 Webhook/消息推送]
    end
    subgraph "基础设施层"
        DB[(PostgreSQL)]
        CACHE[(Redis 缓存/队列)]
        OSS[(对象存储 S3)]
        MQ[消息队列]
        LOG[可观测性平台]
    end
    GW --> MAIN
    GW --> REGISTRY
    SDK --> GW
    WEB --> GW
    MAIN --> SANDBOX
    MAIN --> LOG
    REGISTRY --> DB
    REGISTRY --> OSS
    SANDBOX --> OSS
```

---

## 三、差距全景图

### 3.1 架构维度

#### 安全防护（🔴 最紧迫）

```mermaid
flowchart LR
    subgraph "当前状态（无防护）"
        C1[任意客户端] -->|HTTP 明文| C2[主服务 :3000]
        C1 -->|HTTP 明文| C3[Registry :8001]
        C2 -->|无认证| C4[Sandbox :8000]
    end
    subgraph "目标状态（纵深防御）"
        T1[客户端] -->|HTTPS + JWT| T2[API Gateway]
        T2 -->|mTLS| T3[主服务]
        T2 -->|mTLS| T4[Registry]
        T3 -->|mTLS| T5[Sandbox]
    end
```

| 缺失项 | 严重度 | 当前表现 | 建议方案 |
|--------|:---:|----------|----------|
| API 认证 | 🔴 | 所有端点无需认证即可访问 | JWT + API Key 双模式 |
| 服务间鉴权 | 🟡 | sandbox/registry 无鉴权 | mTLS 或 shared secret |
| 传输加密 | 🟡 | 全链路 HTTP 明文 | TLS termination at gateway |
| 权限模型 | 🔴 | 无 RBAC | 基于 owner_id 的 ACL + RBAC |
| 密钥管理 | 🟠 | API Key 明文在 .env | 引入 Vault/KMS |
| 下载令牌 | 🟡 | 已实现但未接入主链路 | 完成分发闭环集成 |

#### 可观测性（🔴 运维盲区）

```
当前日志格式：
2026-05-13 10:00:00 - INFO - trace_abc123 - Built agent 'SKILL_AGENT_APP' with toolkit

缺失：
✗ 结构化日志（JSON 格式，可被 ELK/Loki 索引）
✗ 指标暴露（/metrics 端点，Prometheus 格式）
✗ 分布式追踪（OpenTelemetry 集成）
✗ 健康检查（/healthz, /readyz, /livez）
✗ 告警规则（错误率、延迟、沙箱可用性）
✗ 审计日志持久化策略（目前仅 Registry 有基础实现）
```

#### 数据架构（🟠 生产就绪差距）

| 问题 | 影响 |
|------|------|
| SQLite 不支持并发写入 | 无法支撑多实例部署 |
| 技能包存储在本地文件系统 | 无法跨实例共享，无备份 |
| 无数据库连接池管理 | 连接泄漏风险 |
| 无读写分离 | 报表查询影响在线业务 |
| 无数据备份恢复机制 | 灾难性数据丢失风险 |

#### 可靠性（🟡 故障场景薄弱）

```mermaid
flowchart TB
    START[请求进入] --> SB{沙箱可用?}
    SB -->|否| CRASH[主流程崩溃 无降级]
    SB -->|是| LLM{LLM API 可用?}
    LLM -->|否| TIMEOUT[超时无重试 无熔断保护]
    LLM -->|是| REG{Registry 可用?}
    REG -->|否| FALLBACK[仅 meta 源有 fallback]
    REG -->|是| OK[正常流程]
```

缺失的韧性模式：熔断器/重试策略/优雅关闭/限流/沙箱TTL回收/降级方案

#### 工程化（🟡）

- 无 CI/CD 流水线
- 无自动化测试体系（仅一个手工测试脚本 test/test_api.py）
- 无容器化编排（K8s）
- 无 GitOps 部署方案

#### 代码质量（🟡 结构性债务）

- **Manager 类 828 行**：承担会话管理+技能关联+元数据获取+绑定管理+审计回写等过多职责
- **app.py**：端点定义、ProcessContext、文件上传/下载逻辑混在一起
- **service.py**：文件头注释为乱码（编码问题）
- **硬编码路径散布**：/workspace/skill/、/workspace/upload/ 出现在多处
- **mock.py**：装饰器与生产逻辑耦合，测试数据加载依赖本地文件
- **REACT_MAX_ITERS**：默认值 31 但 .env.example 设为 17，不一致
- **无统一异常处理层**：各层 try/except 返回格式不一致

---

### 3.2 产品维度

#### 用户体系（🔴）

- 无用户注册/登录
- 无组织/团队管理
- 无角色权限分配
- 无 SSO 集成

#### 技能市场（🔴 完全空白）

- 无技能发现/搜索
- 无技能分类/标签
- 无技能评价/打分
- 无使用热度排行
- 无技能依赖声明

#### 协作开发（🔴）

- 无技能 Fork/Clone
- 无协作编辑
- 无变更审批流
- 无版本对比 Diff

#### 运营管理（🟠）

- 无用量仪表盘
- 无配额/计费
- 无 SLA 承诺
- 无租户管理后台

#### 开发者体验（🟠）

- 无 API 文档门户（Swagger/Redoc）
- 无多语言 SDK
- 无交互式 Playground
- 无 Quick Start 教程
- 无技能模板库
- 无沙箱模板市场

#### 合规治理（🟡）

- 无数据留存策略
- 无审计报表导出
- 无合规认证（SOC2/GDPR）
- 无导出/导入迁移工具

---

## 四、竞争对比

| 维度 | open-skill-graph | OpenAI GPTs | Dify | Coze |
|------|:---:|:---:|:---:|:---:|
| 技能执行引擎 | ✅ 沙箱隔离 | ✅ 服务端 | ✅ Docker | ✅ 服务端 |
| 版本管理+审计 | ✅ 差异化优势 | ❌ | ✅ 基础 | ❌ |
| 用户体系 | ❌ | ✅ | ✅ | ✅ |
| 多租户 | ❌ | ✅ | ✅ | ✅ |
| 技能市场 | ❌ | ✅ GPT Store | ✅ | ✅ |
| 管理控制台 | ❌ | ✅ | ✅ | ✅ |
| SDK | ❌ | ❌ | ✅ | ✅ |
| 计费 | ❌ | ✅ | ✅ | ✅ |
| 团队协作 | ❌ | ❌ | ✅ | ✅ |
| 开源 | ✅ | ❌ | ✅ | ❌ |

**定位建议：** 差异化优势在于**企业级技能治理**（审计、版本、分发令牌、沙箱隔离）。应围绕此优势补齐周边体验。

---

## 五、分阶段产品化路线图建议

```mermaid
gantt
    title 产品化路线图（建议）
    dateFormat  YYYY-MM
    axisFormat  %Y-%m
    section P0 安全基线
    API认证鉴权 JWT       :p0a, 2026-06, 2026-07
    服务间mTLS           :p0b, 2026-07, 2026-08
    RBAC权限模型          :p0c, 2026-07, 2026-08
    传输加密 HTTPS        :p0d, 2026-06, 2026-06
    section P1 可运维性
    健康检查+指标暴露      :p1a, 2026-06, 2026-07
    PostgreSQL迁移        :p1b, 2026-07, 2026-08
    结构化日志+追踪       :p1c, 2026-08, 2026-09
    CI/CD流水线           :p1d, 2026-08, 2026-09
    section P2 产品体验
    用户管理系统           :p2a, 2026-09, 2026-10
    管理控制台 Web UI     :p2b, 2026-10, 2026-12
    API文档门户 Swagger   :p2c, 2026-09, 2026-10
    技能搜索与发现         :p2d, 2026-10, 2026-11
    section P3 生态建设
    Python SDK           :p3a, 2026-11, 2026-12
    技能市场              :p3b, 2026-12, 2027-02
    多租户隔离            :p3c, 2027-01, 2027-03
    section P4 商业化
    计费/配额             :p4a, 2027-03, 2027-04
    协作开发              :p4b, 2027-04, 2027-06
    合规认证              :p4c, 2027-05, 2027-08
```

---

## 六、技术架构演进目标

```mermaid
flowchart TB
    subgraph "外部"
        USERS[终端用户]
        DEV[开发者]
    end
    subgraph "接入层"
        GW[API Gateway Kong/APISIX]
        PORTAL[开发者门户 Swagger]
        CONSOLE[管理控制台 React/Vue]
    end
    subgraph "核心服务"
        MAIN_SVC[主服务 FastAPI + AgentScope]
        REG_SVC[元数据服务 Django + DRF]
        SB_SVC[沙箱管理 AgentScope Runtime]
        TASK_SVC[异步任务 Celery]
    end
    subgraph "中间件"
        PG[(PostgreSQL 主从)]
        REDIS_CLUSTER[(Redis Cluster)]
        S3_STORE[(MinIO/S3)]
        MQ[RabbitMQ/Kafka]
    end
    subgraph "可观测性"
        LOKI[Loki 日志]
        PROM[Prometheus 指标]
        TEMPO[Tempo 追踪]
        GRAFANA[Grafana 仪表盘]
        ALERT[AlertManager 告警]
    end
    USERS --> GW
    DEV --> PORTAL
    DEV --> CONSOLE
    GW --> MAIN_SVC
    GW --> REG_SVC
    MAIN_SVC --> SB_SVC
    MAIN_SVC --> REDIS_CLUSTER
    MAIN_SVC --> MQ
    MAIN_SVC -.-> LOKI
    MAIN_SVC -.-> PROM
    MAIN_SVC -.-> TEMPO
    REG_SVC --> PG
    REG_SVC --> S3_STORE
    SB_SVC --> S3_STORE
    TASK_SVC --> MQ
    TASK_SVC --> PG
    LOKI --> GRAFANA
    PROM --> GRAFANA
    PROM --> ALERT
    TEMPO --> GRAFANA
```

---

## 七、数据模型演进

```mermaid
erDiagram
    Skill ||--o{ SkillVersion : has
    Skill ||--o{ SkillPermission : has
    SkillVersion ||--o{ SessionSkillBinding : bound_to
    SkillVersion ||--o{ DownloadToken : issues
    Skill ||--o{ SkillReview : reviewed
    Skill ||--o{ SkillTagMap : tagged
    SkillTag ||--o{ SkillTagMap : tagged
    
    Skill {
        uuid id PK
        string owner_id
        string name
        string display_name
        string description
        enum visibility
        enum status
        datetime created_at
    }
    
    SkillVersion {
        uuid id PK
        uuid skill_id FK
        string version
        string artifact_uri
        string artifact_sha256
        bool is_active
    }
    
    SessionSkillBinding {
        uuid id PK
        string session_id
        string user_id
        uuid skill_version_id FK
        string mounted_path
        enum status
    }
    
    AuditLog {
        uuid id PK
        string trace_id
        string actor_id
        string action
        string target_type
        string target_id
        enum result
        json detail
    }

    User {
        uuid id PK
        string username
        string email
        string password_hash
        enum status
    }
    
    Organization {
        uuid id PK
        string name
        string slug
        enum plan_tier
    }
    
    SkillReview {
        uuid id PK
        uuid skill_id FK
        uuid user_id FK
        int rating
        string comment
    }
    
    SkillTag {
        uuid id PK
        string name
        string category
    }
    
    SkillTagMap {
        uuid skill_id FK
        uuid tag_id FK
    }
    
    UsageRecord {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        uuid skill_version_id FK
        int tokens_used
        int duration_ms
    }
    
    BillingQuota {
        uuid id PK
        uuid org_id FK
        string resource_type
        int limit_value
        int used
    }
```

> 上半部分（Skill ~ AuditLog）为现有模型，下半部分（User ~ BillingQuota）为建议新增。

---

## 八、关键决策建议

### 立即需要做的（阻止性）

| # | 事项 | 理由 |
|---|------|------|
| 1 | 添加 API 认证层（至少 API Key） | 当前任何人都可以直接调用所有接口 |
| 2 | 添加健康检查端点 /healthz | 无健康检查，负载均衡器/K8s 无法工作 |
| 3 | 迁移 Registry 数据库到 PostgreSQL | SQLite 在并发写入和生产环境不可靠 |
| 4 | 完成分发闭环（sha256 + 令牌接入） | 技能包可能被篡改，缺少安全校验 |

### 短期应做的（竞争力）

| # | 事项 | 理由 |
|---|------|------|
| 5 | 实现用户注册/登录 + RBAC | 没有用户体系，无法区分不同用户/租户 |
| 6 | 构建管理控制台（最小可用） | Django Admin 不够，需要面向租户的界面 |
| 7 | 技能搜索与标签分类 | 技能多了以后，没有搜索等于不可用 |
| 8 | 统一错误码 + API 文档门户 | 开发者集成的第一道门槛 |

### 中期规划的（生态壁垒）

| # | 事项 | 理由 |
|---|------|------|
| 9 | 多租户隔离 | 企业客户的核心需求 |
| 10 | 技能市场 + 评价体系 | 形成技能生态飞轮 |
| 11 | 审批工作流 | 企业合规的刚性需求 |
| 12 | Python SDK | 降低集成门槛 |

---

## 九、风险清单

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:---:|:---:|----------|
| 未授权访问导致数据泄露 | 高 | 严重 | P0 优先添加认证 |
| SQLite 并发写入损坏 | 中 | 严重 | 尽快迁移 PostgreSQL |
| Docker 依赖导致部署复杂 | 高 | 中 | 提供 docker-compose + K8s helm chart |
| 技能包本地存储单点故障 | 中 | 高 | 迁移到 S3/MinIO |
| 无监控导致故障发现延迟 | 高 | 中 | 接入 Prometheus + Grafana |
| AgentScope 框架升级不兼容 | 中 | 中 | 锁定版本 + 升级前集成测试 |
| LLM API 厂商锁定 | 低 | 中 | 保持 OpenAI 兼容接口抽象 |

---

## 十、总结

**open-skill-graph 当前处于「技术验证到产品化」的过渡阶段。**

- **做对了什么：** 核心链路（元数据 → 沙箱 → 执行 → 审计）架构合理，版本化、审计、分发令牌的设计有企业级基因
- **还差什么：** 安全防护几乎为零，可观测性空白，数据层未达到生产标准
- **缺失什么：** 完整的用户体系、管理界面、技能市场、开发者生态、计费系统

**一句话：这个项目有一个坚实的「引擎」，但现在还没有「车身」、「方向盘」和「仪表盘」。**

---

> 本文档由 DeepSeek TUI 生成。分析基于 2026-05-13 代码快照。所有 mermaid 图表可在支持 mermaid 渲染的 Markdown 阅读器中查看。
