# CI/CD 规范（GitHub Actions）

> **Pre-Check（加载前确认）：** 代码托管在 GitHub 还是 GitLab？只做 CI（检查+测试）还是全自动 CD 部署？服务器 SSH 免密登录配置好了吗？有镜像仓库吗？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 可运行的 CI/CD workflow 文件。

## 适用场景

当项目部署频繁（每周多次）、手动部署容易出错、或需要自动化测试时引入。小项目手动部署也可以，但 CI/CD 能显著提升效率和可靠性。

## 工作流设计

```
代码推送到 main 分支
    ↓
1. 代码检查（Lint + TypeScript 类型检查）
2. 运行测试（前端单元测试 + 后端单元测试）
3. 构建前端（npm run build → dist/）
4. 构建后端 Docker 镜像并推送到镜像仓库
5. SSH 到服务器，拉取新镜像，重启容器，更新前端文件
6. 通知（成功/失败）
```

## GitHub Actions 配置

### 主工作流（.github/workflows/ci-cd.yml）

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: registry.example.com
  IMAGE_NAME: student-backend

jobs:
  # ===== 前端检查与构建 =====
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: TypeScript check
        working-directory: frontend
        run: npx tsc --noEmit

      - name: Lint
        working-directory: frontend
        run: npm run lint

      - name: Test
        working-directory: frontend
        run: npm run test -- --run

      - name: Build
        working-directory: frontend
        run: npm run build

      - name: Upload dist artifact
        uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: frontend/dist/

  # ===== 后端测试与构建 =====
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'

      - name: Test
        working-directory: backend
        run: ./mvnw test

      - name: Build Docker image
        if: github.ref == 'refs/heads/main'
        working-directory: backend
        run: |
          docker build -t $REGISTRY/$IMAGE_NAME:${{ github.sha }} .
          docker tag $REGISTRY/$IMAGE_NAME:${{ github.sha }} $REGISTRY/$IMAGE_NAME:latest

      - name: Login to registry
        if: github.ref == 'refs/heads/main'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Push image
        if: github.ref == 'refs/heads/main'
        run: |
          docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}
          docker push $REGISTRY/$IMAGE_NAME:latest

  # ===== 部署 =====
  deploy:
    needs: [frontend, backend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download frontend dist
        uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: dist/

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            # 更新前端
            rm -rf /var/www/student/*
            # 前端文件通过 scp 上传（这里用 ssh-action 的另一种方式）
            echo "前端更新完成"

            # 更新后端
            docker pull $REGISTRY/$IMAGE_NAME:${{ github.sha }}
            docker stop student-backend || true
            docker rm student-backend || true
            docker run -d \
              --name student-backend \
              --restart=always \
              -p 127.0.0.1:8080:8080 \
              --env-file /opt/student/.env \
              $REGISTRY/$IMAGE_NAME:${{ github.sha }}

            # 清理旧镜像
            docker image prune -f

            echo "部署完成"
```

### 前端文件上传（单独步骤）

由于 `ssh-action` 不直接支持文件上传，用 `scp-action`：

```yaml
      - name: Upload frontend to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          source: "dist/*"
          target: "/var/www/student/"
          strip_components: 1
```

## 需要配置的 Secrets

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名 | 说明 |
|-----------|------|
| `SERVER_HOST` | 服务器公网 IP |
| `SERVER_USER` | SSH 用户名（root） |
| `SERVER_SSH_KEY` | SSH 私钥（用于免密登录） |
| `REGISTRY_USERNAME` | 镜像仓库用户名 |
| `REGISTRY_PASSWORD` | 镜像仓库密码 |

## SSH 免密登录配置

```bash
# 本地生成密钥对（不设密码）
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_actions.pub root@服务器IP

# 复制私钥内容，粘贴到 GitHub Secrets 的 SERVER_SSH_KEY
cat ~/.ssh/github_actions
```

## 简化版：只有测试和构建（不自动部署）

如果不想自动部署到生产环境，可以只做 CI（持续集成），手动触发部署：

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # 前端测试
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: cd frontend && npm ci && npm run test -- --run
      # 后端测试
      - uses: actions/setup-java@v4
        with: { java-version: '21', distribution: 'temurin', cache: 'maven' }
      - run: cd backend && ./mvnw test
```

## 部署策略

### 蓝绿部署（推荐）
- 同时运行两个版本（蓝/绿），Nginx 切换流量
- 新版本验证通过后切流量，出问题立即切回
- 适合对可用性要求高的项目

### 滚动更新
- 逐个替换实例，不中断服务
- 需要多实例（K8s 或负载均衡），单服务器不适用

### 直接替换（学生项目够用）
- 停旧容器 → 启新容器
- 有几秒中断，可接受
- 简单可靠

## CI/CD 引入时机

- 版本1-2：手动部署即可，先把业务跑通
- 版本3+：部署频繁后引入 GitHub Actions
- 不要在项目初期就花大量时间搞复杂的 CI/CD 流水线
