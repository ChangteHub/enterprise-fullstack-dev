---
name: enterprise-fullstack-dev
description: >-
  企业级全栈 Web 应用的搭建、重构与部署工作流。当用户要创建或开发全栈项目、前后端分离工程、
  React+TypeScript+Vite 前端、Spring Boot/Java 后端、MySQL 数据库，或提到全栈目录结构、分层架构、
  REST API、CRUD、JWT/RBAC 登录权限、Docker、Docker Compose、Nginx、反向代理、HTTPS、VPS/云服务器部署、
  CI/CD、数据库迁移、Redis/MQ/ES 选型、Kubernetes、微服务拆分、生产级/企业级工程规范时使用。
  也适用于"帮我把 React 前端和 Java 后端部署到服务器""给 Spring Boot 项目加 Docker 和 Nginx"
  "设计学生管理系统前后端结构""我的网站需要 Redis 吗"等自然说法。对项目级/跨层 Web 工程任务进行
  架构、实现、验证与部署；对单函数、单文件或纯算法任务不套用完整流程。默认先用最小可用技术栈跑通业务，
  只有存在真实问题时才引入 Redis、消息队列、ES、微服务、Kubernetes。不适用于纯算法题、单文件代码润色、
  与 Web 全栈无关的编程任务。
compatibility: 需要可读写的项目工作区；涉及构建/部署任务时需要 Node、Java(Maven)、Docker 等对应工具链。
version: 3.1.1
---

# Skill: enterprise-fullstack-dev（v3.1.1 冻结版）

> **定位**：轻量的"项目操作系统"，不是知识手册。生命周期：**先认识项目 → 只问必须决定的事 → 冻结决策 → 蓝图骨架 → 按模块实现 → 持续卫生 → 可验证交付**。
> SKILL.md 是控制流（思考与流程）；references/ 按阶段加载（知识）；scripts/ 确定性执行层（只检查不修改）；assets/ 可复用模板；evals/ 证明 Skill 自身有效。

## Trigger / Not-Trigger（触发边界）

**应触发**：创建全栈项目、前后端分离、重构已有全栈项目、设计全栈目录、分层架构、REST API、JWT/RBAC、Docker/Nginx 部署、VPS/云上生产部署、CI/CD、DB migration、Redis/MQ/ES/K8s 选型判断、项目结构审计。
**不应触发**：纯算法题、单个文件/函数润色、与 Web 全栈工程无关的任务——直接做，不套本 Skill。

## Task Depth（先定 Scope）与 Task Mode（先定路径）

| Scope | 典型任务 | 行为 |
|-------|---------|------|
| L0 单点 | 改一个函数、润色一个文件 | 不走本流程，直接处理 |
| L1 单层 | 只改 React 页面、只写一个 Controller | 只加载对应 reference，不走全局 Gate |
| L2 跨层 | React+Spring 对接、API+DB、Docker+Nginx | 走核心流程，按需加载 |
| L3 项目级 | 新建/重构全栈项目、生产部署、架构拆分 | 完整走状态机全流程 |

**Scope 定了还不够，必须定 Mode**（决定走哪条流水线，禁止所有任务共用一条）：

| Mode | 触发场景 | 第一步 | 核心流程 | 禁止 |
|------|---------|--------|---------|------|
| **CREATE** | 新建项目 | Initialization | Decision → Blueprint → Scaffold → Implement → Verify → Deploy | 先写业务再补目录 |
| **REFACTOR** | 改造已有项目 | **Discover + Audit**（inspect-project → PROJECT AUDIT） | Baseline → Gap（check-project-gap）→ Refactor Plan → Incremental Change → Regression | 按理想模板重写、无视现有体系 |
| **FEATURE** | 已有项目加功能 | 轻量 Recon | Impact Analysis → Decide → Implement → Test → Hygiene | 重新设计整个项目 |
| **DEPLOY** | 部署上线 | Environment Recon | Preflight → Build → Config → Deploy → Health → Evidence | 把"配置写好"当"部署成功" |
| **AUDIT** | 审查/评估 | 只读 Recon | Inventory → Hygiene → Security → Architecture → Report | 默认不修改项目 |

## 生命周期状态机（每个状态定义：进入条件 / 允许动作 / 退出条件 / 必需证据）

统一状态词，按 Mode 分叉（各模式入口/必经阶段/禁止行为不同）：

