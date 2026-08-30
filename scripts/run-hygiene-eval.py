#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-hygiene-eval.py — Hygiene Eval Runner（v3.1.1）。
用法: python run-hygiene-eval.py
对 hygiene.json 逐用例执行 machine_checks（干净/污染双 fixture + 严重度断言）。
"""
import sys

from _eval_common import load_cases, report


def main() -> int:
    cases = load_cases("hygiene")
    if len(cases) < 3:
        print(f"FAIL  Hygiene Eval: 用例数 {len(cases)} < 3")
        return 1
    results = []
    for c in cases:
        status, details = __import__("_eval_common").run_machine_checks(c)
        results.append((c.get("id", "?"), status, details))
    return report("Hygiene Eval", results, "（Queue 持久化断言需真实项目核对）")


if __name__ == "__main__":
    sys.exit(main())
