# 进阶组件：Redis / 消息队列 / Elasticsearch

> **Pre-Check（加载前确认）：** 具体遇到了什么问题（DB 性能瓶颈？异步任务？搜索慢？）？确认不用这些组件无法解决吗？MQ 选 RabbitMQ 还是 Kafka？ES 数据同步方案（双写/Canal）？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 先确认真实需求，再产出对应组件集成代码。

> **前置原则：先用最少技术把业务跑通，再因真实问题增加技术。** 以下组件都不是 CRUD 项目必须的，只有遇到对应的真实问题时才引入。

## Redis：解决高频访问数据库的问题

### 什么时候引入

- 同一个查询被高频访问，数据库成为性能瓶颈
- 需要分布式会话共享（多实例部署时用户登录状态共享）
- 需要排行榜、计数器、分布式锁等数据结构场景
- 热点数据（首页、详情页）读取远多于写入

### 没有缓存 vs 有缓存

```
没有缓存：用户 → 后端 → MySQL（每次都查数据库）
有缓存：  用户 → 后端 → Redis（命中直接返回）
                      ↓ miss（未命中）
                     MySQL → 写入 Redis → 返回
```

### Cache Aside 模式（最常用缓存策略）

```
读：先查 Redis → 命中返回；未命中查 MySQL → 结果写入 Redis → 返回
写：先更新 MySQL → 再删除 Redis 缓存（下次读时重建）
```

### Spring Boot 集成

**依赖：**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

**配置（application.yml）：**
```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      password: ${REDIS_PASSWORD:}
      timeout: 3000ms
      lettuce:
        pool:
          max-active: 8
          max-idle: 4
          min-idle: 0
```

**缓存代码示例（Service 层）：**
```java
@Service
@RequiredArgsConstructor
public class StudentServiceImpl implements StudentService {

    private final StudentRepository studentRepository;
    private final StringRedisTemplate redisTemplate;

    private static final String CACHE_KEY = "student:";
    private static final Duration CACHE_TTL = Duration.ofMinutes(30);

    @Override
    @Transactional(readOnly = true)
    public StudentResponse getById(Long id) {
        String key = CACHE_KEY + id;

        // 1. 先查 Redis
        String cached = redisTemplate.opsForValue().get(key);
        if (cached != null) {
            return objectMapper.readValue(cached, StudentResponse.class);
        }

        // 2. 未命中查数据库
        Student student = studentRepository.findById(id)
            .orElseThrow(() -> new BusinessException(404, "学生不存在"));
        StudentResponse response = studentMapper.toResponse(student);

        // 3. 写入 Redis，设置过期时间
        redisTemplate.opsForValue().set(key, objectMapper.writeValueAsString(response), CACHE_TTL);

        return response;
    }

    @Override
    @Transactional
    public StudentResponse update(Long id, StudentUpdateRequest request) {
        Student student = studentRepository.findById(id)
            .orElseThrow(() -> new BusinessException(404, "学生不存在"));
        studentMapper.updateEntity(request, student);
        student = studentRepository.save(student);

        // 更新数据库后删除缓存（Cache Aside）
        redisTemplate.delete(CACHE_KEY + id);

        return studentMapper.toResponse(student);
    }
}
```

### 缓存三大问题及防护

| 问题 | 发生原因 | 后果 | 解决方案 |
|------|---------|------|---------|
| **缓存穿透** | 查询不存在的数据，Redis 没有、MySQL 也没有，每次都打到数据库 | 数据库被恶意请求打垮 | ① 缓存空值（设短TTL）② 布隆过滤器 |
| **缓存击穿** | 某个热点 key 过期瞬间，大量并发请求同时打到数据库 | 数据库瞬时压力过大 | ① 热点数据永不过期 ② 互斥锁（只让一个线程查库重建缓存） |
| **缓存雪崩** | 大量 key 同时过期，或 Redis 宕机 | 数据库大面积压力 | ① TTL 加随机偏移 ② Redis 集群高可用 ③ 限流降级 |

### Redis 不是什么

- 不是"比 MySQL 更好的数据库"，不适合长期存储核心业务数据
- 数据在内存中，重启可能丢失（虽然有持久化，但不如关系数据库可靠）
- 不支持复杂 SQL 查询和事务关联

---

## 消息队列（MQ）：解决"现在不用马上做完"的问题

### 什么时候引入

- 有异步处理需求（发短信、发邮件、生成报表、推送通知），不需要让用户等
- 需要服务间解耦（下单后通知服务、积分服务、数据分析服务各自消费）
- 需要削峰填谷（秒杀时请求先进队列，后端按能力消费）
- 简单 CRUD 项目不需要 MQ

### 异步事件驱动流程

```
下单请求
  ↓
保存订单（同步，必须立即完成）
  ↓
发送"订单已创建"事件 → 消息队列
                      ├→ 通知服务（发短信/邮件）
                      ├→ 积分服务（加积分）
                      └→ 数据分析服务（统计）
```

### RabbitMQ 集成（Spring Boot）

**依赖：**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
```

**配置：**
```yaml
spring:
  rabbitmq:
    host: ${RABBITMQ_HOST:localhost}
    port: 5672
    username: ${RABBITMQ_USERNAME:guest}
    password: ${RABBITMQ_PASSWORD:guest}
```

**队列配置：**
```java
@Configuration
public class RabbitMQConfig {
    public static final String STUDENT_QUEUE = "student.created.queue";
    public static final String STUDENT_EXCHANGE = "student.exchange";
    public static final String STUDENT_ROUTING_KEY = "student.created";

    @Bean
    public Queue studentQueue() {
        return QueueBuilder.durable(STUDENT_QUEUE).build();
    }

