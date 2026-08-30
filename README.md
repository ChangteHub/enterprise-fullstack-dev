# enterprise-fullstack-dev

企业级全栈 Web 应用（React + TypeScript + Vite / Spring Boot 3 / MySQL / Docker / Nginx）的搭建、重构与部署工作流 Skill。定位是"工程控制系统"而不是知识百科：先决策再编码、最小技术栈优先、确定性检查交给脚本、结论必须有证据。

## 目录结构

```
enterprise-fullstack-dev/
├── SKILL.md           # 大脑和控制流：五任务模式(CREATE/REFACTOR/FEATURE/DEPLOY/AUDIT)、
│                       #   生命周期状态机、Layer -1 初始化、Decision Record(项目文件化)、
│                       #   Recon/Blueprint/Hygiene、Validator 哲学、Stop/Output 契约、Release Gate
├── references/        # 按需知识库（18 个文件，按阶段加载而非全家桶，每个含 Pre-Check / Deliverable）
│   ├── architecture/  frontend/  backend/  api/  database/  deployment/  quality/  security/  advanced/
│   └── compatibility.md
├── scripts/           # 确定性脚本（只检查不修改，统一 Summary + 退出码）
│   ├── inspect-project.py         # Project Recon 侦察 → PROJECT AUDIT（Facts/Risks/Next Actions）
│   ├── check-project-hygiene.py   # 项目卫生：CRITICAL/ERROR 阻断 + WARN 进 Queue + INFO 四级
│   ├── validate-decision-record.py# 决策机器门禁（缺失/DRAFT/字段缺失 → BLOCKED）
│   ├── check-project-gap.py       # 事实 vs 决策目标状态差距（HIGH/MEDIUM/LOW + 最小动作）
│   ├── validate-project.py        # 结构合规（模式感知分层：mapper|repository|dao 等惯例均认可）
│   ├── check-security.py          # 安全（git 跟踪状态优先、测试 fixture 识别、行内 allowlist）
│   ├── check-db-schema.py         # 迁移重放（CREATE/ALTER/DROP，兼容单行 DDL），按最终 schema 检查
│   ├── check-api-contract.py / verify-deployment.py / validate-skill.py
│   ├── seed/reset/verify-test-data.sh  # 测试数据生命周期三件套（幂等 + loopback 环境保护）
│   └── run-trigger/functional/regression/hygiene-eval.py  # 4 个 Eval Runner（_eval_common 共享内核）
├── assets/templates/  # 可复用模板（复制后改造：Result.java、安全基线 docker-compose.yml）
├── evals/             # trigger/functional(五模式)/regression/hygiene 用例 + baseline + fixtures(黄金+污染)
└── CHANGELOG.md
```

## 使用

1. 将整个目录放入 Agent 的 skills 发现路径（如 `~/.zcode/skills/`）；
2. L2 跨层 / L3 项目级任务自动进入完整流程；L0/L1 局部任务只按需加载对应 reference；
3. 交付前按 SKILL.md Layer 7 运行对应 validator，按 Output Contract 汇报。

## 维护者指南（改动后必做）

```bash
python scripts/validate-skill.py .                                # 结构自检（Release Gate 第一道门）
python scripts/validate-project.py evals/fixtures/sample-project  # validator smoke test（其余脚本同理）
```

- 改 description → 重跑 `evals/trigger.json` 用例；
- 改核心 workflow / Stop Conditions / 脚本接口 → 至少跑一组 `evals/regression.json` 旧用例；
- 全部通过后更新版本号并在 `CHANGELOG.md` 记录变更原因，再发布（完整清单见 SKILL.md 的 Skill Release Gate，含 Real Project Trial 项）。

## 当前版本

v3.1.1（变更记录见 [CHANGELOG.md](CHANGELOG.md)）。v3.1 核心：v3.0 生命周期操作系统之上补齐执行闭环——决策机器门禁（.decision yaml + validator）、差距分析机器化（check-project-gap）、卫生四级严重度 + Hygiene Queue + Artifact Policy、测试数据生命周期（seed/reset/verify）、凭据生命周期规范、Lint Ratchet + 债务登记簿、Skill 自身 Eval Runner 可机检。v3.1.1 为验收修复：单行 DDL 误报修复、第四个 eval runner（hygiene）、runner 输出断言、CREATE 演练记录。