```
CREATE   INIT → INITIALIZE → DECIDE → RECORD → BLUEPRINT → SCAFFOLD → VALIDATE
              → IMPLEMENT → VERIFY → INTEGRATE → RELEASE
REFACTOR INIT → DISCOVER → AUDIT → HYGIENE → GAP → PLAN → RECORD → CHANGE
              → REGRESSION → RELEASE
FEATURE  INIT → LIGHT-RECON → IMPACT → MICRO-DECISION → IMPLEMENT → TEST
              → HYGIENE → RELEASE
DEPLOY   INIT → ENV-RECON → PREFLIGHT → BUILD → CONFIG → DEPLOY → HEALTH
              → EVIDENCE → RELEASE
AUDIT    INIT → READONLY-RECON → HYGIENE → SECURITY → ARCHITECTURE → REPORT
```

关键硬门禁（Gate，未过不得推进）：

| Gate | 退出条件（机器可查） |
|------|--------------------|
| RECORD | `validate-decision-record.py` PASS（status=confirmed、字段齐全）；DRAFT 阻断 |
| VALIDATE_SCAFFOLD | `validate-project` PASS + hygiene 无 CRITICAL/ERROR |
| IMPLEMENT 期间 | hygiene WARN 只进 Queue 不阻塞；CRITICAL/ERROR 即停 |
| FINAL_HYGIENE | Queue 已呈报用户；CRITICAL/ERROR=0 |
| RELEASE_CHECK | 全部 validator + eval runner 通过；证据齐全 |

- 每次状态推进都要在最终汇报的 State Transition 字段留下轨迹

## Layer -1: Project Initialization（收集会影响结构的初始化信息）

**提问方式**：先扫描已有项目/读取现有配置，只询问**无法可靠自动发现且会改变架构**的决策；新项目才做完整问卷。不确定时按最小可行方案兜底（单体+单前端+MySQL），并写入 Assumptions。

| 决策域 | 何时必答 | 典型问题 | 输出字段 |
|--------|---------|---------|---------|
| 项目类型 | 永远 | 新建/改造/加功能/部署 | Project Mode |
| 代码组织 | 新建 | 单仓库 / monorepo / 多仓库 | Repository |
| 前端 | 新建 | 单前端 / 用户端+后台 / 多端 | Frontend |
| 后端 | 新建 | 单体 / 模块化单体 / 微服务 | Backend |
| 语言框架 | 新建或迁移 | React+TS+Vite；Java+Spring Boot | Tech Baseline |
| 数据 | 涉及数据 | MySQL / PostgreSQL；迁移策略 | Database |
| 认证授权 | 有登录才问 | 无 / JWT / OIDC / OAuth2 | Auth |
| 工程化 | 项目级 | CI/CD 是否需要、哪家 | CI/CD |
| 可观测性 | 项目级/生产 | 无 / 日志 / Metrics / Tracing | Observability |
| 高级组件 | 按需求问 | Redis / MQ / ES / K8s（默认不引入） | Advanced |
| 部署 | 涉及部署 | 本地 / VPS / 云 / K8s | Deployment |
| 特殊需求 | 按场景问 | 上传、WebSocket、定时任务、支付 | Constraints |

## Decision Record：从"问过"变成"项目状态"

编码前先落**项目文件**（非聊天记录），后续一切模块开发引用同一份：

```markdown
<!-- docs/architecture/decision-record.md -->
Project Mode: CREATE / REFACTOR / FEATURE / DEPLOY / AUDIT
Repository: single-repo / monorepo        Frontend: ...
Backend: ...                              Database: ...（迁移方式）
Auth: ...（无登录写 N/A）                  CI/CD: ...
Observability: ...                        Advanced: ...（默认"暂不引入"）
Deployment: ...
Assumptions: 列出全部默认假设
Status: CONFIRMED / DRAFT（DRAFT 不得进入 SCAFFOLD）
```

**机器可读状态（v3.1.1 硬门禁）**：同时维护 `.decision/project-decision.yaml`（格式见 `.decision/schema.yaml`），
含 `decision_id`（稳定标识）与 `revision`（Re-open 递增）。`validate-decision-record.py` 校验：
文件缺失 / status=draft / 必填字段缺失 / md 与 yaml 状态不一致 → **BLOCKED**（阻断 BLUEPRINT 及之后全部状态）。

**三态语义**（解决"缺信息停工"与"擅自危险决策"的两难）：

