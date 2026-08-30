#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-project.py — 检查一个全栈项目的目录结构、必备文件与命名规范。
用法:
    python validate-project.py <项目根路径> [--mode A|B]
不区分 Mode A(frontend/+backend/) 与 Mode B(apps/+services/)，自动探测。
输出: project structure: PASS / 缺失项清单；有致命缺失时退出码 1。只检查不修改。

v3.0 判定策略（模式感知，尊重框架惯例，不为命名牺牲正确性）:
    - 数据访问层接受 repository/ 或 mapper/ 或 dao/（MyBatis-Plus 项目惯用 mapper/，
      强制改名属于无意义重构——参见 Project Recon "不要强行统一"原则）
    - 传输对象层接受 dto/ 或 vo/ 或 model/
    - 异常层接受 exception/ 或 common/（Skill 结构两者均合法）
    - security/ 为推荐项（WARN）；认证代码放在 config/ 或 utils/ 同样常见
    - 后端构建文件接受 pom.xml 或 build.gradle(.kts)；前端接受 npm/pnpm 锁文件
"""
import os
import re
import sys
import argparse

# 前端必备（相对一个前端 app 根目录）
FRONTEND_DIRS = ["src"]
FRONTEND_FILES = ["package.json", "tsconfig.json"]  # vite.config.ts / vue.config.ts 由框架别名判断
FRONTEND_CONFIG_ALIASES = ["vite.config.ts", "vite.config.js", "vite.config.mts", "vue.config.js", "next.config.js", "nuxt.config.ts"]
FRONTEND_SRC = {
    "http 层": ["services", "api"],
    "页面": ["pages", "views"],
    "组件": ["components"],
    "路由": ["router", "routes"],
    "状态(推荐)": ["stores", "store"],
}
# 后端必备（相对一个后端 service 根目录）
BACKEND_BUILD_FILES = ["pom.xml", "build.gradle", "build.gradle.kts"]
# 分层包：error=错误, transfer=传输对象, data=数据访问 —— 每组任选其一即视为该层存在
BACKEND_LAYER_GROUPS = {
    "controller": ["controller"],
    "service": ["service"],
    "entity": ["entity", "domain", "model"],
    "数据访问(repository|mapper|dao)": ["repository", "mapper", "dao"],
    "传输对象(dto|vo|model)": ["dto", "vo", "model"],
    "错误/异常(exception|common)": ["exception", "common"],
}
BACKEND_RECOMMENDED = {"security(认证授权)": ["security"], "config": ["config"]}
# 根目录推荐文件
ROOT_FILES = [".gitignore", "README.md", ".env.example"]


def find_frontend_roots(root: str):
    candidates = []
    fa = os.path.join(root, "frontend")
    if os.path.isdir(fa):
        candidates.append(fa)
    apps = os.path.join(root, "apps")
    if os.path.isdir(apps):
        for name in os.listdir(apps):
            p = os.path.join(apps, name)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "package.json")):
                candidates.append(p)
    return candidates


def find_backend_roots(root: str):
    candidates = []
    be = os.path.join(root, "backend")
    if os.path.isdir(be):
        candidates.append(be)
    svcs = os.path.join(root, "services")
    if os.path.isdir(svcs):
        for name in os.listdir(svcs):
            p = os.path.join(svcs, name)
            if any(os.path.isfile(os.path.join(p, f)) for f in BACKEND_BUILD_FILES):
                candidates.append(p)
    return candidates


def find_first_dir(base, names):
    for n in names:
        if os.path.isdir(os.path.join(base, n)):
            return n
    return None


def check_frontend(path, errors, warns):
    name = os.path.basename(path)
    for d in FRONTEND_DIRS:
        if not os.path.isdir(os.path.join(path, d)):
            errors.append(f"[frontend:{name}] 缺少目录 {d}/")
    for f in FRONTEND_FILES:
        if not os.path.isfile(os.path.join(path, f)):
            errors.append(f"[frontend:{name}] 缺少文件 {f}")
    if not any(os.path.isfile(os.path.join(path, f)) for f in FRONTEND_CONFIG_ALIASES):
        warns.append(f"[frontend:{name}] 未发现构建框架配置（vite/vue/next config）")
    src = os.path.join(path, "src")
    if os.path.isdir(src):
        for label, aliases in FRONTEND_SRC.items():
            found = find_first_dir(src, aliases)
            if found is None:
                if "推荐" in label:
                    warns.append(f"[frontend:{name}] src/ 下建议有 {label} 目录 {aliases}")
                else:
                    warns.append(f"[frontend:{name}] src/ 下建议有 {label} 目录 {aliases}")
        # 禁止在 pages/components 里直接 import axios
        for dirpath, _, files in os.walk(src):
            for fn in files:
                if fn.endswith((".ts", ".tsx")) and ("pages" in dirpath or "components" in dirpath):
                    txt = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
                    if re_import_axios(txt):
                        warns.append(f"[frontend:{name}] {fn} 直接 import axios，应走 services/ 层")


def re_import_axios(txt: str) -> bool:
    return bool(re.search(r"""from\s+['"]axios['"]""", txt))


