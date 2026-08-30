#!/bin/bash
# seed-test-data.sh — 测试数据种子（v3.1 测试数据生命周期）
# 用法: bash seed-test-data.sh [项目根路径，默认当前目录]
# 模板说明: 本脚本为可工作实例（源自真实 trial 项目，表名为 user/product 等）；
#           接入新项目时由 .env 的 MYSQL_CONTAINER/MYSQL_DATABASE 覆盖容器与库名，
#           并按目标项目表结构改写下方 SQL（机制：幂等/环保/utf8mb4 保持不变）。
# 特性:
#   幂等：重复执行不产生重复数据（基于唯一键 upsert）
#   环境保护：只允许作用于"本地 docker compose 的 mysql 容器"，且端口绑定必须为 loopback；
#             .env 缺失或容器未运行时直接拒绝；检测到面向非本机的数据库配置时拒绝
#   可审查：本脚本入 Git，review 可见它到底创建什么数据
#   编码一致：统一 --default-character-set=utf8mb4，避免 bash→mysql 客户端乱码
# 硬规则（Skill v3.1）：生产环境禁止 ad-hoc SQL 创建测试账号；测试数据必须来自本脚本
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"

if [ ! -f "$ROOT/.env" ]; then
  echo "拒绝：未找到 $ROOT/.env（种子脚本只作用于显式声明的本地环境）" >&2
  exit 1
fi
# shellcheck disable=SC1091
export $(grep -v '^#' "$ROOT/.env" | grep -E 'MYSQL_ROOT_PASSWORD|MYSQL_DATABASE|MYSQL_CONTAINER' | xargs) 2>/dev/null || true

CONTAINER="${MYSQL_CONTAINER:-secondhand-mysql}"
DB="${MYSQL_DATABASE:-xust_secondhand}"

command -v docker >/dev/null || { echo "拒绝：未安装 docker" >&2; exit 1; }
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "拒绝：容器 $CONTAINER 未运行（只作用于本地 compose 数据库）" >&2; exit 1; }

# 环境保护：目标数据库容器必须只绑定 loopback，禁止作用于暴露公网的库
PORT_MAP=$(docker port "$CONTAINER" 3306/tcp 2>/dev/null || true)
if [ -n "$PORT_MAP" ] && ! echo "$PORT_MAP" | grep -qE '127\.0\.0\.1|::1'; then
  echo "拒绝：$CONTAINER 的 3306 绑定到非 loopback 地址（$PORT_MAP），疑似非本地环境" >&2
  exit 1
fi

echo "向本地容器 $CONTAINER 的 $DB 播种测试数据（幂等）..."
docker exec -i "$CONTAINER" mysql --default-character-set=utf8mb4 -uroot -p"${MYSQL_ROOT_PASSWORD}" "$DB" << 'SQL'
-- 测试账号（幂等 upsert；密码均为已知测试值，生产环境禁止使用本脚本）
INSERT INTO `user` (`username`, `password`, `nickname`, `phone`, `school`, `student_id`, `bio`, `role`)
VALUES
('test1', '$2b$10$O8In8FZQAvU6CfXqkPX2J.s1ui/NfKTgBM1ELbYAjnSrxCEUfuMSO', '测试用户1', '13800138001', '西南科技大学', '2024001', '大三计算机专业', 0),
('test2', '$2b$10$O8In8FZQAvU6CfXqkPX2J.s1ui/NfKTgBM1ELbYAjnSrxCEUfuMSO', '测试用户2', '13800138002', '西南科技大学', '2024002', '大四机械专业', 0)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), role=VALUES(role), deleted=0;

-- 冒烟管理员（可选：SMOKE_ADMIN=1 时创建，密码 SmokeAdmin2026!）
-- INSERT INTO `user` (`username`,`password`,`nickname`,`role`) VALUES ('smoke_admin','$2b$10$…','冒烟测试管理员',1)
--   ON DUPLICATE KEY UPDATE role=1;
SQL

echo "seed 完成。校验请运行：bash scripts/verify-test-data.sh"
