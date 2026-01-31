# API Versioning Strategy

## Overview

Flash Assistant API follows semantic versioning with explicit version support.

**Current Version**: v1  
**Version Format**: `vMAJOR.MINOR.PATCH` or `vMAJOR` for public APIs

---

## Versioning Scheme

### Major Version (v1, v2, v3)

**Breaking changes** that require client updates:

- Removed endpoints
- Changed required fields
- Modified response structures
- Changed authentication method

**Example**: v1 → v2

### Minor Version (Optional)

**Backward-compatible additions**:

- New optional fields
- New endpoints
- New features

**Example**: v1.1, v1.2

### Patch Version (Internal)

**Bug fixes and internal improvements**:

- No API contract changes
- Performance improvements
- Bug fixes

**Example**: v1.0.1, v1.0.2

---

## Version Communication

### Header-Based Versioning (Current)

Clients specify version via header:

```http
GET /health HTTP/1.1
X-API-Version: v1
```

### Response Headers

Server indicates version in response:

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-Deprecated: false
```

---

## Version Support Policy

### Active Support

- **v1 (Current)**: Full support, all new features
- **v2 (Future)**: When released, both v1 and v2 supported for 6 months

### Deprecation Process

1. **Announcement**: 6 months notice before deprecation
2. **Warning Headers**: `X-Deprecated: true, X-Sunset: 2027-01-31`
3. **Migration Guide**: Published with upgrade path
4. **Sunset Date**: After 6 months, old version removed

---

## Backward Compatibility

### Guaranteed Compatibility Within Major Version

- Adding optional fields: ✅ Allowed
- Adding new endpoints: ✅ Allowed
- Adding new error codes: ✅ Allowed (with documentation)
- Changing required fields: ❌ Requires major version bump

### Example Backward-Compatible Change (v1.1)

```json
// v1.0
{
  "status": "ok"
}

// v1.1 (backward compatible)
{
  "status": "ok",
  "uptime_seconds": 3600  // New optional field
}
```

---

## Future Versioning (v2+)

### Planned v2 Changes

- Multi-worker support with Redis
- Enhanced WebSocket contracts
- GraphQL endpoint option
- Advanced plugin marketplace

### Version Negotiation

Future versions may support content negotiation:

```http
GET /api/plans HTTP/1.1
Accept: application/vnd.flash.v2+json
```

---

## Client Recommendations

### For Library Authors

```python
class FlashClient:
    def __init__(self, api_version="v1"):
        self.api_version = api_version
        self.headers = {" X-API-Version": api_version}

    def request(self, endpoint):
        return requests.get(
            f"http://127.0.0.1:8765{endpoint}",
            headers=self.headers
        )
```

### Version Pinning

**Production**: Pin to specific major version (`v1`)  
**Development**: Can use latest

---

## Migration Guide (Future v1 → v2)

When v2 is released, migration guide will include:

1. Breaking changes summary
2. Deprecated endpoint mapping
3. Code examples (before/after)
4. Automated migration scripts

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-31  
**Maintained By**: Flash Assistant API Team
