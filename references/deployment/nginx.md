# Nginx 配置与部署规范

> **Pre-Check（加载前确认）：** 域名是什么（DNS 解析好了吗）？有几个前端 app？需要 HTTPS 吗（证书用 Let's Encrypt）？文件上传大小限制？后端服务端口？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** server block + API 反向代理 + HTTPS + 健康检查四项。

## Nginx 核心配置

### 完整生产配置

```nginx
# /etc/nginx/sites-available/student.conf

# HTTP 自动跳转 HTTPS
server {
    listen 80;
    server_name www.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name www.example.com;

    # SSL 证书（certbot 自动配置）
    ssl_certificate /etc/letsencrypt/live/www.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 安全响应头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
    gzip_min_length 1024;

    # 前端静态文件
    location / {
        root /var/www/student/dist;
        index index.html;
        try_files $uri $uri/ /index.html;  # React 路由必须配置

        # 静态资源缓存（带哈希的文件名长期缓存）
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # index.html 不缓存（确保用户拿到最新版本）
        location = /index.html {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;

        # 传递请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # 缓冲
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # 健康检查（可选，供负载均衡器探测）
    location = /health {
        access_log off;
        return 200 "ok";
        add_header Content-Type text/plain;
    }

    # 访问日志
    access_log /var/log/nginx/student_access.log;
    error_log /var/log/nginx/student_error.log;
}
```

### 配置要点说明

| 配置 | 作用 | 必须 |
|------|------|------|
| `try_files $uri $uri/ /index.html;` | React BrowserRouter 路由刷新不 404 | ✅ 必须 |
| `proxy_pass http://127.0.0.1:8080/;` | 转发 API 请求到后端 | ✅ 必须 |
| `proxy_set_header X-Real-IP` | 传递真实客户端 IP 给后端 | ✅ 必须 |
| `proxy_set_header X-Forwarded-Proto` | 告诉后端原始协议是 HTTPS | ✅ 必须 |
| `return 301 https://...` | HTTP 强制跳转 HTTPS | ✅ 必须 |
| `gzip on` | 压缩响应，减少传输量 | 推荐 |
| 静态资源 `expires 30d` | 浏览器缓存静态资源 | 推荐 |
| `index.html` 不缓存 | 确保用户拿到最新版本 | 推荐 |
| 安全响应头 | 防止 XSS、点击劫持等 | 推荐 |

### `proxy_pass` 末尾斜杠的区别

```nginx
# 有斜杠：/api/students → 转发为 /students（去掉 /api 前缀）
location /api/ {
    proxy_pass http://127.0.0.1:8080/;
}

# 无斜杠：/api/students → 转发为 /api/students（保留 /api 前缀）
location /api/ {
    proxy_pass http://127.0.0.1:8080;
}
```

**推荐用有斜杠的方式**，后端 Controller 的 `@RequestMapping` 不需要加 `/api` 前缀。

## 前端部署

### 方式1：直接上传 dist/（推荐学生项目）

```bash
# 本地构建
cd frontend
npm ci
npm run build

# 上传到服务器
scp -r dist/* root@服务器IP:/var/www/student/dist/

# 或者在服务器上拉代码后构建
ssh root@服务器IP
cd /opt/student/frontend
npm ci && npm run build
cp -r dist/* /var/www/student/dist/
```

### 方式2：Docker 运行 Nginx + dist

把前端构建成 Docker 镜像，用容器运行（适合 CI/CD 自动化）。

## HTTPS 证书配置

### Let's Encrypt 免费证书（certbot）

```bash
# 安装 certbot
apt update
apt install certbot python3-certbot-nginx -y

# 申请证书并自动配置 Nginx
certbot --nginx -d www.example.com

# 测试自动续期
certbot renew --dry-run
```

certbot 会自动：
- 验证域名所有权
- 申请证书（有效期 90 天）
- 修改 Nginx 配置加上 SSL
- 设置 systemd timer 自动续期

### 证书文件位置
```
/etc/letsencrypt/live/www.example.com/
├── fullchain.pem   # 证书链（Nginx 用这个）
├── privkey.pem     # 私钥
└── cert.pem        # 单独证书
```

## 域名 DNS 配置

在域名服务商后台添加 DNS 记录：

| 类型 | 主机记录 | 记录值 | 说明 |
|------|---------|--------|------|
| A | www | 服务器公网IP | www.example.com 指向服务器 |
| A | @ | 服务器公网IP | example.com 指向服务器（可选） |
| CNAME | api | www.example.com | api.example.com 别名指向 www（可选） |

> DNS 生效需要时间（几分钟到几小时），用 `nslookup www.example.com` 验证。

## 防火墙配置

### Ubuntu ufw

```bash
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw enable
ufw status verbose
```

### 云服务商安全组

在阿里云/腾讯云控制台的安全组中，入方向规则：
- 22 端口：允许（SSH 远程管理，建议限制来源 IP）
- 80 端口：允许（HTTP）
- 443 端口：允许（HTTPS）
- 其他端口：全部拒绝（3306、6379、8080 等不开放）

## Nginx 常用命令

```bash
nginx -t                  # 测试配置文件语法
nginx -s reload           # 重载配置（不中断服务）
nginx -s stop             # 停止 Nginx
systemctl status nginx    # 查看运行状态
systemctl restart nginx   # 重启 Nginx
tail -f /var/log/nginx/error.log  # 实时查看错误日志
```

## 部署后验证

1. **DNS**：`nslookup www.example.com` 确认解析到正确 IP
2. **HTTP 跳转**：访问 `http://www.example.com` 自动跳转到 HTTPS
3. **HTTPS**：浏览器地址栏有小锁，证书有效
4. **首页**：访问 `https://www.example.com` 页面正常加载
5. **路由刷新**：进入子页面后刷新，不出现 404
6. **API**：`curl https://www.example.com/api/health` 返回成功
7. **静态资源**：F12 Network 面板，JS/CSS 加载状态 200，有缓存头
8. **日志**：`tail /var/log/nginx/error.log` 无异常

## 常见问题排查

| 问题 | 可能原因 | 排查 |
|------|---------|------|
| 502 Bad Gateway | 后端没启动或端口不对 | `docker ps` 看后端容器，`curl 127.0.0.1:8080/api/health` |
| 前端刷新 404 | 缺少 `try_files` 配置 | 检查 Nginx 配置是否有 `try_files $uri $uri/ /index.html;` |
| API 404 | proxy_pass 斜杠问题或后端路径不对 | 确认 `proxy_pass` 末尾有斜杠，后端 Controller 路径匹配 |
| HTTPS 证书错误 | 证书域名不匹配或过期 | `certbot certificates` 查看证书状态 |
| 静态资源 404 | root 路径不对或 dist 没上传 | 检查 `root /var/www/student/dist;` 路径，确认文件存在 |
| 大文件上传失败 | Nginx 默认限制 1M | 加 `client_max_body_size 10m;` |
