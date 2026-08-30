# Kubernetes 基础规范（容器编排）

> **Pre-Check（加载前确认）：** 确认 Docker Compose 已经不够用了？有几台服务器？几个服务需要编排？需要自动扩缩容吗？团队有人能运维 K8s 集群吗？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 先确认 Docker Compose 不够用，再产出基础编排 YAML。

> **K8s 不是必须的。** 只有一台 VPS、流量不大、服务很少时，Docker Compose + Nginx 完全够用。K8s 的价值在于管理大量容器和多台服务器，不是"更高级"的象征。

## 什么时候需要 K8s

| 条件 | Docker Compose | Kubernetes |
|------|---------------|------------|
| 服务器数量 | 1 台 | 多台组成集群 |
| 服务数量 | 1-5 个 | 几十个以上 |
| 需要自动扩缩容 | 不需要 | 流量波动大，需要自动增减实例 |
| 需要滚动更新零停机 | 手动停启（有短暂中断） | 声明式滚动更新，自动保证可用性 |
| 需要故障自愈 | `--restart=always`（容器级） | Pod 级自动调度恢复（节点宕机也能恢复） |
| 团队规模 | 1-3 人 | 多人协作，需要标准化部署 |

**以下情况绝对不要上 K8s：**
- 只有一台 VPS，学生项目/毕业设计
- 服务不超过 5 个，QPS 很低
- 团队没人懂 K8s 运维
- Docker Compose 已经能稳定运行

## 核心概念（用最简单的话理解）

| K8s 对象 | 生活化理解 | 用途 |
|---------|-----------|------|
| **Pod** | 一个正在运行的应用实例（里面装着容器） | K8s 中可部署的最小计算单位，一个 Pod 通常装一个应用容器 |
| **Deployment** | "我要运行几个副本、用哪个镜像版本" | 管理 Pod 的副本数、滚动更新、回滚 |
| **Service** | "其他服务怎么找到它"（稳定的内部网络入口） | Pod 会重启换 IP，Service 提供固定访问地址和负载均衡 |
| **Ingress** | "公网请求怎么进入集群"（HTTP/HTTPS 路由） | 相当于集群内的 Nginx，按域名/路径转发到不同 Service |
| **ConfigMap** | 普通配置文件 | 注入非敏感配置（环境变量、配置文件） |
| **Secret** | 加密的配置 | 注入密码、Token、密钥（Base64 编码，配合 RBAC 限制访问） |
| **Namespace** | 虚拟集群分区 | 隔离 dev/staging/prod 环境或不同团队 |

## 请求在 K8s 中的流转路径

```
公网用户
  ↓ https://www.example.com
Ingress（HTTP 路由，相当于 Nginx）
  ↓ 按路径转发
Service（稳定网络入口 + 负载均衡）
  ↓ 分发到多个副本
Pod × N（实际运行的应用容器）
  ↓
数据库（集群内 Service 或云数据库）
```

## 基础 YAML 模板

### Deployment（部署后端服务）

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: student-backend
  labels:
    app: student-backend
spec:
  replicas: 2                          # 运行 2 个副本（高可用）
  selector:
    matchLabels:
      app: student-backend
  template:                            # Pod 模板
    metadata:
      labels:
        app: student-backend
    spec:
      containers:
        - name: backend
          image: registry.example.com/student-backend:1.0.0    # 固定版本，不用 latest
          ports:
            - containerPort: 8080
          resources:                   # 资源限制（防止一个服务吃光集群资源）
            requests:                  # 最小保障
              cpu: 250m
              memory: 512Mi
            limits:                    # 最大上限
              cpu: 500m
              memory: 1Gi
          envFrom:
            - configMapRef:
                name: backend-config   # 普通配置
            - secretRef:
                name: backend-secret   # 敏感配置
          readinessProbe:              # 就绪探针：通过才接收流量
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:               # 存活探针：失败自动重启 Pod
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 30
```

### Service（内部网络入口 + 负载均衡）

```yaml
# backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: student-backend-svc
spec:
  selector:
    app: student-backend              # 选中带这个 label 的 Pod
  ports:
    - port: 8080                      # Service 监听端口
      targetPort: 8080                # 转发到容器的端口
  type: ClusterIP                     # 只在集群内部访问（默认类型）
