# Error Recovery and Retry Strategies

**Version**: 1.0.0  
**Last Updated**: 2026-01-31

---

## Overview

Cowork AI Assistant implements comprehensive error recovery patterns to ensure reliability and graceful degradation under failure conditions.

## Core Principles

1. **Fail-Secure**: Errors never compromise security - sessions revoke on uncertainty
2. **Progressive Degradation**: Fallback to simpler strategies when advanced ones fail
3. **User Transparency**: Always inform users of errors and recovery actions
4. **Automatic Retry**: Transient failures retry with exponential backoff

---

## Recovery Strategies by Component

### 1. WebSocket Connections

**Failure Modes**:

- Network interruption
- Timeout (> 30s)
- Server restart

**Recovery**:

```python
from assistant.resilience.websocket_timeout import TimeoutHandler

timeout_handler = TimeoutHandler()

# Automatic reconnection with exponential backoff
await timeout_handler.reconnect_with_backoff(
    connect_func=create_websocket_connection,
    on_success=lambda conn: logger.info("Reconnected"),
    on_failure=lambda err: notify_user("Connection failed")
)
```

**Parameters**:

- Initial backoff: 1s
- Max backoff: 32s
- Max attempts: 5

### 2. Session Auth

**Failure Modes**:

- Session expiration
- Concurrent access race conditions
- Disk I/O errors (session persistence)

**Recovery**:

1. **Expiration**: Revoke immediately, prompt user for re-grant
2. **Race Conditions**: Thread-safe with `threading.Lock`
3. **Disk I/O**: Fallback to in-memory session

```python
try:
    session_auth.ensure()
except SessionExpiredError:
    # Prompt user via UI
    await request_permission_grant()
except PermissionDeniedError:
    # Block action, show error
    raise HTTPException(403, "Permission required")
```

### 3. Voice Transcription (STT)

**Failure Modes**:

- API rate limit (Deepgram/OpenAI)
- Network timeout
- Invalid audio format

**Recovery**:

1. **Rate Limit**: Queue request, retry after delay
2. **Timeout**: Retry with fallback provider
3. **Invalid Audio**: Prompt user to retry voice command

```python
# Primary: Deepgram
try:
    transcription = await deepgram_stt.transcribe(audio)
except RateLimitError:
    await asyncio.sleep(5)  # Wait and retry
    transcription = await deepgram_stt.transcribe(audio)
except TimeoutError:
    # Fallback: OpenAI Whisper
    transcription = await openai_whisper.transcribe(audio)
```

### 4. Plan Execution

**Failure Modes**:

- Strategy failure (UI element not found)
- Timeout (step takes > 30s)
- Environment change (window closed)

**Recovery**:

1. **Strategy Failure**: Try next strategy in ranking
2. **Timeout**: Mark step as failed, continue or abort
3. **Environment Change**: Pause execution, prompt user

```python
# Progressive strategy fallback
strategies = [VisionStrategy, UIAStrategy, CoordsStrategy]

for strategy in strategies:
    try:
        result = await strategy.execute(step)
        if result.success:
            break
    except Exception as e:
        logger.warning(f"{strategy} failed: {e}")
        continue
```

### 5. Plugin Loading

**Failure Modes**:

- Signature verification failure
- Import error (missing dependencies)
- Runtime error in plugin code

**Recovery**:

1. **Signature Failure**: Reject plugin, log security event
2. **Import Error**: Show user dependency requirements
3. **Runtime Error**: Sandbox plugin, kill on timeout

```python
try:
    plugin = await plugin_loader.load(plugin_path)
except SignatureVerificationError:
    logger.error("Plugin signature invalid - REJECTED")
    raise SecurityError("Untrusted plugin")
except ImportError as e:
    raise PluginDependencyError(f"Missing: {e}")
```

---

## Retry Patterns

### Exponential Backoff

Used for: Network calls, API requests, WebSocket reconnection

```python
def exponential_backoff(attempt: int, base: float = 1.0, max: float = 32.0) -> float:
    """Calculate exponential backoff delay."""
    return min(base * (2 ** attempt), max)

for attempt in range(MAX_RETRIES):
    try:
        return await api_call()
    except TransientError:
        if attempt < MAX_RETRIES - 1:
            delay = exponential_backoff(attempt)
            await asyncio.sleep(delay)
```

### Linear Backoff

Used for: Database operations, file I/O

```python
for attempt in range(MAX_RETRIES):
    try:
        return await db_operation()
    except DatabaseLockedError:
        await asyncio.sleep(0.1 * attempt)  # 0ms, 100ms, 200ms...
```

### Circuit Breaker

Used for: External APIs (OpenAI, Deepgram)

```python
class CircuitBreaker:
def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0

    async def call(self, func):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError("Service unavailable")

        try:
            result = await func()
            self.failures = 0
            self.state = "closed"
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = "open"
                self.last_failure_time = time.time()
            raise
```

---

## Error Reporting

All errors are:

1. **Logged** with context (module, user, timestamp)
2. **Redacted** to remove sensitive data (API keys, passwords)
3. **Reported** to user via UI with actionable guidance

```python
try:
    await risky_operation()
except Exception as e:
    # Log with redaction
    logger.error(f"Operation failed", extra={
        "user": session.user_id,
        "error": str(e),
        "context": redact_sensitive(context)
    })

    # User-friendly notification
    await notify_user(
        message="Operation failed. Please retry or contact support.",
        error_code=f"ERR-{type(e).__name__}",
        retry_available=is_retryable(e)
    )
```

---

## Monitoring & Alerts

### Prometheus Metrics

```prometheus
# Error rate
rate(http_errors_total[5m])

# Retry attempts
sum(retry_attempts_total) by (component)

# Circuit breaker state
circuit_breaker_state{service="openai"}
```

### Alerts

| Condition             | Threshold | Action                    |
| --------------------- | --------- | ------------------------- |
| Error rate > 5%       | 5 minutes | Page on-call engineer     |
| WebSocket disconnects | > 10/min  | Investigate network       |
| Circuit breaker open  | Any       | Check external API status |

---

## Future Improvements

1. **Distributed Tracing**: OpenTelemetry integration
2. **Dead Letter Queue**: For permanently failed tasks
3. **Automatic Rollback**: Revert failed multi-step operations
4. **Chaos Engineering**: Fault injection testing

---

**For implementation details, see**:

- `assistant/resilience/websocket_timeout.py`
- `assistant/safety/session_auth.py`
- `assistant/telemetry/prometheus.py`
