#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-functional-eval.py — Functional Eval Runner（v3.1）。
用法: python run-functional-eval.py
对 functional.json 逐用例执行 machine_checks（validator/文件断言）；
无 machine_checks 的行为类用例如实标记 MANUAL。
"""
import sys

from _eval_common import load_cases, report


def main() -> int:
    cases = load_cases("functional")
    if len(cases) < 5:
        print(f"FAIL  Functional Eval: 用例数 {len(cases)} < 5")
        return 1
    results = []
    for c in cases:
        status, details = __import__("_eval_common").run_machine_checks(c)
        results.append((c.get("id", "?"), status, details))
    return report("Functional Eval", results, "（行为断言按 baseline.md 演练核对）")


if __name__ == "__main__":
    sys.exit(main())
