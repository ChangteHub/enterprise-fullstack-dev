# Real Project Trial (CREATE) — enterprise-fullstack-dev v3.1

> Release Gate 要求项：**至少一次新项目（CREATE）演练，记录状态/命令/证据/误报**。REFACTOR 侧演练见 `TRIAL-v3.0.0.md`。
- 试验日期：2026-08-30
- 演练项目：`C:\Users\EN\Desktop\skill\_drill-new`（"Demo 新项目演练"，Mode A 最小骨架：React+Vite 前端壳 / Spring Boot 后端壳 / MySQL Flyway 单迁移）
- 演练性质：**状态机前半段（INIT → VALIDATE_SCAFFOLD）端到端走查**；IMPLEMENT 之后阶段不在本次覆盖范围（文末如实标注）

## 一、状态机轨迹与证据

| 状态 | 动作/命令 | 结果 | 证据（Summary 行） |
|------|----------|------|--------------------|
| INIT → DISCOVER | 读取需求，CREATE 模式 | — | 最小栈兜底：单体 + 单前端 + MySQL + JWT |
| DECIDE → RECORD | 生成 `.decision/project-decision.yaml`（含 UX Surface Matrix 四表面） | PASS | `validate-decision-record.py`：status=confirmed, 23 fields |
| BLUEPRINT → SCAFFOLD | Mode A 骨架：frontend/ + backend/，空包结构、V1 迁移、.gitignore | 完成 | 见 _drill-new 目录树 |
| VALIDATE_SCAFFOLD | `validate-project.py` | WARN（0 failed） | 0 failed, 2 warnings（骨架缺 vite 配置与 .env.example，属阶段内合理提示，不阻断） |
| VALIDATE_SCAFFOLD | `check-project-hygiene.py` | PASS | 3 allowed, 0 queue, 0 error, 0 critical |
| VALIDATE_SCAFFOLD | `check-security.py` | PASS（1 warn） | 缺 .env.example 模板，骨架阶段补齐即可，0 critical |
| VALIDATE_SCAFFOLD | `check-db-schema.py` | PASS | 1 tables / 0 indexes, **0 warnings** |
| VALIDATE_SCAFFOLD | `check-api-contract.py` | WARN | 空壳 Controller 尚无 Result/@RequestMapping，0 endpoint，属骨架阶段预期 |
| GAP（旁路核对） | `check-project-gap.py` | WARN | 0 high / 4 medium / 2 low：如实报出骨架尚缺 seed 脚本、CI 工作流、compose、测试目录、nginx 配置、人读版 decision-record.md——与 SCAFFOLD 阶段事实一致 |

## 二、本次演练发现并修复的问题（v3.1.1）

| # | 现象 | 根因 | 修复 | 回归 |
|---|------|------|------|------|
| 1 | `_drill-new` 的 V1 迁移为**单行压缩 DDL**，check-db-schema 对 id/created_at/updated_at/deleted 全部误报"缺失"（4 WARN） | `parse_columns` 按物理行逐行匹配列名，单行 DDL 只有一行且以 CREATE TABLE 开头，零列命中；建表块截断依赖文本 `);` 同样假设多行排版 | 改为括号深度匹配建表块 + 按顶层逗号切分列定义（忽略 DECIMAL(10,2) 等括号内逗号），单行/多行两种排版统一解析 | 新增 fixture `singleline-ddl` 与 regression 用例 010（断言输出 `1 tables / 1 indexes, 0 warnings` 且不含缺失字段提示）；sample/alter 两 fixture 复验不退化 |
| 2 | `evals/hygiene.json` 写了 machine_checks 但没有 runner 消费，只能人工执行 | v3.1 只交付 trigger/functional/regression 三个 runner | 新增 `run-hygiene-eval.py`（同构 runner），实测 3/4 machine-PASS，行为用例 004 如实 MANUAL | 纳入发布前 runner 清单 |
| 3 | reset/verify-test-data.sh 缺少 seed 已有的 loopback 绑定环境保护 | 三件套环境保护不一致 | 补齐相同的 `docker port` loopback 校验，`bash -n` 语法通过 | 代码审查 |

## 三、骨架阶段 WARN 的定性（不是误报）

- validate-project 的"缺 vite config / .env.example"、security 的"缺 .env.example"、api-contract 的"空壳 Controller 无契约"：都是**骨架未填充**的真实提示，WARN 不阻断符合状态机设计（VALIDATE_SCAFFOLD 只要求无 CRITICAL/ERROR、0 failed）。
- gap 的 4 MEDIUM / 2 LOW 是 SCAFFOLD → IMPLEMENT 的待办清单，恰好证明 gap 分析对新项目同样有效。

## 四、未覆盖项（如实记录，不冒充端到端全绿）

- IMPLEMENT（真实业务 CRUD）、VERIFY（HTTP 实测）、INTEGRATE（JWT/RBAC/CORS）、DEPLOY（真实服务器）、EVIDENCE/RELEASE：本次**未演练**。
- seed/reset/verify 三件套需要本地 MySQL 容器环境，本次只做 `bash -n` 语法检查与环境保护代码审查，未做真实播种/清理/就位的运行时验证。
- 结论：CREATE 路径的 **DECIDE/RECORD → BLUEPRINT → SCAFFOLD → VALIDATE_SCAFFOLD 门禁链真实可走通**；后半段证据仍待一次带真实业务实现的 CREATE 演练补齐。
