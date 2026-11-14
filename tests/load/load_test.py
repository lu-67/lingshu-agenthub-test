"""灵枢 AgentHub · 混合业务压测脚本

模拟真实用户场景：登录 → 拉列表 → 发对话 → 查定时任务 → 查 admin（如果有权限）。
多线程并发，输出 QPS / 平均 / P95 延迟。

运行：
    python tests/load/load_test.py -n 10 -d 60

参数：
    -n 并发线程数（默认 5）
    -d 压测持续秒数（默认 30）
    --host 后端地址（默认 http://127.0.0.1:8000）
    -u 用户名（默认 admin，admin token 权限最大）
    -p 密码
"""
from __future__ import annotations
import argparse
import json
import sys
import threading
import time
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    print("需要 requests：pip install requests")
    sys.exit(1)


class Stats:
    def __init__(self):
        self.latencies = defaultdict(list)   # endpoint -> [ms]
        self.statuses = defaultdict(lambda: defaultdict(int))
        self.errors = []
        self.lock = threading.Lock()

    def record(self, endpoint: str, latency_ms: float, status: int):
        with self.lock:
            self.latencies[endpoint].append(latency_ms)
            self.statuses[endpoint][status] += 1

    def record_error(self, endpoint: str, err: str):
        with self.lock:
            self.errors.append((endpoint, err))

    def summary(self) -> str:
        lines = ["\n" + "=" * 60, "压测结果汇总", "=" * 60]
        total_req, total_ok = 0, 0
        for ep, codes in sorted(self.statuses.items()):
            ep_lat = self.latencies[ep]
            n = sum(codes.values())
            ok = sum(v for k, v in codes.items() if 200 <= k < 400)
            total_req += n
            total_ok += ok
            if ep_lat:
                lat_avg = statistics.mean(ep_lat)
                lat_p95 = (sorted(ep_lat)[int(len(ep_lat) * 0.95)]
                           if len(ep_lat) >= 20 else max(ep_lat))
                lines.append(f"  {ep:35s} 请求={n:4d}  成功率={ok/n*100:5.1f}%  "
                             f"avg={lat_avg:7.1f}ms  p95={lat_p95:7.1f}ms")
        if self.errors:
            lines.append(f"\n  错误数: {len(self.errors)}")
            for ep, err in self.errors[:5]:
                lines.append(f"    {ep}: {err[:120]}")
        if total_req == 0:
            return "\n".join(lines)
        lines.append(f"\n  总计: {total_req} 请求, {total_ok} 成功, "
                     f"成功率 {total_ok/max(1,total_req)*100:.1f}%")
        elapsed_s = max(len(v) for v in self.latencies.values()) or 1
        lines.append(f"  估算 QPS: {total_req / elapsed_s:.1f}")
        return "\n".join(lines)


def worker(base_url: str, username: str, password: str,
           stats: Stats, stop_flag: threading.Event):
    """单个并发线程：登录 → 循环发请求直到 stop。"""
    s = requests.Session()
    try:
        t0 = time.time()
        r = s.post(f"{base_url}/api/auth/login",
                   json={"username": username, "password": password}, timeout=5)
        lat = (time.time() - t0) * 1000
        stats.record("POST /auth/login", lat, r.status_code)
        if not r.ok:
            stats.record_error("login", r.text[:200])
            return
        token = r.json().get("token")
        if token:
            s.headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        stats.record_error("login", str(e))
        return

    # 只保留当前真实存在的接口
    endpoints = [
        ("GET", "/api/agents", None),
        ("GET", "/api/sessions?limit=50", None),
        ("GET", "/api/automations", None),
        ("GET", "/api/admin/stats", None),
        ("GET", "/api/auth/me", None),
    ]

    while not stop_flag.is_set():
        for method, path, body in endpoints:
            if stop_flag.is_set():
                break
            t0 = time.time()
            try:
                url = f"{base_url}{path}"
                r = s.request(method, url, json=body, timeout=5)
                lat = (time.time() - t0) * 1000
                stats.record(f"{method} {path.split('?')[0]}", lat, r.status_code)
            except Exception as e:
                lat = (time.time() - t0) * 1000
                stats.record_error(path, str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--threads", type=int, default=5, help="并发线程数")
    ap.add_argument("-d", "--duration", type=int, default=30, help="压测秒数")
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("-u", "--user", default="admin")
    ap.add_argument("-p", "--password", default="admin123")
    args = ap.parse_args()

    # 健康检查
    try:
        r = requests.get(f"{args.host}/health", timeout=5)
        print(f"✓ 后端健康 OK: {args.host}  status={r.json().get('status')}")
    except Exception as e:
        print(f"! 后端可能没启动: {e}")
        return

    print(f"\n启动压测: {args.threads} 并发 x {args.duration}s, 目标 {args.host}")
    print(f"  账号: {args.user}/{args.password}")

    stats = Stats()
    stop = threading.Event()

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = [pool.submit(worker, args.host, args.user, args.password,
                               stats, stop)
                   for _ in range(args.threads)]
        time.sleep(args.duration)
        stop.set()
        for f in futures:
            try:
                f.result(timeout=10)
            except Exception:
                pass
    elapsed = time.time() - t0

    print(stats.summary())
    print(f"\n总耗时: {elapsed:.1f}s")

    # 保存 JSON 报告
    report_path = f"load_report_{int(time.time())}.json"
    report = {
        "config": {"threads": args.threads, "duration": args.duration,
                   "host": args.host},
        "elapsed_s": round(elapsed, 1),
        "latencies_ms": {k: {"avg": round(statistics.mean(v), 1) if v else 0,
                             "p95": round(sorted(v)[int(len(v)*0.95)] if v else 0, 1),
                             "count": len(v)}
                         for k, v in stats.latencies.items()},
        "statuses": {k: dict(v) for k, v in stats.statuses.items()},
        "errors_count": len(stats.errors),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON 报告: {report_path}")


if __name__ == "__main__":
    main()
