# API Documentation

## Overview

Flash Assistant backend API built with FastAPI, providing voice-controlled desktop automation with security-first design.

**Base URL**: `http://127.0.0.1:8765`  
**API Version**: v1  
**Authentication**: Session-based (SessionAuth)

---

## Core Endpoints

### Health & Status

#### `GET /health`

Health check endpoint for monitoring.

**Response**:

```json
{
  "status": "ok",
  "timestamp": "2026-01-31T12:00:00Z"
}
```

#### `GET /capabilities`

Get system capabilities and configuration.

**Response**:

```json
{
  "version": "1.0.0",
  "features": ["voice", "execution", "plugins"]
}
```

---

### Permission Management

#### `GET /permission/status`

Get current session permission status.

**Response**:

```json
{
  "granted": true,
  "expires_at": "2026-01-31T13:00:00Z",
  "apps": ["notepad.exe"],
  "folders": ["C:\\Users\\Documents"]
}
```

#### `POST /permission/grant`

Grant session permissions.

**Request**:

```json
{
  "ttl_minutes": 60,
  "apps": ["notepad.exe", "calc.exe"],
  "folders": ["C:\\Users\\Documents"],
  "network_allowed": false
}
```

**Response**:

```json
{
  "status": "granted",
  "expires_at": "2026-01-31T13:00:00Z"
}
```

#### `POST /permission/revoke`

Revoke all permissions.

**Response**:

```json
{
  "status": "revoked"
}
```

---

### Voice Pipeline

#### `POST /voice/listen`

Start voice listening session.

**Request**:

```json
{
  "duration": 5,
  "engine": "whisper"
}
```

**Response**:

```json
{
  "transcription": "Open Notepad",
  "confidence": 0.95,
  "duration_ms": 2340
}
```

#### `GET /voice/health`

Voice engine health status.

**Response**:

```json
{
  "status": "ready",
  "engine": "WhisperSTT",
  "available_engines": ["whisper", "openai_whisper"]
}
```

---

### Plan Execution

#### `POST /plan/preview`

Preview execution plan from voice command.

**Request**:

```json
{
  "task": "Open Notepad and type Hello"
}
```

**Response**:

```json
{
  "plan_id": "plan-123",
  "description": "Open Notepad and type Hello",
  "steps": [
    {
      "step_id": "1",
      "tool": "system",
      "params": { "action": "open_app", "app": "notepad" }
    }
  ],
  "risk_score": 2,
  "requires_approval": true
}
```

#### `POST /plan/approve`

Approve and execute a plan.

**Request**:

```json
{
  "plan_id": "plan-123"
}
```

**Response**:

```json
{
  "status": "executing",
  "plan_id": "plan-123"
}
```

---

## WebSocket Endpoints

### `/ws`

WebSocket connection for real-time updates.

**Connection**:

```javascript
const ws = new WebSocket("ws://127.0.0.1:8765/ws");
```

**Message Types**:

#### Server → Client Events

**Execution Progress**:

```json
{
  "event": "step_complete",
  "data": {
    "step_id": "1",
    "status": "success",
    "result": "Notepad opened"
  }
}
```

**Session Updates**:

```json
{
  "event": "session_expired",
  "data": {
    "message": "Session expired, request new permission"
  }
}
```

**Heartbeat**:

```json
{
  "type": "ping"
}
```

#### Client → Server Messages

**Heartbeat Response**:

```json
{
  "type": "pong"
}
```

---

## API Versioning

### Version Header

Include API version in requests:

```
X-API-Version: v1
```

### Version Compatibility

- **v1**: Current version (stable)
- Future versions will maintain backward compatibility
- Breaking changes will increment major version (v2, v3)

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Permission denied",
  "error": "PERMISSION_REQUIRED",
  "status": 403
}
```

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (validation error)
- `401`: Unauthorized
- `403`: Forbidden (permission required)
- `404`: Not Found
- `429`: Too Many Requests (rate limited)
- `500`: Internal Server Error

---

## Rate Limiting

**Limits**:

- Voice endpoints: 10 requests/minute
- Execution endpoints: 5 requests/minute
- General endpoints: 60 requests/minute

**Headers**:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1643640000
```

---

## Security

### CORS

Allowed origins: `http://localhost:3002`, `http://127.0.0.1:3002`

### Session Secret

Required environment variable: `FLASH_SESSION_SECRET`

### Input Validation

All inputs validated with Pydantic schemas

---

## Examples

### Complete Flow

```python
import requests

# 1. Check health
health = requests.get('http://127.0.0.1:8765/health')

# 2. Grant permission
requests.post('http://127.0.0.1:8765/permission/grant', json={
    "ttl_minutes": 60,
    "apps": ["notepad.exe"]
})

# 3. Listen for voice command
result = requests.post('http://127.0.0.1:8765/voice/listen', json={
    "duration": 5
})
transcription = result.json()['transcription']

# 4. Preview plan
plan = requests.post('http://127.0.0.1:8765/plan/preview', json={
    "task": transcription
})

# 5. Approve execution
requests.post('http://127.0.0.1:8765/plan/approve', json={
    "plan_id": plan.json()['plan_id']
})
```

---

**Last Updated**: 2026-01-31  
**Maintained By**: Flash Assistant Team
