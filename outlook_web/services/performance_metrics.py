"""进程内性能指标采集与聚合。

采集器使用有界队列，避免观测数据持续增长。指标只保留路由模板、耗时、
状态码和 trace ID，不记录查询参数、请求体或响应体。
"""

from __future__ import annotations

import math
import re
import threading
import time
from collections import defaultdict, deque
from typing import Any, Iterable

_MAX_METRICS = 2000
_MAX_CLIENT_BATCH = 100
_DEFAULT_WINDOW_SECONDS = 3600
_MIN_WINDOW_SECONDS = 300
_MAX_WINDOW_SECONDS = 86400

_SERVER_METRICS: deque[dict[str, Any]] = deque(maxlen=_MAX_METRICS)
_CLIENT_METRICS: deque[dict[str, Any]] = deque(maxlen=_MAX_METRICS)
_AI_METRICS: deque[dict[str, Any]] = deque(maxlen=_MAX_METRICS)
_LOCK = threading.Lock()

_DYNAMIC_SEGMENT = re.compile(
    r"^(?:\d+|[0-9a-f]{16,}|[0-9a-f]{8}-[0-9a-f-]{27,}|[^/]*@[^/]*)$",
    re.IGNORECASE,
)


def normalize_metric_name(value: Any) -> str:
    """移除查询参数并收敛动态路径段，防止高基数和敏感信息进入指标。"""
    raw = str(value or "unknown").strip().split("?", 1)[0].split("#", 1)[0]
    if not raw:
        return "unknown"
    if not raw.startswith("/"):
        return raw[:120]
    segments = [":id" if _DYNAMIC_SEGMENT.match(part) else part for part in raw.split("/")]
    return "/".join(segments)[:160]


def _safe_duration(value: Any) -> float | None:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(duration) or duration < 0 or duration > 300_000:
        return None
    return round(duration, 2)


def record_server_request(
    *,
    route: str,
    method: str,
    status: int,
    duration_ms: float,
    trace_id: str | None = None,
) -> None:
    """记录一次 Flask 请求。"""
    duration = _safe_duration(duration_ms)
    if duration is None:
        return
    normalized_route = normalize_metric_name(route)
    if normalized_route.startswith("/static/") or normalized_route == "/api/performance/client":
        return
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        status_code = 0
    metric = {
        "timestamp": time.time(),
        "route": normalized_route,
        "method": str(method or "GET").upper()[:10],
        "status": status_code,
        "success": 0 < status_code < 400,
        "duration_ms": duration,
        "trace_id": str(trace_id or "")[:64],
    }
    with _LOCK:
        _SERVER_METRICS.append(metric)


def record_client_metrics(metrics: Any) -> int:
    """校验并记录浏览器批量上报的性能数据。"""
    if not isinstance(metrics, list):
        return 0
    accepted: list[dict[str, Any]] = []
    timestamp = time.time()
    for raw in metrics[:_MAX_CLIENT_BATCH]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "").strip().lower()
        if kind not in {"api", "page", "navigation"}:
            continue
        duration = _safe_duration(raw.get("duration_ms"))
        if duration is None:
            continue
        try:
            status = int(raw.get("status") or 0)
        except (TypeError, ValueError):
            status = 0
        success_value = raw.get("success")
        success = success_value if isinstance(success_value, bool) else status < 400
        accepted.append(
            {
                "timestamp": timestamp,
                "kind": kind,
                "name": normalize_metric_name(raw.get("name")),
                "status": status,
                "success": success,
                "duration_ms": duration,
                "trace_id": str(raw.get("trace_id") or "")[:64],
            }
        )
    if accepted:
        with _LOCK:
            _CLIENT_METRICS.extend(accepted)
    return len(accepted)


def record_ai_call(*, success: bool, duration_ms: float, model: str = "") -> None:
    """记录一次真实 AI 回退调用，不保存端点、密钥或邮件内容。"""
    duration = _safe_duration(duration_ms)
    if duration is None:
        return
    with _LOCK:
        _AI_METRICS.append(
            {
                "timestamp": time.time(),
                "success": bool(success),
                "duration_ms": duration,
                "model": str(model or "unknown")[:80],
            }
        )


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 1)


