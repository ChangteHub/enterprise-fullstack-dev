#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-skill.py — 校验 enterprise-fullstack-dev Skill 自身结构是否合规。
用法:
    python validate-skill.py [skill根目录]
不传参数时，默认校验本脚本上一级目录（即 Skill 根目录）。
检查项:
    1. SKILL.md 存在且含合法 YAML frontmatter（name/description）
    2. name 与目录名一致（小写+连字符）
    3. SKILL.md 中引用的 references/*.md 全部真实存在（无死链）
    4. references/scripts/evals 目录与关键文件存在
输出: 逐项 PASS/FAIL，结尾汇总；存在 FAIL 时退出码为 1。
"""
import os
import re
import sys


def main() -> int:
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failures, warnings, passes = [], [], []

    def check(cond: bool, ok_msg: str, fail_msg: str):
        (passes if cond else failures).append(ok_msg if cond else fail_msg)

    # 1. SKILL.md 存在
    skill_md = os.path.join(root, "SKILL.md")
    check(os.path.isfile(skill_md), "SKILL.md 存在", "缺少 SKILL.md")
    check(os.path.isfile(os.path.join(root, "CHANGELOG.md")), "CHANGELOG.md 存在（Release Gate）", "缺少 CHANGELOG.md 变更记录")
    if not os.path.isfile(skill_md):
        report(passes, warnings, failures)
        return 1

    content = read_text(skill_md)

    # 2. frontmatter + name/description
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.S)
    check(bool(fm), "YAML frontmatter 存在", "缺少 YAML frontmatter（--- 包裹）")
    name = desc = None
    if fm:
        head = fm.group(1)
        m_name = re.search(r"^name:\s*(\S+)", head, re.M)
        name = m_name.group(1) if m_name else None
        check(bool(name), "frontmatter 含 name", "frontmatter 缺少 name")
        check(bool(re.search(r"^description:", head, re.M)), "frontmatter 含 description", "frontmatter 缺少 description")
        if name:
            check(bool(re.fullmatch(r"[a-z0-9-]+", name)), f"name 格式合法: {name}", f"name 应为小写字母/数字/连字符: {name}")
            dir_name = os.path.basename(root)
            check(name == dir_name, f"name 与目录名一致: {name}", f"name({name}) 与目录名({dir_name}) 不一致")
            desc_text = head
            check(desc_text.count("。") >= 1 or "时使用" in desc_text, "description 含 WHAT/WHEN 描述", "description 未说明做什么+何时用")

    # 3. SKILL.md 行数（OpenAI 建议 <500 行）
    line_count = content.count("\n") + 1
    check(line_count <= 500, f"SKILL.md 行数 {line_count} <= 500", f"SKILL.md 行数 {line_count} 超过 500，建议精简")
    if line_count > 500:
        pass
    # 4. references 死链检查（支持按域分子目录，如 references/frontend/structure.md）
    refs = re.findall(r"references/[a-zA-Z0-9_\-/]+\.md", content)
    ref_dir = os.path.join(root, "references")
    for link in sorted(set(refs)):
        check(os.path.isfile(os.path.join(root, link)), f"引用存在: {link}", f"死链: SKILL.md 引用了不存在的 {link}")
    ref_files = []
    if os.path.isdir(ref_dir):
        for dirpath, _, fnames in os.walk(ref_dir):
            ref_files += [os.path.join(dirpath, f) for f in fnames if f.endswith(".md")]
    ref_files = sorted(ref_files)
    check(len(ref_files) >= 10, f"references/ 含 {len(ref_files)} 个知识文件", "references/ 知识文件过少")

    # 5. scripts / evals 目录
    scripts_dir = os.path.join(root, "scripts")
    evals_dir = os.path.join(root, "evals")
    check(os.path.isdir(scripts_dir), "scripts/ 目录存在", "缺少 scripts/ 目录")
    check(os.path.isdir(evals_dir), "evals/ 目录存在", "缺少 evals/ 目录")
    expected_evals = {
        "trigger.json": "触发用例(正/反例)",
        "functional.json": "功能用例",
        "regression.json": "回归用例",
        "baseline.md": "对照实验协议",
    }
    for must, label in expected_evals.items():
        p = os.path.join(evals_dir, must)
        check(os.path.isfile(p), f"evals/{must} 存在（{label}）", f"缺少 evals/{must}（{label}）")
    # evals 数量下限：trigger >=10, functional >=5
    try:
        import json
        tj = os.path.join(evals_dir, "trigger.json")
        fj = os.path.join(evals_dir, "functional.json")
        if os.path.isfile(tj):
            tcases = json.load(open(tj, encoding="utf-8")).get("cases", [])
            pos = [c for c in tcases if c.get("should_trigger") is True]
            neg = [c for c in tcases if c.get("should_trigger") is False]
            check(len(tcases) >= 20, f"trigger 用例共 {len(tcases)} 个 (>=20)", f"trigger 用例仅 {len(tcases)} 个，至少 10 正+10 反")
            check(len(pos) >= 10, f"trigger 正例 {len(pos)} 个 (>=10)", f"trigger 正例仅 {len(pos)} 个，至少 10 个")
            check(len(neg) >= 10, f"trigger 反例 {len(neg)} 个 (>=10)", f"trigger 反例仅 {len(neg)} 个，至少 10 个")
        if os.path.isfile(fj):
            n = len(json.load(open(fj, encoding="utf-8")).get("cases", []))
            check(n >= 5, f"functional 用例 {n} 个 (>=5)", f"functional 用例仅 {n} 个，至少 5 个")
    except Exception as e:  # noqa
        failures.append(f"evals JSON 解析失败: {e}")
    # 必备脚本
    expected_scripts = ["validate-skill.py", "validate-project.py", "check-security.py",
                        "check-api-contract.py", "check-db-schema.py", "verify-deployment.py"]
    for s in expected_scripts:
        p = os.path.join(scripts_dir, s)
        check(os.path.isfile(p), f"scripts/{s} 存在", f"缺少 scripts/{s}")

    # 6. 每个 reference 是否带 Pre-Check / 参考模板 / Deliverable（递归子目录）
    if os.path.isdir(ref_dir):
        for fpath in ref_files:
            rel = os.path.relpath(fpath, root)
            txt = read_text(fpath)
            if "Pre-Check" not in txt:
                warnings.append(f"{rel} 缺少 Pre-Check 加载前确认")
            if "参考模板" not in txt:
                warnings.append(f"{rel} 缺少参考模板声明")
            if "Deliverable" not in txt:
                warnings.append(f"{rel} 缺少 Deliverable 读完产出要求")

    report(passes, warnings, failures)
    return 1 if failures else 0


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def report(passes, warnings, failures):
    print("PASS  validate-skill.py" if not failures else "FAIL  validate-skill.py")
    for p in passes:
        print(f"  - {p}: OK")
    for w in warnings:
        print(f"  - WARN {w}")
    for f in failures:
        print(f"  - {f}")
    print("-" * 60)
    print(f"Summary: {len(passes)} passed, {len(warnings)} warnings, {len(failures)} failed")
    print("结论:", "FAIL —— 必须修复后才能使用" if failures else ("PASS（有告警）" if warnings else "PASS"))


if __name__ == "__main__":
    sys.exit(main())
