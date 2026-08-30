# 后端项目结构规范（Spring Boot 3.x 分层架构）

> **Pre-Check（加载前确认）：** ORM 用 JPA 还是 MyBatis-Plus？包含哪些业务 module？认证方案（JWT/Session/OAuth）？对象转换用 MapStruct 还是手写？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 分层目录 + 一个实体从 Entity 到 Controller 的完整链路代码。

## 目录结构

```
backend/                           # 或 services/student-service/（Monorepo 模式）
├── src/
│   ├── main/
│   │   ├── java/com/example/student/
│   │   │   ├── StudentApplication.java      # 启动类
│   │   │   ├── common/                      # 通用类
│   │   │   │   ├── Result.java              # 统一响应封装
│   │   │   │   ├── PageResult.java          # 分页结果封装
│   │   │   │   └── BusinessException.java   # 业务异常
│   │   │   ├── config/                      # 配置类
│   │   │   │   ├── SecurityConfig.java      # Spring Security 配置
│   │   │   │   ├── WebConfig.java           # Web 配置（CORS、拦截器）
│   │   │   │   ├── JwtConfig.java           # JWT 配置
│   │   │   │   └── MybatisPlusConfig.java   # ORM 配置（分页插件等）
│   │   │   ├── controller/                  # 控制层（接收请求）
│   │   │   │   ├── AuthController.java
│   │   │   │   └── StudentController.java
│   │   │   ├── service/                     # 业务逻辑层
│   │   │   │   ├── AuthService.java         # 接口
│   │   │   │   ├── impl/
│   │   │   │   │   └── AuthServiceImpl.java # 实现
│   │   │   │   ├── StudentService.java
│   │   │   │   └── impl/
│   │   │   │       └── StudentServiceImpl.java
│   │   │   ├── repository/                  # 数据访问层
│   │   │   │   ├── StudentRepository.java
│   │   │   │   └── UserRepository.java
│   │   │   ├── entity/                      # 数据库实体（对应表）
│   │   │   │   ├── Student.java
│   │   │   │   ├── User.java
│   │   │   │   └── Role.java
│   │   │   ├── dto/                         # 数据传输对象
│   │   │   │   ├── request/                 # 请求 DTO
│   │   │   │   │   ├── LoginRequest.java
│   │   │   │   │   ├── StudentCreateRequest.java
│   │   │   │   │   └── StudentUpdateRequest.java
│   │   │   │   └── response/                # 响应 DTO
│   │   │   │       ├── LoginResponse.java
│   │   │   │       └── StudentResponse.java
│   │   │   ├── mapper/                      # 对象转换（Entity ↔ DTO）
│   │   │   │   ├── StudentMapper.java
│   │   │   │   └── UserMapper.java
│   │   │   ├── exception/                   # 异常处理
│   │   │   │   └── GlobalExceptionHandler.java  # 全局异常处理器
│   │   │   ├── security/                    # 认证授权
│   │   │   │   ├── JwtTokenProvider.java    # JWT 工具
│   │   │   │   ├── JwtAuthenticationFilter.java  # JWT 过滤器
│   │   │   │   └── UserDetailsServiceImpl.java
│   │   │   └── annotation/                  # 自定义注解
│   │   │       └── CurrentUser.java
│   │   └── resources/
│   │       ├── application.yml              # 主配置
│   │       ├── application-dev.yml          # 开发环境配置
│   │       ├── application-prod.yml         # 生产环境配置
│   │       ├── db/migration/                # Flyway 迁移脚本
│   │       │   ├── V1__init_schema.sql
│   │       │   └── V2__add_student_table.sql
│   │       └── logback-spring.xml           # 日志配置
│   └── test/
│       └── java/com/example/student/
│           ├── service/                     # Service 单元测试
│           └── controller/                  # Controller 集成测试
├── Dockerfile                               # 多阶段构建
├── .dockerignore
├── pom.xml
└── .gitignore
```

## 分层职责

| 层 | 职责 | 不做什么 |
|----|------|---------|
| **Controller** | 接收 HTTP 请求、参数校验、调用 Service、返回响应 | 不写业务逻辑、不直接操作数据库 |
| **Service** | 业务逻辑、事务管理、调用 Repository 和 Mapper | 不直接处理 HTTP 请求/响应、不手写对象转换 |
| **Repository** | 数据库 CRUD、自定义查询 | 不写业务逻辑 |
| **Entity** | 数据库表映射（JPA 注解） | 不包含业务方法 |
| **DTO** | 请求/响应数据结构 | 不包含业务逻辑 |
| **Mapper** | Entity ↔ DTO 对象转换（MapStruct 自动生成） | 不写业务逻辑、不操作数据库 |

