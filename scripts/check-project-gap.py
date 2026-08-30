#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-project-gap.py — Project Gap Analysis（v3.1）。
用法:
    python check-project-gap.py <项目根路径>
定位:
    已有项目 REFACTOR 的 Gap Analysis 步骤：把"项目事实"与".decision/project-decision.yaml"
    声明的目标状态做机器比对，输出 HIGH / MEDIUM / LOW 差距与最小改造动作。
    不再依赖人工记忆比对规范——差距清单可复现。
分级:
    HIGH    安全/正确性/决策冲突（如声明 Mode A 却存在 apps/；auth=jwt 却无 security 层）
    MEDIUM  工程化缺口（决策启用 CI 但无 workflow；启用 docker-compose 但无编排文件）
    LOW     文档/辅助缺口（缺人读版决策记录、缺种子脚本）
前置: 建议先运行 validate-decision-record.py（status=confirmed 才有意义比对）。
只检查不修改。
"""
import importlib.util
import os
import sys

sys.dont_write_bytecode = True  # 零依赖脚本不应在用户项目/skill 目录留下 __pycache__

# 复用 validate-decision-record.py 的零依赖 YAML 子集解析器（文件名含连字符，用 importlib 加载）
_vdr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate-decision-record.py")
_spec = importlib.util.spec_from_file_location("validate_decision_record", _vdr_path)
_vdr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vdr)
parse_simple_yaml = _vdr.parse_simple_yaml

SKIP_DIRS = {"node_modules", "target", "dist", "build", ".git", ".idea", ".venv", "coverage"}


def load_decision(root):
    path = os.path.join(root, ".decision", "project-decision.yaml")
    if not os.path.isfile(path):
        return None
    data = {}
    raw = parse_simple_yaml(open(path, encoding="utf-8").read())
    # 展平为 section.key
    for k, v in raw.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                data[f"{k}.{k2}"] = str(v2).lower()
        else:
            data[k] = str(v).lower()
    return data


def has_dir(root, *parts):
    return os.path.isdir(os.path.join(root, *parts))


def has_file(root, *parts):
    return os.path.isfile(os.path.join(root, *parts))


def any_dir_exists(root, names):
    return any(has_dir(root, n) for n in names)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--json"]
    json_out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if not args:
        print("用法: python check-project-gap.py <项目根路径> [--json 输出路径]")
        return 2
    root = os.path.abspath(args[0])
    if not os.path.isdir(root):
        print(f"错误: 目录不存在 {root}")
        return 2

    decision = load_decision(root)
    if decision is None:
        print("BLOCKED check-project-gap.py")
        print("  - BLOCKED 缺少 .decision/project-decision.yaml——没有 Target State 就没有 Gap 可言")
        print("  - 先建立决策记录（可参考 Skill 包内 .decision/schema.yaml）")
        return 1

    highs, mediums, lows, nexts = [], [], [], []
    d = decision

    # ---- 决策冲突类（HIGH）----
    fe_mode = d.get("frontend.mode", "a")
    has_apps = has_dir(root, "apps")
    has_frontend = has_dir(root, "frontend")
    if fe_mode == "a" and has_apps:
        highs.append("决策 frontend.mode=a（单前端）但仓库存在 apps/ ——结构与决策冲突（Mode A 禁止 apps/ 与 frontend/ 并存）")
        nexts.append("移除 apps/ 或将决策升级为 a-plus 并说明理由")
    if fe_mode in ("a-plus", "b") and not has_apps:
        mediums.append(f"决策 frontend.mode={fe_mode} 但未发现 apps/ 多前端结构")
    if has_frontend and has_apps:
        highs.append("frontend/ 与 apps/ 并存——两套前端目录违反结构禁令")

    backend_arch = d.get("backend.architecture", "monolith")
    if backend_arch == "microservices" and not has_dir(root, "services"):
        highs.append("决策 backend.architecture=microservices 但不存在 services/ ——决策与事实严重不符，需 Re-open 决策")

    # ---- 认证/数据（HIGH）----
    java_root = None
    for cand in ("backend", "."):
        base = os.path.join(root, cand, "src", "main", "java")
        if has_dir(root, cand, "src", "main", "java"):
            java_root = os.path.join(root, cand, "src", "main", "java")
            break
    pkgs = set()
    if java_root:
        for dirpath, dirnames, _ in os.walk(java_root):
            pkgs.add(os.path.basename(dirpath))
    if d.get("auth.enabled") == "true" and d.get("auth.strategy") == "jwt":
        if not ({"security", "config"} & pkgs):
            highs.append("决策 auth=jwt 但后端未见 security/ 或 config/ 包（认证层缺失）")
    if d.get("database.migration") == "flyway":
        if not (has_dir(root, "backend", "src", "main", "resources", "db", "migration")
                or has_dir(root, "src", "main", "resources", "db", "migration")
                or has_dir(root, "database", "migrations")):
            highs.append("决策 database.migration=flyway 但未发现迁移目录（schema 无版本管理）")
            nexts.append("建立 db/migration 并以 V1 起步")
    if d.get("database.engine") in ("mysql", "postgresql") and d.get("database.migration") != "none":
        if not has_file(root, "scripts", "seed-test-data.sh"):
            mediums.append("启用数据库但缺少测试数据生命周期脚本（seed/reset/verify）——临时 SQL 是被禁止的默认路径")
            nexts.append("添加 scripts/seed-test-data.sh（幂等 + 环境保护）")

    # ---- 工程化（MEDIUM）----
    if d.get("ci.enabled") == "true":
        wf = os.path.join(root, ".github", "workflows")
        has_ci = os.path.isdir(wf) and any(f.endswith((".yml", ".yaml")) for f in os.listdir(wf)) if os.path.isdir(wf) else False
        if not has_ci:
            mediums.append("决策 ci.enabled=true 但未发现 CI 工作流")
            nexts.append("添加 .github/workflows/ci.yml")
    if d.get("deployment.runtime") == "docker-compose" and not any(
            has_file(root, f) for f in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml")):
        mediums.append("决策 runtime=docker-compose 但缺少 compose 编排文件")
    if d.get("deployment.proxy") == "nginx" and not any_dir_exists(root, ["nginx", "deploy", "infrastructure"]) \
            and not has_file(root, "frontend", "nginx.conf"):
        lows.append("决策 proxy=nginx 但未发现 Nginx 配置文件")

    # ---- 测试与文档（LOW/MEDIUM）----
    if d.get("scope") in ("l2", "l3"):
        has_tests = any_dir_exists(root, ["tests", "test"]) or has_dir(root, "backend", "src", "test") or has_dir(root, "frontend", "src")
        if not (has_dir(root, "backend", "src", "test") or has_dir(root, "tests") or has_dir(root, "test")):
            mediums.append("L2/L3 项目未见任何测试目录（回归无从谈起）")
    if not has_file(root, "docs", "architecture", "decision-record.md"):
        lows.append("缺少人读版决策记录 docs/architecture/decision-record.md（机器版与人读版应并存）")
        nexts.append("补充 docs/architecture/decision-record.md")
    if not has_file(root, "README.md"):
        lows.append("缺少 README.md")

    # 输出
    print("=== PROJECT GAP ANALYSIS ===")
    print("-" * 60)
    print("Target State: " + ", ".join(f"{k}={v}" for k, v in sorted(d.items()) if not isinstance(v, dict))[:150])
    for label, items in (("HIGH", highs), ("MEDIUM", mediums), ("LOW", lows)):
        for it in items:
            print(f"  {label:6} {it}")
    if not (highs or mediums or lows):
        print("  （无差距——项目事实与决策一致）")
    print("-" * 60)
    if nexts:
        print("Suggested Next Actions:")
        for i, n in enumerate(dict.fromkeys(nexts), 1):
            print(f"  {i}. {n}")
    head = "FAIL  check-project-gap.py" if highs else ("WARN  check-project-gap.py" if mediums else "PASS  check-project-gap.py")
    print(head)
    print(f"Summary: {len(highs)} high, {len(mediums)} medium, {len(lows)} low（HIGH 阻断，MEDIUM 建议本轮处理，LOW 记入债务）")
    if json_out:
        import json, datetime
        os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
        payload = {
            "artifact": "PROJECT GAP",
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "project_root": root,
            "target_state": d,
            "gaps": {"high": highs, "medium": mediums, "low": lows},
            "next_actions": list(dict.fromkeys(nexts)),
        }
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"PROJECT GAP 已落盘: {json_out}")
    return 1 if highs else 0


if __name__ == "__main__":
    sys.exit(main())
