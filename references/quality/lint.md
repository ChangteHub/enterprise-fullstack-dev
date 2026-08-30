# Lint Baseline + Ratchet（质量债收敛）

> **Pre-Check（加载前确认）：** 项目是否已存在 lint 存量警告？CI 是否只拦 error 不拦 warning？——只拦 error 等于放养：warning 只会从 59 涨到 100。
>
> 本文件为策略参考模板（Reference Template）：Baseline/Ratchet/Debt Register 三件套是规范，工具实现随 lint 品牌调整。
>
> **Deliverable（读完必须产出）：** 本项目的 lint baseline 数值 + Debt Register 文件 + CI ratchet 接线。

## 三件套

### 1. Baseline（存量冻结）

```
# CI 中：
npx eslint frontend/src            # errors 阻断（永远）
npx eslint frontend/src --max-warnings 59   # 超过基线即失败
```

- 本次 ≤59 → PASS；60 → FAIL；55 → PASS + 改进（应下调基线）
- **基线只降不升**：每次真实消减 warning 后，把 `--max-warnings` 数字下调并记入 CHANGELOG

### 2. Ratchet（增量清零）

- 新代码引入的新 warning 会让总数超基线 → 自动阻断
- 效果：存量不恶化，增量必须干净；无需一次性大修

### 3. Accepted Technical Debt Register（债务登记簿）

不修的 warning 必须登记（通常放 `docs/lint-debt.md` 或 CI 任务说明）：

| 字段 | 说明 | 示例 |
|------|------|------|
| rule | 规则名 | react-hooks/exhaustive-deps |
| file / line | 定位 | pages/Home/index.tsx:35 |
| reason | 为什么不修 | 挂载即拉取的惯用写法，改依赖数组会改变行为 |
| owner | 谁负责 | @someone |
| target_version | 计划解决版本 | v2.2 |
| status | accepted / planned / resolved | accepted |

**没有登记簿的 warning = 遗忘的 warning**。登记簿让"不修"成为被评审的显式决策。

## lint-baseline.json（债务登记簿的机器格式）

CI ratchet 的 `--max-warnings` 只看总数；每条"决定不修"的债务在本文件登记：

```json
{
  "baseline": 59,
  "updated_at": "2026-08-30",
  "debts": [
    {
      "rule": "react-hooks/exhaustive-deps",
      "file": "frontend/src/pages/Home/index.tsx",
      "line": 35,
      "reason": "挂载即拉取的惯用写法，改依赖数组会改变行为",
      "owner": "@someone",
      "target_version": "v2.2",
      "status": "accepted"
    }
  ]
}
```

- `baseline` 只降不升；消减后同步下调并记 CHANGELOG
- `status`: accepted（评审通过不修）/ planned（排期）/ resolved（已消除）

## 与 CI 的关系

- pre-commit（Husky/lint-staged）：本地快速反馈，`--fix` 自动修可修项
- CI：`--max-warnings <baseline>` 作为最终门禁（本地钩子可被 --no-verify 绕过，CI 是真门禁）
- 分支保护（如可用）：required check 指向 lint job
