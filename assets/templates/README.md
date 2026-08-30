# assets/templates — 可复用模板

> assets 与 references 的分工：references 给 AI 读（知识），assets 给 AI 复制改造（材料）。以下均为参考模板（Reference Template），复制后必须按项目实际包名/业务调整，不逐字照抄。

| 模板 | 用途 | 何时用 |
|------|------|--------|
| `backend/Result.java` | 统一响应包装 `Result<T>`（code/message/data） | 新建后端统一响应结构时 |
| `deployment/docker-compose.yml` | 单台 VPS 安全基线 compose（Nginx 唯一公网入口、backend/db 绑 127.0.0.1、密钥走 env 注入） | 部署到单台 VPS 时 |

## 使用规则

1. 复制到项目对应位置后，先改包名、再改业务字段，保证与项目分层一致；
2. 模板中的 `${ENV_VAR}` 是注入占位：密钥/密码一律走环境变量或 `.env`（不入 Git），不得把示例值硬编码提交；
3. 改动须满足 SKILL.md 的 Code Usage Policy：正确性优先（P0/P1）、不破坏分层、改动可解释。
