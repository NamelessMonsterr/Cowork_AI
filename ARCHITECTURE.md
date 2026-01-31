# Architecture Documentation

## System Architecture

```mermaid
graph TD
    A[User Voice/UI Input] --> B[FastAPI Backend]
    B --> C[STT Engine]
    C --> D[AI Planner]
    D --> E[PlanGuard Validation]
    E --> F{SessionAuth Permission}
    F -->|Approved| G[Executor]
    F -->|Denied| H[Reject]
    G --> I[Strategy Selection]
    I --> J[Windows Automation]
    J --> K[Audit Logging]

    style E fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style K fill:#bfb,stroke:#333,stroke-width:2px
```

## Security Layers

```mermaid
graph LR
    Input[User Input] --> V1[Input Validator]
    V1 --> V2[PlanGuard]
    V2 --> V3[SessionAuth]
    V3 --> V4[Restricted Shell]
    V4 --> Exec[Execution]

    V1 -.->|Logs| Audit[Audit Trail]
    V2 -.->|Logs| Audit
    V3 -.->|Logs| Audit
    V4 -.->|Logs| Audit

    style V1 fill:#f96,stroke:#333
    style V2 fill:#f96,stroke:#333
    style V3 fill:#f96,stroke:#333
    style V4 fill:#f96,stroke:#333
```

## Component Breakdown

### 1. Voice Pipeline

- **STT Engine**: Whisper-based speech-to-text
- **Fallback**: Mock engine for testing
- **WebSocket**: Real-time audio streaming

### 2. Planning Layer

- **AI Planner**: OpenAI-based command interpretation
- **Plan Guard**: Pre-execution validation
  - App allowlist checking
  - Domain allowlist checking
  - Risk scoring

### 3. Security Stack

- **SessionAuth**: Permission management
  - Time-based expiry
  - Explicit app/folder grants
  - Network permission control
- **Input Validator**: Whitelist-based validation
- **Secrets Filter**: Log redaction

### 4. Execution Engine

- **Executor**: Async task coordinator
- **Strategies**: Platform-specific implementations
  - SystemStrategy: Windows automation
  - AppStrategy: Application control
  - RestrictedShellTool: Sandboxed commands

### 5. Audit & Logging

- **Security Audit**: Structured logging
- **Rotating Logs**: Disk-safe storage
- **Secrets Redaction**: Privacy protection

## Data Flow

```
Voice Input → STT → AI Plan → Guard → Auth → Execute → Audit
     ↓         ↓       ↓       ↓      ↓        ↓         ↓
  WebSocket  Whisper  GPT   Validate Check  Windows  JSON Log
```

## Trust Boundaries

| Boundary             | Input      | Validation      | Output         |
| -------------------- | ---------- | --------------- | -------------- |
| **User → System**    | Voice/UI   | Input Validator | Sanitized      |
| **AI → Execution**   | Plan       | PlanGuard       | Approved Plan  |
| **Session → Action** | Permission | SessionAuth     | Granted        |
| **System → OS**      | Commands   | RestrictedShell | Safe Execution |

## Security Model

**Default-Deny**: Everything blocked unless explicitly allowed
**Fail-Closed**: Errors deny access, never grant
**Defense-in-Depth**: Multiple validation layers
**Least Privilege**: Minimum required permissions
**Audit Everything**: Comprehensive logging
