# Security Policy

## Reporting a Vulnerability

The Flash Assistant team takes security seriously. We appreciate your efforts to responsibly disclose your findings.

**Please DO NOT file a public GitHub issue for security vulnerabilities.**

### How to Report

Send security vulnerabilities to: **security@[your-domain].com** (or create a [GitHub Security Advisory](https://github.com/[your-org]/[your-repo]/security/advisories/new))

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Timeline**: Critical issues within 30 days, High within 90 days
- **Disclosure**: Coordinated disclosure after fix is released

---

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Security Best Practices

### Production Deployment

1. **Set Required Environment Variables**:

   ```bash
   # REQUIRED: Generate a strong session secret
   export FLASH_SESSION_SECRET="$(openssl rand -hex 32)"

   # REQUIRED: Set production mode
   export ENV="production"

   # OPTIONAL: OpenAI API key
   export OPENAI_API_KEY="sk-your-key-here"
   ```

2. **Never Enable Debug Endpoints in Production**:

   ```bash
   # This should ALWAYS be false or unset in production
   # FLASH_DEV_ENDPOINTS_ENABLED=false
   ```

3. **Use HTTPS Only**: Deploy behind a reverse proxy with TLS termination

4. **Restrict Network Access**: Bind to localhost (127.0.0.1) and use reverse proxy

5. **Regular Updates**: Subscribe to security advisories and update dependencies

### Development

- Use `.env` files (never commit to git)
- Rotate secrets regularly (90-day cycle recommended)
- Enable all security warnings
- Test with `ENV=production` before deploying

---

## Known Security Considerations

### AI Agent Execution Model

Flash Assistant executes system commands based on AI-generated plans. This creates inherent security considerations:

1. **Prompt Injection**: Malicious input in documents or user prompts could manipulate AI behavior
   - **Mitigation**: PlanGuard validation, user confirmation for sensitive actions

2. **File System Access**: AI agents can read/write files within granted permissions
   - **Mitigation**: Session-based permission model, explicit folder grants

3. **Command Execution**: System commands are executed based on AI plans
   - **Mitigation**: Input sanitization, parameterized subprocess execution (no shell=True)

### Trust Boundaries

- **User ↔ AI Agent**: Session authentication with time-limited permissions
- **AI Agent ↔ File System**: Path validation and permission checks
- **AI Agent ↔ Network**: OpenAI API only (no arbitrary network access)
- **AI Agent ↔ Windows**: COM interface access requires explicit grants

---

## Security Hardening History

### P0 Critical Fixes (2026-01-31)

- Removed `/just_do_it` bypass endpoint (unauthenticated execution)
- Fixed shell injection vulnerability (shell=True → shell=False)
- Enforced strict secrets management (production hard-fail)

### Historical Remediations

- **Commit [48]**: 24 critical issues (shell injection, auth, secrets, debug endpoints)
- **Commit [76]**: SessionAuth fixes, memory leaks, Pydantic schema
- **Commit [82]**: Layered hardening (shell, secrets, cookies, debug)

---

## Vulnerability Disclosure Timeline

| CVE/Issue | Severity | Disclosed | Fixed | Notes                 |
| --------- | -------- | --------- | ----- | --------------------- |
| TBD       | TBD      | TBD       | TBD   | No published CVEs yet |

---

## Security Contacts

- **Security Issues**: security@[your-domain].com
- **General Contact**: GitHub Issues (non-security only)
- **Bug Bounty**: [Pending setup]

---

## Acknowledgments

We thank the security research community for responsible disclosure. Contributors will be acknowledged here upon coordinated disclosure.

---

**Last Updated**: 2026-01-31
