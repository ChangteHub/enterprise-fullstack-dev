#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-decision-record.py — Decision Record 机器门禁（v3.1 P0）。
用法:
    python validate-decision-record.py <项目根路径>
校验对象: <项目根>/.decision/project-decision.yaml（机器可读决策状态）
判定（对应 Skill v3.1.1 三态决策门禁）:
    BLOCKED  文件不存在 / status=draft / 必填字段缺失 / 字段取值不合法 / md 与 yaml 状态不一致
    PASS     status=confirmed（正常执行）或 status=assumed（见下方边界）
三态语义（v3.1.1）:
    DRAFT      关键决策尚未形成：只允许收集信息/生成问题，禁止进入 Scaffold 与一切实现
    ASSUMED    已按最小方案作出明确假设：允许 Blueprint/Scaffold/本地构建测试；
               禁止生产部署、Remote Side Effect、高风险迁移；最终报告必须列出假设请用户追认
    CONFIRMED  开发者已确认：完整正常流程（仍受 P0/Stop/Evidence 约束）
规则:
    - decision_id（稳定标识）与 revision（每次 Re-open 递增）为必填
    - docs/architecture/decision-record.md 存在时，其 Status 行必须与 yaml 一致，否则阻断
    - 本脚本零第三方依赖：只解析两层结构的 key: value YAML 子集
    - 结构与决策的冲突检查（如 mode=a 却存在 apps/）由 check-project-gap.py 负责
只检查不修改。
"""
import os
import re
import sys

REQUIRED_TOP = ["status", "decision_id", "revision", "scope", "project_mode", "frontend", "backend", "database", "deployment"]
REQUIRED_NESTED = {
    "frontend": ["mode"],
    "backend": ["architecture"],
    "database": ["engine"],
    "deployment": ["target", "runtime"],
}
ALLOWED = {
    "status": {"confirmed", "assumed", "draft"},
    "scope": {"l0", "l1", "l2", "l3"},
    "project_mode": {"create", "refactor", "feature", "deploy", "audit"},
    "frontend.mode": {"a", "a-plus", "b"},
    "backend.architecture": {"monolith", "modular-monolith", "microservices"},
    "database.engine": {"mysql", "postgresql", "none"},
    "database.migration": {"flyway", "liquibase", "none"},
    "auth.strategy": {"none", "jwt", "oauth2", "oidc"},
    "deployment.target": {"local", "vps", "cloud", "k8s"},
    "deployment.runtime": {"docker-compose", "k8s", "bare-metal"},
    "deployment.proxy": {"nginx", "none"},
}


def parse_simple_yaml(text):
    """解析两层 key: value YAML 子集。返回 {'top.key': 'value', ...}（一级键也平铺）。"""
    data = {}
    section = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()  # 去注释
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                section = key
                data.setdefault(key, {})
            else:
                data[key] = val
                section = ""
        else:
            m = re.match(r"^\s+([A-Za-z0-9_\-]+):\s*(.*)$", line)
            if not m or not section:
                continue
            data[section][m.group(1)] = m.group(2).strip()
    return data


def flat(data):
    """把嵌套 dict 展平为 'section.key' -> value，一级标量保持原名。"""
    out = {}
    for k, v in data.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[f"{k}.{k2}"] = v2
        else:
            out[k] = v
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python validate-decision-record.py <项目根路径>")
        return 2
    root = os.path.abspath(sys.argv[1])
    decision_path = os.path.join(root, ".decision", "project-decision.yaml")

    blocked = []
    if not os.path.isfile(decision_path):
        print("BLOCKED validate-decision-record.py")
        print("  - BLOCKED 缺少 .decision/project-decision.yaml（Decision Record 机器可读状态）")
        print("-" * 60)
        print("Summary: BLOCKED —— DECIDE/RECORD 门禁未通过，禁止进入 BLUEPRINT/SCAFFOLD/IMPLEMENT")
        return 1

    raw = parse_simple_yaml(open(decision_path, encoding="utf-8").read())
    data = flat(raw)

    status = str(data.get("status", "")).lower()
    if status == "draft":
        blocked.append("status=draft —— 关键决策尚未形成：禁止进入 Scaffold/实现；请先形成决策或改为 assumed/confirmed")
    decision_id = str(data.get("decision_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9]+-[A-Za-z0-9]+-\d+", decision_id):
        blocked.append(f"decision_id 非法: {decision_id or '(缺失)'}（稳定标识，格式如 FS-2026-001）")
    try:
        if int(data.get("revision", 0)) < 1:
            blocked.append("revision 必须 >= 1（每次 Re-open 递增）")
    except (TypeError, ValueError):
        blocked.append(f"revision 非法: {data.get('revision', '(缺失)')}")

    # md 人读版与 yaml 状态一致性
    md_path = os.path.join(root, "docs", "architecture", "decision-record.md")
    if os.path.isfile(md_path):
        m = re.search(r"Status:\s*[`:]?\s*(DRAFT|ASSUMED|CONFIRMED)", open(md_path, encoding="utf-8", errors="ignore").read(), re.I)
        if m and m.group(1).lower() != status:
            blocked.append(f"状态不一致：yaml={status} 但 md 记录 {m.group(1).upper()}——请同步两份记录后再进入实现")

    for key in REQUIRED_TOP:
        # section 键（frontend/backend 等）在 flat 后以 frontend.mode 形式存在，需对原始 parse 判存在
        if key not in raw and not any(k.startswith(key + ".") for k in data):
            blocked.append(f"缺少必填字段: {key}")
    for section, keys in REQUIRED_NESTED.items():
        for key in keys:
            if f"{section}.{key}" not in data:
                blocked.append(f"缺少必填字段: {section}.{key}")

    for key, allowed in ALLOWED.items():
        if key in data and str(data[key]).lower() not in allowed:
            blocked.append(f"{key}={data[key]} 不在合法取值 {sorted(allowed)}")

    for w in blocked:
        print(f"  - BLOCKED {w}")
    print("-" * 60)
    if blocked:
        print("BLOCKED validate-decision-record.py")
        print(f"Summary: {len(blocked)} blocked —— DECIDE/RECORD 门禁未通过，禁止进入 BLUEPRINT/SCAFFOLD/IMPLEMENT")
        return 1
    print("PASS  validate-decision-record.py")
    if status == "assumed":
        print("Summary: status=ASSUMED —— 本地 Blueprint/Scaffold/构建测试可用；"
              "生产部署、Remote Side Effect、高风险迁移已锁定；最终报告必须列出全部假设请求追认")
    else:
        print(f"Summary: status=confirmed, {len(data)} fields —— 决策门禁通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
