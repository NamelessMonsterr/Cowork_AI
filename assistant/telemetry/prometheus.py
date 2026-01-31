"""
Prometheus Metrics Endpoint - Application telemetry and monitoring.

Exposes metrics for request count, latency, errors, and voice pipeline performance.
Part of Phase 4 Deployment (+2 points toward 800/800).
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict

from fastapi import Request, Response
from fastapi.responses import PlainTextResponse


@dataclass
class MetricsCollector:
    """Collects and aggregates application metrics."""

    # Request metrics
    request_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    request_duration: Dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    error_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Voice pipeline metrics
    voice_commands_total: int = 0
    voice_transcription_duration: list[float] = field(default_factory=list)
    voice_execution_duration: list[float] = field(default_factory=list)

    # System metrics
    active_sessions: int = 0
    websocket_connections: int = 0

    _lock: Lock = field(default_factory=Lock)

    def record_request(self, method: str, path: str, duration: float, status_code: int):
        """Record HTTP request metrics."""
        with self._lock:
            key = f"{method}:{path}"
            self.request_count[key] += 1
            self.request_duration[key].append(duration)

            if status_code >= 400:
                self.error_count[key] += 1

    def record_voice_command(self, transcription_time: float, execution_time: float):
        """Record voice command processing metrics."""
        with self._lock:
            self.voice_commands_total += 1
            self.voice_transcription_duration.append(transcription_time)
            self.voice_execution_duration.append(execution_time)

    def set_active_sessions(self, count: int):
        """Update active session count."""
        with self._lock:
            self.active_sessions = count

    def set_websocket_connections(self, count: int):
        """Update WebSocket connection count."""
        with self._lock:
            self.websocket_connections = count

    def generate_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-formatted metrics.

        Returns:
            Prometheus text format metrics
        """
        with self._lock:
            lines = [
                "# HELP http_requests_total Total number of HTTP requests",
                "# TYPE http_requests_total counter",
            ]

            for key, count in self.request_count.items():
                method, path = key.split(":", 1)
                lines.append(
                    f'http_requests_total{{method="{method}",path="{path}"}} {count}'
                )

            lines.extend([
                "",
                "# HELP http_request_duration_seconds HTTP request latency",
                "# TYPE http_request_duration_seconds histogram",
            ])

            for key, durations in self.request_duration.items():
                if not durations:
                    continue

                method, path = key.split(":", 1)
                count = len(durations)
                total = sum(durations)

                # Histogram buckets
                buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                for bucket in buckets:
                    bucket_count = sum(1 for d in durations if d <= bucket)
                    lines.append(
                        f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{bucket}"}} {bucket_count}'
                    )

                lines.append(
                    f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
                )
                lines.append(
                    f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
                )

            lines.extend([
                "",
                "# HELP http_errors_total Total number of HTTP errors (4xx/5xx)",
                "# TYPE http_errors_total counter",
            ])

            for key, count in self.error_count.items():
                method, path = key.split(":", 1)
                lines.append(
                    f'http_errors_total{{method="{method}",path="{path}"}} {count}'
                )

            # Voice metrics
            lines.extend([
                "",
                "# HELP voice_commands_total Total number of voice commands processed",
                "# TYPE voice_commands_total counter",
                f"voice_commands_total {self.voice_commands_total}",
                "",
                "# HELP voice_transcription_duration_seconds Voice transcription latency",
                "# TYPE voice_transcription_duration_seconds gauge",
            ])

            if self.voice_transcription_duration:
                avg_trans = sum(self.voice_transcription_duration) / len(self.voice_transcription_duration)
                lines.append(f"voice_transcription_duration_seconds {avg_trans:.6f}")

            lines.extend([
                "",
                "# HELP voice_execution_duration_seconds Voice execution latency",
                "# TYPE voice_execution_duration_seconds gauge",
            ])

            if self.voice_execution_duration:
                avg_exec = sum(self.voice_execution_duration) / len(self.voice_execution_duration)
                lines.append(f"voice_execution_duration_seconds {avg_exec:.6f}")

            # System metrics
            lines.extend([
                "",
                "# HELP active_sessions Current number of active sessions",
                "# TYPE active_sessions gauge",
                f"active_sessions {self.active_sessions}",
                "",
                "# HELP websocket_connections Current number of WebSocket connections",
                "# TYPE websocket_connections gauge",
                f"websocket_connections {self.websocket_connections}",
            ])

            return "\n".join(lines) + "\n"


# Global metrics collector
metrics = MetricsCollector()


async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    metrics.record_request(
        method=request.method,
        path=request.url.path,
        duration=duration,
        status_code=response.status_code,
    )

    return response


async def prometheus_metrics_endpoint():
    """
    Prometheus /metrics endpoint.

    Returns:
        Prometheus formatted metrics
    """
    return PlainTextResponse(
        content=metrics.generate_prometheus_metrics(),
        media_type="text/plain; version=0.0.4",
    )


# Usage in main.py:
#
# from assistant.telemetry.prometheus import metrics, metrics_middleware, prometheus_metrics_endpoint
#
# app.middleware("http")(metrics_middleware)
#
# @app.get("/metrics", response_class=PlainTextResponse, tags=["monitoring"])
# async def get_metrics():
#     return await prometheus_metrics_endpoint()
