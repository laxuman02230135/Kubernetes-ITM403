"""Read-only HTTP load through Ingress; record real HPA observations every 30s.

Requires Python 3 and kubectl on the Windows host, plus a running minikube
tunnel and the hosts-file entry. No additional Python packages are needed.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import urlsplit


def kubectl(*args):
    return subprocess.check_output(
        ["kubectl", "--context=minikube", "-n", "usermgmt-02230135", *args],
        text=True, timeout=20,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://usermgmt-02230135.local/users")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--cooldown", type=int, default=420)
    args = parser.parse_args()
    if min(args.seconds, args.concurrency, args.cooldown) <= 0:
        parser.error("Durations and concurrency must be positive.")
    url = urlsplit(args.url)
    if url.scheme != "http" or not url.hostname:
        parser.error("Use an http:// URL for this local lab.")
    path = url.path or "/"
    if url.query:
        path += "?" + url.query
    check = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=10)
    check.request("GET", path)
    response = check.getresponse()
    response.read()
    check.close()
    if response.status != 200:
        raise RuntimeError(f"Ingress preflight returned HTTP {response.status}")
    evidence = Path(__file__).resolve().parent.parent / "evidence"
    evidence.mkdir(exist_ok=True)
    run = evidence / ("M5-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run.mkdir()
    counts = Counter()
    lock = threading.Lock()
    stop = threading.Event()
    rows = []
    observed_restarts = {}
    baseline_restarts = {}
    started = time.monotonic()

    def worker():
        connection = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=10)
        try:
            while not stop.is_set() and time.monotonic() < started + args.seconds:
                try:
                    connection.request("GET", path)
                    reply = connection.getresponse()
                    reply.read()
                    result = str(reply.status)
                except (OSError, http.client.HTTPException) as error:
                    result = type(error).__name__
                    connection.close()
                with lock:
                    counts[result] += 1
        finally:
            connection.close()

    def sample(phase, writer, stream, log):
        hpa = json.loads(kubectl("get", "hpa", "api", "-o", "json"))
        deployment = json.loads(kubectl("get", "deployment", "api", "-o", "json"))
        pods = json.loads(kubectl("get", "pods", "-l", "app=api", "-o", "json"))
        for pod in pods["items"]:
            uid = pod["metadata"]["uid"]
            restarts = sum(c.get("restartCount", 0) for c in pod.get("status", {}).get("containerStatuses", []))
            observed_restarts[uid] = max(restarts, observed_restarts.get(uid, 0))
            if phase == "baseline":
                baseline_restarts[uid] = restarts
        with lock:
            responses = dict(counts)
        metrics = hpa.get("status", {}).get("currentMetrics") or []
        cpu = next((m["resource"]["current"].get("averageUtilization", "")
                    for m in metrics if m.get("resource", {}).get("name") == "cpu"), "")
        row = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                   elapsed_seconds=round(time.monotonic() - started), phase=phase,
                   cpu_percent=cpu, desired=hpa.get("status", {}).get("desiredReplicas", ""),
                   replicas=deployment["status"].get("replicas", 0),
                   ready=deployment["status"].get("readyReplicas", 0),
                   active_pods=sum(not p["metadata"].get("deletionTimestamp") for p in pods["items"]),
                   successful_requests=responses.get("200", 0),
                   failed_requests=sum(n for status, n in responses.items() if status != "200"),
                   new_restarts=sum(n - baseline_restarts.get(uid, 0) for uid, n in observed_restarts.items()))
        rows.append(row)
        writer.writerow(row)
        stream.flush()
        print(row, flush=True)
        log.write(json.dumps({"sample": row, "hpa": hpa, "deployment": deployment, "pods": pods}) + "\n")
        log.flush()

    print(f"Evidence: {run}\nGET {args.url}, {args.concurrency} clients, {args.seconds}s load, {args.cooldown}s cooldown", flush=True)
    fields = ["timestamp_utc", "elapsed_seconds", "phase", "cpu_percent", "desired", "replicas", "ready", "active_pods", "successful_requests", "failed_requests", "new_restarts"]
    with (run / "timeline.csv").open("w", newline="", encoding="utf-8") as stream, (run / "observations.jsonl").open("w", encoding="utf-8") as log:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        sample("baseline", writer, stream, log)
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(worker) for _ in range(args.concurrency)]
            try:
                total = args.seconds + args.cooldown
                for offset in range(30, total + 30, 30):
                    deadline = started + min(offset, total)
                    time.sleep(max(0, deadline - time.monotonic()))
                    if offset >= args.seconds:
                        stop.set()
                    sample("load" if offset < args.seconds else "cooldown", writer, stream, log)
                    if offset >= total:
                        break
            finally:
                stop.set()
            for future in futures:
                future.result()
    for resource, name in [("hpa", "api"), ("vpa", "postgres")]:
        (run / f"{resource}-describe.txt").write_text(kubectl("describe", resource, name), encoding="utf-8")
    (run / "metrics.txt").write_text(kubectl("top", "pods"), encoding="utf-8")
    vpa = json.loads(kubectl("get", "vpa", "postgres", "-o", "json"))
    recommendations = vpa.get("status", {}).get("recommendation", {}).get("containerRecommendations", [])
    summary = dict(url=args.url, concurrency=args.concurrency, load_seconds=args.seconds,
                   cooldown_seconds=args.cooldown, responses=dict(counts),
                   max_replicas=max(row["replicas"] for row in rows),
                   new_restarts=rows[-1]["new_restarts"],
                   final_replicas=rows[-1]["replicas"], final_ready=rows[-1]["ready"],
                   vpa_mode=vpa["spec"]["updatePolicy"]["updateMode"],
                   vpa_recommendations=recommendations)
    summary["passed"] = (rows[0]["replicas"] == 2 and summary["max_replicas"] > 2
                         and summary["final_replicas"] == 2 and summary["final_ready"] == 2
                         and bool(recommendations) and summary["vpa_mode"] == "Off"
                         and counts.get("200", 0) > 0 and set(counts) == {"200"}
                         and summary["new_restarts"] == 0)
    (run / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    if not summary["passed"]:
        raise SystemExit("Review evidence: not all scaling, response, or VPA checks passed.")


if __name__ == "__main__":
    main()
