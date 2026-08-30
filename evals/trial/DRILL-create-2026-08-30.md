# CREATE 演练记录 — 2026-08-30（v3.1.0 Release Gate：Real Project Trial 新建路径）

- 目标：验证 CREATE 模式 INIT→BLUEPRINT→SCAFFOLD→VALIDATE_SCAFFOLD 全链与三态决策门禁
- 现场：`_drill-new/`（最小 Mode A 骨架，演练后删除）
- 命令与结果：
  1. `validate-decision-record.py`（status=draft）→ **BLOCKED, exit 1**（硬门禁实测）
  2. `validate-decision-record.py`（status=confirmed）→ PASS, 23 fields
  3. `validate-project.py` → WARN 0 failed（新骨架的 backlog 信号：缺 vite config/.env.example）
  4. `check-project-hygiene.py` → PASS
  5. `check-project-gap.py` → WARN：4 MEDIUM（缺 CI/compose/测试目录）+ 2 LOW（缺 nginx conf/人读决策记录）
     ——差距清单正是骨架进入 IMPLEMENT 前的 backlog，符合"先骨架后业务"设计
- 结论：CREATE 路径通过；连同 REFACTOR 路径（evals/trial/TRIAL-v3.0.0.md + v3.1 实测）满足 Release Gate 的双演练要求
