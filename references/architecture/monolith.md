# Monorepo 根目录结构规范（简单单体模式）

> **Pre-Check（加载前确认）：** 确认用 Mode A（frontend/ + backend/）？需要 Git Hooks（husky）做提交检查吗？需要 Makefile 简化命令吗？团队统一用 VSCode 吗？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** Mode A 根目录配置文件全集。

## 完整目录树

```
project-root/
├── .github/                        # GitHub 平台配置
├── .husky/                         # Git Hooks 自动化
├── .vscode/                        # 团队共享编辑器配置
├── docs/                           # 项目文档
├── scripts/                        # 运维/部署脚本
├── frontend/                       # React 前端子项目
├── backend/                        # Spring Boot 后端子项目
├── docker-compose.yml              # 本地开发编排
├── docker-compose.prod.yml         # 生产环境编排（可选）
├── .env                            # 本地环境变量（不提交Git）
├── .env.example                    # 环境变量模板（提交Git）
├── .gitignore                      # Git 忽略规则
├── .gitattributes                  # Git 属性（行尾、大文件）
├── .editorconfig                   # 编辑器统一配置
├── .prettierrc                     # 代码格式化规则
├── .prettierignore                 # Prettier 忽略文件
├── Makefile                        # 常用命令快捷方式（可选）
├── README.md                       # 项目说明
├── CHANGELOG.md                    # 版本变更日志（可选）
└── LICENSE                         # 开源协议（可选）
```

## 各目录/文件详细说明

### .github/ — GitHub 平台配置

```
.github/
├── workflows/
│   └── ci-cd.yml                   # CI/CD 工作流（详见 cicd.md）
├── ISSUE_TEMPLATE/
│   ├── bug_report.md               # Bug 报告模板
│   └── feature_request.md          # 功能需求模板
├── PULL_REQUEST_TEMPLATE.md        # PR 描述模板
└── dependabot.yml                  # 依赖自动更新（可选）
```

**PULL_REQUEST_TEMPLATE.md 模板：**
```markdown
## 变更内容
<!-- 描述这个 PR 做了什么 -->

## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 其他

## 测试
- [ ] 单元测试通过
- [ ] 本地手动验证
- [ ] 无需测试（文档/配置变更）

## 截图（如适用）

## 关联 Issue
Closes #
```

### .husky/ — Git Hooks 自动化

在代码提交前自动运行检查，防止不规范代码进入仓库。

```
.husky/
├── pre-commit        # git commit 前触发
└── commit-msg        # 校验提交信息格式
```

**安装方式：**
```bash
npm install -D husky lint-staged
npx husky init
```

**pre-commit 内容：**
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# 前端：只检查暂存的文件
npx lint-staged
```

**commit-msg 内容（校验 Conventional Commits）：**
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

commit_regex='^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)(\(.+\))?: .+'
error_msg="提交信息格式错误，必须符合 Conventional Commits 规范，例如：feat: 添加学生管理功能"

if ! grep -qE "$commit_regex" "$1"; then
  echo "$error_msg"
  exit 1
fi
```

**package.json 中配置 lint-staged：**
```json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{css,md,json}": ["prettier --write"]
  }
}
```

### .vscode/ — 团队共享编辑器配置

```
.vscode/
├── settings.json       # 统一编辑器设置
└── extensions.json     # 推荐安装的插件
```

**settings.json：**
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "files.eol": "\n",
  "files.encoding": "utf8",
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,
  "[java]": {
    "editor.defaultFormatter": "redhat.java"
  }
}
```

**extensions.json：**
```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "redhat.java",
    "vscjava.vscode-spring-boot-dashboard",
    "ms-azuretools.vscode-docker",
    "editorconfig.editorconfig"
  ]
}
```

### docs/ — 项目文档

```
docs/
├── architecture.md     # 系统架构设计（技术选型、模块划分、部署架构图）
├── api.md              # API 接口文档（或用 Swagger 自动生成，这里放补充说明）
├── database.md         # 数据库设计（ER 图、表结构说明、索引设计理由）
├── deployment.md       # 部署文档（环境要求、部署步骤、回滚方案）
└── dev-guide.md        # 开发指南（本地启动、调试、编码规范）
```

> 文档要和代码同步更新。架构变更、API 变更、数据库变更时必须更新对应文档。

### scripts/ — 运维/部署脚本

```
scripts/
├── deploy.sh           # 一键部署到服务器
├── backup.sh           # 数据库定时备份
├── init-db.sh          # 本地数据库初始化（建库、跑迁移、灌测试数据）
└── logs.sh             # 快速查看各服务日志
```

**init-db.sh 示例：**
```bash
#!/bin/bash
# 本地数据库初始化脚本
set -e

echo "启动 MySQL..."
docker-compose up -d mysql

echo "等待 MySQL 就绪..."
until docker exec student-mysql mysqladmin ping -uroot -proot123 --silent; do
  sleep 2
done

echo "创建数据库..."
docker exec student-mysql mysql -uroot -proot123 -e "CREATE DATABASE IF NOT EXISTS student_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "数据库初始化完成"
```

### 根目录配置文件

#### .editorconfig — 编辑器统一配置

跨编辑器/IDE 的统一代码格式配置，确保所有人的缩进、行尾、编码一致。

```ini
# EditorConfig is awesome: https://EditorConfig.org
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false

