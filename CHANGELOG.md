# Changelog

本文件记录 enterprise-fullstack-dev Skill 的版本变更。遵循 Release Gate：每次发布需通过 `scripts/validate-skill.py` 与 evals 回归。

## [3.1.2] - 最终冻结版（实践问题闭环收口 + 冻结验收修复）

### 定位
控制面冻结：不再新增领域知识，只修状态语义与边界冲突。目标是从"规则完整"到"真实可执行、可验证、可持续维护"。

### Added
- **三态决策（DRAFT/ASSUMED/CONFIRMED）**：解决"缺信息停工"与"擅自危险决策"的两难——ASSUMED 允许本地 Blueprint/Scaffold/构建测试，锁定生产部署/Remote Side Effect/高风险迁移，最终报告必须列出假设请求追认；validator 按 status 分级行为。
- **decision_id + revision 必填**：稳定标识 + Re-open 递增；md 人读版与 yaml 状态源一致性校验（不一致即 BLOCKED）。
- **PROJECT BASELINE / GAP / PLAN 三件套落盘**：`inspect-project.py --json` 与 `check-project-gap.py --json` 输出 `docs/audit/project-baseline.json` / `project-gap.json`——现状快照与差距可持久化，换执行者/隔天可续，不靠聊天上下文。
- **Hygiene Queue 持久化**：`check-project-hygiene.py --queue docs/quality/hygiene-queue.json`，条目含 path/severity/reason/first_seen/status，消失条目自动标 resolved——Queue 从聊天上下文升级为项目治理状态。
- **run-hygiene-eval.py**：第 4 个 Eval Runner（干净/污染双 fixture + 严重度断言）。
- **references/quality/test-data.md**：测试数据生命周期独立成文（seed→verify→reset；幂等；环境保护；生产禁止 ad-hoc SQL）。

### Changed
- **Docker 端口语义纠偏**：宿主机发布端口绑 127.0.0.1 ≠ 容器内服务监听 127.0.0.1——保护来自端口绑定与 Nginx 唯一入口，容器内进程按网络需要监听；"防火墙只开 22/80/443"改为"公网只开业务真正需要的端口，管理入口走安全组/VPN/来源限制"。
- 状态机按 Task Mode 显式分叉（CREATE/REFACTOR/FEATURE/DEPLOY/AUDIT 各自的入口/必经阶段）。
- schema 文件定名 `.decision/schema.yaml`（原 project-decision.schema.yaml）。
- Release Gate 扩至三态决策行为/Queue 持久化/三件套落盘等冻结项。

### Fixed（v3.1.1 压测实测发现并修复）
- **reset-test-data.sh 在最小 schema（仅 user+category）崩溃**：`Table 'product' doesn't exist`——全量表假设错误。
  重写为逐表探测式清理（information_schema 确认存在才生成 DELETE，依赖顺序子表在前），
  并以临时 SQL 文件执行规避 heredoc 引号嵌套。一次性容器全闭环复验：reset→verify FAIL→空库幂等→seed 复活→verify PASS。
- **reset 失败静默半完成**：失败现在显式 exit 1 并提示可安全重跑（删除语义按语句级执行，中断不产生部分删除）。
- 附带：check-project-gap.py 加载器设置 `sys.dont_write_bytecode`，不再在用户项目留下 `__pycache__`。

### 冻结验收修复（3.1.2 同日复验发现并修复）
- **Hygiene Queue 路径抽取 bug**：`--queue` 持久化时正则 `root/([^（]+?)` 非贪婪无下限，path 只捕获到单字符（tmp/debug.log→"t"、backup→"b"），不同条目首字母撞车会互相覆盖；改为 `root/(\S+?)(?:（|\s|$)` 捕获完整路径并去掉尾斜杠。
- **Queue 复发状态错误**：曾 resolved 的问题再次检出时旧逻辑沿用 resolved，等于把复发问题永久藏起；改为本次检出一律 pending，resolved 只由"本次未检出"分支赋予。三轮生命周期实测：7 pending → 全 resolved → 复发重回 7 pending。
- **三态文档同步**：SKILL.md 的 Gate 表/md 模板/自主执行路径/Validator Philosophy/CREATE workflow/Output Contract 六处仍写两态（自主执行教标 DRAFT，而 DRAFT 已被硬门禁阻断，Agent 会被自己的门禁卡死），全部同步为 DRAFT/ASSUMED/CONFIRMED；schema.yaml 头注释同步。
- **eval 断言加固**：hygiene.json 污染/干净用例补 `expect_contains/expect_not_contains` 输出断言（锁死 2 error/0 critical 等语义，不再只比退出码）；fixtures/README 污染基线更新为 git 跟踪路径实测值。
- **仓库卫生**：`test-fixture-secret/target/.../DemoTest.class`（Maven 编译产物）曾被 git 跟踪，违反自家 Artifact Policy → git rm --cached，根 .gitignore 补 target/ 与 *.class；sample-project/target 工作区残留清理。
- 版本号整理：本冻结版原与上一验收修复同名 3.1.1，按时间顺序与兼容性影响（decision_id/revision 必填）递进为 3.1.2。