## Mapper 对象转换（MapStruct）

用 MapStruct 在编译期自动生成转换代码，避免手写 getter/setter，性能比反射好。

### pom.xml 依赖

```xml
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>1.5.5.Final</version>
</dependency>
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct-processor</artifactId>
    <version>1.5.5.Final</version>
    <scope>provided</scope>
</dependency>
```

### Mapper 接口（mapper/StudentMapper.java）

```java
@Mapper(componentModel = "spring")
public interface StudentMapper {

    StudentResponse toResponse(Student student);

    Student toEntity(StudentCreateRequest request);

    List<StudentResponse> toResponseList(List<Student> students);

    // 部分更新：把 request 的非空字段复制到已有 entity
    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntity(StudentUpdateRequest request, @MappingTarget Student student);
}
```

### Service 中使用 Mapper

```java
@Service
@RequiredArgsConstructor
public class StudentServiceImpl implements StudentService {

    private final StudentRepository studentRepository;
    private final StudentMapper studentMapper;

    @Override
    @Transactional(readOnly = true)
    public PageResult<StudentResponse> getPage(int page, int size) {
        Page<Student> studentPage = studentRepository.findAll(
            PageRequest.of(page - 1, size, Sort.by(Sort.Direction.DESC, "createdAt")));
        return PageResult.of(studentPage.map(studentMapper::toResponse));
    }

    @Override
    @Transactional
    public StudentResponse create(StudentCreateRequest request) {
        Student student = studentMapper.toEntity(request);
        student = studentRepository.save(student);
        return studentMapper.toResponse(student);
    }

    @Override
    @Transactional
    public StudentResponse update(Long id, StudentUpdateRequest request) {
        Student student = studentRepository.findById(id)
            .orElseThrow(() -> new BusinessException(404, "学生不存在"));
        studentMapper.updateEntity(request, student);  // 部分更新
        student = studentRepository.save(student);
        return studentMapper.toResponse(student);
    }
}
```

> 简单项目也可以手写转换方法（如之前 Service 里的 `toResponse`），但字段多了之后 MapStruct 更省心。两种方式选一种，不要混用。

## 核心代码模板

### 统一响应（common/Result.java）

```java
@Data
@AllArgsConstructor
public class Result<T> {
    private int code;
    private String message;
    private T data;

    public static <T> Result<T> success(T data) {
        return new Result<>(200, "success", data);
    }

    public static <T> Result<T> success() {
        return new Result<>(200, "success", null);
    }

    public static <T> Result<T> error(int code, String message) {
        return new Result<>(code, message, null);
    }
}
```

### Controller 模板

```java
@RestController
@RequestMapping("/api/students")
@RequiredArgsConstructor
public class StudentController {

    private final StudentService studentService;

    @GetMapping
    public Result<PageResult<StudentResponse>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        return Result.success(studentService.getPage(page, size));
    }

    @GetMapping("/{id}")
    public Result<StudentResponse> getById(@PathVariable Long id) {
        return Result.success(studentService.getById(id));
    }

    @PostMapping
    public Result<StudentResponse> create(@Valid @RequestBody StudentCreateRequest request) {
        return Result.success(studentService.create(request));
    }

    @PutMapping("/{id}")
    public Result<StudentResponse> update(@PathVariable Long id,
                                          @Valid @RequestBody StudentUpdateRequest request) {
        return Result.success(studentService.update(id, request));
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        studentService.delete(id);
        return Result.success();
    }
}
```

### Service 接口 + 实现

```java
public interface StudentService {
    PageResult<StudentResponse> getPage(int page, int size);
    StudentResponse getById(Long id);
    StudentResponse create(StudentCreateRequest request);
    StudentResponse update(Long id, StudentUpdateRequest request);
    void delete(Long id);
}

@Service
@RequiredArgsConstructor
public class StudentServiceImpl implements StudentService {

    private final StudentRepository studentRepository;

    @Override
    @Transactional(readOnly = true)
    public PageResult<StudentResponse> getPage(int page, int size) {
        Page<Student> studentPage = studentRepository.findAll(
            PageRequest.of(page - 1, size, Sort.by(Sort.Direction.DESC, "createdAt")));
        return PageResult.of(studentPage.map(this::toResponse));
    }

    @Override
    @Transactional(readOnly = true)
    public StudentResponse getById(Long id) {
        Student student = studentRepository.findById(id)
            .orElseThrow(() -> new BusinessException(404, "学生不存在"));
        return toResponse(student);
    }

    @Override
    @Transactional
    public StudentResponse create(StudentCreateRequest request) {
        Student student = new Student();
        student.setName(request.getName());
        student.setStudentNo(request.getStudentNo());
        student.setMajor(request.getMajor());
        student = studentRepository.save(student);
        return toResponse(student);
    }

    private StudentResponse toResponse(Student student) {
        StudentResponse response = new StudentResponse();
        response.setId(student.getId());
        response.setName(student.getName());
        response.setStudentNo(student.getStudentNo());
        response.setMajor(student.getMajor());
        response.setCreatedAt(student.getCreatedAt());
        return response;
    }
}
```