[*.{java,xml,yml,yaml,sql}]
indent_size = 4

[Makefile]
indent_style = tab
```

#### .prettierrc — 代码格式化规则

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "endOfLine": "lf",
  "arrowParens": "always"
}
```

#### .gitignore — Git 忽略规则

```gitignore
# ===== 依赖 =====
node_modules/
**/node_modules/
target/
**/target/

# ===== 构建产物 =====
dist/
build/
out/
*.jar
*.war

# ===== 环境变量 =====
.env
.env.local
.env.*.local
!.env.example

# ===== IDE =====
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
*.iml
*.ipr
*.iws

# ===== 系统 =====
.DS_Store
Thumbs.db
desktop.ini

# ===== 日志 =====
*.log
logs/
npm-debug.log*

# ===== 测试覆盖 =====
coverage/
.nyc_output/

# ===== 临时文件 =====
*.tmp
*.temp
*.swp
*.swo
```

#### .gitattributes — Git 属性

```gitattributes
# 统一行尾为 LF
* text=auto eol=lf

# 明确指定文本文件
*.md text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.xml text eol=lf
*.sql text eol=lf

# 二进制文件不做行尾转换
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.woff binary
*.woff2 binary
*.ttf binary
*.jar binary
```

#### .env.example — 环境变量模板

```bash
# ===== 数据库 =====
DB_HOST=localhost
DB_PORT=3306
DB_NAME=student_db
DB_USERNAME=root
DB_PASSWORD=your_strong_password

# ===== JWT =====
JWT_SECRET=your_jwt_secret_key_at_least_32_chars
JWT_EXPIRATION=86400000

# ===== 应用 =====
SPRING_PROFILES_ACTIVE=dev
SERVER_PORT=8080

# ===== Redis（可选） =====
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Makefile — 常用命令快捷方式（可选）

把常用的长命令简化为 `make xxx`，团队成员不用记复杂命令。

```makefile
.PHONY: help dev build test deploy clean db-init db-backup logs

# 默认目标：显示帮助
help:
	@echo "可用命令："
	@echo "  make dev        - 启动本地开发环境（MySQL+Redis）"
	@echo "  make backend    - 启动后端开发服务"
	@echo "  make frontend   - 启动前端开发服务"
	@echo "  make build      - 构建前后端"
	@echo "  make test       - 运行全部测试"
	@echo "  make deploy     - 部署到生产环境"
	@echo "  make db-init    - 初始化本地数据库"
	@echo "  make db-backup  - 备份数据库"
	@echo "  make logs       - 查看各服务日志"
	@echo "  make clean      - 清理构建产物和容器"

dev:
	docker-compose up -d mysql redis

backend:
	cd backend && ./mvnw spring-boot:run

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm ci && npm run build
	cd backend && ./mvnw clean package -DskipTests

test:
	cd frontend && npm run test -- --run
	cd backend && ./mvnw test

deploy:
	bash scripts/deploy.sh

db-init:
	bash scripts/init-db.sh

db-backup:
	bash scripts/backup.sh

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf frontend/dist backend/target
```

#### README.md — 项目说明

必须包含：项目简介、技术栈、快速开始（本地启动步骤）、项目结构、部署方式、贡献指南。

```markdown
# 项目名称

## 简介
一句话描述项目是做什么的。

## 技术栈
- 前端：React 18 + TypeScript + Vite + Ant Design
- 后端：Java 21 + Spring Boot 3 + MySQL 8
- 部署：Docker + Nginx

## 快速开始

### 前置要求
- Node.js 20+
- JDK 21
- Docker & Docker Compose

### 本地启动
```bash
# 1. 克隆项目
git clone <repo-url>
cd project-root

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 3. 启动依赖服务
make dev

# 4. 初始化数据库
make db-init

# 5. 启动后端（另一个终端）
make backend

# 6. 启动前端（另一个终端）
make frontend
```

访问 http://localhost:5173

## 项目结构
见 [docs/architecture.md](docs/architecture.md)

## 部署
见 [docs/deployment.md](docs/deployment.md)

## 贡献
提交代码前请确保通过 lint 和测试，提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)。
```

## 脚手架创建顺序

创建新项目时，按以下顺序建立根目录结构：

1. `git init` 初始化仓库
2. 创建 `.gitignore`、`.gitattributes`、`.editorconfig`
3. 创建 `.env.example`，复制为 `.env` 并填入本地配置
4. 创建 `docker-compose.yml` 启动 MySQL/Redis
5. 创建 `frontend/`（Vite 脚手架）和 `backend/`（Spring Initializr）
6. 创建 `docs/` 文档目录，先写 architecture.md 和 dev-guide.md
7. 创建 `scripts/` 运维脚本
8. 配置 `.husky/` + `lint-staged` + `commitlint`
9. 配置 `.github/workflows/` CI/CD
10. 写 `README.md`

> 最小可用版本可以只建 frontend/、backend/、docker-compose.yml、.env.example、.gitignore、README.md。其他工程化文件在项目稳定后逐步补充。
