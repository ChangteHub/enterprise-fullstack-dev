#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-project-hygiene.py — Project Hygiene（项目卫生，v3.1）。
用法:
    python check-project-hygiene.py <项目根路径>
四级严重度（v3.1：WARN 不再阻塞主线，进入 Hygiene Queue 由用户批量裁决）:
    CRITICAL  敏感文件（.env 被跟踪、私钥、凭据、生产 dump）            → 阻断（exit 1）
    ERROR     破坏仓库约束：可执行/构建产物被跟踪、Artifact 入库        → 阻断（exit 1）
    WARN      可疑临时/遗留（tmp/old/backup/test2）、孤儿条目           → 不阻断，进 Hygiene Queue
    INFO      正常但不属于核心路径（工具本地配置目录等）                 → 不阻断
v3.1 新增 Artifact Policy:
    测试证据（截图/coverage/临时报告/日志）归属 CI Artifacts 或临时目录，
    不应留在源码仓库；根目录出现 screenshot*/coverage/logs/test-results 类条目 → WARN + 建议 .gitignore。
v3.1 原则不变:
    1. Git tracked 状态优先于文件名猜测
    2. 只检测，绝不自动删除；WARN 项给证据与候选处理，由人批量裁决（Hygiene Queue）
    3. 初始化前 / 每阶段后 / 发布前持续运行
