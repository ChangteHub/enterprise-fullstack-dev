# 可观测性规范（日志、指标、链路追踪）

> **Pre-Check（加载前确认）：** 当前是单体还是微服务（决定是否需要链路追踪）？需要监控哪些核心指标？日志保留多久？告警通知渠道（邮件/钉钉/企业微信）？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 结构化日志格式 + 指标/健康端点配置。

## 三支柱

| 支柱 | 回答的问题 | 工具 |
|------|-----------|------|
| **日志（Logs）** | 发生了什么？具体错误信息？ | Logback + 文件/ELK |
| **指标（Metrics）** | 系统现在怎么样？QPS、延迟、错误率？ | Micrometer + Prometheus + Grafana |
| **链路追踪（Traces）** | 一个请求经过了哪些服务？哪里慢？ | OpenTelemetry + Jaeger |

> 学生项目和小项目：日志 + 基础指标就够了。链路追踪在微服务架构下才有必要。

## 日志规范

### 日志级别

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| ERROR | 系统错误、需要立即处理 | 数据库连接失败、空指针异常 |
| WARN | 潜在问题、不影响主流程 | 配置缺失用默认值、重试 |
| INFO | 关键业务节点、系统状态 | 用户登录、订单创建、服务启动 |
| DEBUG | 调试信息、开发阶段用 | 方法入参出参、SQL 参数 |
| TRACE | 最详细、极少用 | 方法调用栈 |

### 日志格式（结构化）

```json
{
  "timestamp": "2024-01-15T10:30:00.123",
  "level": "INFO",
  "thread": "http-nio-8080-exec-1",
  "logger": "com.example.student.controller.StudentController",
  "message": "创建学生成功",
  "traceId": "abc123def456",
  "userId": "1001",
  "studentId": "2001"
}
```

### Logback 配置（logback-spring.xml）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <springProperty scope="context" name="APP_NAME" source="spring.application.name" defaultValue="student"/>

    <!-- 控制台输出 -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- 文件输出（按天滚动） -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>/var/log/${APP_NAME}/app.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>/var/log/${APP_NAME}/app.%d{yyyy-MM-dd}.log</fileNamePattern>
            <maxHistory>30</maxHistory>
            <totalSizeCap>1GB</totalSizeCap>
        </rollingPolicy>
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} [%X{traceId}] - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- 错误日志单独文件 -->
    <appender name="ERROR_FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>/var/log/${APP_NAME}/error.log</file>
        <filter class="ch.qos.logback.classic.filter.ThresholdFilter">
            <level>ERROR</level>
        </filter>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>/var/log/${APP_NAME}/error.%d{yyyy-MM-dd}.log</fileNamePattern>
            <maxHistory>90</maxHistory>
        </rollingPolicy>
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} [%X{traceId}] - %msg%n</pattern>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="FILE"/>
        <appender-ref ref="ERROR_FILE"/>
    </root>

    <!-- 调整特定包的日志级别 -->
    <logger name="com.example.student" level="DEBUG"/>
    <logger name="org.springframework.web" level="INFO"/>
    <logger name="org.hibernate.SQL" level="DEBUG"/> <!-- 打印SQL -->
</configuration>
```

### 日志最佳实践

- 用 SLF4J 门面（`@Slf4j` 注解），不直接用具体实现
- 用占位符 `{}`，不用字符串拼接：`log.info("用户 {} 登录成功", userId)`
- 异常日志要带堆栈：`log.error("创建学生失败", e)`
- 生产环境日志级别设 INFO，DEBUG 只在排查问题时临时开启
- 日志文件按天滚动，保留 30 天，总大小限制
- 关键操作记录审计日志（谁在什么时候做了什么）
- 不在日志中打印密码、token 等敏感信息

## 指标（Metrics）

### Spring Boot Actuator

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  endpoint:
    health:
      show-details: when-authorized
  metrics:
    tags:
      application: ${spring.application.name}
```