| 状态 | 含义 | 允许 | 禁止 |
|------|------|------|------|
| DRAFT | 关键决策尚未形成 | 收集信息、生成问题 | Scaffold、一切实现 |
| ASSUMED | 按最小方案作出明确假设 | Blueprint、Scaffold、本地构建测试 | 生产部署、Remote Side Effect、高风险迁移 |
| CONFIRMED | 开发者已确认 | 完整正常流程 | 无（仍受 P0/Stop/Evidence 约束） |

yaml 是状态源，md 是人读镜像；md/yaml 状态不一致时 validator 阻断并要求同步。

- L2/L3 必须有；L1 可省略。自主执行（无人可答）时：按兜底默认生成、Status 标 DRAFT、逐条列入 Assumptions，并在最终汇报请用户追认——**不因信息缺失停工，也不擅自升级复杂架构**
- **Re-open 规则**：新事实导致原决策失效时，说明新事实 → 重新决策 → 更新 md+yaml 并记录变更原因
- **初始化必答 UX Surface Matrix**（frontend.ux_surface 字段）：用户端/管理后台 × 移动/桌面 逐个表态支持与否；
  不支持可以是合理产品决策，但必须显式记录——测试按矩阵选 viewport，禁止测试时临时换尺寸"让测试通过"

## Project Recon：已有项目先认识再修改（REFACTOR/FEATURE 必做）

第一步不是设计理想架构，而是建立当前状态快照（运行 `scripts/inspect-project.py`）：

```
detect 前端/后端技术栈 → DB/迁移 → Docker/Compose/Nginx → CI/CD → 可观测性
→ Git 状态/包管理器 → 可疑文件 → 产出 PROJECT BASELINE（Risks/Open Questions/Unknowns）
```

**不要强行统一**：已有项目用 MyBatis-Plus、Gradle、Vue、PostgreSQL 等，只要符合目标与约束，优先保持现有体系——不为匹配 Skill 模板做无意义重构（数据访问层叫 mapper 还是 repository 都合法）。

## Directory Blueprint：先施工图，再写代码

提问结束后、业务代码前，输出目录蓝图并创建**空骨架**，通过 validator 后才进入 Implementation——AI 不允许一边写功能一边发明目录。

蓝图必须回答：**边界**（每个目录负责什么）、**必备项**（按所选模式）、**禁止项**（哪些目录不能出现）、**扩展点**（未来 Redis/MQ/监控从哪里接入）、**环境**（dev/staging/prod 配置放哪）、**验证**（如何证明蓝图正确）。

## Project Hygiene：持续保持项目干净（四级严重度 + Queue）

目录会随迭代变脏。运行 `scripts/check-project-hygiene.py`，时机：**初始化前 / 每个阶段后 / 发布前**。

| 级别 | 例子 | 处理 |
|------|------|------|
| Allowed / INFO | frontend/ docs/；.claude/ 等工具配置 | PASS / INFO |
| WARN（Hygiene Queue） | tmp/ old-backend/ test2/ 孤儿文件、Artifact 入库 | **不阻断**，阶段收尾一次性呈报用户批量裁决 |
| ERROR | 可执行/构建产物被 git 跟踪 | 阻断 |
| CRITICAL | .env 被跟踪、私钥、凭据 | 阻断 |

**Artifact Policy**：测试截图/coverage/临时报告/日志归属 CI Artifacts 或临时目录，不入源码仓库；正式文档与 fixtures 入 Git。
**绝不自动删除**：WARN 项给证据（是什么/多大/最后修改），由人批量裁决。详见 references/quality/hygiene.md。
**Queue 持久化（v3.1.1）**：`check-project-hygiene.py --queue docs/quality/hygiene-queue.json` 把 WARN 写入
`{path, severity, reason, first_seen, status}`，消失的条目自动标 resolved——Queue 属于项目治理状态，不活在聊天上下文里。

**测试数据生命周期（v3.1 硬规则）**：测试账号/数据只能来自 `scripts/seed-test-data.sh`（幂等+环境保护+入 Git 可评审），
配对 `reset-test-data.sh` / `verify-test-data.sh`；**生产环境禁止 ad-hoc SQL 创建测试账号**。
管理员等凭据遵循六阶段生命周期（references/security/credentials.md）：生成→受控交付→首登改密→轮换→恢复→审计，
**禁止"随机生成只打印一次日志"作为唯一交付方式**。