输出: PASS / WARN（exit 0，可含 Queue）/ FAIL（exit 1，存在 CRITICAL/ERROR）。
"""
import os
import re
import subprocess
import sys
import time

SKIP_DIRS = {"node_modules", "target", "dist", "build", "coverage", ".git", ".idea", ".venv", "venv",
             "__pycache__", ".next", ".nuxt", "vendor"}

ALLOWED_TOP_DIRS = {
    "frontend", "backend", "apps", "services", "packages", "database", "deploy", "infrastructure",
    "docs", "scripts", "tests", "test", "monitoring", "nginx", "public", "src", "tools",
    ".github", ".husky", ".vscode", ".gitlab", "evals", "references", "assets",
}
# 工具本地配置目录：正常但不属于核心路径 → INFO
TOOL_DOT_DIRS = {".claude", ".cursor", ".reasonix", ".agent", ".trae", ".windsurf"}
ALLOWED_TOP_FILES_RE = re.compile(
    r"^(README.*|CHANGELOG.*|LICENSE.*|CONTRIBUTING.*|SECURITY.*|Makefile|makefile|justfile"
    r"|docker-compose.*\.ya?ml|compose\.ya?ml|\.env\.example|\.gitignore|\.gitattributes|\.editorconfig"
    r"|\.prettierrc.*|\.prettierignore|\.eslintrc.*|eslint\.config\..*|\.npmrc|\.nvmrc|\.node-version"
    r"|pom\.xml|build\.gradle.*|settings\.gradle.*|gradlew.*|mvnw.*|package\.json|pnpm-workspace\.yaml"
    r"|package-lock\.json|lerna\.json|turbo\.json|nx\.json|vitest\.config\..*|vite\.config\..*"
    r"|tsconfig.*\.json|\.tool-versions|.*\.md)$",
    re.I,
)
SUSPICIOUS_RE = re.compile(
    r"(^|[_\-\.\s])(tmp|temp|old|backup|bak|copy|debug|draft|废弃|临时|缓存|副本)([_\-\.\s]|$)|^test\d+|^unittest\d+|final|useless",
    re.I,
)
SENSITIVE_FILE_RE = re.compile(r"^(.*\.env$|\.env|id_rsa.*|.*\.pem$|.*\.key$|credentials.*\.json$|.*secret.*\.txt$|secrets?.*)", re.I)
FORBIDDEN_EXT = (".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".msi", ".apk", ".dmg", ".jar", ".war")

# v3.1 Artifact Policy：测试证据类条目不应留在源码仓库
ARTIFACT_ENTRY_RE = re.compile(
    r"^(gui-test-screenshots|screenshots?|coverage|logs?|reports?|test-results?|playwright-report|\.nyc_output|error-shots?)$",
    re.I,
)
ARTIFACT_FILE_RE = re.compile(r"^(screenshot.*|.*-shot\.png|.*\.log)$", re.I)

SECOND_LEVEL_EXEMPT = {"scripts", "docs", "tests", "test", "tools"}
OPS_SCRIPT_RE = re.compile(r"^(backup|restore|init-db|logs|deploy|rollback|health)\.(sh|ps1)$", re.I)


def git_tracked(root):
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return None
        return {l.strip().replace("\\", "/") for l in out.stdout.splitlines() if l.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return None


def evidence(path):
    try:
        st = os.stat(path)
        mtime = time.strftime("%Y-%m-%d", time.localtime(st.st_mtime))
        if os.path.isdir(path):
            n = sum(len(fs) for _, _, fs in os.walk(path))
            return f"{n} 个文件, 最后修改 {mtime}"
        return f"{st.st_size / 1024:.1f} KB, 最后修改 {mtime}"
    except OSError:
        return "无法读取"


def main() -> int:
    argv = sys.argv[1:]
    queue_out = None
    if "--queue" in argv:
        qi = argv.index("--queue")
        queue_out = argv[qi + 1]
        argv = argv[:qi] + argv[qi + 2:]
    if not argv:
        print("用法: python check-project-hygiene.py <项目根路径> [--queue docs/quality/hygiene-queue.json]")
        return 2
    root = os.path.abspath(argv[0])
    if not os.path.isdir(root):
        print(f"错误: 目录不存在 {root}")
        return 2

    tracked = git_tracked(root)
    criticals, errors, warns, infos, passes = [], [], [], [], []

    def is_tracked(rel):
        return tracked is not None and rel.replace("\\", "/") in tracked

    # 1. 顶层结构与孤儿条目
    for entry in sorted(os.listdir(root)):
        if entry in SKIP_DIRS:
            continue
        full = os.path.join(root, entry)
        rel = entry
        if entry.startswith("."):
            if entry == ".env":
                if tracked is not None and is_tracked(rel):
                    criticals.append(".env 已被 git 跟踪（凭据可能已入库，需轮换密钥并 git rm --cached）")
                elif tracked is not None:
                    passes.append(".env 存在但未被跟踪（符合忽略策略）")
                else:
                    criticals.append("存在 .env 且项目非 git 仓库/无法确认忽略状态（凭据泄露风险，需人工确认）")
            elif entry in TOOL_DOT_DIRS:
                infos.append(f"工具本地配置 root/{entry}/（INFO：正常但不属于项目核心路径，不入库即可）")
            continue
        if os.path.isdir(full):
            if entry in ALLOWED_TOP_DIRS:
                passes.append(f"root/{entry}/ 符合清单")
            elif ARTIFACT_ENTRY_RE.match(entry):
                warns.append(f"[Artifact Policy] root/{entry}/（{evidence(full)}）——测试证据应归属 CI Artifacts 或临时目录；建议 .gitignore 或移出仓库")
            elif SUSPICIOUS_RE.search(entry):
                warns.append(f"可疑目录 root/{entry}/（{evidence(full)}）——[Hygiene Queue] 候选处理：确认后归档/删除/移入 docs/archive，本脚本不自动删除")
            else:
                warns.append(f"孤儿目录 root/{entry}/ 未被识别为项目标准目录（{evidence(full)}）——[Hygiene Queue] 请确认归属")
        else:
            if ALLOWED_TOP_FILES_RE.match(entry):
                passes.append(f"root/{entry} 符合清单")
            elif ARTIFACT_FILE_RE.match(entry):
                warns.append(f"[Artifact Policy] root/{entry}（{evidence(full)}）——测试证据/日志应归属 CI Artifacts；建议 .gitignore")
            elif SUSPICIOUS_RE.search(entry):
                warns.append(f"可疑文件 root/{entry}（{evidence(full)}）——[Hygiene Queue] 候选处理：确认后删除/归档")
            else:
                warns.append(f"孤儿文件 root/{entry} 未被识别为项目标准文件（{evidence(full)}）——[Hygiene Queue] 请确认归属")
        if os.path.isfile(full) and entry.lower().endswith(FORBIDDEN_EXT):
            msg = f"可执行/构建产物 root/{entry} 不应入库"
            if tracked is None or is_tracked(rel):
                errors.append(msg)
            else:
                warns.append(msg + " [未跟踪，请确认] ")

    # 2. 二级可疑目录扫描（scripts/docs/tests 豁免：运维与文档的正常命名组成）
    for entry in sorted(os.listdir(root)):
        base = os.path.join(root, entry)
        if not os.path.isdir(base) or entry in SKIP_DIRS or entry.startswith("."):
            continue
        for sub in sorted(os.listdir(base)):
            if sub in SKIP_DIRS or entry in SECOND_LEVEL_EXEMPT:
                continue
            if OPS_SCRIPT_RE.match(sub):
                continue
            full = os.path.join(base, sub)
            if SUSPICIOUS_RE.search(sub):
                warns.append(f"可疑条目 root/{entry}/{sub}（{evidence(full)}）——[Hygiene Queue] 候选处理：确认后归档/删除，本脚本不自动删除")

    # 3. 敏感文件与被跟踪的构建产物（git 跟踪状态优先）
    if tracked is not None:
        for rel in sorted(tracked):
            base = os.path.basename(rel)
            if SENSITIVE_FILE_RE.match(base) and not base.endswith(".example"):
                criticals.append(f"敏感文件已被 git 跟踪: {rel}（需确认是否含真实凭据；是则轮换密钥并移出跟踪）")
            if base.lower().endswith(FORBIDDEN_EXT) and not rel.startswith("assets/"):
                errors.append(f"可执行/构建产物已被 git 跟踪: {rel}（ERROR：应 .gitignore 并 git rm --cached）")
    else:
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in files:
                if SENSITIVE_FILE_RE.match(f) and not f.endswith(".example"):
                    rel = os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/")
                    if os.path.dirname(rel) == "" and f == ".env":
                        continue  # 顶层 .env 已在结构检查中报告
                    criticals.append(f"敏感文件存在: {rel}（非 git 仓库无法确认忽略状态，需人工确认）")

    # 汇总输出
    for p in sorted(set(passes))[:8]:
        print(f"  - PASS     {p}")
    if len(set(passes)) > 8:
        print(f"  - PASS     ...（其余 {len(set(passes)) - 8} 项符合清单，略）")
    for i in sorted(set(infos)):
        print(f"  - INFO     {i}")
    for w in sorted(set(warns)):
        print(f"  - WARN     {w}")
    for e in sorted(set(errors)):
        print(f"  - ERROR    {e}")
    for c in sorted(set(criticals)):
        print(f"  - CRITICAL {c}")
    print("-" * 60)
    blocking = len(set(criticals)) + len(set(errors))
    head = "FAIL  check-project-hygiene.py" if blocking else ("WARN  check-project-hygiene.py" if warns else "PASS  check-project-hygiene.py")
    print(head)
    print(f"Summary: {len(set(passes))} allowed, {len(set(infos))} info, {len(set(warns))} hygiene-queue, {len(set(errors))} error, {len(set(criticals))} critical")
    print("原则: 只检测不删除；WARN 进 Hygiene Queue 由人批量裁决；CRITICAL/ERROR 阻断（exit 1）")
    if queue_out:
        import json, datetime
        qp = queue_out if os.path.isabs(queue_out) else os.path.join(root, queue_out)
        os.makedirs(os.path.dirname(qp), exist_ok=True)
        today = datetime.date.today().isoformat()
        prev = {"items": []}
        if os.path.isfile(qp):
            try:
                prev = json.load(open(qp, encoding="utf-8"))
            except (OSError, ValueError):
                prev = {"items": []}
        prev_map = {it.get("path"): it for it in prev.get("items", [])}
        items = []
        for w in sorted(set(warns)):
            # 抽取路径证据（首个 root/xxx 片段）
            m = re.search(r"root/([^（]+?)", w)
            path_key = m.group(1).strip() if m else w[:60]
            old = prev_map.get(path_key)
            items.append({
                "path": path_key,
                "severity": "WARN",
                "reason": w.split("——")[0].strip(),
                "first_seen": (old or {}).get("first_seen", today),
                "status": (old or {}).get("status") if (old and (old or {}).get("status") == "resolved") else "pending",
                "detail": w,
            })
        # 之前 Queue 中存在、本次未检出的条目 → resolved（文件已消失）
        for path_key, old in prev_map.items():
            if path_key not in {it["path"] for it in items} and old.get("status") != "resolved":
                items.append({**old, "status": "resolved", "resolved_at": today})
        payload = {"updated_at": today, "items": items}
        with open(qp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        pending = sum(1 for it in items if it.get("status") == "pending")
        print(f"Hygiene Queue 已持久化: {qp}（pending {pending} / resolved {len(items) - pending}）")
    if blocking:
        print("卫生检查: FAIL —— CRITICAL/ERROR 阻断，修复后才能继续")
        return 1
    print("卫生检查: PASS" + ("（Queue 中有待裁决项）" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