### 关键监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| `http_server_requests_seconds` | HTTP 请求延迟 | P99 > 3s |
| `http_server_requests_count` | 请求量（QPS） | 突增 200% |
| `jvm_memory_used_bytes` | JVM 内存使用 | > 80% |
| `jvm_gc_pause_seconds` | GC 停顿时间 | 单次 > 1s |
| `hikaricp_connections_active` | 数据库活跃连接 | > 80% 最大连接 |
| `system_cpu_usage` | CPU 使用率 | > 80% 持续 5 分钟 |
| `process_uptime_seconds` | 进程运行时间 | 频繁重启 |
| 自定义：业务指标 | 订单量、注册量等 | 根据业务设定 |

### 自定义业务指标

```java
@Service
@RequiredArgsConstructor
public class StudentService {
    private final MeterRegistry meterRegistry;

    public StudentResponse create(StudentCreateRequest request) {
        // 计数：创建学生次数
        meterRegistry.counter("student.create.count").increment();

        // 计时：方法执行时间
        Timer.Sample sample = Timer.start(meterRegistry);
        try {
            // ... 业务逻辑
        } finally {
            sample.stop(meterRegistry.timer("student.create.duration"));
        }
    }
}
```

### Prometheus + Grafana（可选）

- Prometheus 定时抓取 `/actuator/prometheus` 端点
- Grafana 配置 Prometheus 数据源，导入 Spring Boot 仪表盘模板（ID: 12900）
- 设置告警规则，异常时发邮件/钉钉通知

> 学生项目可以先用 Actuator 的 `/actuator/health` 和 `/actuator/metrics` 手动查看，Prometheus+Grafana 在有真实用户后再引入。

## 链路追踪（Traces）

### 引入条件
- 微服务架构（一个请求经过多个服务）
- 需要定位跨服务的性能瓶颈
- 单体应用不需要

### OpenTelemetry 集成

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 1.0  # 采样率，生产环境建议 0.1
  otlp:
    tracing:
      endpoint: http://jaeger:4318/v1/traces
```

### traceId 传递
- 每个请求生成唯一 traceId
- 通过 HTTP Header `X-Trace-Id` 在服务间传递
- 日志中打印 traceId，方便关联日志和链路
- 前端也可以生成 traceId，通过请求头传给后端

## 健康检查

### Actuator 健康端点

```java
@Component
public class DatabaseHealthIndicator implements HealthIndicator {
    private final DataSource dataSource;

    @Override
    public Health health() {
        try (Connection conn = dataSource.getConnection()) {
            if (conn.isValid(1)) {
                return Health.up().withDetail("database", "connected").build();
            }
            return Health.down().withDetail("database", "connection invalid").build();
        } catch (Exception e) {
            return Health.down(e).withDetail("database", "error").build();
        }
    }
}
```

### Docker 健康检查引用

Dockerfile 中：
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1
```

## 告警通知

### 简单方案（学生项目）
- 写一个定时脚本，每分钟 `curl /actuator/health`
- 返回非 200 时发邮件/钉钉通知
- 用 `crontab` 定时执行

### 专业方案
- Prometheus Alertmanager 配置告警规则
- 告警渠道：邮件、钉钉、企业微信、PagerDuty
- 分级：P0（立即处理）、P1（工作时间处理）、P2（记录即可）

## 可观测性引入时机

| 阶段 | 需要什么 |
|------|---------|
| 版本1-2 | 控制台日志 + 文件日志（Logback 配置好就行） |
| 版本3 | Actuator 健康检查 + 基础指标 |
| 版本4 | Prometheus + Grafana 仪表盘 + 告警 |
| 版本5 | 结构化日志 + ELK/Loki 日志聚合 |
| 版本6（微服务） | OpenTelemetry + Jaeger 链路追踪 |

**不要在项目初期就搭全套监控，先有日志，再逐步加指标和追踪。**