## Layer 1: Core Principles（P0 Safety → P1 Correctness → P2 Operability → P3 Maintainability → P4 Optimization）

规则冲突时低优先级让位高优先级；"更企业级"永远不能推翻 P0/P1；任何 PASS 优先服从 Evidence Policy——没有证据宁写 PARTIAL/Unverified。

1. **Minimal Stack First（P3）**：单体+分层+MySQL+Docker+Nginx 能做绝大多数项目，不为炫技引入 Redis/K8s/MQ
2. **Versioned Iteration（P3）**：v1 登录+CRUD → v2 JWT+RBAC+Docker → v3 CI/CD → v4 MQ/通知 → v5 监控 → v6 微服务；每版可运行
3. **Config != Code（P0）**：密码/密钥走环境变量，`.env` 不提交 Git，`.env.example` 提交
4. **Secure by Default（P0）**：宿主机发布端口默认绑 `127.0.0.1`；容器内服务按容器网络需要监听（如 `0.0.0.0`）——保护来自端口绑定与 Nginx 唯一入口，不是让容器内进程监听 127.0.0.1；公网只开业务真正需要的端口，管理入口走安全组/VPN/来源限制；HTTPS 强制；SQL 参数化；BCrypt
5. **Deploy != Copy Files（P2）**：部署=准备→构建→配置→启动→暴露→连DB→安全→验证→监控→回滚

## Layer 2: Tech Stack（基线版本）

Frontend: React 18 + TypeScript + Vite · UI: Ant Design 或 Tailwind · HTTP: Axios
Backend: Java 21 + Spring Boot 3.x 分层 · Database: MySQL 8 + Flyway · Deploy: Docker Compose + Nginx · CI: GitHub Actions

版本策略：大版本为基线不随意跨；发现本地实际版本与基线冲突时以本地可运行版本为准并说明差异；**升级语言大版本属于方向性决策，须进入 Decision Record**。兼容矩阵见 references/compatibility.md。

## Layer 3: Request Flow（请求链路与三边界）

`pages/ → services/(HTTP) → Controller(校验) → Service(业务) → repository(mapper)(数据) → MySQL(Flyway) → Result<DTO> 返回`。代码位置与各层职责见 references/backend/structure.md、references/frontend/structure.md。

- **事务边界**：先定业务原子性再决定 `@Transactional`，只加 Service 层；读多写少用 readOnly；跨服务调用不共享本地事务；慢操作不包进事务
- **鉴权边界**：认证在 Filter/Security 层；授权在 Controller/Service 入口；业务层不重复登录校验
- **失败路径**：前端失败有提示兜底；后端抛 BusinessException → 全局异常转标准错误 JSON；DB 失败回滚；外部依赖不可用要降级或明确报错，不静默吞

> 命名警示：前端 `services/`=HTTP 通信层；后端 `service/`=业务逻辑层。名字相似，职责完全不同。

## Layer 4: Project Structure（按蓝图模式选择）

```
1 前端+单体后端   → Mode A: frontend/ + backend/（默认，学生/小团队）
多前端+单体后端   → Mode A+: apps/ + backend/ + packages/
边界混乱+并行开发冲突 → 先模块化单体 references/architecture/modular-monolith.md，再考虑微服务 Mode B
```

禁止：①给学生 CRUD 直接上微服务；②Mode A 里同时出现 `apps/` 和 `frontend/`；③混用 `service/`（后端业务层）与 `services/`（前端 HTTP 层）的职责。目录细节见 references/architecture/monolith.md（Mode A 全套根目录文件）、references/architecture/monorepo.md（Mode B）。

## Validator Philosophy：上下文感知，不是字符串命中

校验器的目标是判断"**是否有足够证据支持 PASS**"，不是"看起来像符合规范"。无法可靠判断时输出 WARN/UNVERIFIED，不为绿灯猜测：

