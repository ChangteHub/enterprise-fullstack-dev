#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify-deployment.py — 部署后健康检查：站点可达性、HTTPS、API 反代、后端健康端点。
用法:
    python verify-deployment.py https://your-domain.com [--api /api/actuator/health]
    python verify-deployment.py http://服务器IP
不依赖第三方库，仅用标准库 urllib。
输出: frontend OK/FAIL、api OK/FAIL、https OK/FAIL；任一 FAIL 退出码 1。
"""
import argparse
import ssl
import sys
import urllib.request
import urllib.error


def fetch(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": "skill-verify-deployment/1.0"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.geturl(), resp.read(512)
    except urllib.error.HTTPError as e:
        # 401/403 也说明服务在线（只是需要鉴权），单独标记
        return e.code, url, b""
    except Exception as e:  # noqa
        return None, url, str(e).encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="站点根地址，如 https://example.com")
    ap.add_argument("--api", default="/api/actuator/health", help="后端健康检查路径")
    ap.add_argument("--expect-https", action="store_true", help="强制要求 HTTPS")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    results = {}

    # 1. 前端站点
    status, final_url, _ = fetch(base + "/")
    frontend_ok = status is not None and status < 500
    results["frontend"] = ("OK" if frontend_ok else "FAIL", f"GET / -> {status}")

    # 2. HTTPS
    if base.startswith("https://"):
        https_ok = status is not None
        results["https"] = ("OK" if https_ok else "FAIL", "TLS 握手并返回响应" if https_ok else "HTTPS 不可达")
    else:
        results["https"] = ("NOT READY", "当前为 http://，生产应配置 HTTPS")

    # 3. API 反向代理 / 健康端点
    api_url = base + (args.api if args.api.startswith("/") else "/" + args.api)
    a_status, _, _ = fetch(api_url)
    if a_status is None or a_status >= 500:
        api_flag = "FAIL"
    elif a_status == 404:
        # 404 只证明反代链路有响应，健康端点未命中——不能当作后端健康的证据
        api_flag = "WARN"
    else:
        # 200/2xx 是健康证据；401/403 说明服务在线仅缺鉴权
        api_flag = "OK"
    results["api"] = (api_flag, f"GET {args.api} -> {a_status}")

    failed = False
    head_flag = "PASS"
    for k, (flag, detail) in results.items():
        mark = {"OK": "✅", "FAIL": "❌", "NOT READY": "⚠️ ", "WARN": "⚠️ "}.get(flag, "?")
        print(f"  - {mark} {k:<9} {flag:<9} {detail}")
        if flag == "FAIL":
            failed = True
        if args.expect_https and flag == "NOT READY":
            failed = True
    print("-" * 60)
    print(f"{'FAIL' if failed else head_flag}  verify-deployment.py")
    print(f"Summary: frontend={results['frontend'][0]}, https={results['https'][0]}, api={results['api'][0]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
