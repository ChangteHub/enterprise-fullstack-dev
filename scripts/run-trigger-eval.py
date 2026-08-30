#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-trigger-eval.py — Trigger Eval Runner（v3.1）。
用法: python run-trigger-eval.py
机器可执行部分：trigger.json 的结构完整性（用例数/正反例分布/字段齐全/id 唯一/深度合法）。
"正例应触发、反例不应触发" 属 LLM 行为断言，需带 Skill 演练核对（协议见 evals/baseline.md）。
"""
import sys

from _eval_common import load_cases, report


def main() -> int:
    cases = load_cases("trigger")
    results = []
    seen_ids = set()
    for c in cases:
        cid = c.get("id", "?")
        problems = []
        if cid in seen_ids:
            problems.append("id 重复")
        seen_ids.add(cid)
        if not c.get("input"):
            problems.append("缺 input")
        # 兼容 JSON 中的布尔或字符串 'True'/'False'
        st = str(c.get("should_trigger", "")).lower()
        if st not in ("true", "false"):
            problems.append("缺 should_trigger 布尔")
        # 正例必须带合法深度；负例（should_trigger=false）不触发任务，深度允许为空
        depth = c.get("expected_depth")
        if st == "true" and depth not in ("L0", "L1", "L2", "L3"):
            problems.append(f"expected_depth 非法: {depth}")
        if st == "false" and depth not in ("L0", "L1", "L2", "L3", "NONE", None, ""):
            problems.append(f"负例 expected_depth 非法: {depth}")
        results.append((cid, "FAIL" if problems else "PASS", problems))

    pos = sum(1 for c in cases if str(c.get("should_trigger", "")).lower() == "true")
    neg = sum(1 for c in cases if str(c.get("should_trigger", "")).lower() == "false")
    structural = []
    if len(cases) < 20:
        structural.append(f"用例总数 {len(cases)} < 20")
    if pos < 10:
        structural.append(f"正例 {pos} < 10")
    if neg < 10:
        structural.append(f"反例 {neg} < 10")
    for s in structural:
        print(f"  [STRUCT] {s}")

    code = report("Trigger Eval（结构层）", results, "；触发行为需带 Skill 演练核对")
    if structural:
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
