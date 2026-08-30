# evals/fixtures — 评测与 smoke test 固定样例

> 目的：给 validator 提供可复现的输入，避免每次 smoke test 临时凑项目。`sample-project/` 是一个**应通过**的最小 Mode A 样例（单前端 + 单体后端）。

## sample-project 黄金基线（2026-08-29 实测）

| 脚本 | 预期结果 | 实测基线 |
|------|---------|---------|
| `validate-project.py sample-project` | PASS（0 error / 0 warning） | `0 failed, 0 warnings` |
| `check-security.py sample-project` | PASS（0 critical） | `0 warnings / 0 critical` |
| `check-api-contract.py sample-project` | PASS | `3 endpoints checked, 0 warnings` |
| `check-db-schema.py sample-project` | PASS | `1 tables / 2 indexes, 0 warnings` |

## 怎么跑（Smoke Test 流程）

```bash
cd <skill根目录>
python scripts/validate-project.py evals/fixtures/sample-project
python scripts/check-security.py   evals/fixtures/sample-project
python scripts/check-api-contract.py evals/fixtures/sample-project
python scripts/check-db-schema.py  evals/fixtures/sample-project
```

任何脚本报 FAIL/CRITICAL 即视为回归失败：先区分是 fixture 需要更新，还是脚本误报/规则变化，修复后再发布（对应 SKILL.md Release Gate 的"全部 validator smoke test"一项）。

## polluted-project 污染基线（2026-08-30 实测，v3.1.0 四级严重度）

用于 Project Hygiene 的"应发现"路径（evals/hygiene.json，含 machine_checks 可由 runner 执行）：

| 脚本 | 预期结果 | 实测基线 |
|------|---------|---------|
| `check-project-hygiene.py polluted-project` | FAIL（退出码 1） | `1 CRITICAL`（.env 未忽略）+ `1 ERROR`（legacy_tool.exe 可执行文件，v3.1 起为 ERROR 级）+ `5 WARN`（tmp/、old-backend/、backup/、test2/、notes.txt，进 Hygiene Queue） |
| `check-project-hygiene.py sample-project` | PASS（0 CRITICAL/ERROR） | 通过 |

## 其他 v3.1 回归 fixture

| fixture | 用途 | 预期 |
|---------|------|------|
| `test-fixture-secret/` | 测试文件中的 SECRET 常量 | check-security PASS（fixture 降级 WARN，不阻断） |
| `alter-migrations/` | V1 缺列 + V3 ALTER 补齐 | check-db-schema PASS（迁移重放后字段齐全） |

要点：脚本只检测不删除；CRITICAL 才阻断；WARN 必须给出证据与候选处理方案由人决定。

## 扩展约定

- 每个 fixture 是一个真实可跑的最小结构，并在本文件维护它的预期结果表；
- 需要"应 FAIL"路径的用例时，复制 sample-project 后故意加入问题（如硬编码密码、缺分层包），**不要污染黄金样例本身**；
- `verify-deployment.py` 面向真实 URL，不适用文件型 fixture，smoke test 时对任一可达 HTTPS 站点执行并人工核对输出即可。

## 注意：对 Skill 包自身运行 hygiene 的预期结果

在 skill 根目录运行 `check-project-hygiene.py .` 会因 `polluted-project/.env` 报 1 个 CRITICAL——
**这是扫描器正确工作的证据**（fixture 故意放置的敏感文件占位，内容为 change-me 占位值，非真实凭据）。
该 CRITICAL 仅在"把 skill 包当作被检项目"这一非典型场景出现；对被测项目无影响。