```

> 其他 Pod 通过 `http://student-backend-svc:8080` 访问这个服务，服务名就是域名，不需要知道具体 Pod IP。

### Ingress（公网入口路由）

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    cert-manager.io/cluster-issuer: letsencrypt-prod    # 自动 HTTPS 证书
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - www.example.com
      secretName: tls-secret
  rules:
    - host: www.example.com
      http:
        paths:
          # 前端静态文件
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-svc
                port:
                  number: 80
          # 后端 API
          - path: /api/
            pathType: Prefix
            backend:
              service:
                name: student-backend-svc
                port:
                  number: 8080
```

### ConfigMap（非敏感配置）

```yaml
# backend-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
data:
  SPRING_PROFILES_ACTIVE: "prod"
  DB_HOST: "mysql-svc"
  DB_PORT: "3306"
  DB_NAME: "student_db"
  REDIS_HOST: "redis-svc"
```

### Secret（敏感配置）

```yaml
# backend-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
type: Opaque
stringData:                          # stringData 直接写明文，K8s 自动编码
  DB_PASSWORD: "your_strong_password"
  JWT_SECRET: "your_jwt_secret_at_least_32_chars"
```

> 生产环境建议用外部 Secret 管理方案（Sealed Secrets、Vault、云厂商 KMS），不要把 Secret YAML 提交到 Git。

## 常用 kubectl 命令

```bash
# 部署应用
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml

# 查看状态
kubectl get pods                    # 查看所有 Pod
kubectl get svc                     # 查看所有 Service
kubectl get ingress                 # 查看 Ingress
kubectl describe pod <pod-name>     # 查看 Pod 详细事件（排查启动失败）

# 日志和调试
kubectl logs <pod-name>             # 查看日志
kubectl logs -f <pod-name>          # 实时跟踪日志
kubectl exec -it <pod-name> -- sh   # 进入容器

# 扩缩容
kubectl scale deployment student-backend --replicas=3    # 手动扩到3副本

# 更新和回滚
kubectl set image deployment/student-backend backend=registry.example.com/student-backend:1.1.0
kubectl rollout status deployment/student-backend       # 查看滚动更新状态
kubectl rollout undo deployment/student-backend         # 回滚到上一版本
kubectl rollout history deployment/student-backend      # 查看版本历史
```

## 从 Docker Compose 演进到 K8s 的对应关系

| Docker Compose | Kubernetes | 说明 |
|---------------|------------|------|
| `services:` | Deployment + Pod | 每个 service 对应一个 Deployment |
| `ports:` | Service | 服务发现和负载均衡 |
| `environment:` | ConfigMap + Secret | 配置和敏感信息分离 |
| `depends_on:` | 没有直接对应 | K8s 设计为服务解耦，应用要自己做连接重试 |
| `volumes:` | PersistentVolume / PVC | 持久化存储 |
| `restart: always` | livenessProbe + Deployment | 自动重启和故障恢复 |
| `docker-compose up` | `kubectl apply -f` | 声明式部署 |
| Nginx 反向代理 | Ingress | 集群内统一入口 |

## 演进路径

1. **阶段1-2**：Docker Compose 部署（单服务器，够用）
2. **阶段3-4**：Docker Compose + 云数据库/Redis（数据层托管）
3. **阶段5**：服务变多，考虑 Docker Swarm（轻量编排）或直接上云托管 K8s
4. **阶段6**：多服务器集群、需要自动扩缩容时，正式引入 Kubernetes

**不要在阶段1就搭 K8s 集群。**