| Script | v3.0 判定策略 |
|--------|--------------|
| `inspect-project.py` | 只读侦察产出 **PROJECT AUDIT**（Facts/Risks/Next Actions）；信息类，不定级不阻断 |
| `check-project-hygiene.py` | Git tracked 优先；CRITICAL/ERROR/WARN(Queue)/INFO 四级；Artifact Policy；只检测绝不删除 |
| `validate-decision-record.py` | 决策门禁：yaml 缺失/status≠confirmed/字段缺失 → BLOCKED |
| `check-project-gap.py` | 项目事实 vs 决策目标状态 → HIGH/MEDIUM/LOW 差距 + 最小改造动作 |
| `seed/reset/verify-test-data.sh` | 测试数据生命周期：幂等播种/清理/就位校验，环境保护（仅本地 loopback 容器） |
| `run-trigger/functional/regression/hygiene-eval.py` | Skill 自评估执行器：结构校验 + machine_checks（validator/文件断言/输出断言），行为类如实标 MANUAL |
| `validate-project.py` | 模式感知分层判定：数据访问接受 repository/mapper/dao，传输对象接受 dto/vo/model，异常接受 exception/common；构建文件接受 pom/gradle |
| `check-security.py` | Git 跟踪状态优先（未跟踪降 WARN）；测试 fixture 自动识别降 WARN；行内 `security-allowlist` 例外声明；占位值放行 |
| `check-db-schema.py` | 按版本序重放迁移（CREATE/ALTER/DROP/INDEX），对**最终 schema** 做必备字段检查；纯数据文件不做外键启发 |
| `check-api-contract.py` | 路由/方法/Result 契约一致性；无法解析真实路由时 WARN 不伪造 PASS |
| `verify-deployment.py` | 实际请求 health/HTTPS/API；"DNS 已配置"与"公网已验证"分开报告 |

## Dev Workflow（分模式，带通过条件的检查点）

**CREATE（新项目）**
1. **Initialization**：Layer -1 问卷 → Decision Record（Status: CONFIRMED）
2. **Blueprint + Scaffold**：目录蓝图 → 空骨架 → `validate-project.py` PASS 才继续
3. **Backend**：Entity→repository→Service→Controller，全局异常+@Valid；🔍 先跑通一个实体的完整 CRUD（HTTP 实测返回正确 Result）
4. **Frontend**：Axios interceptor → router→pages→components→services；🔍 先打通一个页面"列表→新增→编辑→删除"（真实后端+loading/错误态+token 自动携带）
5. **Integration**：JWT → RBAC 守卫；🔍 CORS 放行正确来源、401 跳登录、403 按钮隐藏
6. **Deploy**：按 references/deployment/checklist.md 8 步；🔍 域名/端口/非默认密码/备份逐项打勾

**REFACTOR（改造已有项目）**
1. **Discover + Audit**：`inspect-project.py` → PROJECT AUDIT 给用户过目（发现优先于提问）
2. **Gap Analysis + Plan（三件套落盘）**：`inspect-project.py --json docs/audit/project-baseline.json`（现状快照）、
   `check-project-gap.py --json docs/audit/project-gap.json`（与决策的差距）、`docs/audit/refactor-plan.md`（顺序/风险/保持不变项/回滚）——
   换执行者、隔几天都能从快照继续，不靠聊天上下文记忆
3. **Incremental Change**：小步改、每步可运行；schema 变更走新迁移文件
4. **Regression**：改前先补回归测试（哪怕最小），改后全量跑；🔍 行为保持证据（同接口同响应）

**FEATURE（加功能）**：轻量 Recon → Impact Analysis（动哪些层/表/接口）→ 微型 Decision Record → 实现 → 测试 → Hygiene。禁止借机重构无关部分。

**DEPLOY**：Environment Recon（域名/服务器/备案）→ Preflight（references/deployment/checklist.md 逐项）→ Build → Config（env 注入）→ Deploy → Health（真实请求）→ Evidence。配置写好≠部署成功。

**AUDIT**：只读 Recon → Hygiene → Security → Architecture → Report，默认零修改。

## Reference 分阶段加载（L3 也不全家桶）

| 阶段 | 加载 |
|------|------|
| Initialization | architecture 概览 + compatibility |
| Blueprint/Scaffold | 对应 structure reference + assets 模板 |
| Implementation | 只加载当前模块的 reference |
| Deployment | docker + nginx + deployment checklist |
| Advanced | 确认需要 Redis/MQ/ES/K8s 后才加载对应文件 |
| Verification | validator 输出解读 + quality/hygiene.md |

## Layer 6: Standards Quick Ref（机械检查交给 scripts）

