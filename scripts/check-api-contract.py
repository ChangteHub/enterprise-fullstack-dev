#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-api-contract.py — 检查后端 Controller 的 RESTful 路由与统一 Result 契约。
用法:
    python check-api-contract.py <后端项目路径>
检查项:
    1. Controller 方法是否使用标准 HTTP 注解(Get/Post/Put/Delete/Patch)
    2. 资源路径是否为名词复数风格（粗略启发式，给出 WARN）
    3. 是否返回统一包装类型 Result
    4. 写操作的 @RequestBody 是否带 @Valid 校验
输出: N endpoints checked。启发式静态检查，结果供人工复核。
"""
import os
import re
import sys

HTTP_ANNOT = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping")
MAPPING_PATH = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\s*\(([^)]*)\)")
CLASS_MAPPING = re.compile(r"@RequestMapping\s*\(([^)]*)\)")
VERB_PATH = re.compile(r"/(get|find|query|add|create|insert|update|edit|delete|remove|save)[a-zA-Z]*", re.I)


def find_controllers(root):
    hits = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.endswith("Controller.java"):
                hits.append(os.path.join(dirpath, fn))
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check-api-contract.py <后端项目路径>")
        return 2
    root = os.path.abspath(sys.argv[1])
    controllers = find_controllers(root)
    if not controllers:
        print("WARN  check-api-contract.py")
        print("  - 未发现 *Controller.java（若后端尚未编写可忽略）")
        print("-" * 60)
        print("Summary: 0 endpoints checked, 1 warnings")
        return 0

    endpoint_count = 0
    warns = []
    for path in controllers:
        rel = os.path.relpath(path, root)
        txt = open(path, encoding="utf-8", errors="ignore").read()
        endpoint_count += len(HTTP_ANNOT.findall(txt))

        if not re.search(r"\bResult\b", txt):
            warns.append(f"{rel}: 未出现统一返回类型 Result，确认是否统一响应契约")

        for m in MAPPING_PATH.finditer(txt):
            verb, args = m.group(1), m.group(2)
            if VERB_PATH.search(args):
                warns.append(f"{rel}: @{verb}Mapping({args.strip()}) 路径含动词，RESTful 推荐名词复数")
            tail = txt[m.end(): m.end() + 300]
            if verb in ("Post", "Put", "Patch") and "@RequestBody" in tail and "@Valid" not in tail:
                warns.append(f"{rel}: @{verb}Mapping 的 @RequestBody 缺少 @Valid 校验")

        if not CLASS_MAPPING.search(txt):
            warns.append(f"{rel}: 类上缺少 @RequestMapping 基础路径（如 /api/students）")

    for w in sorted(set(warns)):
        print(f"  - WARN {w}")
    print("-" * 60)
    head = "WARN  check-api-contract.py" if warns else "PASS  check-api-contract.py"
    print(head)
    print(f"Summary: {endpoint_count} endpoints checked, {len(set(warns))} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
