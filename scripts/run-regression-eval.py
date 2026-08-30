#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-regression-eval.py — Regression Eval Runner（v3.1）。
用法: python run-regression-eval.py
对 regression.json 逐用例执行 machine_checks，防止 v3.0/v3.1 修复过的误报退化。
"""
import sys

from _eval_common import load_cases, report


def main() -> int:
    cases = load_cases("regression")
    if len(cases) < 5:
        print(f"FAIL  Regression Eval: 用例数 {len(cases)} < 5")
        return 1
    results = []
    for c in cases:
        status, details = __import__("_eval_common").run_machine_checks(c)
        results.append((c.get("id", "?"), status, details))
    return report("Regression Eval", results, "（行为断言按 baseline.md 演练核对）")


if __name__ == "__main__":
    sys.exit(main())
