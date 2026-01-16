# ⚡ CoworkAI Assistant

> **The Production-Grade, Voice-Controlled Desktop Agent Protocol**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)](./README.md)
[![Platform](https://img.shields.io/badge/platform-windows-win.svg)](https://www.microsoft.com/windows)

CoworkAI is a robust agentic platform that automates complex desktop workflows. It combines LLM planning with a self-healing execution engine, secure sandboxing, and an extensible plugin architecture.

---

## ✨ Key Features (W1-W12)

| Feature                  | Description                                                                         | Architecture               |
| :----------------------- | :---------------------------------------------------------------------------------- | :------------------------- |
| **🧠 Reliable Planning** | Breaks tasks into verified actions. Uses `PlanGuard` to prevent unsafe operations.  | `Planner` + `LLM`          |
| **🛡️ Self-Healing**      | Detects execution failures (popups, UI changes) and auto-repairs using LLM logic.   | `RecoveryManager`          |
| **👁️ Computer Vision**   | Hybrid UIA + Vision strategy to interact with non-standard apps (Paint, Games).     | `VisionStrategy`           |
| **⚙️ Plugin Platform**   | Extensible SDK with strict permission scopes, secrets isolation, and audit logging. | `ToolRouter` + `Registry`  |
| **🧪 Reliability**       | Includes a full 50-task benchmark suite to validate stability before release.       | `BenchmarkRunner`          |
| **📦 Production Core**   | Single-instance lock, Watchdog recovery, and signed Installer packaging.            | `PyInstaller` + `Electron` |

---

## 🚀 Quick Start (Dev Mode)

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API Key (Set `OPENAI_API_KEY` env var)

### 2. Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Backend (Port 8765)
python assistant/entrypoints/backend_main.py
```

### 3. Frontend Setup

```bash
cd ui
npm install
npm start
```

---

## 🔌 Plugin System

CoworkAI supports 3rd-party tools via `plugins/`.

### Built-in Plugins

- **Clipboard Manager:** Read/Write system clipboard (`cowork.clipboard`).

### Creating a Plugin

Place a folder in `%APPDATA%/CoworkAI/plugins/my_plugin/` with:

**plugin.json**

```json
{
  "id": "my.plugin",
  "name": "My Plugin",
  "entrypoint": "main:MyPlugin",
  "permissions_required": ["network:google.com", "notifications"]
}
```

**main.py**

```python
from assistant.plugins.sdk import Plugin, Tool

class MyPlugin(Plugin):
    def get_tools(self):
        return [MyTool()]
```

---

## 🧪 Reliability Benchmarks

Validate system stability using the built-in benchmark suite.

```bash
# Run Smoke Test (Safe Mode)
$env:COWORK_BENCHMARK_MODE="1"
python -m assistant.benchmark.cli --suite assistant/benchmark/tasks/smoke.yaml --repeat 5
```

---

## 📦 Building for Production

Create a standalone Windows Installer (`.exe`).

1. **Build Backend:** `python backend/build_backend.py`
2. **Package UI + Installer:** `cd ui && npm run dist`

Output: `ui/dist/CoworkAI-Setup-1.0.0.exe`

---

## 📄 Architecture & Modules

| Module                    | Description                                               |
| :------------------------ | :-------------------------------------------------------- |
| **`assistant/agent`**     | Core Logic: Planner, PlanGuard, LLM Client.               |
| **`assistant/executor`**  | Reliable execution engine with Verifiers and Retry logic. |
| **`assistant/recovery`**  | Self-healing strategies and Failure Classification.       |
| **`assistant/safety`**    | Permission gating (UAC, Auth) and Environment Monitoring. |
| **`assistant/computer`**  | Low-level OS control (Windows API, OCR, Input Injection). |
| **`assistant/plugins`**   | Extension platform: SDK, Registry, Router, Sandbox.       |
| **`assistant/benchmark`** | QA suite for automated reliability testing.               |

---

## 📄 License

MIT © 2026 CoworkAI Project
