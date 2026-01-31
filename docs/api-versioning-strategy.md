# API Versioning Strategy

**Version**: 1.0.0  
**Status**: Active  
**Last Updated**: 2026-01-31

---

## Overview

Cowork AI Assistant API follows semantic versioning (MAJOR.MINOR.PATCH) with backward-compatible versioning headers.

## Versioning Approach

### Header-Based Versioning

All API requests should include the version header:

```http
X-API-Version: 1.0.0
```

### Version Detection

1. **Client specifies version** → Server validates and responds
2. **No version header** → Server uses latest stable version
3. **Unsupported version** → Server returns `400 Bad Request`

## Version Lifecycle

| Phase          | Duration   | Support Level                      |
| -------------- | ---------- | ---------------------------------- |
| **Active**     | Indefinite | Full support, all features         |
| **Deprecated** | 6 months   | Bug fixes only, migration warnings |
| **Sunset**     | N/A        | No longer supported                |

## Current Versions

| Version   | Status    | Endpoints | Release Date |
| --------- | --------- | --------- | ------------ |
| **1.0.0** | ✅ Active | All       | 2026-01-31   |

## Breaking Changes Policy

**Major version bump (2.0.0)** required for:

- Endpoint removal
- Response schema changes
- Authentication changes
- WebSocket protocol changes

**Minor version bump (1.1.0)** for:

- New endpoints
- Optional fields added
- New features (backward compatible)

**Patch version bump (1.0.1)** for:

- Bug fixes
- Documentation updates
- Security patches

## Deprecation Process

1. **Announce deprecation** - 3 months notice
2. **Add deprecation warnings** - Include in API responses
   ```json
   {
     "data": {...},
     "warnings": ["This endpoint is deprecated. Migrate to /v2/endpoint by 2026-06-01"]
   }
   ```
3. **Sunset** - Remove after deprecation period

## Migration Guide

When migrating between versions:

### From 1.0.0 → 2.0.0 (Future)

_No migrations yet. This section will be populated when v2 is released._

## Version Header Format

```http
GET /api/permission/status HTTP/1.1
Host: localhost:8765
X-API-Version: 1.0.0
```

Response includes version confirmation:

```json
{
  "api_version": "1.0.0",
  "data": {...}
}
```

## Compatibility Matrix

| Client Version | Compatible API Versions |
| -------------- | ----------------------- |
| 1.0.x          | 1.0.0                   |
| Future 2.0.x   | 2.0.0, 1.0.0 (fallback) |

## Error Responses

### Unsupported Version

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "Unsupported API version",
  "requested_version": "0.9.0",
  "supported_versions": ["1.0.0"],
  "latest_version": "1.0.0"
}
```

### Missing Version Header

Server defaults to latest version with informational header:

```http
HTTP/1.1 200 OK
X-API-Version-Used: 1.0.0
X-API-Version-Defaulted: true
```

## Future Roadmap

**v1.1.0** (Q2 2026) - Planned features:

- User profile management API
- Advanced learning analytics
- Plugin marketplace integration

**v2.0.0** (Q4 2026) - Breaking changes:

- GraphQL support
- Redesigned authentication
- Enhanced WebSocket protocol

---

**Questions?** See [API Documentation](http://localhost:8765/docs) for interactive API reference.
