# 大型 Monorepo 结构规范（apps + services + packages）

> **Pre-Check（加载前确认）：** 确认用 Mode B？几个前端 app / 后端 service？需要 packages 共享代码吗？包管理器用 pnpm workspace？需要 Turborepo 构建编排吗？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** apps/services/packages 结构 + pnpm workspace 配置。

## 适用场景

当项目满足以下条件时，使用大型 Monorepo 结构：
- 有**多个前端应用**（如用户端 web + 管理员后台 admin + 移动端 H5）
- 有**多个后端服务**（按业务拆分为 auth-service、user-service、order-service 等）
- 需要**共享代码**（多个应用共用 UI 组件库、工具函数、类型定义）
- 团队人数较多（5 人以上），需要统一管理基础设施和部署配置
- 需要统一的 CI/CD、监控、测试体系

**不满足以上条件时，用简单单体模式（frontend/ + backend/）即可，不要过度设计。**

## 完整目录树

```
project-root/
├── apps/                            # 前端应用（可多个，每个内部结构同 frontend/structure.md）
│   ├── web/                         # 用户端网站
│   ├── admin/                       # 管理员后台
│   └── mobile/                      # 移动端 H5（可选）
├── services/                        # 后端服务（可多个，每个内部结构同 backend/structure.md）
│   ├── auth-service/                # 登录、身份认证、权限
│   ├── user-service/                # 用户资料、个人中心
│   ├── student-service/             # 学生业务（增删改查）
│   ├── course-service/              # 课程业务
│   └── notification-service/        # 通知（短信、邮件、站内信）
├── packages/                        # 多应用/多服务共享的代码
│   ├── shared-types/                # 共享 TypeScript 类型定义
│   │   ├── src/
│   │   │   ├── api.ts               # 统一 API 响应类型
│   │   │   ├── user.ts              # 用户相关类型
│   │   │   └── index.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── shared-utils/                # 通用工具函数（前端用）
│   │   ├── src/
│   │   │   ├── format.ts            # 日期/金额格式化
│   │   │   ├── validate.ts          # 表单校验
│   │   │   └── index.ts
│   │   └── package.json
│   └── ui/                          # 共享 UI 组件库
│       ├── src/
│       │   ├── Button/
│       │   ├── Table/
│       │   ├── Modal/
│       │   └── index.ts
│       ├── package.json
│       └── vite.config.ts           # 组件库构建配置（库模式）
├── database/                        # 数据库相关（统一管理）
│   ├── migrations/                  # Flyway/Liquibase 表结构变更记录
│   │   ├── V1__init_schema.sql
│   │   ├── V2__create_user_table.sql
│   │   └── V3__add_student_table.sql
│   └── seeds/                       # 初始化/演示数据
│       ├── dev/                     # 开发环境测试数据
│       │   └── seed_users.sql
│       └── prod/                    # 生产环境初始数据（如管理员账号）
│           └── init_admin.sql
├── infrastructure/                  # 基础设施配置
│   ├── docker/
│   │   ├── mysql/
│   │   │   └── my.cnf               # MySQL 配置文件
│   │   ├── redis/
│   │   │   └── redis.conf
│   │   └── nginx/
│   │       └── nginx.conf           # 统一 Nginx 配置
│   ├── kubernetes/                  # K8s 部署配置（微服务阶段才需要）
│   │   ├── base/                    # 基础配置
│   │   │   ├── auth-service.yaml
│   │   │   ├── user-service.yaml
│   │   │   └── ingress.yaml
│   │   └── overlays/                # 环境覆盖
│   │       ├── dev/
│   │       ├── staging/
│   │       └── prod/
│   └── terraform/                   # 基础设施即代码（可选，云资源管理）
│       └── main.tf
├── deploy/                          # 不同环境的发布配置
│   ├── dev/                         # 开发环境
│   │   ├── .env                     # 开发环境变量
│   │   └── docker-compose.dev.yml   # 开发环境编排
│   ├── staging/                     # 测试/预发布环境
│   │   ├── .env
│   │   └── docker-compose.staging.yml
│   └── prod/                        # 生产环境
│       ├── .env                     # 生产环境变量（不提交Git，只存模板）
│       ├── .env.example
│       └── docker-compose.prod.yml
├── monitoring/                      # 监控配置
│   ├── prometheus/
│   │   └── prometheus.yml           #  Prometheus 抓取配置
│   ├── grafana/
│   │   ├── dashboards/              # 仪表盘 JSON
│   │   │   └── spring-boot.json
│   │   └── datasources/
│   │       └── prometheus.yml
│   └── otel/                        # OpenTelemetry 链路追踪
│       └── otel-collector-config.yaml
├── tests/                           # 项目级测试（跨服务/跨应用）
│   ├── integration/                 # 集成测试（服务间调用）
│   │   └── auth-flow.test.ts
│   ├── e2e/                         # 端到端测试（Playwright/Cypress）
│   │   ├── login.spec.ts
│   │   └── student-crud.spec.ts
│   └── performance/                 # 性能测试（k6）
│       └── load-test.js
├── docs/                            # 项目文档
│   ├── architecture.md              # 系统架构设计
│   ├── api.md                       # API 文档（或用 Swagger 自动生成）
│   ├── database.md                  # 数据库设计
│   ├── deployment.md                # 部署文档
│   └── dev-guide.md                 # 开发指南
├── scripts/                         # 自动化脚本
│   ├── deploy.sh                    # 一键部署
│   ├── backup.sh                    # 数据库备份
│   ├── init-db.sh                   # 数据库初始化
│   └── new-service.sh               # 脚手架：创建新后端服务
├── .github/
│   ├── workflows/                   # CI/CD 流水线
│   │   ├── ci.yml                   # 代码检查+测试
│   │   ├── build.yml                # 构建镜像
│   │   └── deploy.yml               # 部署
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── .husky/                          # Git Hooks
├── .vscode/                         # 编辑器配置
├── .env.example                     # 根环境变量模板
├── .gitignore / .gitattributes
├── .editorconfig / .prettierrc
├── docker-compose.yml               # 本地一键启动所有依赖（MySQL+Redis+各服务）
├── package.json                     # 根 package.json（Monorepo 工具配置）
├── pnpm-workspace.yaml              # pnpm workspace 配置（推荐）
├── turbo.json                       # Turborepo 配置（构建编排，可选）
├── Makefile                         # 常用命令快捷方式
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## 各目录详细说明

### apps/ — 前端应用

每个子目录都是一个独立的前端应用，内部结构完全遵循 [frontend/structure.md](../frontend/structure.md)。

```
apps/
├── web/            # 用户端：学生、教师使用的主站
├── admin/          # 管理端：系统管理员后台
└── mobile/         # 移动端：H5 页面（可选，也可以用 web 响应式代替）
```

**共享代码**：多个应用共用的组件、工具、类型放在 `packages/` 里，通过包名引用（如 `@project/ui`、`@project/shared-types`），不要在 apps 之间互相 import。

### services/ — 后端服务

每个子目录都是一个独立的 Spring Boot 服务，内部结构完全遵循 [backend/structure.md](../backend/structure.md)。

```
services/
├── auth-service/        # 认证服务：登录、注册、JWT、权限
├── user-service/        # 用户服务：用户资料、头像、个人设置
├── student-service/     # 学生服务：学生 CRUD、班级、专业
├── course-service/      # 课程服务：课程、选课、成绩
└── notification-service/ # 通知服务：短信、邮件、站内信（异步）
```

**服务间通信**：
- 同步调用：OpenFeign / RestTemplate（服务名作为域名）
- 异步通信：消息队列（RabbitMQ/Kafka），如 notification-service 消费消息发通知
- 服务发现：Nacos / Eureka / Consul（微服务阶段才需要）

**数据库**：
- 每个服务有自己独立的数据库（或独立 schema），服务间不直接访问对方的数据库
- 跨服务数据一致性用最终一致性（事件驱动），不用分布式事务

### packages/ — 共享代码

Monorepo 的核心优势：一份代码，多处复用。

```
packages/
├── shared-types/     # TS 类型定义：API 响应类型、业务实体类型
├── shared-utils/     # 工具函数：格式化、校验、加密
└── ui/               # UI 组件库：按钮、表格、表单、布局
```

**包管理工具**：推荐用 **pnpm workspace**（比 npm/yarn 快，磁盘占用小）。

**pnpm-workspace.yaml：**
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

**根 package.json：**
```json
{
  "name": "campus-management-system",
  "private": true,
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "test": "turbo run test"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  }
}
```

**引用共享包**：在 apps/web/package.json 中：
```json
{
  "dependencies": {
    "@project/ui": "workspace:*",
    "@project/shared-types": "workspace:*",
    "@project/shared-utils": "workspace:*"
  }
}
```

### database/ — 统一数据库管理

大型项目把数据库迁移和种子数据从各个服务中抽出来，统一管理。

```
database/
├── migrations/    # Flyway/Liquibase 迁移脚本（按版本号排序）
└── seeds/         # 初始化数据
    ├── dev/       # 开发环境测试数据
    └── prod/      # 生产环境初始数据
