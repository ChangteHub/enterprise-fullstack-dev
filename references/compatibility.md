# 版本兼容性规范（Baseline + 冲突处理）

> 职责：当项目实际版本与本 Skill 基线冲突时，决定"沿用本地还是升级"。SKILL.md Layer 2 只保留"先检测本地版本，再决定"的原则，详细矩阵在这里维护。

## Pre-Check（加载前确认）

- 当前任务是否真的遇到版本冲突（构建失败、依赖不兼容、API 不存在、Node/Java 版本报错）？
- 是否要为新项目生成依赖/环境配置？

未遇到版本冲突时不需要读本文件，按 SKILL.md Layer 2 基线直接生成；不要为"检查版本"而加载。

## 基线矩阵（Baseline）

| Layer | 基线 | 说明 |
|-------|------|------|
| Frontend | React 18.x + TypeScript 5.x + Vite 5.x | Function Component + Hooks |
| UI | Ant Design 5.x 或 Tailwind CSS 3.x | 二选一，不混用 |
| Node | 20 LTS（Vite 5 要求 >=18） | 前端构建环境 |
| Backend | Java 21 + Spring Boot 3.3.x | Spring Boot 3 要求 Java 17+ |
| Database | MySQL 8.0.x | Flyway 10.x 管理 schema |
| Container | Docker 24+ / Compose v2 | dev 与部署一致 |

## 冲突处理策略（Policy）

1. **先检测**：动手前先读项目实际版本（`package.json`、`pom.xml`、`application.yml`、`node -v`、`mvn -version`）。
2. **本地可运行优先**：项目已锁定的小版本优先于 Skill 基线；生成依赖/配置以本地实际版本为准。
3. **大版本不自动升级**：不为"最新版"自动升级项目大版本（React 18→19、Boot 2→3、MySQL 5.7→8 均属破坏性变更）。
4. **差异必须显式说明**：在最终报告 Assumptions/Warnings 中写明"本地为 X，Skill 基线为 Y，按 X 处理，原因是 Z"。
5. **新项目**：直接采用基线版本，不从 EOL 版本起步。

## 常见不兼容对照（踩坑速查）

| 变更 | 影响 | 处理 |
|------|------|------|
| Spring Boot 2.x → 3.x | `javax.*` → `jakarta.*`；需 Java 17+；Spring Security 配置体系重写 | 按 Boot 3 语法生成，不混用 javax |
| React 18 → 19 | 类型与部分行为变化 | 基线仍为 18，除非项目已是 19 |
| MySQL 5.7 → 8.0 | 默认字符集 utf8mb4；认证插件 caching_sha2_password；only_full_group_by 默认开启 | 驱动与连接串同步升级 |
| Node < 18 | Vite 5/6 无法运行 | 建议升级 Node 而非降级 Vite |
| Flyway 与 MySQL 配套 | 老库配新 Flyway 可能有 schema 校验问题 | Flyway 版本与团队现状锁定一致 |

## 参考模板（Reference Template）

本文件是版本判断的参考模板，不是强制升级指南；具体项目以 P1 Correctness（能编译、能运行、不引入 bug）为最终裁决。

## Deliverable（读完必须产出）

- 版本对齐结论：沿用本地版本 / 采用基线 / 计划升级（含风险说明），三选一。
- 若与基线不同：把差异与理由写进最终报告的 Assumptions。
