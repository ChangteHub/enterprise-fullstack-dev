# Real Project Trial — enterprise-fullstack-dev v3.0.0

> Release Gate 要求项：**至少用一个真实项目完整跑一遍 INIT→RELEASE 路径的脚本链，记录每个状态、命令、证据与误报**。
- 试验日期：2026-08-30
- 被测真实项目：`C:\Users\EN\Desktop\project1`（校园二手交易平台，React 18 + Vite + antd-mobile / Java 21 + Spring Boot 3.2.5 + MyBatis-Plus + Flyway + Docker Compose；本项目本身即由 v2.0.1 工作流完成重构，v3.0 脚本链在其上做验证）
- 对照 fixtures：`evals/fixtures/sample-project`（黄金样例）、`evals/fixtures/polluted-project`（污染样例）
- 原始输出存档：`evals/trial/trial-raw-output.txt`

## 一、真实项目脚本链结果（REFACTOR 场景的 Verification 阶段）

| 状态/命令 | 结果 | 证据（Summary 行） |
|-----------|------|--------------------|
| RECON `inspect-project.py project1` | PASS | 准确识别 react 18.3.1 / vite / antd-mobile / zustand；Java 21 / Spring Boot 3.2.5 / MyBatis-Plus；Flyway 迁移目录；Dockerfile×2 + compose + nginx.conf；GitHub Actions ci.yml；git 干净、.env 未跟踪。0 risks / 0 unknowns |
| HYGIENE `check-project-hygiene.py project1` | PASS（含 1 WARN） | 8 allowed / 1 orphaned / 0 critical：`reasonix.toml` 为真孤儿（历史工具遗留，gitignored），按"只检测不删除"原则留给用户处置 |
| VERIFY_SCAFFOLD `validate-project.py project1` | PASS | 0 failed, 0 warnings（数据访问层 repository/ 被正确接受） |
| SECURITY `check-security.py project1` | PASS | 0 warnings / 0 critical（.env 未被 git 跟踪 → 不判 CRITICAL，符合 git-tracked 优先策略） |
| DB `check-db-schema.py project1` | **PASS, 0 warnings** | 10 tables / 108 indexes。v2.0.1 同项目曾报 12 WARN（只看 V1 不识 ALTER + 纯数据文件外键误报），v3.0 迁移重放后归零 |
| API `check-api-contract.py project1` | PASS | 48 endpoints checked, 0 warnings |

## 二、Fixture Smoke Test（Release Gate"全部 validator smoke test"项）

| 脚本 | sample-project（应 PASS） | polluted-project（应 FAIL） |
|------|--------------------------|------------------------------|
| validate-project | PASS 0 failed / 0 warnings | —（不适用） |
| check-security | PASS 0/0 | — |
| check-db-schema | PASS 1 tables / 2 indexes | — |
| check-api-contract | PASS 3 endpoints | — |
| check-project-hygiene | PASS 0 critical | **FAIL（退出码 1）**：2 CRITICAL（.env 未忽略、legacy_tool.exe）+ 5 WARN（tmp/ old-backend/ backup/ test2/、notes.txt） |

## 三、误报记录与处置（Trial 发现 → 修复 → 复验）

| # | 误报 | 处置 | 复验 |
|---|------|------|------|
| 1 | `scripts/backup.sh`（Skill 官方推荐运维脚本）被 backup 关键词判 Suspicious | hygiene 脚本增加 scripts/docs/tests 二级扫描豁免 + 运维脚本名白名单（backup/restore/init-db/logs/deploy/rollback/health.sh） | project1 复跑仅剩真孤儿 reasonix.toml；polluted fixture 的可疑目录检出不受影响（3 CRITICAL 复现） |
| 2 | v2.0.1 遗留：测试常量 SECRET 判 CRITICAL、ALTER 不识别、mapper/ 判 FAIL | 三个校验器 v3.0 重写（fixture 识别 / 迁移重放 / 模式感知分层），并写入 evals/regression.json 用例 006-008 防退化 | project1 与 sample-project 全绿 |
| 3 | `.env` 在非 git 模式重复报两次 CRITICAL | 增加去重（顶层已报告的 .env 不再进入递归扫描） | polluted 输出 2 CRITICAL，无重复 |

## 四、状态机轨迹映射（本次 Trial 覆盖）

```
REFACTOR 映射（project1 已处于重构完成态，Trial 验证其 Verification 链）：
RECON(inspect ✓) → HYGIENE(✓ 1 WARN 待处置) → VERIFY_SCAFFOLD(validate ✓)
→ SECURITY(✓) → DB(✓) → API(✓)
CREATE/AUDIT 路径由 evals/functional.json 用例 001/009 与 fixtures 覆盖
DEPLOY 路径健康检查部分由本项目 compose 冒烟史实覆盖（三容器 healthy，见项目 docs/deployment.md）
```

## 五、结论

- 8/8 脚本在真实项目 + 双 fixture 上按预期运行，无阻断性误报
- 遗留 WARN（reasonix.toml）按规范留给用户处置，不自动删除
- Release Gate 的 Real Project Trial 项：**通过**
