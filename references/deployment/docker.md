# Docker 容器化规范

> **Pre-Check（加载前确认）：** 部署目标 OS（Linux 发行版）？本地需要哪些依赖服务（MySQL/Redis）？镜像仓库选 Docker Hub / 阿里云 / 私有 Harbor？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 前后端 Dockerfile + docker-compose 一键启动文件。

## 后端 Dockerfile（多阶段构建）

```dockerfile
# ===== 构建阶段 =====
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /app

# 先复制 pom.xml，利用 Docker 缓存依赖
COPY pom.xml .
COPY mvnw .
COPY .mvn .mvn
RUN ./mvnw dependency:go-offline -B

# 复制源码并打包
COPY src ./src
RUN ./mvnw clean package -DskipTests -B

# ===== 运行阶段 =====
FROM eclipse-temurin:21-jre
WORKDIR /app

# 从构建阶段复制 jar
COPY --from=builder /app/target/*.jar app.jar

# 非 root 用户运行（安全）
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8080

# JVM 参数：容器感知内存 + GC 优化
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0 -XX:+UseG1GC -XX:+ExitOnOutOfMemoryError"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

### 多阶段构建的好处
- 最终镜像只包含 JRE，不包含 JDK 和 Maven，体积小（~200MB vs ~600MB）
- 构建过程和运行环境分离
- 源码不会留在最终镜像里

### .dockerignore

```
target/
.idea/
.vscode/
*.iml
.git/
.gitignore
Dockerfile
docker-compose.yml
README.md
```

## 前端 Dockerfile（可选，通常直接用 Nginx 提供 dist）

```dockerfile
# ===== 构建阶段 =====
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ===== 运行阶段 =====
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

> 更常见的做法：前端在本地或 CI 中 `npm run build` 生成 `dist/`，直接上传到服务器由 Nginx 提供，不需要为前端单独构建 Docker 镜像。

## docker-compose.yml（本地开发）

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.4
    container_name: student-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-root123}
      MYSQL_DATABASE: student_db
    ports:
      - "127.0.0.1:3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:7-alpine
    container_name: student-redis
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: student-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      DB_HOST: mysql
      DB_PORT: 3306
      DB_NAME: student_db
      DB_USERNAME: root
      DB_PASSWORD: ${DB_PASSWORD:-root123}
      JWT_SECRET: ${JWT_SECRET:-dev-secret}
      SPRING_PROFILES_ACTIVE: dev
    depends_on:
      - mysql
      - redis

volumes:
  mysql_data:
  redis_data:
```

### 关键要点
- 端口语义（v3.1.1 澄清，两层不是一回事）：
  **Host published port**（compose 的 `ports:`）默认只绑 `127.0.0.1`，避免直接暴露公网；
  **容器内服务监听**按容器网络需要监听容器接口（如 Spring Boot `0.0.0.0`）——
  保护来自宿主机端口绑定与 Nginx 唯一入口，而不是让容器内进程监听 127.0.0.1
- 公网只开放业务真正需要的端口；管理入口（SSH/DB/监控）通过安全组/VPN/来源限制控制，而非一刀切端口表
- DB 优先走内部 Docker network，不发布公网端口
- 服务名（`mysql`、`redis`）作为容器间通信的域名
- `depends_on` 控制启动顺序（但不等待服务就绪，应用要自己做重试）
- 数据用 named volume 持久化，容器删除数据不丢
- 环境变量用 `${VAR:-default}` 支持 `.env` 文件覆盖

## 镜像管理规范

### 标签策略
- 用语义化版本：`student-backend:1.0.0`、`student-backend:1.1.0`
- 不用 `latest`（不可追踪、无法回滚）
- 可以同时打 Git commit hash 标签：`student-backend:a1b2c3d`
- 生产部署用固定版本标签，不用浮动标签

### 镜像仓库
- 个人/小项目：Docker Hub 或阿里云容器镜像服务
- 企业：私有 Harbor 仓库
- 推送前先登录：`docker login registry.example.com`

### 构建与推送命令

```bash
# 构建
docker build -t registry.example.com/student-backend:1.0.0 ./backend

# 推送
docker push registry.example.com/student-backend:1.0.0

# 服务器拉取并运行
docker pull registry.example.com/student-backend:1.0.0
docker run -d \
  --name student-backend \
  --restart=always \
  -p 127.0.0.1:8080:8080 \
  --env-file .env \
  registry.example.com/student-backend:1.0.0
```

## 容器安全规范

- 非 root 用户运行容器（Dockerfile 中 `USER appuser`）
- 镜像基础版本固定，不用 `latest`
- 敏感信息通过环境变量或 Secret 注入，不写进镜像
- 生产容器不挂载宿主机敏感目录
- 定期更新基础镜像修复安全漏洞
- 不用 `--privileged` 特权模式

## 常用运维命令

```bash
# 查看运行中的容器
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 查看日志
docker logs student-backend           # 查看全部日志
docker logs -f student-backend        # 实时跟踪
docker logs --tail 100 student-backend # 最后100行

# 进入容器
docker exec -it student-backend sh

# 重启容器
docker restart student-backend

# 停止并删除容器
docker stop student-backend && docker rm student-backend

# 查看容器资源使用
docker stats

# 清理无用镜像和容器
docker system prune -a
```

## 健康检查

Dockerfile 中加健康检查：

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1
```

Spring Boot 加 `spring-boot-starter-actuator`，暴露 `/actuator/health` 端点作为健康检查。
