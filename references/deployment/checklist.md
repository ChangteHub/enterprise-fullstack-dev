# 完整部署流程与验证清单

> **Pre-Check（加载前确认）：** 服务器配置（几核几G/OS）？域名解析到服务器 IP 了吗？数据库用 Docker 容器还是云数据库？有备案吗（国内服务器需要）？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 8 步部署执行记录 + 每步验证结果。

## 8 步部署流程

### 第1步：准备服务器

- 购买云服务器（阿里云/腾讯云，2核4G起步）
- 操作系统选 Ubuntu 22.04 LTS
- 记录公网 IP
- 配置安全组：开放 22/80/443 端口

### 第2步：安装基础环境

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 安装 Nginx
apt install nginx -y
systemctl enable nginx

# 安装 Node.js（前端构建用，也可以在本地构建后上传）
curl -fsSL https://deb.nodesource.com/setup_20.x | bash
apt install nodejs -y
```

### 第3步：配置环境变量

```bash
# 创建项目目录
mkdir -p /opt/student
cd /opt/student

# 创建 .env 文件（不提交 Git）
cat > .env << 'EOF'
DB_PASSWORD=你的强密码
JWT_SECRET=你的随机密钥(至少32位)
SPRING_PROFILES_ACTIVE=prod
EOF

# 设置权限（只有 root 可读）
chmod 600 .env
```

### 第4步：部署数据库

```bash
# 用 Docker 运行 MySQL
docker run -d \
  --name student-mysql \
  --restart=always \
  -p 127.0.0.1:3306:3306 \
  -e MYSQL_ROOT_PASSWORD=$(grep DB_PASSWORD .env | cut -d= -f2) \
  -e MYSQL_DATABASE=student_db \
  -v mysql_data:/var/lib/mysql \
  mysql:8.4 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci

# 验证 MySQL 启动
docker logs student-mysql
```

### 第5步：构建并部署后端

```bash
# 方式A：在服务器上构建（需要 JDK/Maven）
cd /opt/student/backend
docker build -t student-backend:1.0.0 .

# 方式B：在本地构建推送镜像仓库，服务器拉取
docker pull registry.example.com/student-backend:1.0.0

# 运行后端容器
docker run -d \
  --name student-backend \
  --restart=always \
  -p 127.0.0.1:8080:8080 \
  --env-file /opt/student/.env \
  -e DB_HOST=host.docker.internal \
  --add-host=host.docker.internal:host-gateway \
  student-backend:1.0.0

# 验证后端
curl http://127.0.0.1:8080/api/health
```

> 注意：如果 MySQL 和后端都在 Docker 中，用 docker-compose 编排更方便，服务名 `mysql` 直接作为域名。

### 第6步：构建并部署前端

```bash
cd /opt/student/frontend
npm ci
npm run build