    @Bean
    public TopicExchange studentExchange() {
        return ExchangeBuilder.topicExchange(STUDENT_EXCHANGE).durable(true).build();
    }

    @Bean
    public Binding binding(Queue studentQueue, TopicExchange studentExchange) {
        return BindingBuilder.bind(studentQueue).to(studentExchange).with(STUDENT_ROUTING_KEY);
    }
}
```

**生产者（发送消息）：**
```java
@Service
@RequiredArgsConstructor
public class StudentServiceImpl {

    private final RabbitTemplate rabbitTemplate;

    @Override
    @Transactional
    public StudentResponse create(StudentCreateRequest request) {
        Student student = studentMapper.toEntity(request);
        student = studentRepository.save(student);

        // 发送事件（异步，不阻塞主流程）
        StudentCreatedEvent event = new StudentCreatedEvent(student.getId(), student.getName());
        rabbitTemplate.convertAndSend(
            RabbitMQConfig.STUDENT_EXCHANGE,
            RabbitMQConfig.STUDENT_ROUTING_KEY,
            event
        );

        return studentMapper.toResponse(student);
    }
}
```

**消费者（异步处理，如发通知）：**
```java
@Component
@Slf4j
@RequiredArgsConstructor
public class NotificationConsumer {

    private final EmailService emailService;

    @RabbitListener(queues = RabbitMQConfig.STUDENT_QUEUE)
    public void onStudentCreated(StudentCreatedEvent event) {
        try {
            log.info("收到学生创建事件: id={}", event.getStudentId());
            emailService.sendWelcomeEmail(event.getName());
        } catch (Exception e) {
            log.error("处理学生创建事件失败: id={}", event.getStudentId(), e);
            // 消息确认机制：失败后重试或进入死信队列
        }
    }
}
```

### MQ 使用注意事项

- 消费者要做**幂等处理**（同一条消息可能重复投递，处理多次结果要相同）
- 消息消费失败要有**重试 + 死信队列**机制
- 消息体用 JSON，不要直接序列化 Java 对象（跨语言兼容）
- MQ 会增加系统复杂度和运维成本，简单异步需求可以先用 Spring `@Async` 代替

---

## Elasticsearch：解决专业全文搜索的问题

### 什么时候引入

- MySQL LIKE 模糊查询在大数据量下太慢（`%keyword%` 无法用索引）
- 需要中文分词搜索、多字段联合搜索、搜索结果相关性排序
- 需要日志检索分析（ELK 架构）
- 简单搜索先用 MySQL LIKE + 索引，满足不了再引入 ES

### MySQL vs ES 分工

| 问题 | 优先工具 | 原因 |
|------|---------|------|
| 保存核心业务数据 | MySQL | 事务、一致性、结构化查询 |
| 热点数据快速读取 | Redis | 内存访问、缓存 |
| 异步任务/事件 | MQ | 解耦、削峰 |
| 全文搜索/日志检索 | Elasticsearch | 倒排索引、分词、相关性评分 |

### Spring Boot 集成

**依赖：**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-elasticsearch</artifactId>
</dependency>
```

**文档实体：**
```java
@Document(indexName = "student")
@Data
public class StudentDocument {
    @Id
    private Long id;

    @Field(type = FieldType.Text, analyzer = "ik_max_word")
    private String name;

    @Field(type = FieldType.Keyword)
    private String studentNo;

    @Field(type = FieldType.Text, analyzer = "ik_max_word")
    private String major;
}
```

**搜索 Repository：**
```java
public interface StudentSearchRepository extends ElasticsearchRepository<StudentDocument, Long> {

    // 多字段全文搜索
    @Query("{\"multi_match\":{\"query\":\"?0\",\"fields\":[\"name\",\"major\"]}}")
    Page<StudentDocument> search(String keyword, Pageable pageable);
}
```

**搜索 Service：**
```java
@Service
@RequiredArgsConstructor
public class StudentSearchService {

    private final StudentSearchRepository searchRepository;

    public Page<StudentDocument> search(String keyword, int page, int size) {
        return searchRepository.search(keyword, PageRequest.of(page - 1, size));
    }

    // 数据同步：MySQL 写入后同步到 ES（也可以用 Canal 监听 binlog 自动同步）
    public void syncToEs(Student student) {
        StudentDocument doc = new StudentDocument();
        doc.setId(student.getId());
        doc.setName(student.getName());
        doc.setStudentNo(student.getStudentNo());
        doc.setMajor(student.getMajor());
        searchRepository.save(doc);
    }
}
```

### ES 使用注意事项

- ES 不是数据源，**MySQL 仍然是主存储**，ES 只存搜索需要的字段（冗余）
- MySQL 和 ES 的数据同步：简单项目在 Service 里双写；复杂项目用 Canal 监听 MySQL binlog 自动同步
- 需要安装 IK 分词器插件支持中文分词
- ES 集群运维成本高，小项目可以用云搜索服务

---

## 引入决策速查

| 你遇到的问题 | 引入什么 | 不引入会怎样 |
|-------------|---------|------------|
| 同一个查询每次都查库，数据库 CPU 高 | Redis 缓存 | 数据库压力大，响应慢，但功能正常 |
| 发邮件/短信让用户等了3秒 | MQ 异步 | 用户体验差，但功能正常 |
| 下单后要同时通知3个服务，耦合严重 | MQ 解耦 | 代码耦合，改一个服务要动主流程 |
| 搜索框 LIKE 查询10万条数据要2秒 | Elasticsearch | 查询慢，但功能正常 |
| 没有以上问题 | **什么都不引入** | 完全没问题 |