### 兼容性影响
- 既有项目决策 yaml 需补 `decision_id` 与 `revision`，否则 DECIDE 门禁 BLOCKED（对存量库接入属预期行为）。
- `references/security/credentials.md`、`references/quality/lint.md`、seed/verify/reset 脚本自 v3.1.0 起已存在，本轮无破坏性变更。


## [3.1.1] - v3.1 验收修复（CREATE 演练发现的误报与自动化缺口）

### Fixed
- **check-db-schema.py 单行 DDL 误报**：原列解析按物理行逐行匹配，整条 CREATE TABLE 写在一行（压缩/导出/AI 生成常见）时解析不到任何列，对 id/created_at/updated_at/deleted 全部误报缺失；建表块截断还依赖文本 `);`。改为括号深度匹配建表块 + 按顶层逗号切分列定义（正确忽略 `DECIMAL(10,2)`、`ENUM('a','b')` 等括号内逗号），单行/多行排版统一解析。
- **eval runner 输出断言能力**：`_eval_common.py` 的 validator 类 machine_check 新增可选 `expect_contains` / `expect_not_contains`——WARN 不影响退出码的脚本（如 check-db-schema）现在能用输出文本证明误报未退化，不再只比退出码。

### Added
- **run-hygiene-eval.py**：hygiene.json 此前写了 machine_checks 却无 runner 消费，现补齐第四个同构 runner（实测 3/4 machine-PASS，git 跟踪类行为用例如实 MANUAL）。
- **fixture `singleline-ddl` + regression 用例 010**：单行压缩 DDL（含 DECIMAL(10,2) 与内联 INDEX）应输出 `1 tables / 1 indexes, 0 warnings`，锁死本次修复防退化。
- **evals/trial/TRIAL-v3.1-create-drill.md**：CREATE 模式演练记录（_drill-new），如实覆盖 DECIDE→VALIDATE_SCAFFOLD 门禁链，并标注 IMPLEMENT 之后阶段未覆盖。
- reset/verify-test-data.sh 补齐与 seed 一致的 loopback 绑定环境保护；三件套头部补充"可工作实例模板，接入新项目需替换表结构"说明。

### 验证
- validate-skill 41 项 PASS；trigger 20/20、functional 5/9+4 MANUAL、regression 5/10+5 MANUAL（新增 010 机检 PASS）、hygiene 3/4+1 MANUAL，全部 runner 退出码 0。
- check-db-schema 对 singleline-ddl / _drill-new / sample-project / alter-migrations 四目标均 0 warnings，无退化。
- 三个 shell 脚本 `bash -n` 语法通过。

### 兼容性影响
- machine_check 新增字段均为可选，旧 eval JSON 无需改动；脚本退出码语义不变。


## [3.1.0] - 项目控制平面（v3.0 实践问题复盘落地）

### 核心转向
v3.0 实践（真实项目 REFACTOR + UI 冒烟 + Lint 引入）暴露的短板不是知识覆盖率，而是**项目状态管理与执行闭环**。v3.1 把 Skill 从"规则中心"升级为"项目控制平面"：决策可机检、差距可复现、卫生分级不堵路、测试数据可重放、Skill 自身可被 runner 验证。

