# RESTful API 设计规范

> **Pre-Check（加载前确认）：** API 统一前缀是什么（/api/v1？）？需要 API 版本化吗？分页参数约定？认证方式（JWT/Session）？需要自动生成 Swagger 文档吗？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** API 清单 + 统一 Result/DTO/全局异常结构。

## URL 设计

### 基本原则
- URL 用**名词复数**，不用动词
- 层级关系用路径表示：`/api/students/{studentId}/courses`
- 过滤、排序、分页用查询参数
- 所有 API 统一前缀 `/api`

### 资源命名示例

| 操作 | 方法 | URL | 说明 |
|------|------|-----|------|
| 列表 | GET | `/api/students` | 获取学生列表 |
| 详情 | GET | `/api/students/{id}` | 获取单个学生 |
| 新增 | POST | `/api/students` | 创建学生 |
| 全量更新 | PUT | `/api/students/{id}` | 更新学生（全部字段） |
| 部分更新 | PATCH | `/api/students/{id}` | 更新学生（部分字段） |
| 删除 | DELETE | `/api/students/{id}` | 删除学生 |
| 子资源 | GET | `/api/students/{id}/courses` | 获取学生的课程 |
| 动作 | POST | `/api/students/{id}/enroll` | 非CRUD动作（报名） |

### 动作类接口
对于不是标准 CRUD 的操作（如登录、注册、导出、审批），用动词作为子资源：
- `POST /api/auth/login` — 登录
- `POST /api/auth/register` — 注册
- `POST /api/students/{id}/export` — 导出
- `POST /api/orders/{id}/cancel` — 取消订单

## HTTP 方法语义

| 方法 | 语义 | 幂等 | 安全 | 有请求体 |
|------|------|------|------|---------|
| GET | 查询 | 是 | 是 | 否 |
| POST | 创建 | 否 | 否 | 是 |
| PUT | 全量更新 | 是 | 否 | 是 |
| PATCH | 部分更新 | 否 | 否 | 是 |
| DELETE | 删除 | 是 | 否 | 否 |

- **幂等**：多次执行结果相同。PUT/DELETE 是幂等的，POST/PATCH 不是
- **安全**：不修改服务器资源。只有 GET 是安全的

## 统一响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 分页响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [ ... ],
    "page": 1,
    "size": 10,
    "totalElements": 100,
    "totalPages": 10
  }
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "参数校验失败: name不能为空",
  "data": null
}
```

## HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | OK | GET/PUT/PATCH 成功 |
| 201 | Created | POST 创建成功 |
| 204 | No Content | DELETE 成功（无响应体） |
| 400 | Bad Request | 参数错误、校验失败 |
| 401 | Unauthorized | 未登录、token 无效/过期 |
| 403 | Forbidden | 已登录但无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如重复创建） |
| 422 | Unprocessable Entity | 请求格式正确但语义错误 |
| 429 | Too Many Requests | 请求过于频繁（限流） |
| 500 | Internal Server Error | 服务器内部错误 |

> 注意：业务错误也可以在响应体的 `code` 字段中用自定义业务码，但 HTTP 状态码仍应符合语义。

## 查询参数规范

### 分页
- `page`：页码，从 1 开始，默认 1
- `size`：每页条数，默认 10，最大 100

### 排序
- `sort`：排序字段，支持多字段，格式 `field,direction`
- 示例：`?sort=createdAt,desc&sort=name,asc`

### 过滤
- 简单过滤直接用字段名：`?name=张三&major=计算机`
- 范围查询：`?createdAtStart=2024-01-01&createdAtEnd=2024-12-31`
- 模糊搜索：`?keyword=张`

### 完整示例
```
GET /api/students?page=1&size=20&sort=createdAt,desc&major=计算机&keyword=张
```

## 请求/响应 DTO 规范

### 请求 DTO（带校验注解）

```java
@Data
public class StudentCreateRequest {
    @NotBlank(message = "姓名不能为空")
    @Size(max = 50, message = "姓名最长50字符")
    private String name;

    @NotBlank(message = "学号不能为空")
    @Pattern(regexp = "^[0-9]{10}$", message = "学号必须是10位数字")
    private String studentNo;

    @NotBlank(message = "专业不能为空")
    private String major;

    @Email(message = "邮箱格式不正确")
    private String email;
}
```

### 响应 DTO（只返回需要的字段，不暴露 Entity）

```java
@Data
public class StudentResponse {
    private Long id;
    private String name;
    private String studentNo;
    private String major;
    private String email;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

> 禁止直接返回 Entity 作为响应，必须转换为 DTO。Entity 包含数据库字段（如密码、逻辑删除标记），不应暴露给前端。

## 认证规范

- 使用 JWT（JSON Web Token）
- 请求头：`Authorization: Bearer <token>`
- token 过期返回 401
- 刷新 token 接口：`POST /api/auth/refresh`
- 登出：前端清除 token，后端可加入黑名单（可选）

## 版本管理

- URL 路径版本：`/api/v1/students`、`/api/v2/students`
- 小版本迭代尽量保持向后兼容，不破坏性变更
- 破坏性变更才升大版本号

## API 文档

- 使用 SpringDoc OpenAPI（`springdoc-openapi-starter-webmvc-ui`）自动生成 Swagger 文档
- 访问地址：`/swagger-ui.html`
- Controller 方法加 `@Operation`、`@Parameter` 注解说明
- DTO 字段加 `@Schema` 注解说明