def check_backend(path, errors, warns):
    name = os.path.basename(path)
    if not any(os.path.isfile(os.path.join(path, f)) for f in BACKEND_BUILD_FILES):
        errors.append(f"[backend:{name}] 缺少构建文件 pom.xml / build.gradle(.kts)")
    # 递归找包目录
    found = set()
    src_main = os.path.join(path, "src", "main", "java")
    search_root = src_main if os.path.isdir(src_main) else path
    for dirpath, dirnames, _ in os.walk(search_root):
        found.add(os.path.basename(dirpath))
    for layer, aliases in BACKEND_LAYER_GROUPS.items():
        if not any(a in found for a in aliases):
            errors.append(f"[backend:{name}] 缺少分层包（{layer}，接受其一: {aliases}）")
    for layer, aliases in BACKEND_RECOMMENDED.items():
        if not any(a in found for a in aliases):
            warns.append(f"[backend:{name}] 建议有 {layer} 包（接受其一: {aliases}）")
    res = os.path.join(path, "src", "main", "resources")
    if os.path.isdir(res):
        has_yml = any(f.startswith("application") for f in os.listdir(res))
        if not has_yml:
            warns.append(f"[backend:{name}] resources/ 下没有 application*.yml")
    mig = os.path.join(path, "src", "main", "resources", "db", "migration")
    if not os.path.isdir(mig):
        root_mig = os.path.join(path, "database", "migrations")
        if not os.path.isdir(root_mig):
            warns.append(f"[backend:{name}] 未发现 Flyway migration 目录(db/migration 或 database/migrations)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="项目根路径")
    ap.add_argument("--mode", choices=["A", "B"], help="可选，强制指定模式")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    if not os.path.isdir(root):
        print("FAIL  validate-project.py")
        print(f"  - 路径不存在: {root}")
        print("-" * 60)
        print("Summary: 1 failed, 0 warnings")
        return 1

    errors, warns = [], []
    fe_roots = find_frontend_roots(root)
    be_roots = find_backend_roots(root)

    if not fe_roots:
        errors.append("未发现前端工程（frontend/ 或 apps/*/package.json）")
    if not be_roots:
        errors.append("未发现后端工程（backend/ 或 services/*/pom.xml|build.gradle）")
    for p in fe_roots:
        check_frontend(p, errors, warns)
    for p in be_roots:
        check_backend(p, errors, warns)
    for f in ROOT_FILES:
        if not os.path.isfile(os.path.join(root, f)):
            warns.append(f"根目录建议有 {f}")

    for w in warns:
        print(f"  - WARN {w}")
    for e in errors:
        print(f"  - FAIL {e}")
    print("-" * 60)
    mode = args.mode or ("B" if os.path.isdir(os.path.join(root, "services")) else "A")
    print(f"探测模式: Mode {mode} | 前端 {len(fe_roots)} 个, 后端 {len(be_roots)} 个")
    print("分层判定: 数据访问 repository|mapper|dao / 传输对象 dto|vo|model / 异常 exception|common 任选其一")
    head = "FAIL  validate-project.py" if errors else ("WARN  validate-project.py" if warns else "PASS  validate-project.py")
    print(head)
    print(f"Summary: {len(errors)} failed, {len(warns)} warnings")
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