- **API**：名词复数 `/api/students`；GET查/POST增/PUT全改/DELETE删；分页 page 从 1；400/401/403/404/500 语义。详见 references/api/design.md，校验跑 `check-api-contract.py`
- **Database**：表名小写下划线；必备 id(BIGINT)/created_at/updated_at/deleted；WHERE/JOIN/ORDER BY 加索引；最左前缀；**schema 变更只能新增迁移文件，不改已执行脚本**。详见 references/database/design.md，校验跑 `check-db-schema.py`
- **Docker**：后端多阶段构建；前端 dist 由 Nginx 托管；镜像语义化 tag 不用 latest。详见 references/deployment/docker.md
- **Nginx**：唯一公网入口；`try_files $uri $uri/ /index.html`；`/api/` 反代；certbot 签 HTTPS。详见 references/deployment/nginx.md

## Layer 7: Resource Index（按需加载）

| 加载时机 | Reference |
|---------|-----------|
| 单体架构决策 | references/architecture/monolith.md |
| 模块化单体 | references/architecture/modular-monolith.md |
| Mode B 大仓 | references/architecture/monorepo.md |
| 创建前端 | references/frontend/structure.md |
| 创建后端 | references/backend/structure.md |
| 设计 API / DB | references/api/design.md · references/database/design.md |
| Docker / Nginx / 部署清单 / CI | references/deployment/docker.md · nginx.md · checklist.md · cicd.md · observability.md |
| 项目卫生 / Artifact Policy | references/quality/hygiene.md |
| Lint Baseline + Ratchet + Debt Register | references/quality/lint.md |
| 测试数据生命周期（seed/verify/reset） | references/quality/test-data.md |
| 凭据生命周期（生产部署/审计场景必载） | references/security/credentials.md |
| 版本兼容 | references/compatibility.md |
| Redis/MQ/ES · K8s | references/advanced/components.md · kubernetes.md |

**Scripts**（只检查不修改；CRITICAL/FAIL 阻断下一阶段）：

| Script | 作用 |
|--------|------|
| `inspect-project.py` | Project Recon 侦察 → PROJECT AUDIT |
| `check-project-hygiene.py` | 项目卫生：CRITICAL/ERROR/WARN(Queue)/INFO 四级 + Artifact Policy |
| `validate-decision-record.py` | Decision Record 机器门禁 |
| `check-project-gap.py` | 事实 vs 目标状态差距分析 |
| `seed/reset/verify-test-data.sh` | 测试数据生命周期三件套 |
| `run-trigger/functional/regression/hygiene-eval.py` | Skill 自评估执行器（4 个） |
| `validate-project.py` | 结构/分层/必备文件合规 |
| `check-security.py` | 密钥/.env/端口暴露 |
| `check-api-contract.py` | API 契约一致性 |
| `check-db-schema.py` | 迁移重放 + 最终 schema 检查 |
| `verify-deployment.py` | 部署后健康检查 |
| `validate-skill.py` | Skill 自身结构校验（发布门） |

## Stop Conditions

| 场景 | 条件 |
|------|------|
| 架构 | 单体/微服务、前端入口数未定 → 先 Initialization，不搭目录 |
| 骨架 | Blueprint 未通过 validator → 不进入业务编码 |
| 生产部署 | 域名/环境变量/备份未就绪 → 停止发布，列缺项 |
| 数据库 | schema 变更没有迁移文件 → 先补 migration，不手动改库 |
| 安全 | secret 入库、.env 将提交 → 立即停止，改 env 注入并轮换密钥 |
| 校验脚本 | 任一 CRITICAL/FAIL → 修复到 PASS 才继续（误报可申诉：修脚本豁免规则并记 CHANGELOG） |
| 不可逆生产操作 | 删库/重置密钥/删服务器/高风险 migration → 影响展示→回滚方案→显式确认→执行 |
| 高成本副作用 | 批量通知/大量云资源/DNS/支付 → 同上确认门 |
| 卫生清理 | WARN 项处置必须用户确认，绝不自动删除 |

默认能力上限 LOCAL_MUTATION / REMOTE_SAFE；REMOTE_SIDE_EFFECT 需对该动作显式授权（影响展示 → 回滚方案 → 显式确认 → 执行后验证）。

## Output Contract（完成可交付阶段后统一汇报）