def _metric_summary(records: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
    durations = [float(item["duration_ms"]) for item in records]
    errors = sum(1 for item in records if not item.get("success"))
    count = len(records)
    return {
        "count": count,
        "error_count": errors,
        "error_rate": round(errors * 100 / count, 1) if count else 0.0,
        "avg_ms": round(sum(durations) / count, 1) if count else 0.0,
        "p50_ms": _percentile(durations, 0.5),
        "p95_ms": _percentile(durations, 0.95),
        "max_ms": round(max(durations), 1) if durations else 0.0,
        "source": source,
    }


def _grouped_summary(
    records: list[dict[str, Any]],
    *,
    key_builder,
    source: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped[key_builder(item)].append(item)
    rows = []
    for name, items in grouped.items():
        row = {"name": name, **_metric_summary(items, source=source)}
        if "method" in items[0]:
            row["method"] = items[0]["method"]
        rows.append(row)
    rows.sort(key=lambda row: (-row["p95_ms"], -row["count"], row["name"]))
    return rows[:limit]


def _finding(*, layer: str, severity: str, title: str, evidence: str, recommendation: str) -> dict[str, str]:
    return {
        "layer": layer,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def get_performance_snapshot(window_seconds: int = _DEFAULT_WINDOW_SECONDS) -> dict[str, Any]:
    """返回指定滚动窗口内的聚合指标和可执行瓶颈判断。"""
    try:
        seconds = int(window_seconds)
    except (TypeError, ValueError):
        seconds = _DEFAULT_WINDOW_SECONDS
    seconds = max(_MIN_WINDOW_SECONDS, min(_MAX_WINDOW_SECONDS, seconds))
    now = time.time()
    cutoff = now - seconds
    with _LOCK:
        server = [item.copy() for item in _SERVER_METRICS if item["timestamp"] >= cutoff]
        client = [item.copy() for item in _CLIENT_METRICS if item["timestamp"] >= cutoff]
        ai = [item.copy() for item in _AI_METRICS if item["timestamp"] >= cutoff]

    client_api = [item for item in client if item["kind"] == "api"]
    page = [item for item in client if item["kind"] in {"page", "navigation"}]
    server_mail = [item for item in server if "email" in item["route"].lower()]
    client_mail = [item for item in client_api if "email" in item["name"].lower()]
    mail = client_mail or server_mail
    mail_source = "browser_end_to_end" if client_mail else "server"

    backend_summary = _metric_summary(server, source="server")
    frontend_summary = _metric_summary(client_api, source="browser_end_to_end")
    page_summary = _metric_summary(page, source="browser")
    mail_summary = _metric_summary(mail, source=mail_source)
    ai_summary = _metric_summary(ai, source="server_external_call")

    findings: list[dict[str, str]] = []
    if backend_summary["count"] and backend_summary["p95_ms"] >= 1000:
        findings.append(
            _finding(
                layer="后端",
                severity="high" if backend_summary["p95_ms"] >= 3000 else "medium",
                title="后端接口尾延迟偏高",
                evidence=f"后端 API P95 为 {backend_summary['p95_ms']:.0f} ms",
                recommendation="优先检查端点分布中 P95 最高的接口及其数据库、Graph 调用日志。",
            )
        )
    if frontend_summary["count"] and backend_summary["count"]:
        overhead = frontend_summary["p95_ms"] - backend_summary["p95_ms"]
        if overhead >= 500:
            findings.append(
                _finding(
                    layer="前端/网络",
                    severity="medium",
                    title="浏览器端到端耗时明显高于服务端",
                    evidence=f"浏览器与服务端 API P95 相差约 {overhead:.0f} ms",
                    recommendation="检查请求瀑布、代理链路、资源竞争和响应反序列化耗时。",
                )
            )
    if page_summary["count"] and page_summary["p95_ms"] >= 2500:
        findings.append(
            _finding(
                layer="前端",
                severity="high" if page_summary["p95_ms"] >= 5000 else "medium",
                title="关键页面稳定时间偏长",
                evidence=f"页面加载/切换 P95 为 {page_summary['p95_ms']:.0f} ms",
                recommendation="按页面分布定位慢页，减少首屏串行请求和同步渲染工作。",
            )
        )
    if mail_summary["count"] and mail_summary["p95_ms"] >= 2000:
        findings.append(
            _finding(
                layer="邮件链路",
                severity="high" if mail_summary["p95_ms"] >= 5000 else "medium",
                title="邮件获取链路偏慢",
                evidence=f"邮件相关请求 P95 为 {mail_summary['p95_ms']:.0f} ms",
                recommendation="结合 trace ID 区分 Graph、IMAP 回退、数据库和前端渲染耗时。",
            )
        )
    if ai_summary["count"] and ai_summary["p95_ms"] >= 3000:
        findings.append(
            _finding(
                layer="AI/外部服务",
                severity="high" if ai_summary["p95_ms"] >= 6000 else "medium",
                title="AI 调用延迟偏高",
                evidence=f"AI 调用 P95 为 {ai_summary['p95_ms']:.0f} ms",
                recommendation="检查上游模型可用性，并为验证码规则命中保留快速路径和严格超时。",
            )
        )
    if backend_summary["count"] and backend_summary["error_rate"] >= 5:
        findings.append(
            _finding(
                layer="后端",
                severity="high",
                title="接口错误率偏高",
                evidence=f"后端 API 错误率为 {backend_summary['error_rate']:.1f}%",
                recommendation="按端点错误率和 trace ID 检查失败请求，先处理高频系统性错误。",
            )
        )

    recommendations = list(dict.fromkeys(item["recommendation"] for item in findings))
    if not recommendations:
        if server or client or ai:
            recommendations.append("当前窗口未触发阈值；继续观察高峰时段的 P95 与错误率。")
        else:
            recommendations.append("暂无样本；请在新前端完成邮件列表、详情和验证码提取操作后刷新。")

    return {
        "window": {
            "seconds": seconds,
            "started_at": cutoff,
            "generated_at": now,
            "storage": "process_memory",
            "sample_limit_per_type": _MAX_METRICS,
        },
        "summary": {
            "backend_api": backend_summary,
            "frontend_api": frontend_summary,
            "page": page_summary,
            "mail": mail_summary,
            "ai": ai_summary,
        },
        "endpoints": _grouped_summary(
            server,
            key_builder=lambda item: item["route"],
            source="server",
        ),
        "client_endpoints": _grouped_summary(
            client_api,
            key_builder=lambda item: item["name"],
            source="browser_end_to_end",
        ),
        "pages": _grouped_summary(
            page,
            key_builder=lambda item: item["name"],
            source="browser",
        ),
        "bottlenecks": findings,
        "recommendations": recommendations,
    }


def reset_performance_metrics() -> None:
    """清空采集器。仅供测试隔离使用。"""
    with _LOCK:
        _SERVER_METRICS.clear()
        _CLIENT_METRICS.clear()
        _AI_METRICS.clear()
