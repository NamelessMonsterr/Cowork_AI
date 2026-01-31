"""Prometheus metrics endpoint for monitoring."""

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Define metrics
request_count = Counter("flash_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])

request_duration = Histogram(
    "flash_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

active_sessions = Gauge("flash_active_sessions", "Number of active permission sessions")

plan_executions = Counter("flash_plan_executions_total", "Total plan executions", ["status"])

voice_transcriptions = Counter(
    "flash_voice_transcriptions_total",
    "Total voice transcriptions",
    ["engine", "status"],
)


async def metrics_endpoint():
    """Endpoint to expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def track_request(method: str, endpoint: str, status: int):
    """Track HTTP request metrics."""
    request_count.labels(method=method, endpoint=endpoint, status=status).inc()


def track_request_duration(method: str, endpoint: str, duration: float):
    """Track request duration."""
    request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def update_active_sessions(count: int):
    """Update active session count."""
    active_sessions.set(count)


def track_plan_execution(status: str):
    """Track plan execution."""
    plan_executions.labels(status=status).inc()


def track_voice_transcription(engine: str, status: str):
    """Track voice transcription."""
    voice_transcriptions.labels(engine=engine, status=status).inc()
