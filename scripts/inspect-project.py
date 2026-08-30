#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect-project.py — Project Recon（项目侦察）：为已有项目建立当前状态快照。
用法:
    python inspect-project.py <项目根路径>
定位:
    REFACTOR / FEATURE 模式的第一步。先认识项目，再决定改什么——
    不要为了匹配模板对已有项目做无意义重构（保持现有体系优先原则）。
输出 PROJECT BASELINE 字段:
    Detected Stack / Repository Shape / Runtime / Database / CI-CD /
    Observability / Git Status / Current Risks / Open Questions / Unknowns
只读取，不修改任何文件；信息类输出恒以退出码 0 结束（发现的风险交给 hygiene/security 检查器定级）。
"""
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {"node_modules", "target", "dist", ".git", "build", ".idea", ".venv", "venv", "coverage"}


def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def run_git(args, root):
    try:
        out = subprocess.run(["git"] + args, cwd=root, capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def detect_frontend(root, fe_root):
    info = {}
    pkg = json.loads(read(os.path.join(fe_root, "package.json")) or "{}")
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    fw = None
    for name, ver in sorted(deps.items()):
        if name in ("react", "vue", "next", "nuxt", "svelte") and fw is None:
            fw = f"{name} {ver.lstrip('^~')}"
    ui = [n for n in deps if re.match(r"(antd|antd-mobile|element|arco|vant|tailwind)", n)]
    state = [n for n in deps if n in ("zustand", "redux", "@reduxjs/toolkit", "pinia", "mobx", "jotai")]
    build = "vite" if any(n in deps for n in ("vite",)) else ("webpack" if "webpack" in deps else "?")
    info["框架"] = fw or "未识别"
    info["构建"] = build
    if ui:
        info["UI"] = ", ".join(ui[:3])
    if state:
        info["状态管理"] = ", ".join(state[:3])
    lock = [f for f in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock") if os.path.isfile(os.path.join(fe_root, f))]
    info["锁文件"] = ", ".join(lock) if lock else "未发现（构建不可复现）"
    src = os.path.join(fe_root, "src")
    if os.path.isdir(src):
        sub = sorted(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
        info["src 目录"] = ", ".join(sub[:12])
    return info


def detect_backend(root, be_root):
    info = {}
    pom = read(os.path.join(be_root, "pom.xml"))
    gradle = read(os.path.join(be_root, "build.gradle")) + read(os.path.join(be_root, "build.gradle.kts"))
    build_file = "Maven (pom.xml)" if pom else ("Gradle" if gradle else "未识别")
    info["构建"] = build_file
    txt = pom or gradle
    m = re.search(r"<java\.version>([^<]+)</java\.version>|sourceCompatibility\s*=?\s*['\"]?(\d+)", txt)
    if m:
        info["Java"] = m.group(1) or m.group(2)
    m = re.search(r"spring-boot-starter-parent</artifactId>\s*<version>([^<]+)", pom)
    if m:
        info["Spring Boot"] = m.group(1)
    if "mybatis-plus" in txt:
        info["ORM"] = "MyBatis-Plus"
    elif "spring-boot-starter-data-jpa" in txt:
        info["ORM"] = "JPA/Hibernate"
    for mark, label in (("spring-boot-starter-security", "Spring Security"), ("jjwt|java-jwt", "JWT"),
                        ("spring-boot-starter-websocket", "WebSocket"), ("spring-boot-starter-actuator", "Actuator"),
                        ("knife4j|springdoc", "API 文档")):
        if re.search(mark, txt):
            info.setdefault("组件", []).append(label)
    if "组件" in info:
        info["组件"] = ", ".join(info["组件"])
    src_main = os.path.join(be_root, "src", "main", "java")
    pkgs = set()
    if os.path.isdir(src_main):
        for dirpath, dirnames, _ in os.walk(src_main):
            b = os.path.basename(dirpath)
            if b in ("controller", "service", "repository", "mapper", "dao", "entity", "domain",
                     "dto", "vo", "model", "config", "security", "exception", "common", "utils"):
                pkgs.add(b)
    if pkgs:
        info["后端分层包"] = ", ".join(sorted(pkgs))
    return info


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--json"]
    json_out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if not args:
        print("用法: python inspect-project.py <项目根路径> [--json 输出路径]")
        return 2
    root = os.path.abspath(args[0])
    if not os.path.isdir(root):
        print(f"错误: 目录不存在 {root}")
        return 2

    lines, risks, open_questions, unknowns = [], [], [], []
    audit_facts = {}

    def section(title, items):
        lines.append(f"{title}:")
        audit_facts[title] = dict(items) if items else {}
        if items:
            for k, v in items.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append("  - （未发现）")

    # 仓库形态
    has = lambda *names: [n for n in names if os.path.isdir(os.path.join(root, n))]
    fe_dirs = has("frontend") + [f"apps/{d}" for d in (os.listdir(os.path.join(root, "apps"))
                    if os.path.isdir(os.path.join(root, "apps")) else [])]
    be_dirs = has("backend") + [f"services/{d}" for d in (os.listdir(os.path.join(root, "services"))
                    if os.path.isdir(os.path.join(root, "services")) else [])]
    shape = {}
    if fe_dirs:
        shape["前端工程"] = ", ".join(fe_dirs)
    if be_dirs:
        shape["后端工程"] = ", ".join(be_dirs)
    shape["仓库形态"] = "monorepo(apps/services/packages)" if os.path.isdir(os.path.join(root, "apps")) \
        else "单仓库(frontend+backend)"
    section("Repository Shape", shape)

    # 技术栈
    fe_root = os.path.join(root, fe_dirs[0].split("/")[-1] if "/" not in fe_dirs[0] else fe_dirs[0]) if fe_dirs else None
    if fe_dirs and os.path.isdir(os.path.join(root, fe_dirs[0])):
        section("Frontend Stack", detect_frontend(root, os.path.join(root, fe_dirs[0])))
    if be_dirs and os.path.isdir(os.path.join(root, be_dirs[0])):
        section("Backend Stack", detect_backend(root, os.path.join(root, be_dirs[0])))

    # 数据库 / 迁移
    db = {}
    mig_dirs = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if os.path.basename(dirpath) in ("migration", "migrations"):
            mig_dirs.append(os.path.relpath(dirpath, root))
        if os.path.basename(dirpath) == "changelog":
            db["Liquibase"] = os.path.relpath(dirpath, root)
    if mig_dirs:
        db["迁移目录"] = ", ".join(sorted(mig_dirs)[:3])
        db["Flyway"] = "是"
    else:
        db["迁移"] = "未发现 Flyway/Liquibase（风险：schema 无版本管理）"
        risks.append("数据库 schema 缺少版本化迁移（Flyway/Liquibase）")
    if os.path.isfile(os.path.join(root, "backend/src/main/resources/schema.sql")) or \
       any("schema.sql" in f for _, _, fs in os.walk(root) for f in fs):
        pass  # schema.sql 与迁移共存属正常
    section("Database", db)

    # 运行时
    rt = {}
    dockerfiles = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in files:
            if f == "Dockerfile":
                dockerfiles.append(os.path.relpath(os.path.join(dirpath, f), root))
    if dockerfiles:
        rt["Dockerfile"] = ", ".join(dockerfiles[:4])
    compose = [f for f in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml")
               if os.path.isfile(os.path.join(root, f))]
    if compose:
        rt["Compose"] = ", ".join(compose)
    nginx = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".conf") and "nginx" in os.path.join(dirpath, f).lower():
                nginx.append(os.path.relpath(os.path.join(dirpath, f), root))
    if nginx:
        rt["Nginx"] = ", ".join(nginx[:3])
    if not rt:
        risks.append("未发现容器化/代理配置（部署能力未就绪）")
    section("Runtime", rt)

    # CI/CD
    ci = {}
    wf = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf):
        ymls = [f for f in os.listdir(wf) if f.endswith((".yml", ".yaml"))]
        ci["GitHub Actions"] = ", ".join(ymls) if ymls else "目录存在但无工作流"
    for f in (".gitlab-ci.yml", "Jenkinsfile"):
        if os.path.isfile(os.path.join(root, f)):
            ci[f] = "存在"
    if not ci:
        unknowns.append("未发现 CI/CD 配置——需确认是否要求持续集成")
    section("CI-CD", ci)

    # 可观测性
    obs = {}
    pom_paths = [os.path.join(root, "backend", "pom.xml"), os.path.join(root, "pom.xml")]
    be_txt = "".join(read(p) for p in pom_paths)
    if "actuator" in be_txt:
        obs["健康检查"] = "Spring Actuator"
    if re.search(r"logback|log4j", be_txt):
        obs["日志"] = "logback/log4j"
    if not obs:
        unknowns.append("未发现可观测性配置（健康检查/日志/指标）——需确认生产要求")
    section("Observability", obs)

    # Git 状态
    gs = {}
    if run_git(["rev-parse", "--git-dir"], root):
        gs["分支"] = run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
        dirty = run_git(["status", "--porcelain"], root)
        gs["未提交变更"] = f"{len(dirty.splitlines())} 项" if dirty else "干净"
        tracked_env = ".env" in run_git(["ls-files"], root).splitlines()
        if tracked_env:
            risks.append("CRITICAL 级风险：.env 被 git 跟踪（可能凭据入库）")
            gs[".env"] = "已被 git 跟踪（危险）"
        else:
            gs[".env"] = "未跟踪" if os.path.isfile(os.path.join(root, ".env")) else "不存在"
    else:
        unknowns.append("非 git 仓库——无法评估提交历史与敏感文件入库状态")
    section("Git Status", gs)

    print("=== PROJECT AUDIT (Facts) ===")
    print("=" * 60)
    for l in lines:
        print(l)
    print("-" * 60)
    print("Current Risks:")
    for r in risks or ["（未发现明显风险）"]:
        print(f"  - {r}")
    print("Suggested Next Actions（基于事实的最小改造建议）:")
    suggestions = []
    if not mig_dirs:
        suggestions.append("引入版本化数据库迁移（db/migration + Flyway/Liquibase）")
    if not rt:
        suggestions.append("容器化运行时（Dockerfile + docker-compose + 反代）")
    if not ci:
        suggestions.append("添加 CI 工作流（.github/workflows）")
    if not os.path.isfile(os.path.join(root, "scripts", "seed-test-data.sh")):
        suggestions.append("建立测试数据生命周期（scripts/seed-test-data.sh，替代临时 SQL）")
    if os.path.isfile(os.path.join(root, ".decision", "project-decision.yaml")):
        suggestions.append("运行 check-project-gap.py：对照决策记录输出结构差距")
    else:
        suggestions.append("建立 Decision Record（.decision/project-decision.yaml + docs 版）")
    for i, s in enumerate(suggestions or ["（无——事实链完整，进入 Gap/决策比对）"], 1):
        print(f"  {i}. {s}")
    print("Open Questions（需要用户决策的方向）:")
    for q in open_questions or ["（无——由 Decision Record 阶段确定）"]:
        print(f"  - {q}")
    print("Unknowns（未能自动发现，需人工确认）:")
    for u in unknowns or ["（无）"]:
        print(f"  - {u}")
    print("-" * 60)
    print("PASS  inspect-project.py")
    print(f"Summary: recon OK, {len(risks)} risks, {len(unknowns)} unknowns（侦察为只读输出，风险定级交给 hygiene/security 检查器）")
    if json_out:
        import json, datetime
        os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
        payload = {
            "artifact": "PROJECT BASELINE",
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "project_root": root,
            "facts": audit_facts,
            "risks": risks,
            "open_questions": open_questions,
            "unknowns": unknowns,
        }
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"PROJECT BASELINE 已落盘: {json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