# 复制到 Nginx 静态目录
mkdir -p /var/www/student
cp -r dist/* /var/www/student/
```

### 第7步：配置 Nginx + HTTPS

```bash
# 写入 Nginx 配置（参考 nginx-deployment.md）
vim /etc/nginx/sites-available/student.conf

# 启用站点
ln -s /etc/nginx/sites-available/student.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试配置
nginx -t

# 申请 HTTPS 证书
certbot --nginx -d www.example.com

# 重载 Nginx
nginx -s reload
```

### 第8步：验证与监控

按下方验证清单逐项检查。

## 部署验证清单

### 基础连通性
- [ ] `nslookup www.example.com` 解析到正确服务器 IP
- [ ] `ping 服务器IP` 能通（如果服务器允许 ICMP）
- [ ] `ssh root@服务器IP` 能登录

### HTTPS
- [ ] 访问 `http://www.example.com` 自动跳转到 `https://`
- [ ] 浏览器地址栏显示小锁图标
- [ ] 点击证书查看，域名匹配、在有效期内
- [ ] `curl -I https://www.example.com` 返回 200

### 前端
- [ ] 访问首页正常加载，无白屏
- [ ] F12 Console 无 JS 报错
- [ ] F12 Network 中 JS/CSS/图片全部 200
- [ ] 进入子页面后刷新浏览器，不出现 404（React 路由）
- [ ] 静态资源响应头有 `Cache-Control` 缓存策略
- [ ] `index.html` 响应头是 `no-cache`（不缓存）

### 后端 API
- [ ] `curl http://127.0.0.1:8080/api/health` 返回 200
- [ ] `curl https://www.example.com/api/health` 返回 200（经 Nginx 代理）
- [ ] 登录接口返回 token
- [ ] 带 token 请求受保护接口正常
- [ ] 不带 token 请求受保护接口返回 401
- [ ] 数据库读写正常（创建一条数据再查询）

### 数据库
- [ ] MySQL 容器运行中：`docker ps | grep mysql`
- [ ] Flyway 迁移脚本执行成功（后端日志无迁移错误）
- [ ] 表结构正确：`docker exec -it student-mysql mysql -uroot -p -e "use student_db; show tables;"`
- [ ] 数据持久化：重启容器后数据不丢

### 容器状态
- [ ] 所有容器 `docker ps` 状态为 Up
- [ ] `docker logs student-backend` 无 ERROR 级别日志
- [ ] `docker stats` CPU/内存使用正常
- [ ] 容器重启策略为 `always` 或 `unless-stopped`

### 安全
- [ ] 防火墙只开放 22/80/443：`ufw status`
- [ ] 云安全组只开放 22/80/443
- [ ] MySQL 端口绑定 127.0.0.1，公网无法访问：`ss -tlnp | grep 3306`
- [ ] 后端端口绑定 127.0.0.1，公网无法访问：`ss -tlnp | grep 8080`
- [ ] `.env` 文件权限 600，内容不含弱密码
- [ ] JWT 密钥是随机强密钥，不是默认值
- [ ] 数据库密码是强密码

### Nginx
- [ ] `nginx -t` 配置语法通过
- [ ] `systemctl status nginx` 运行正常
- [ ] 访问日志有记录：`tail /var/log/nginx/student_access.log`
- [ ] 错误日志无异常：`tail /var/log/nginx/student_error.log`
- [ ] gzip 压缩生效（响应头有 `Content-Encoding: gzip`）

### 恢复能力
- [ ] 重启服务器后所有服务自动启动（`docker restart` 策略 + systemd）
- [ ] 后端容器崩溃后自动重启（`--restart=always`）
- [ ] 有数据库备份方案（定时 `mysqldump` 或云数据库自动备份）

## 回滚方案

### 后端回滚
```bash
# 停止当前版本
docker stop student-backend && docker rm student-backend

# 运行上一个版本
docker run -d \
  --name student-backend \
  --restart=always \
  -p 127.0.0.1:8080:8080 \
  --env-file /opt/student/.env \
  student-backend:0.9.0  # 上一个稳定版本
```

### 前端回滚
```bash
# 保留上一个版本的 dist
cp -r /var/www/student /var/www/student.bak

# 出问题时恢复
rm -rf /var/www/student
cp -r /var/www/student.bak /var/www/student
nginx -s reload
```

### 数据库回滚
- Flyway 不支持自动回滚，需要手动写回滚脚本
- 部署前备份数据库：`docker exec student-mysql mysqldump -uroot -p student_db > backup_$(date +%Y%m%d).sql`
- 出问题时恢复：`docker exec -i student-mysql mysql -uroot -p student_db < backup_xxx.sql`

## 数据库备份脚本

```bash
#!/bin/bash
# /opt/student/backup.sh
BACKUP_DIR="/opt/student/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec student-mysql mysqldump -uroot -p$(grep DB_PASSWORD /opt/student/.env | cut -d= -f2) student_db > $BACKUP_DIR/student_$DATE.sql

# 保留最近7天的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "备份完成: student_$DATE.sql"
```

设置定时任务：
```bash
chmod +x /opt/student/backup.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/student/backup.sh") | crontab -
```
