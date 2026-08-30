#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-security.py — 安全静态检查：硬编码密钥、.env 入库、危险端口暴露、弱密码。
用法:
    python check-security.py <项目根路径>
分级:
    CRITICAL（必须修复，对应 Stop Condition）/ WARN（建议修复/需人工确认）
v3.0 判定策略（上下文感知，不再只靠字符串命中）:
    1. Git tracked 优先：在 git 仓库内时，只有"已被 git 跟踪"的文件中的密钥才判 CRITICAL
       （= 已入库的真实风险）；未跟踪文件中的密钥降级为 WARN（本地风险，提醒确认忽略规则）。
    2. 测试 fixture 识别：位于 test/tests/fixtures 目录或符合测试文件命名
       （*.test.ts / *.spec.ts / *Test.java / *_test.go / test_*.py 等）的发现降级为 WARN，
       因为测试代码中的字符串字面量按定义是示例值。
    3. 行内 allowlist：命中行尾部含 `security-allowlist` 标记（建议附原因）则跳过该行，
       用于无法立即整改但已人工确认安全的例外。示例：
           const SECRET = "demo"  // security-allowlist: 示例文档用
输出: N warnings / N critical；存在 CRITICAL 时退出码 1。只检查不修改。
"""
import os
import re
import subprocess
import sys

SCAN_EXT = (".java", ".ts", ".tsx", ".js", ".jsx", ".py", ".yml", ".yaml", ".properties", ".env", ".xml", ".json")
SKIP_DIRS = {"node_modules", "target", "dist", ".git", "build", ".idea", ".venv", "venv"}

# 键名含 secret/token/credential/apikey/password 等，后跟 : 或 = 和引号字面量
ASSIGN = re.compile(
    r"""(?ix)
    ([a-z0-9_\-]*(?:secret|token|credential|api[_\-]?key|password|passwd|pwd)[a-z0-9_\-]*)
    \s*[:=]\s*
    ['"]([^'"]{4,})['"]
    """
)
WEAK_PASSWORDS = {"123456", "admin", "password", "000000", "root", "111111", "12345678", "qwerty"}
PLACEHOLDER_MARK = ("${", "your-", "your_", "xxx", "change-me", "changeme", "example",
                    "<", ">", "placeholder", "replace", "todo", "default-", "xxxx", "demo",
                    "test-", "fixture", "sample", "dummy", "mock")
AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
# SQL 字符串拼接（参数化反面）
SQL_CONCAT = re.compile(r"""(['"]select|['"]update|['"]delete|['"]insert)[^'"]*['"]\s*\+""", re.I)

ALLOWLIST_MARK = "security-allowlist"
TEST_DIR_MARKS = ("/test/", "/tests/", "/fixtures/", "\\test\\", "\\tests\\", "\\fixtures\\")
TEST_FILE_RE = re.compile(
    r"(\.test\.tsx?$|\.spec\.tsx?$|Test\.java$|Tests\.java$|_test\.go$|^test_.*\.py$|\.test\.jsx?$|\.spec\.jsx?$)",
    re.I,
)


def git_tracked_files(root):
    """返回 git 跟踪的文件相对路径集合；非 git 仓库返回 None（未知状态，保守处理）。"""
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=15
        )
        if out.returncode != 0:
            return None
        return {line.strip().replace("\\", "/") for line in out.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return None


def is_test_fixture(rel_path):
    """测试 fixture 判定：测试目录或测试文件命名。"""
    norm = rel_path.replace("\\", "/")
    if any(mark in norm for mark in TEST_DIR_MARKS):
        return True
    return bool(TEST_FILE_RE.search(os.path.basename(norm)))


def gitignore_covers_env(root):
    gitignore = os.path.join(root, ".gitignore")
    if not os.path.isfile(gitignore):
        return False
    ignored = open(gitignore, encoding="utf-8", errors="ignore").read()
    lines = [l.strip() for l in ignored.splitlines()]
    return any(l == ".env" or l == ".env*" for l in lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check-security.py <项目根路径>")
        return 2
    root = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root):
        print(f"错误: 目录不存在 {root}")
        return 2
    critical, warns = [], []

    tracked = git_tracked_files(root)

    # 1. .env 入库检查：git 跟踪状态优先，.gitignore 作为兜底启发
    env_rel = ".env"
    if tracked is not None and env_rel in tracked:
        critical.append(".env 已被 git 跟踪（真实凭据可能已入库，需轮换密钥并 git rm --cached）")
    elif not gitignore_covers_env(root):
        (critical if tracked is None else warns).append(
            ".gitignore 未忽略 .env（应包含 .env 行，可保留 .env.example）"
        )
    if not os.path.isfile(os.path.join(root, ".env.example")):
        warns.append("缺少 .env.example 环境变量模板")

    # 2. 扫描源码（逐行：支持行内 allowlist 与精确行号）
    for path in iter_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        if os.path.basename(path) == ".env.example":
            continue
        try:
            txt = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        fixture = is_test_fixture(rel)
        known_tracked = tracked is not None and rel in tracked

        for idx, line in enumerate(txt.splitlines(), start=1):
            if ALLOWLIST_MARK in line:
                continue  # 行内显式 allowlist：人工确认过的例外
            for m in ASSIGN.finditer(line):
                key, val = m.group(1), m.group(2)
                low_val = val.lower()
                if "${" in val or any(mark in low_val for mark in PLACEHOLDER_MARK):
                    continue  # 环境变量引用或占位符模板，放行
                key_low = key.lower()
                is_pwd = "password" in key_low or "passwd" in key_low or "pwd" in key_low
                if is_pwd and val in WEAK_PASSWORDS:
                    msg = f"{rel}:{idx} 弱口令/硬编码密码: {key}=<掩码>"
                elif is_pwd:
                    msg = f"{rel}:{idx} 疑似硬编码密码（应改为环境变量注入）: {key}"
                else:
                    msg = f"{rel}:{idx} 疑似硬编码密钥: {key}"
                if fixture:
                    warns.append(f"{msg} [测试fixture]")
                elif tracked is not None and not known_tracked:
                    warns.append(f"{msg} [未跟踪文件，请确认忽略规则]")
                else:
                    critical.append(msg)

            if AWS_KEY.search(line):
                msg = f"{rel}:{idx} 疑似 AWS Access Key"
                if fixture or (tracked is not None and not known_tracked):
                    warns.append(f"{msg} [{'测试fixture' if fixture else '未跟踪文件'}]")
                else:
                    critical.append(msg)

        if SQL_CONCAT.search(txt):
            warns.append(f"{rel} 疑似 SQL 字符串拼接，应使用参数化查询/预编译")

    # 3. docker-compose 端口暴露检查（0.0.0.0 映射 DB/后端）
    for path in iter_files(root):
        if os.path.basename(path) in ("docker-compose.yml", "docker-compose.yaml"):
            txt = open(path, encoding="utf-8", errors="ignore").read()
            for port in ("3306", "5432", "6379", "8080"):
                # 形如 "3306:3306" 即绑定到所有网卡；"127.0.0.1:3306:3306" 才安全
                if re.search(rf"(?<!127\.0\.0\.1:)['\"]?{port}:{port}", txt):
                    warns.append(f"{os.path.relpath(path, root)} 端口 {port} 可能绑定到 0.0.0.0，生产应对内绑定 127.0.0.1")

    for w in sorted(set(warns)):
        print(f"  - WARN     {w}")
    for c in sorted(set(critical)):
        print(f"  - CRITICAL {c}")
    print("-" * 60)
    head = "FAIL  check-security.py" if critical else ("WARN  check-security.py" if warns else "PASS  check-security.py")
    print(head)
    print(f"Summary: {len(set(warns))} warnings / {len(set(critical))} critical")
    if critical:
        print("安全检查: FAIL —— CRITICAL 阻断，触发 Stop Condition，修复后才能继续")
        return 1
    print("安全检查: PASS" + ("（有告警）" if warns else ""))
    return 0


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(SCAN_EXT):
                yield os.path.join(dirpath, fn)


if __name__ == "__main__":
    sys.exit(main())