### 全局异常处理

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        return Result.error(e.getCode(), e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .collect(Collectors.joining("; "));
        return Result.error(400, message);
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {
        log.error("系统异常", e);
        return Result.error(500, "系统内部错误");
    }
}
```

### application.yml（环境变量读取）

```yaml
spring:
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:dev}
  datasource:
    url: jdbc:mysql://${DB_HOST:localhost}:${DB_PORT:3306}/${DB_NAME:student_db}?useSSL=false&serverTimezone=Asia/Shanghai
    username: ${DB_USERNAME:root}
    password: ${DB_PASSWORD:root}
  jpa:
    hibernate:
      ddl-auto: validate    # 生产用 validate，不自动建表，由 Flyway 管理
    show-sql: false
  flyway:
    enabled: true
    locations: classpath:db/migration

jwt:
  secret: ${JWT_SECRET:default-dev-secret-change-in-production}
  expiration: 86400000

server:
  port: 8080
```

## Security：认证与授权（security/ 目录）

### 认证 vs 授权（两个不同概念，不要混淆）

| 概念 | 英文 | 回答的问题 | 例子 | 对应代码 |
|------|------|-----------|------|---------|
| **认证** | Authentication | 你是谁？ | 登录时验证用户名密码，签发 JWT | `JwtTokenProvider`、`AuthController` |
| **授权** | Authorization | 你能做什么？ | 普通学生不能删除其他学生，只有管理员能删 | `@PreAuthorize`、角色检查 |

### 请求安全过滤链

```
请求进来
  ↓
JwtAuthenticationFilter    ← 认证：从 Header 解析 token，确认"你是谁"
  ↓
SecurityContext            ← 把用户身份存入安全上下文
  ↓
权限检查（@PreAuthorize）   ← 授权：确认"你有没有权限做这件事"
  ↓
Controller                 ← 通过后才执行业务
  ↓
Service
```

### JWT + RBAC 基本流程

1. 用户登录（POST /api/auth/login），验证用户名密码（BCrypt 比对）
2. 认证通过，JwtTokenProvider 生成 JWT token（包含 userId、角色）
3. 前端把 token 存 localStorage，之后每个请求 Header 带 `Authorization: Bearer <token>`
4. JwtAuthenticationFilter 拦截请求，解析 token，把用户身份存入 SecurityContext
5. Controller/Service 方法上用 `@PreAuthorize("hasRole('ADMIN')")` 做授权检查
6. token 过期返回 401，已登录但无权限返回 403

### security/ 目录文件职责

| 文件 | 职责 |
|------|------|
| `JwtTokenProvider` | 生成、解析、验证 JWT token |
| `JwtAuthenticationFilter` | 每个请求拦截，从 Header 提取 token 并认证 |
| `UserDetailsServiceImpl` | 从数据库加载用户信息和角色，供 Spring Security 使用 |
| `SecurityConfig` | 配置过滤链、放行路径（登录/注册）、CSRF/CORS |

> ⚠️ **命名混淆提醒**：后端的 `service/` 是业务逻辑层；前端的 `services/` 是 HTTP 通信层。后端 `security/` 里的认证授权是安全层，不属于业务逻辑。

## 命名规范

- 包名全小写：`controller`、`service`、`repository`
- 类名 PascalCase：`StudentController`、`StudentService`
- 方法名 camelCase：`getById`、`createStudent`
- 常量全大写下划线：`MAX_PAGE_SIZE`
- DTO 后缀：请求用 `XxxRequest`，响应用 `XxxResponse`
- 数据库表名小写下划线，字段名小写下划线（JPA 自动驼峰转下划线）

## 事务规范

- 读操作加 `@Transactional(readOnly = true)`
- 写操作加 `@Transactional`
- 事务加在 Service 层，不加在 Controller 层
- 一个事务方法只做一件事，避免长事务
