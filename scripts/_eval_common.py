#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_eval_common.py — Eval Runner 共享执行内核（v3.1，私有模块，非独立入口）。
设计原则（对应 v3.1 指南 §13）:
    - Eval 必须真正可执行：结构校验 + machine_checks（验证行为与产物，而非文本匹配）
    - 诚实分级：有 machine_checks 的用例给出 PASS/FAIL；没有的如实标记 MANUAL，
      不伪造 "全部 PASS"
"""
import json
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPTS_DIR)


def load_cases(eval_name):
    path = os.path.join(SKILL_ROOT, "evals", f"{eval_name}.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("cases", [])


def run_check(check):
    """执行一条 machine_check，返回 (ok, detail)。"""
    ctype = check.get("type")
    if ctype == "validator":
        script = os.path.join(SCRIPTS_DIR, check["script"])
        if not script.endswith(".py"):
            script += ".py"
        target = os.path.join(SKILL_ROOT, check["target"]) if not os.path.isabs(check["target"]) else check["target"]
        expect_exit = int(check.get("expect_exit", 0))
        try:
            out = subprocess.run([sys.executable, script, target], capture_output=True, text=True, timeout=120)
            merged = out.stdout or out.stderr or ""
            ok = out.returncode == expect_exit
            detail = f"exit={out.returncode}（期望 {expect_exit}）"
            # 可选输出断言：部分脚本 WARN 不影响退出码，须用输出文本证明误报未退化
            for needle in check.get("expect_contains", []):
                if needle not in merged:
                    ok = False
                    detail += f"，输出缺少 '{needle}'"
            for needle in check.get("expect_not_contains", []):
                if needle in merged:
                    ok = False
                    detail += f"，输出出现不应有的 '{needle}'"
            tail = merged.strip().splitlines()[-1] if merged.strip() else ""
            detail += f" {tail[:60]}"
            return ok, detail
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"执行失败: {e}"
    if ctype == "file_exists":
        path = os.path.join(SKILL_ROOT, check["path"])
        return os.path.isfile(path), path
    if ctype == "file_contains":
        path = os.path.join(SKILL_ROOT, check["path"])
        if not os.path.isfile(path):
            return False, f"文件不存在: {check['path']}"
        content = open(path, encoding="utf-8", errors="ignore").read()
        return check["pattern"] in content, f"{check['path']} 含 '{check['pattern']}'"
    if ctype == "file_not_contains":
        path = os.path.join(SKILL_ROOT, check["path"])
        if not os.path.isfile(path):
            return False, f"文件不存在: {check['path']}"
        content = open(path, encoding="utf-8", errors="ignore").read()
        return check["pattern"] not in content, f"{check['path']} 不含 '{check['pattern']}'"
    return False, f"未知 check 类型: {ctype}"


def run_machine_checks(case):
    """返回 (status, details)：status ∈ PASS / FAIL / MANUAL。"""
    checks = case.get("machine_checks") or []
    if not checks:
        return "MANUAL", ["（无 machine_checks——行为类用例需人工/带 Skill 演练核对）"]
    details = []
    ok_all = True
    for c in checks:
        ok, detail = run_check(c)
        ok_all = ok_all and ok
        details.append(f"  {'✓' if ok else '✗'} {c.get('type')}: {detail}")
    return ("PASS" if ok_all else "FAIL"), details


def report(title, results, manual_hint):
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    manual = sum(1 for _, s, _ in results if s == "MANUAL")
    for case_id, status, details in results:
        print(f"  [{status:^6}] {case_id}")
        if status != "PASS":
            for d in details:
                print(f"           {d}")
    print("-" * 60)
    head = "PASS" if failed == 0 else "FAIL"
    print(f"{head}  {title}: {passed}/{len(results)} machine-PASS"
          + (f", {failed} FAIL" if failed else "")
          + (f", {manual} MANUAL{manual_hint}" if manual else ""))
    return 1 if failed else 0
