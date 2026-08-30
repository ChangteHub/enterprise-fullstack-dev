# 数据库设计规范（MySQL 8.x）

> **Pre-Check（加载前确认）：** 核心 entity 有哪些？实体间关系（1:1 / 1:N / N:N）？预计数据量级别？需要逻辑删除吗？迁移工具用 Flyway 还是 Liquibase？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** Flyway 建表迁移脚本 + 索引方案。

## 命名规范

| 对象 | 规则 | 示例 |
|------|------|------|
| 数据库名 | 小写下划线，项目名 | `student_system` |
| 表名 | 小写下划线，名词，不用复数 | `student`、`course`、`student_course` |
| 字段名 | 小写下划线 | `student_no`、`created_at` |
| 索引名 | `idx_表名_字段名` | `idx_student_name` |
| 唯一索引 | `uk_表名_字段名` | `uk_student_student_no` |
| 外键 | `fk_子表_父表` | `fk_student_course` |
| 主键 | 统一 `id` | `id` |

## 表设计规范

### 必备字段（每张表都要有）

```sql
id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
deleted     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
PRIMARY KEY (id)
```

### 字段类型选择

| 数据 | 推荐类型 | 说明 |
|------|---------|------|
| 主键ID | BIGINT AUTO_INCREMENT | 不用 INT，避免数据量大了溢出 |
| 金额 | DECIMAL(10,2) | 不用 FLOAT/DOUBLE，有精度问题 |
| 短字符串 | VARCHAR(n) | 按实际长度定，如 name VARCHAR(50) |
| 长文本 | TEXT | 超过 255 字符用 TEXT |
| 日期时间 | DATETIME | 不用 TIMESTAMP（范围小、有时区问题） |
| 布尔值 | TINYINT(1) | 0/1 表示 |
| 枚举 | TINYINT + 注释 | 或 VARCHAR，不用 ENUM 类型（改值要改表结构） |
| JSON | JSON | MySQL 5.7+ 支持，适合半结构化数据 |

### 字符集与引擎

```sql
CREATE TABLE student (
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生表';
```

- 引擎：**InnoDB**（支持事务、行级锁、外键）
- 字符集：**utf8mb4**（支持 emoji，utf8 是 utf8mb3 的别名，不支持4字节字符）
- 排序规则：`utf8mb4_unicode_ci`

## 索引规范

### 什么时候加索引
- WHERE 条件中频繁使用的字段
- JOIN 关联的字段
- ORDER BY / GROUP BY 的字段
- DISTINCT 的字段

### 索引类型

| 类型 | 语法 | 适用场景 |
|------|------|---------|
| 普通索引 | `INDEX idx_name (name)` | 加速查询 |
| 唯一索引 | `UNIQUE KEY uk_student_no (student_no)` | 字段值唯一（学号、邮箱） |
| 联合索引 | `INDEX idx_name_major (name, major)` | 多字段组合查询 |
| 全文索引 | `FULLTEXT KEY ft_content (content)` | 全文搜索（简单场景，复杂用 ES） |

### 联合索引最左前缀原则

联合索引 `(a, b, c)` 能命中的查询：
- `WHERE a = ?` ✅
- `WHERE a = ? AND b = ?` ✅
- `WHERE a = ? AND b = ? AND c = ?` ✅
- `WHERE b = ?` ❌（跳过了 a，不命中）
- `WHERE a = ? AND c = ?` ⚠️（只命中 a，c 不命中）

**建索引顺序：** 等值查询字段在前，范围查询字段在后。

### 索引注意事项

- 单表索引不超过 5 个（索引多了写性能下降、占空间）
- 不在低基数字段加索引（如性别，只有男/女，索引效果差）
- 不在频繁更新的字段加索引（更新索引成本高）
- 用 `EXPLAIN` 查看执行计划，确认索引是否命中
- 避免索引失效：对索引字段用函数/运算、隐式类型转换、LIKE 左模糊 `%xxx`

## 表关系设计

### 一对一
用外键 + 唯一约束，或直接合并到一张表（优先合并）。

### 一对多
在"多"的表加外键指向"一"的表：
```sql
-- 一个班级有多个学生
CREATE TABLE student (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    class_id BIGINT NOT NULL COMMENT '班级ID',
    ...
    INDEX idx_class_id (class_id)
);
```

### 多对多
用中间表：
```sql
-- 学生和课程多对多
CREATE TABLE student_course (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    score DECIMAL(5,2) COMMENT '成绩',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_course (student_id, course_id),
    INDEX idx_student_id (student_id),
    INDEX idx_course_id (course_id)
);
```

## 事务规范

- 事务加在 Service 层，用 `@Transactional`
- 读操作加 `readOnly = true`
- 事务方法尽量短，不在事务里做远程调用、发消息
- 避免长事务（事务持有锁时间长，影响并发）
- 事务隔离级别默认用 `REPEATABLE READ`（MySQL InnoDB 默认），特殊场景才调整

## 数据库迁移（Flyway）

### 为什么用迁移工具
- 数据库结构变更有版本记录，可追溯
- 团队协作时，别人拉代码后自动执行迁移
- 部署时自动执行，不用手动连数据库执行 SQL
- 可以回滚（部分支持）

### 文件命名规范

```
src/main/resources/db/migration/
├── V1__init_schema.sql          # 版本1：初始化表结构
├── V2__create_student_table.sql # 版本2：创建学生表
├── V3__add_email_to_student.sql # 版本3：学生表加邮箱字段
└── V4__create_course_table.sql  # 版本4：创建课程表
```

- 前缀 `V` + 版本号 + `__`（双下划线）+ 描述 + `.sql`
- 版本号递增，执行过的脚本不能修改（Flyway 会校验 checksum）
- 新增变更写新的版本文件，不改旧的

### 迁移脚本示例

```sql
-- V1__init_schema.sql
CREATE TABLE user (
    id BIGINT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL COMMENT 'BCrypt哈希',
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- V2__create_student_table.sql
CREATE TABLE student (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    student_no VARCHAR(20) NOT NULL,
    major VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_student_no (student_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';
```

### Spring Boot 配置

```yaml
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true  # 已有数据库时首次运行需要
  jpa:
    hibernate:
      ddl-auto: validate  # 用 Flyway 管理表结构，JPA 只校验不自动建表
```

## 安全规范

- 生产数据库账号最小权限：应用账号只有 SELECT/INSERT/UPDATE/DELETE，不给 DROP/ALTER
- 数据库密码强密码，通过环境变量注入
- 数据库端口不暴露公网，只允许应用服务器访问
- 定期备份（mysqldump 或云数据库自动备份）
- 敏感数据（密码）哈希存储，不明文
- 逻辑删除代替物理删除（`deleted` 字段），保留数据可恢复

## 性能规范

- 大表（超过100万行）考虑分表或归档历史数据
- 查询只查需要的字段，不用 `SELECT *`
- 分页用 `LIMIT offset, size`，大 offset 时用游标分页优化
- 批量操作用 `INSERT INTO ... VALUES (...), (...)` 批量插入
- N+1 查询问题：用 JOIN 或 JPA `@EntityGraph` 解决
- 慢查询开启慢查询日志，定期分析优化
