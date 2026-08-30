#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-db-schema.py — 检查数据库迁移脚本(Flyway SQL)的命名、必备字段与索引。
用法:
    python check-db-schema.py <项目路径或迁移目录>
自动在以下位置寻找迁移脚本:
    <path>/src/main/resources/db/migration、<path>/backend/.../db/migration、<path>/database/migrations、<path> 本身
检查项:
    1. 迁移文件命名 V<版本>__<描述>.sql
    2. 每张表是否含必备字段 id / created_at / updated_at（逻辑删除 deleted 给 WARN）
    3. 表名是否为小写下划线风格
    4. 外键/常见查询字段是否建索引（粗略启发式）
v3.0 判定策略（上下文感知，不再只看 V1）:
    - 按 V<版本> 数字顺序重放全部迁移，计算每个表的**最终 schema 状态**
    - 同时解析 CREATE TABLE、ALTER TABLE ... ADD COLUMN、DROP TABLE、CREATE INDEX、ALTER ADD INDEX/KEY
    - 必备字段检查基于最终状态：后期迁移补齐的列不会误报（例如 V3 ALTER 补 updated_at/deleted）
    - 无法可靠判断时输出 WARN，不为绿灯猜测
输出: N tables / N indexes。只检查不修改。
"""
import os
import re
import sys

REQUIRED_COLS = ["id", "created_at", "updated_at"]
RECOMMENDED_COLS = ["deleted"]
CREATE_TABLE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?[`\"]?([a-zA-Z0-9_]+)[`\"]?", re.I)
DROP_TABLE = re.compile(r"drop\s+table\s+(?:if\s+exists\s+)?[`\"]?([a-zA-Z0-9_]+)[`\"]?", re.I)
ALTER_ADD_COLUMN = re.compile(
    r"alter\s+table\s+[`\"]?([a-zA-Z0-9_]+)[`\"]?\s+add\s+(?:column\s+)?[`\"]?([a-zA-Z0-9_]+)[`\"]?", re.I
)
ALTER_ADD_INDEX = re.compile(
    r"alter\s+table\s+[`\"]?[a-zA-Z0-9_]+[`\"]?\s+add\s+(?:unique\s+)?(?:index|key)\s+[`\"a-z0-9_]+\s*\(", re.I
)
CREATE_INDEX = re.compile(r"create\s+(?:unique\s+)?index", re.I)
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
VERSION_NAME = re.compile(r"^V(\d+(?:[_.]\d+)*)__[a-z0-9_]+\.sql$", re.I)
# 建表块内的内联索引：INDEX idx_x (col) / KEY idx_x (col) / UNIQUE KEY uk_x (col)
# 不匹配 PRIMARY KEY 与 FOREIGN KEY（key 后无索引名）
INLINE_INDEX = re.compile(r"\b(?:unique\s+)?(?:index|key)\s+[`\"a-z0-9_]+\s*\(", re.I)
# 建表块内的列定义行：第一个 token 是列名（排除约束行）
COLUMN_LINE = re.compile(r"^[`\"]?([a-zA-Z0-9_]+)[`\"]?\s+[a-zA-Z]", re.M)
CONSTRAINT_START = re.compile(r"^(primary|unique|key|index|constraint|foreign|fulltext|check)\b", re.I)
NON_COLUMN_WORDS = {"primary", "unique", "key", "index", "constraint", "foreign", "fulltext", "check"}


def version_key(path):
    m = VERSION_NAME.match(os.path.basename(path))
    if not m:
        return (10**9, os.path.basename(path))  # 不合规命名排最后，仍会被重放
    return tuple(int(p) for p in re.split(r"[_.]", m.group(1)))


def split_top_level(body):
    """按顶层逗号切分定义段，忽略括号内逗号（如 DECIMAL(10,2)、ENUM('a','b')）。"""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def parse_columns(block):
    """解析建表块列定义。兼容每列一行与单行/压缩 DDL（v3.1.1：不再依赖物理换行）。"""
    open_idx = block.find("(")
    if open_idx == -1:
        return []
    depth = 0
    close_idx = -1
    for i in range(open_idx, len(block)):
        if block[i] == "(":
            depth += 1
        elif block[i] == ")":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    body = block[open_idx + 1:(close_idx if close_idx != -1 else len(block))]
    body = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("--"))
    cols = []
    for segment in split_top_level(body):
        stripped = segment.strip().rstrip(",").strip()
        if not stripped:
            continue
        m = COLUMN_LINE.match(stripped)
        if not m:
            continue
        name = m.group(1).lower()
        if name in NON_COLUMN_WORDS:
            continue
        if CONSTRAINT_START.match(stripped):
            continue
        cols.append(name)
    return cols


def find_matching_paren(txt, open_pos):
    """从 open_pos 的 '(' 出发，返回匹配 ')' 的位置；无匹配返回 -1。"""
    depth = 0
    for i in range(open_pos, len(txt)):
        if txt[i] == "(":
            depth += 1
        elif txt[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_create_blocks(txt):
    """返回 [(table, block, [columns])]，块为 create table 到括号匹配结束（兼容单行 DDL）。"""
    out = []
    for m in CREATE_TABLE.finditer(txt):
        table = m.group(1)
        open_pos = txt.find("(", m.end())
        if open_pos == -1:
            out.append((table, txt[m.start():], []))
            continue
        close_pos = find_matching_paren(txt, open_pos)
        end = close_pos if close_pos != -1 else min(len(txt), m.start() + 2000)
        block = txt[m.start():end]
        out.append((table, block, parse_columns(block)))
    return out


def find_migration_dirs(root):
    found = []
    candidates = [
        os.path.join(root, "database", "migrations"),
        os.path.join(root, "src", "main", "resources", "db", "migration"),
    ]
    for dirpath, dirnames, _ in os.walk(root):
        if os.path.basename(dirpath) in ("migration", "migrations"):
            found.append(dirpath)
    for c in candidates:
        if os.path.isdir(c) and c not in found:
            found.append(c)
    if os.path.isdir(root) and not found:
        found.append(root)
    return sorted(set(found))


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check-db-schema.py <项目路径或迁移目录>")
        return 2
    root = os.path.abspath(sys.argv[1])
    dirs = find_migration_dirs(root)
    sql_files = []
    for d in dirs:
        for fn in os.listdir(d):
            if fn.endswith(".sql"):
                sql_files.append(os.path.join(d, fn))

    if not sql_files:
        print("WARN  check-db-schema.py")
        print("  - 未发现 .sql 迁移脚本（若项目确无数据库可忽略）")
        print("-" * 60)
        print("Summary: 0 tables / 0 indexes, 1 warnings")
        return 0

    warns = []
    # 最终 schema 状态：table -> set(columns)
    final_schema = {}
    tables_seen = set()
    indexes = 0

    for path in sorted(sql_files, key=version_key):
        fn = os.path.basename(path)
        if not VERSION_NAME.match(fn):
            warns.append(f"{fn}: 命名不符合 Flyway 规范 V<版本>__<描述>.sql")
        txt = open(path, encoding="utf-8", errors="ignore").read()
        low = txt.lower()
        file_indexes = len(CREATE_INDEX.findall(low)) + len(ALTER_ADD_INDEX.findall(low))

        for table, block, cols in extract_create_blocks(txt):
            tables_seen.add(table)
            if not SNAKE.match(table):
                warns.append(f"表名 {table} 非小写下划线风格")
            file_indexes += len(INLINE_INDEX.findall(block))
            # 最新一次 CREATE 定义该表列集（兼容旧脚本 DROP+CREATE 模式）
            final_schema[table] = set(cols)

        for m in DROP_TABLE.finditer(low):
            final_schema.pop(m.group(1), None)

        for m in ALTER_ADD_COLUMN.finditer(txt):
            table, col = m.group(1), m.group(2).lower()
            if table in final_schema:
                final_schema[table].add(col)
            # ALTER 引用未知表：可能是 V 前手工建的库，记 WARN 提示迁移自洽性
            else:
                warns.append(f"{fn}: ALTER TABLE {table} 引用了迁移序列中不存在的表")

        indexes += file_indexes

        # 外键字段无索引提示（粗略启发式：仅对含 DDL 的文件检查；
        # 纯数据文件（INSERT/UPDATE）里出现 _id 字样不构成索引缺失证据）
        if re.search(r"\b(create\s+table|alter\s+table)\b", low):
            fk_cols = re.findall(r"\b([a-z]+_id)\b", low)
            if fk_cols and file_indexes == 0:
                warns.append(f"{fn}: 存在外键字段 {sorted(set(fk_cols))} 但未发现索引定义")

    # 必备字段检查：基于迁移序列重放后的最终状态
    for table, cols in sorted(final_schema.items()):
        for col in REQUIRED_COLS:
            if col not in cols:
                warns.append(f"表 {table} 缺少必备字段 {col}")
        for col in RECOMMENDED_COLS:
            if col not in cols:
                warns.append(f"表 {table} 建议含逻辑删除字段 {col}")

    for w in sorted(set(warns)):
        print(f"  WARN {w}")
    print("-" * 60)
    head = "WARN  check-db-schema.py" if warns else "PASS  check-db-schema.py"
    print(head)
    print(f"Summary: {len(final_schema)} tables / {indexes} indexes, {len(set(warns))} warnings")
    print("说明: 检查基于迁移序列重放后的最终 schema（V1..Vn 依次重放 CREATE/ALTER/DROP）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