### Added
- **Decision Record 机器门禁**：`.decision/project-decision.yaml`（两层 YAML 子集，零依赖解析）+ `scripts/validate-decision-record.py`——缺失/status≠confirmed/字段缺失/取值非法 → BLOCKED，硬性阻断 BLUEPRINT 之后全部状态；md 人读版与 yaml 门禁版并存。
- **UX Surface Matrix**：初始化必答 `frontend.ux_surface`（用户端/管理后台 × 移动/桌面），不支持可以是产品决策但必须显式记录；测试按矩阵选 viewport，禁止临时换尺寸让测试通过。
- **Project Gap Analysis**：`scripts/check-project-gap.py` 把项目事实与决策目标状态机器比对，输出 HIGH（冲突/安全）/MEDIUM（工程化）/LOW（文档）差距 + 最小改造动作——Gap 不再依赖人工记忆。
- **Project Audit**：`inspect-project.py` 输出升级为 Facts/Risks/Suggested Next Actions 审计格式。
- **测试数据生命周期**：`scripts/seed-test-data.sh`（幂等 upsert）/`reset-test-data.sh`（只清理种子数据+确认门）/`verify-test-data.sh`（就位校验）；环境保护（仅本地 loopback 容器，拒绝非本机库）；统一 utf8mb4 消除客户端乱码。**硬规则：生产禁止 ad-hoc SQL 建测试账号**。
- **Credential Lifecycle**：`references/security/credentials.md` 六阶段（生成/交付/首用/轮换/恢复/撤销/审计）+ audit 检查项；禁止"随机生成只打印一次日志"作为唯一交付方式。
- **Lint Baseline + Ratchet + Debt Register**：`references/quality/lint.md`——CI `--max-warnings <baseline>` 存量冻结、基线只降不升、不修的 warning 必须登记（rule/file/reason/owner/target_version/status）。
- **Artifact Policy**：测试截图/coverage/临时日志归属 CI Artifacts 或临时目录，不入源码仓库（hygiene 对 screenshots/coverage/logs/test-results 类条目报 WARN + 建议 .gitignore）。
- **Eval Runner ×3**：`run-trigger-eval.py`（结构校验 20/20）/`run-functional-eval.py`/`run-regression-eval.py`——执行用例 machine_checks（validator/文件断言），行为类用例如实标 MANUAL，不伪造全绿。
- 新增回归 fixture：`test-fixture-secret/`（SECRET 常量应 WARN 不阻断）、`alter-migrations/`（V1 缺列 + V3 ALTER 应 PASS）。

### Changed
- **Hygiene 四级严重度**：CRITICAL/ERROR（阻断）+ WARN（Hygiene Queue，不阻塞主线，阶段收尾批量裁决）+ INFO（工具配置目录）；Artifact 检测并入（v3.0 的"一切 WARN 停车场"不再阻塞自主执行）。
- 状态机每个状态定义进入条件/允许动作/退出条件/必需证据；RECON 更名 DISCOVER 并与 AUDIT 衔接。
- SKILL.md 353 行（v3.0 为 320），仍为控制平面；详细策略外置 references。

### Fixed
- eval 用例 `should_trigger` 字符串布尔、负例无 expected_depth 等 runner 兼容问题；eval JSON 全部接入 machine_checks（functional 5/9、regression 4/9 机检，其余如实 MANUAL）。

### 兼容性影响
- hygiene 输出新增 ERROR/INFO 级别行；依赖旧三级文本的脚本需同步。
- REFACTOR 模式第一步更名为 Discover + Audit；项目侧需要新增 `.decision/project-decision.yaml` 才能通过 DECIDE 门禁。
- v3.0.0 完整备份见发布包 `_archive/`（v3.0.0 快照由 v3.0 发布副本留存）。


## [3.0.0] - 项目操作系统重构（v2.0.1→v3.0 改造指导 + 真实项目 Trial 落地）

### 核心转向
从"规则手册"升级为"轻量项目操作系统"：先认识项目 → 只问必须决定的事 → 冻结决策 → 蓝图骨架 → 按模块实现 → 持续卫生 → 可验证交付。不推翻 v2 核心原则（P0-P4 / Evidence / Guardrail 全保留），重构的是任务开始后的实际行为路径。

### Added
- **五种任务模式**：CREATE / REFACTOR / FEATURE / DEPLOY / AUDIT 各有独立流水线与禁止项，不再共用一条流程（解决"已有项目被绿地流程套住"）。
- **生命周期状态机**：INIT→RECON→HYGIENE→DECIDE→BLUEPRINT→SCAFFOLD→VERIFY_SCAFFOLD→IMPLEMENT→VERIFY_MODULE→INTEGRATE→FINAL_HYGIENE→RELEASE_CHECK→DEPLOY/REPORT；骨架未验收不进业务编码，Output Contract 新增 State Transition 字段留轨迹。
- **Layer -1 Project Initialization**：12 个决策域表（何时必答/典型问题/输出字段），替代原 Layer 0 问答式 Gate；提问方式改为"先自动发现，只问会改变架构的决策"。
- **Decision Record 项目文件化**：`docs/architecture/decision-record.md` + Status: CONFIRMED/DRAFT（DRAFT 不得进入 SCAFFOLD）+ Re-open 规则；自主执行模式按兜底默认生成并请用户追认（解决 Checkpoint 阻塞自主代理问题）。
- **Project Recon**：`scripts/inspect-project.py` 只读侦察产出 PROJECT BASELINE（技术栈/迁移/运行时/CI/观测/Git/风险/未知），REFACTOR/FEATURE 必做；确立"不要强行统一"原则（mapper/Gradle/Vue 等现有体系优先保持）。
- **Directory Blueprint**：蓝图六问（边界/必备项/禁止项/扩展点/环境/验证），先空骨架过 validator 再写业务代码。
- **Project Hygiene**：`scripts/check-project-hygiene.py` 五级分类（Allowed/Suspicious/Orphaned/Sensitive/Forbidden）；初始化前/每阶段后/发布前持续运行；**绝不自动删除**；Output Contract 新增 Project Hygiene 字段。配套 references/quality/hygiene.md。
- **evals/hygiene.json**（4 用例）+ **evals/fixtures/polluted-project**（污染样例：.env 未忽略/exe/可疑目录/孤儿文件）。
- **Real Project Trial**：`evals/trial/TRIAL-v3.0.0.md` + 原始输出存档，以校园二手交易平台为真实被测项目完成 Release Gate 新增项。

