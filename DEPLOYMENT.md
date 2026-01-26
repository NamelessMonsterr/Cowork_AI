# Deployment Notes

## ⚠️ CRITICAL: Single-Worker Constraint

**The application MUST run in single-worker mode** until Redis/database backend is implemented.

### Why?

The `AppState` class stores session data, pending plans, and WebSocket clients in **process memory**. Multiple workers create separate memory spaces, causing:

- Random 403 Forbidden errors (session exists in Worker A, but request hits Worker B)
- Lost WebSocket connections
- Inconsistent state across workers

### Deployment Command

```bash
# Uvicorn (ASGI)
uvicorn assistant.main:app --host 0.0.0.0 --port 8000 --workers 1

# Gunicorn + Uvicorn (DO NOT use multiple workers)
gunicorn assistant.main:app --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers 1
```

### Future Scaling

To enable horizontal scaling with multiple workers:

1. Move `session_auth` to Redis (store sessions in shared memory)
2. Move `pending_plans` to Redis with TTL
3. Use Redis Pub/Sub for WebSocket broadcasts
4. Then increase `--workers` as needed

## Security Notes

### Path Traversal Protection

All file paths in execution plans are validated using `os.path.realpath` to prevent `../` attacks.

### Rate Limiting

The `source="agent"` parameter in `InputRateLimiter` is **hardcoded in** the `Executor` class. Never accept this parameter from user input or API requests.

### Log Rotation

- `safety_audit.jsonl`: Auto-rotates at 10MB (keeps 5 backups)
- Total disk usage capped at ~50MB

### Session Backups

- `sessions.json.bak` is created on every write
- Restore from backup if main file is deleted
