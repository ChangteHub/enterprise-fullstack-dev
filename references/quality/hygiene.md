# Project Hygiene（项目卫生规范）

> **Pre-Check（加载前确认）：** 是初始化前、阶段完成后、还是发布前运行？项目在 git 仓库内吗？——卫生检查是持续性活动，不是一次性验收。
>
> 本文件为策略参考模板（Reference Template）：分类定义与处置矩阵是参考规范，执行细节以 `scripts/check-project-hygiene.py` 实际输出为准。
>
> **Deliverable（读完必须产出）：** 卫生检查结论 + 每个 WARN 的处置决定（保留/归档/删除，附证据）。

## 为什么需要独立于结构校验的卫生检查

`validate-project.py` 回答"结构对不对"；`check-project-hygiene.py` 回答"项目里有没有混入不属于项目的东西"。项目随着迭代混入临时文件、遗留目录、个人文件，这些不会让结构校验失败，但会持续污染协作与 AI 上下文。

## 分类与处置矩阵（v3.1 四级严重度 + Hygiene Queue）

| 级别 | 判定 | 例子 | 处理 |
|------|------|------|------|
| Allowed | 顶层清单内的目录/文件 | frontend/ backend/ docs/ README Makefile | PASS |
| INFO | 正常但不属于核心路径 | .claude/ 等工具本地配置目录 | INFO（不入库即可） |
| WARN | 可疑临时/遗留/孤儿/Artifact 入库 | tmp/ old-backend/ test2/ gui-test-screenshots/ | **不阻断**，进 Hygiene Queue，由人批量裁决 |
| ERROR | 破坏仓库约束 | 可执行/构建产物被 git 跟踪、测试证据提交入库 | 阻断（exit 1） |
| CRITICAL | 敏感文件 | .env 被 git 跟踪、id_rsa、凭据、生产 dump | 阻断（exit 1） |

**Hygiene Queue 语义**：WARN 不再阻塞主线（避免反复停下等人裁决）；
Agent 在阶段收尾时把 Queue 一次性呈给用户批量裁决，而不是逐项打断。

## 铁律：绝不自动删除

- 卫生检查器**只检测**，输出证据与候选处理方案
- WARN 项由 Agent 展示证据（是什么、多大、最后修改时间），给用户三个选项：保留（说明理由）/ 归档（移入 docs/archive 或删除前先提交）/ 删除
- "看起来没用"不构成删除理由；只有用户确认后才执行，且优先用 git（可回滚）而非 rm

## 运行时机

| 时机 | 范围 | 动作 |
|------|------|------|
| 项目初始化前（REFACTOR/FEATURE 第一步） | 全量 | 建立卫生基线，脏项先处置再动工 |
| 每个阶段完成后（VERIFY_MODULE/INTEGRATE） | 增量关注 | 新 WARN 当场处置，不让临时文件过夜 |
| 发布前（RELEASE_CHECK） | 全量 | 有 CRITICAL 一律阻断发布 |

## Artifact Policy（v3.1：测试证据与源码分离）

| 资产 | 归属 |
|------|------|
| 源码 / 配置 / Migration / 正式文档 | Git |
| 测试截图 / coverage / HTML 报告 / 临时日志 | **CI Artifacts 或临时工作目录**（任务结束清理） |
| 正式测试样例 | tests/fixtures（入 Git） |
| 正式产品截图 | docs/ 或产品资料库，需显式 allowlist |

- 卫生检查器对根目录的 screenshots/coverage/logs/test-results 类条目报 WARN 并建议 .gitignore
- 截图类证据如需留存，放入 `.gitignore` 声明的目录（如 gui-test-screenshots/），**不提交**

## 与其他检查器的分工

```
inspect-project.py        只读侦察 → PROJECT BASELINE（信息，不定级）
check-project-hygiene.py  混入物检测 → PASS/WARN/CRITICAL（CRITICAL 阻断）
validate-project.py       结构合规 → 分层/必备文件（FAIL 阻断）
check-security.py         密钥/端口 → CRITICAL 阻断
```

## 已知误报豁免（脚本内置）

- `scripts/`、`docs/`、`tests/` 目录内的 backup/restore/old 等命名是运维与文档的正常组成（如官方推荐的 backup.sh），不做二级扫描
- `*.md` 顶层文档、常规工具配置（.editorconfig/.prettierrc 等）在允许清单内
- 遇到新的误报模式：优先修脚本的豁免规则并记录 CHANGELOG，而不是让用户忽略告警