### Changed
- **校验器哲学升级（字符串命中→上下文感知）**，SKILL.md 新增 Validator Philosophy 一节：
  - `validate-project.py`：模式感知分层判定——数据访问接受 repository|mapper|dao，传输对象接受 dto|vo|model，异常接受 exception|common，构建文件接受 pom|gradle（消除"只认 repository/"诱导无意义重命名）。
  - `check-security.py`：git 跟踪状态优先（未跟踪降 WARN）；测试 fixture 自动识别降 WARN；行内 `security-allowlist` 例外声明；占位词表扩充（demo/test-/fixture/sample/dummy/mock）。
  - `check-db-schema.py`：按版本序重放迁移（CREATE/ALTER ADD COLUMN/DROP/CREATE INDEX/ALTER ADD INDEX），对**最终 schema** 检查必备字段；纯数据文件不做外键启发；ALTER 引用未知表给自洽性 WARN。
- **Reference 分阶段加载**：L3 也不全家桶——Initialization/Blueprint/Implementation/Deployment/Advanced/Verification 各阶段只加载对应文件。
- **Output Contract 扩容**：新增 Decision Record（ID/版本/DRAFT 状态）、Project Hygiene、State Transition、Evidence Artifacts 四个事实字段。
- **Release Gate 扩容**：新增 Hygiene eval（双 fixture 预期结果）、Functional eval 五模式覆盖、Real Project Trial 三项。
- Layer 4 结构决策表新增"模块化单体"中间态入口；references 新增 architecture/modular-monolith.md（模块边界/演进触发条件）与 quality/hygiene.md。
- SKILL.md 精简至 320 行（v2.0.1 为 391 行），重复知识下放 references；触发描述与 name 保持不变（trigger eval 无需重跑，仍 20 用例全绿）。

### Fixed
- 真实项目 Trial 发现并修复：hygiene 将官方推荐运维脚本 backup.sh 误判为可疑（scripts/docs/tests 目录豁免二级扫描 + 运维脚本名白名单）；非 git 模式 .env 重复报两次 CRITICAL（去重）。
- v2.0.1 遗留误报全部收敛并写入 evals/regression.json 006-008 防退化：测试常量 SECRET 误判 CRITICAL、ALTER TABLE 不识别导致 12 条假 WARN、mapper/ 目录判 FAIL。
- fixtures/sample-project 补充 stores/、security/、config/ 最小结构，保持"应全 PASS"基线有效。

### 兼容性影响
- 脚本输出新增分级标签（[测试fixture]/[未跟踪文件]），退出码语义不变（CRITICAL/FAIL=1）。
- 原 Layer 0"通用/条件问题"并入 Layer -1 决策域表与 Mode 分流，引用 v2 Checkpoint 语义的文档需同步。
- v2.0.1 完整备份见发布包 `_archive/enterprise-fullstack-dev_v2.0.1/`。


## [2.0.1] - 100分收口版（v2.0.0 最终修改实施指南落地）