```
## Result
Status: PASS / PARTIAL / BLOCKED
State Transition: BLUEPRINT → SCAFFOLD → VERIFY_SCAFFOLD → IMPLEMENT ...（本次实际走过的状态）
Decision Record: docs/architecture/decision-record.md（ID/版本，及是否 DRAFT 待追认）
Architecture: Frontend / Backend / Database
Project Hygiene: 本阶段目录卫生结论 PASS/WARN/CRITICAL（关键发现列出）
Files Changed: 关键新增/修改
Validation: Build / Tests / 各 validator 结果
Commands Executed: 只写真实执行过的
Evidence Summary: 每个结论的证据是什么（退出码/测试报告/health 响应/文件）
Evidence Artifacts: 日志/测试报告/截图等产出物路径
Unverified: 没验证的部分，不省略不含糊
Rollback: 如何退回稳定版本
Warnings / Next Steps
```

## Evidence Policy

1. "已完成/PASS"必须指向实际证据（退出码、测试结果、health 响应、文件）
2. 未执行的命令不写进 Commands Executed；未验证事项必须写进 Unverified
3. 推测与假设不得描述为既成事实；假设写进 Decision Record 的 Assumptions
4. 生产部署以真实 health check、HTTP(S) 请求、容器状态、运行日志为证据

## Environment & Code Quality

- dev/staging(可选)/prod；`.env` 不提交，`.env.example` 提交；Spring 用 `spring.profiles.active` + `application-{env}.yml`
- Backend: Service 层 JUnit5+Mockito 单测，Controller 层 MockMvc；数据层可用 Testcontainers 集成测试；Frontend: 关键 util 用 Vitest
- Commit 遵循 Conventional Commits；`.gitignore` 排除 node_modules/dist/target/.env（保留共享的 .vscode 配置）
- **Lint Ratchet**：CI 用 `--max-warnings <baseline>` 冻结存量（基线只降不升），不修的 warning 登记债务（rule/file/reason/owner/target_version/status），见 references/quality/lint.md

## Security Checklist（可被 check-security.py 验证）

- [ ] BCrypt 存储；JWT secret 从 env 读取；SQL 参数化；接口授权
- [ ] DB/后端的宿主机发布端口绑 127.0.0.1；公网只开放业务真正需要的端口（管理入口走安全组/VPN/来源限制）
- [ ] HTTPS + 301 跳转；`.env` 未提交 Git

## Advanced Tech Timing（条件不满足就不引入）

| Tech | 不因…引入 | 合理触发 |
|------|----------|---------|
| Redis | "都要有缓存" | DB 查询成瓶颈、热点读、分布式 session |
| MQ | "微服务都该有" | 异步任务、解耦、削峰、事件驱动 |
| ES | "有搜索就上" | 全文检索复杂度/数据量超 MySQL 舒适区 |
| K8s | "企业级必须" | 多服务器多服务、需自动扩缩容/自愈 |
| 微服务 | "大项目就要拆" | 边界清晰、需独立部署/扩展/故障隔离（先看 modular-monolith.md） |

## Skill Release Gate（发布门，全过才发版）

- [ ] SKILL.md 可解析、frontmatter 合法、≤500 行、引用无死链（`validate-skill.py` PASS）
- [ ] References/Scripts/Evals 路径真实存在且无死链；References 加载条件明确
- [ ] 全部 validator 完成 smoke test（fixtures/sample-project 全 PASS）
- [ ] Hygiene：sample 与 polluted 双 fixture 得到预期结果（四级严重度）
- [ ] **Decision Record 有机器门禁**（validate-decision-record.py 可阻断 DRAFT/缺失）
- [ ] **seed/reset/verify 可重复运行且有环境保护**
- [ ] **Lint baseline 与 ratchet 策略生效**（项目侧 CI --max-warnings）
- [ ] **Artifact Policy 生效**（测试截图/coverage 不污染 Git）
- [ ] Trigger/Functional/Regression/Hygiene Eval **可由 runner 机器执行**（行为断言如实标 MANUAL）
- [ ] Evidence：PASS 有证据；Unverified 不隐藏；CHANGELOG 记录变更与原因
- [ ] **三态决策行为正确**（DRAFT 阻断 / ASSUMED 限本地 / CONFIRMED 正常；md-yaml 一致性）
- [ ] **Hygiene Queue 持久化**（--queue 可写、消失条目自动 resolved）
- [ ] **PROJECT BASELINE/GAP 可落盘**（docs/audit/*.json 三件套）
- [ ] **Real Project Trial**：至少一次已有项目改造 + 一次新项目演练，记录状态/命令/证据/误报
