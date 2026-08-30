# Test Data Lifecycle（测试数据生命周期）

> **Pre-Check（加载前确认）：** 测试需要哪些账号/数据？目标数据库是本地受控环境吗？——生产环境禁用本生命周期的一切写操作。
>
> 本文件为策略参考模板（Reference Template）：三阶段与环境保护规则是规范，实现见 `scripts/seed-test-data.sh` / `verify-test-data.sh` / `reset-test-data.sh`。
>
> **Deliverable（读完必须产出）：** 本项目的 seed/verify/reset 三件套就位并通过一次真实执行。

## 三阶段

```
seed（幂等播种）→ verify（就位校验）→ [测试] → reset（清理，与 seed 配对）
```

| 阶段 | 脚本 | 要求 |
|------|------|------|
| seed | `seed-test-data.sh` | 幂等（唯一键 upsert，重复执行不重复造数）；只创建声明过的测试数据；入 Git 可评审 |
| verify | `verify-test-data.sh` | 校验种子数据就位，作为 smoke test 的前置检查（PASS 才开测） |
| reset | `reset-test-data.sh` | 只清理 seed 创建的数据（列出影响行数 + 显式确认），不触碰真实数据 |

## 环境保护（硬规则）

1. 只允许作用于**本地受控数据库**（脚本实现：本地 docker compose 容器 + 3306 只绑 loopback，否则拒绝）
2. `.env` 缺失 / 容器未运行 → 直接拒绝
3. **生产环境禁止 ad-hoc SQL 创建测试账号**——即便开发环境允许手工 SQL，也不得作为默认操作路径
4. 统一 `utf8mb4` 客户端字符集（避免 bash→mysql 乱码，实践中真实踩过）

## 与凭据生命周期的关系

测试账号的密码是**已知测试值**（如 `Test only` 语义），与生产凭据严格隔离；生产管理员凭据走
references/security/credentials.md 的六阶段（受控交付/首登改密/轮换/恢复），两者不可混用。

## 项目接入

把 Skill 的三个脚本复制到项目 `scripts/`，按项目表结构调整 seed SQL 与 verify 断言；
`check-project-gap.py` 会把"启用数据库但缺 seed 脚本"列为 MEDIUM 差距。