```

> 简单模式下，迁移脚本放在每个后端服务的 `resources/db/migration/` 里。大型模式下统一放在根目录 `database/migrations/`，部署时统一执行。

### infrastructure/ — 基础设施配置

```
infrastructure/
├── docker/        # Docker 相关配置（MySQL/Redis/Nginx 配置文件）
├── kubernetes/    # K8s 部署 YAML（微服务+多节点集群才需要）
└── terraform/     # 基础设施即代码（管理云服务器、数据库、负载均衡）
```

> K8s 和 Terraform 是进阶技术，项目初期不需要。先用 Docker Compose 部署，等服务多了、需要自动扩缩容了再引入 K8s。

### deploy/ — 多环境配置

```
deploy/
├── dev/          # 开发环境：本地或开发服务器
├── staging/      # 预发布环境：测试团队验证用，数据接近生产
└── prod/         # 生产环境：真实用户使用
```

每个环境有独立的 `.env`（数据库地址、密钥、开关）和 `docker-compose` 配置（副本数、资源限制）。

**环境差异表：**

| 配置项 | dev | staging | prod |
|--------|-----|---------|------|
| 数据库 | 本地 Docker | 独立测试库 | 生产主库+只读从库 |
| 日志级别 | DEBUG | INFO | WARN |
| 副本数 | 1 | 1-2 | 2+ |
| HTTPS | 不需要 | 需要 | 必须 |
| 监控 | 可选 | 基础 | 完整+告警 |

### monitoring/ — 监控配置

```
monitoring/
├── prometheus/    # 指标抓取配置
├── grafana/       # 仪表盘和数据源配置
└── otel/          # OpenTelemetry 链路追踪收集器
```

详见 [deployment/observability.md](../deployment/observability.md)。

### tests/ — 项目级测试

```
tests/
├── integration/    # 集成测试：验证服务间调用、数据库交互
├── e2e/            # 端到端测试：Playwright/Cypress 模拟真实用户操作
└── performance/    # 性能测试：k6 压测，验证 QPS 和延迟
```

> 单元测试放在各自应用/服务的 `src/test/` 里。项目级测试放根目录 `tests/`。

## 本地启动（docker-compose.yml）

大型 Monorepo 的根目录 docker-compose.yml 一键启动所有依赖和服务：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.4
    ports: ["127.0.0.1:3306:3306"]
    environment:
      MYSQL_ROOT_PASSWORD: root123
    volumes:
      - mysql_data:/var/lib/mysql
      - ./infrastructure/docker/mysql/my.cnf:/etc/mysql/conf.d/my.cnf

  redis:
    image: redis:7-alpine
    ports: ["127.0.0.1:6379:6379"]

  auth-service:
    build: ./services/auth-service
    ports: ["127.0.0.1:8081:8080"]
    environment:
      DB_HOST: mysql
      REDIS_HOST: redis
    depends_on: [mysql, redis]

  user-service:
    build: ./services/user-service
    ports: ["127.0.0.1:8082:8080"]
    environment:
      DB_HOST: mysql
    depends_on: [mysql]

  student-service:
    build: ./services/student-service
    ports: ["127.0.0.1:8083:8080"]
    environment:
      DB_HOST: mysql
    depends_on: [mysql]

  web:
    build: ./apps/web
    ports: ["127.0.0.1:3000:80"]
    depends_on: [auth-service, user-service, student-service]

volumes:
  mysql_data:
```

## 模式选择决策树

```
项目规模？
├── 单人/2-3人小团队，单应用单后端
│   └── → 简单单体模式（frontend/ + backend/）
│
├── 多个前端应用（web+admin），但还是单后端
│   └── → 中等模式（apps/ + backend/ + packages/）
│
└── 多前端 + 多后端微服务 + 大团队
    └── → 大型 Monorepo（apps/ + services/ + packages/ + infrastructure/ + deploy/ + monitoring/）
```

**核心原则：从简单模式开始，随着项目增长逐步演进。不要一开始就搭大型 Monorepo，90% 的项目用简单模式就够了。**

## 演进路径

1. **阶段1**：`frontend/` + `backend/`（单体，简单模式）
2. **阶段2**：加 `packages/` 共享代码，前端拆为 `apps/web/` + `apps/admin/`
3. **阶段3**：后端按业务拆为 `services/auth-service/` + `services/user-service/` 等
4. **阶段4**：加 `infrastructure/kubernetes/`，用 K8s 部署
5. **阶段5**：加 `monitoring/` 完整监控体系、`tests/e2e/` 端到端测试

每个阶段都是可运行的完整系统，不要跳阶段。
