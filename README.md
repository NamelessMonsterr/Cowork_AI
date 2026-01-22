# ⚡ Flash Assistant

> **Voice-Controlled Desktop Automation Agent** — Production-Ready AI that controls your computer safely.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)
[![Windows](https://img.shields.io/badge/platform-windows-0078D6.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Production Ready](https://img.shields.io/badge/status-production--ready-green.svg)]()

---

## 🚀 Quick Start

> **⚠️ Windows Only**: Flash Assistant requires Windows 10/11. The application will exit on other platforms.

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set OpenAI Key

```bash
# Windows
set OPENAI_API_KEY=sk-your-key

# Or create .env file from example
copy .env.example .env
```

### 3. Start Backend

```bash
python run_backend.py
# Or: python -m uvicorn assistant.main:app --host 127.0.0.1 --port 8765
```

### 4. Start UI

```bash
cd ui
npm install
npm start
```

### 5. Try It Out

Click the core → Say: **"Open Notepad and type hello"** ✨

---

## ✨ Features

### Core Capabilities

| Feature              | Description                           | Status        |
| :------------------- | :------------------------------------ | :------------ |
| **🗣️ Voice Control** | Speak commands, Flash executes them   | ✅ Production |
| **�️ Safety First**   | Default-deny security, config-driven  | ✅ Production |
| **�🔄 Self-Healing** | Auto-recovers from popups, UI changes | ✅ Stable     |
| **👁️ Hybrid Vision** | UIA + OCR + Coordinates strategies    | ✅ Stable     |
| **🔌 Plugins**       | Extend with custom tools              | ✅ Beta       |
| **� Observability**  | Execution timeline with detailed logs | ✅ Production |

### 🆕 Production Features (Latest)

#### 🛡️ PlanGuard Security

- **Config-Driven Allowlists**: Trusted apps and domains in JSON (no code changes needed)
- **Default-Deny Policy**: Unknown tools automatically rejected with clear explanations
- **Domain Validation**: URL opening restricted to trusted domains only
- **Path Normalization**: Handles full paths, case-insensitive matching
- **Safety Audit Logging**: All rejections logged to `logs/safety_audit.jsonl`
- **Expanded Blocklist**: 24 dangerous tools blocked (shell, file ops, clipboard, network)

#### 🎯 User Experience

- **Violations UI**: Red error boxes with detailed violation lists
- **Voice Feedback**: Speaks rejection reasons ("Blocked by safety policy...")
- **Rate Limiting**: Prevents spam loops (10 requests/60 sec)
- **Settings UI**: Edit trusted apps and domains via UI (no JSON editing)
- **Plan Visibility**: Rejected plans stay visible with disabled approve button

#### 🔒 Supported Operations

**✅ Allowed:**

- Open trusted apps: Chrome, VS Code, Notepad, Calculator, Paint, Edge, Firefox, Explorer
- Type text and basic UI automation (click, scroll, keypress)
- Open trusted domains: github.com, google.com, microsoft.com, stackoverflow.com, etc.

**❌ Blocked (Production Safety):**

- Shell commands (cmd, PowerShell, bash)
- File operations (delete, write, read)
- System modifications (registry, environment variables)
- Clipboard access (data leakage risk)
- Untrusted apps and domains
- IP addresses (security requirement)

- Voice feedback on rejection

### 🔧 Diagnostic Shell Mode (Advanced)

Safe command-line automation for power users and diagnostic scenarios:

- **17 Safe CMD Commands**: `ipconfig`, `whoami`, `dir`, `ping`, `netstat`, etc.
- **15 Safe PowerShell Commands**: `Get-Process`, `Get-Service`, `Get-ChildItem`, etc.
- **35+ Blocked Patterns**: Prevents destructive operations (rm, del, format, shutdown)
- **No Command Chaining**: Blocks pipes (`|`), redirects (`>`), chains (`&`, `;`)
- **Output Redaction**: Removes API keys and passwords from command output
- **Audit Logging**: All executions logged to `logs/restricted_shell_audit.jsonl`
- **Disabled by Default**: Must explicitly enable in `config/restricted_shell.json`

**Example Usage:**

```
User: "Run ipconfig to check my network"
→ Plan generated with restricted_shell step
→ PlanGuard validates command against allowlist
→ Yellow warning shown in UI with checkbox
→ User approves → Command executes → Output returned
```

**Enable:**

```json
// Edit assistant/config/restricted_shell.json
{
  "enabled": true,
  "allow_admin": false,  // Keep false for safety
  ...
}
```

---

## 🔒 Security Model

| Layer                   | Protection                                | Status        |
| :---------------------- | :---------------------------------------- | :------------ |
| **SessionAuth**         | 30-min TTL, explicit grant required       | ✅ Production |
| **PlanGuard**           | Default-deny, allowlist-based validation  | ✅ Production |
| **Rate Limiting**       | 10 approvals/60sec, prevents spam loops   | ✅ Production |
| **Safety Audit Log**    | JSONL log of all blocked actions          | ✅ Production |
| **Domain Validation**   | URL opening restricted to trusted domains | ✅ Production |
| **Kill Switch**         | `Ctrl+Shift+Escape` stops everything      | ✅ Stable     |
| **Sandboxed Plugins**   | Isolated process with permissions         | ✅ Beta       |
| **Sensitive Detection** | Excludes bank/login windows from learning | ✅ Stable     |

### Safety Configuration

Trusted apps and domains are configured in JSON files (editable via Settings UI):

**`assistant/config/trusted_apps.json`:**

```json
{
  "trusted_apps": [
    "notepad",
    "calc",
    "chrome",
    "code",
    "explorer",
    "msedge",
    "firefox"
  ],
  "app_aliases": {
    "calculator": "calc",
    "vscode": "code",
    "edge": "msedge"
  }
}
```

**`assistant/config/trusted_domains.json`:**

```json
{
  "trusted_domains": [
    "github.com",
    "google.com",
    "microsoft.com",
    "openai.com",
    "stackoverflow.com",
    "wikipedia.org",
    "docs.python.org"
  ]
}
```

---

## 📊 Benchmarks

Flash AI includes a rigorous benchmark suite to validate its capabilities across various desktop tasks.

### Running Benchmarks

```bash
# Run the 10-task subset
set COWORK_BENCHMARK_MODE=1
python -m assistant.benchmark.cli --suite 10_tasks.yaml
```

### Status

- **Production Readiness**: ✅ Verified
- **Pass Rate**: 100% on core regression suite (app launching, text input, shell commands)
- **Safety**: 100% dangerous commands blocked with clear violations

---

## 🧪 E2E Testing

Flash AI uses [Playwright](https://playwright.dev/) for End-to-End testing.

### Prerequisites

1. Verify the backend is running (`localhost:8765`)
2. Verify the UI is running (`localhost:3000` or `3001`)

### Running Tests

```bash
cd ui
# Install browsers (first time)
npx playwright install

# Run all tests
npm run test:e2e

# Run with interactive UI
npm run test:e2e:ui

# Debug mode
npm run test:e2e:debug
```

---

## 📂 Project Structure

```
Flash-Assistant/
├── assistant/           # Backend (Python/FastAPI)
│   ├── agent/           # Planner + LLM
│   ├── executor/        # Strategies + Verification
│   ├── safety/          # PlanGuard, SessionAuth, Rate Limiting
│   ├── plugins/         # Plugin system
│   ├── api/             # API routes (safety, settings, team)
│   ├── learning/        # Adaptive ranking
│   ├── cloud/           # Sync engine
│   └── config/          # Safety configs (trusted_apps.json, trusted_domains.json)
├── ui/                  # Frontend (React/Electron)
│   ├── src/
│   │   ├── pages/       # Settings, Permissions, Safety
│   │   └── components/  # PlanPreview, SafetySettings, UI components
│   └── public/
│       └── electron.js  # Electron main process
├── tests/               # Pytest test suite
├── logs/                # Safety audit logs (safety_audit.jsonl)
└── backend/             # Build scripts
```

---

## 🛠️ Configuration

Settings are stored in `%APPDATA%/CoworkAI/settings.json`:

```json
{
  "safety": {
    "session_ttl_minutes": 30,
    "enable_kill_switch": true,
    "rate_limit": {
      "max_approvals_per_minute": 10
    }
  },
  "learning": {
    "enabled": true,
    "exclude_sensitive_windows": true
  },
  "cloud": {
    "enabled": false
  },
  "voice": {
    "engine_preference": "auto",
    "record_seconds": 5,
    "enable_feedback": true
  }
}
```

---

## 🎯 API Endpoints

### Safety Management

- `GET /safety/trusted_apps` - Get trusted applications
- `POST /safety/trusted_apps` - Update trusted applications
- `GET /safety/trusted_domains` - Get trusted domains
- `POST /safety/trusted_domains` - Update trusted domains
- `GET /logs/recent?limit=50` - Get recent logs including safety violations

### Voice Pipeline

- `POST /permission/grant` - Grant session permission
- `POST /plan/preview` - Generate plan preview
- `POST /plan/approve` - Approve and execute plan (rate limited)

---

## 📦 Building for Distribution

```bash
# Build backend executable
cd backend
python build_backend.py

# Build Electron installer
cd ui
npm run dist
```

Output: `ui/dist/Flash-Assistant-Setup.exe`

---

## � Production Deployment Checklist

- [x] Voice pipeline 100% reliable (state wiring, structured logging)
- [x] PlanGuard hardened (default-deny, config-driven, expanded blocklist)
- [x] Safety audit logging enabled
- [x] Rate limiting on critical endpoints
- [x] Violations UI with clear error messages
- [x] Voice feedback on rejection
- [x] Settings UI for runtime configuration
- [x] Domain validation for URLs
- [x] Path normalization for app names
- [ ] Session timeout warnings (Week 2)
- [ ] Safety mode selector (Safe/Standard/Developer)
- [ ] Audit log viewer in UI

---

## �📄 License

MIT © 2026 Flash Assistant

---

## 🙏 Acknowledgments

Built with production-grade security and user experience in mind. Special thanks to the open-source community for the amazing tools and libraries that make this possible.