### Added
- **Capability / Permission Boundary**：READ_ONLY / LOCAL_MUTATION / REMOTE_SAFE / REMOTE_SIDE_EFFECT 四级能力边界，与 Stop Conditions 互补（前者管"最多能做什么"，后者管"什么时候必须停"）。
- **敏感权限 Guardrail 行**：改 DNS、轮换生产密钥/证书、改访问策略纳入确认门（影响说明 + 权限确认 + 可恢复方案）。
- **references/compatibility.md**：版本基线矩阵、冲突处理策略（先检测、本地可运行优先、大版本不自动升级）与常见不兼容对照；SKILL.md Layer 2 只保留原则并链接该文件。
- **assets/templates/**：`backend/Result.java`（统一响应包装）与 `deployment/docker-compose.yml`（单台 VPS 安全基线），SKILL.md 定位行中的 assets/ 由"口头提及"变为真实目录。
- **evals/fixtures/sample-project/**：应全 PASS 的最小 Mode A 黄金样例 + fixtures/README.md 记录实测基线，供 validator smoke test 复现。
- **README.md**：Skill 包结构、使用方式与维护者指南。
- Release Gate 由 9 项扩为 12 项：新增 validate-skill 本身可运行、全部 validator smoke test（可用 fixtures）、validator 只检查不修改、baseline 对照方法明确、PASS 必须有 Evidence 等。

### Changed
- 优先级裁决补充证据优先级：任何 PASS 优先服从 Evidence Policy，没有证据宁可写 PARTIAL/Unverified。
- Decision Record 补充重开规则：只有出现新事实导致原决策失效时才重新打开决策，并记录变更原因。
- Task Depth 补充 L1 边界说明：L1 仍受所选 reference 自身安全/正确性要求约束，只是不走全局架构 Gate。
- evals 索引补充 fixtures 条目；verify-deployment.py 输出说明修正为 frontend/https/api 各项 OK/WARN/FAIL。

### Fixed
- **check-db-schema.py**：索引统计现在同时识别建表语句内的内联 `INDEX/KEY` 定义（此前只认独立 `CREATE INDEX`，导致内联索引被漏计、外键无索引误报）；外键警告改为按本文件索引计数判断，消除跨文件累积计数互相掩盖的问题。
- **verify-deployment.py**：健康端点返回 404 由 OK 改为 WARN（404 只证明反代链路有响应，不能当作后端健康的证据），符合 Evidence Policy。

## [2.0.0] - 最终可交付版

### Added
- **Decision Record**：L2/L3 任务编码前输出简短决策记录（Scope/Project/Frontend/Backend/Database/Auth/Advanced/Deployment/Assumptions），全流程引用同一份决策。
- **Evidence Policy**：PASS 必须有实际证据；未执行命令不进 Commands Executed；未验证项进 Unverified；推测不写成事实。
- **Evidence Summary**：Output Contract 新增字段，区分"执行了什么命令"与"哪些结论有证据"。
- **高成本外部副作用 Guardrail**：批量通知、创建大量云资源、改 DNS、支付等纳入与不可逆操作同级的确认门。
- **Task Depth 加载纪律硬规则**：L0 不加载 reference，L1 只加载一个，禁止因 Skill 已安装就全量加载。
- **Release Gate**：发布前 11 项检查清单。
- references 按任务域重组为 7 个子目录：architecture/ frontend/ backend/ api/ database/ deployment/ advanced/。
- trigger 反例补到 10 个（合计 10 正 + 10 反 = 20 用例）。
- CHANGELOG.md。

### Changed
- 默认兜底方案由"单体+单前端+MySQL+JWT"改为"单体+单前端+MySQL，仅涉及登录/权限时才按需加 JWT"。
- @Transactional 规则改为业务事务边界优先，不再机械给所有 Service 方法加事务。
- 优先级补充：P4 不得为"看起来更企业级"推翻稳定的 P2/P3 简单方案。
- description 补充任务深度触发线索（项目级/跨层才走完整流程，单函数/单文件/算法不走）。
- validate-skill.py 支持 references 子目录递归扫描、死链检查、正/反例分别计数、Deliverable 检查。
- 6 个脚本统一输出格式（脚本名头行 + 逐项结果 + Summary + 退出码）。

## [1.6.0]
### Added
- Task Depth（L0 单点 / L1 单层 / L2 跨层 / L3 项目级）分流。
- Decision Gate 拆分为 Universal Gate + Conditional Gate。
- 五级优先级 P0 Safety / P1 Correctness / P2 Operability / P3 Maintainability / P4 Optimization。
- 不可逆生产操作确认门；Output Contract 增加 Assumptions/Commands Executed/Unverified/Rollback。
- scripts/ 6 个确定性检查脚本（只检查不修改）。
- evals/：trigger.json / functional.json / regression.json / baseline.md。

## [1.5.0]
### Added
- 七层结构（Layer 0-7）、Pre-Dev Q&A Gate、请求链路全景、开发检查点。
- references/ 13 个按需知识文件，每个含 Pre-Check / 参考模板声明 / Deliverable。
- Code Usage Policy（代码为参考模板，可调整但不引入 bug）。

## [1.0.0]
### Added
- 初版：企业级全栈开发标准，React+TS+Vite / Spring Boot / MySQL / Docker / Nginx 技术栈，最小技术栈优先与版本式演进原则。
