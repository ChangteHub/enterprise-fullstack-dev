#!/bin/bash
# reset-test-data.sh — 清理种子测试数据（与 seed-test-data.sh 配对使用）
# 用法: bash reset-test-data.sh [项目根路径]
# 模板说明: 可工作实例（源自真实 trial 项目）；接入新项目时按 seed 的账号与
#           业务外键关系改写下方清理 SQL，只允许清理本 seed 创建的数据。
# 范围：只删除本 seed 脚本创建的数据（test1/test2 及其名下业务数据），
#       不触碰任何真实用户数据；删除前打印将影响的行数。
# v3.1.1 压测修复：逐表探测式清理——不同项目结构的表子集不同（压测实证：
# 全量假设在只有 user+category 的最小库上会因 Table doesn't exist 崩溃且静默半完成）。
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
[ -f "$ROOT/.env" ] || { echo "拒绝：未找到 .env" >&2; exit 1; }
# shellcheck disable=SC1091
export $(grep -v '^#' "$ROOT/.env" | grep -E 'MYSQL_ROOT_PASSWORD|MYSQL_DATABASE|MYSQL_CONTAINER' | xargs) 2>/dev/null || true

CONTAINER="${MYSQL_CONTAINER:-secondhand-mysql}"
DB="${MYSQL_DATABASE:-xust_secondhand}"
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "拒绝：容器 $CONTAINER 未运行" >&2; exit 1; }

# 环境保护（与 seed-test-data.sh 对齐）：目标容器必须只绑定 loopback
PORT_MAP=$(docker port "$CONTAINER" 3306/tcp 2>/dev/null || true)
if [ -n "$PORT_MAP" ] && ! echo "$PORT_MAP" | grep -qE '127\.0\.0\.1|::1'; then
  echo "拒绝：$CONTAINER 的 3306 绑定到非 loopback 地址（$PORT_MAP），疑似非本地环境" >&2
  exit 1
fi

MYSQL="docker exec -i $CONTAINER mysql --default-character-set=utf8mb4 -uroot -p${MYSQL_ROOT_PASSWORD} $DB"

echo "将删除种子测试用户（test1/test2）及其名下业务数据。影响预览："
$MYSQL -e "SELECT 'user' AS tbl, COUNT(*) AS rows_affected FROM \`user\` WHERE username IN ('test1','test2');"

read -r -p "确认删除？输入 YES 继续：" CONFIRM
[ "$CONFIRM" = "YES" ] || { echo "已取消"; exit 0; }

# 逐表探测式清理：information_schema 确认表存在才生成 DELETE，按依赖顺序子表在前。
# 生成临时 SQL 文件执行，避免 heredoc 引号嵌套问题。
TMPSQL="$(mktemp)"
cat > "$TMPSQL" << 'HEAD'
SET @uids = (SELECT GROUP_CONCAT(id) FROM `user` WHERE username IN ('test1','test2'));
SET @ddl = '';
HEAD

append_if_table() {
  local table="$1" where="$2"
  cat >> "$TMPSQL" << SQL
SET @ddl = IFNULL((SELECT CONCAT(@ddl, 'DELETE FROM \`$table\` WHERE $where;')
  FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = '$table'
  LIMIT 1), @ddl);
SQL
}

append_if_table "chat_message"     "session_id IN (SELECT id FROM @T@chat_session@T@ WHERE buyer_id IN (@U@) OR seller_id IN (@U@)) OR sender_id IN (@U@)"
append_if_table "chat_session"     "buyer_id IN (@U@) OR seller_id IN (@U@)"
append_if_table "favorite"         "user_id IN (@U@)"
append_if_table "browsing_history" "user_id IN (@U@)"
append_if_table "product_image"    "product_id IN (SELECT id FROM @T@product@T@ WHERE seller_id IN (@U@))"
append_if_table "product"          "seller_id IN (@U@)"
append_if_table "verification"     "user_id IN (@U@)"

cat >> "$TMPSQL" << 'TAIL'
SET @ddl = CONCAT(@ddl, 'DELETE FROM `user` WHERE id IN (', IFNULL(@uids, 'NULL'), ');');
SET @sql = IF(@uids IS NULL, 'SELECT ''种子用户不存在，无需清理'' AS result', @ddl);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
TAIL

# 占位符替换为真实 SQL 片段（@U@ -> ', @uids, '；@T@ -> 反引号）
sed -i "s/@U@/', @uids, '/g; s/@T@/\`/g" "$TMPSQL"

if $MYSQL < "$TMPSQL"; then
  echo "reset 完成（逐表探测，仅清理种子数据；不存在的表自动跳过）。"
  rm -f "$TMPSQL"
else
  echo "reset 执行出错（未完成即停止，可安全重跑）" >&2
  rm -f "$TMPSQL"
  exit 1
fi
