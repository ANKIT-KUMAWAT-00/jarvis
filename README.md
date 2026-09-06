# JARVIS — Personal Autonomous AI Operating Layer

> **A local-first, verified, security-gated personal autonomous AI agent inspired by JARVIS, built for macOS.**

JARVIS is not a conversational chatbot. It is a **personal autonomous engineering agent** designed to act as an operating layer for your computer. It plans, inspects repositories, uses tools, executes terminal commands, modifies code, observes results, verifies receipts, updates permanent memory, and repairs common failures—with zero hallucination of unverified actions.

---

## 1. System Architecture

```text
USER (Voice / Text)
       ↓
Futuristic Cybernetic HUD (HTML5 / Vanilla CSS / Web Audio / Canvas Core)
       ↓
Intent Classifier & Epistemic Retriever (KNOWN, OBSERVED, REMEMBERED, INFERRED, UNKNOWN)
       ↓
Strategic Planner (Decomposes Goals into Verifiable Steps)
       ↓
Security & Permission Engine (Action Levels 0-3 with One-Time Narrow Tokens)
       ↓
Tool & Skill Registry (Filesystem, Terminal, Process, Git, Screen, Browser, System)
       ↓
Observation & Verification Engine (Exit Codes, Output Matching, File Fingerprints)
       ↓
Self-Repair Loop (Minimal Fixes within MAX_REPAIR_ATTEMPTS)
       ↓
Persistent Memory (SQLite Store, Notes Index, Semantic Knowledge Graph)
       ↓
Truthful Response with Verification Receipts
```

### Directory Structure

```text
jarvis/
├── backend/
│   ├── agent/            # Agent core loop, planner, verification, self-repair
│   ├── memory/           # SQLite store, semantic search, knowledge graph builder
│   ├── providers/        # LLMProvider abstraction (GeminiProvider, MockProvider)
│   ├── security/         # Permission engine, action levels, sanitizers, injection guards
│   ├── tasks/            # Persistent task queue and scheduler
│   ├── tools/            # Safe filesystem, terminal, git, screen, browser, process tools
│   ├── config.py         # System configuration & environment management
│   └── main.py           # FastAPI server, REST endpoints, WebSocket telemetry broadcaster
├── frontend/
│   ├── css/              # Cybernetic futuristic theme (jarvis.css)
│   ├── js/               # Visual neural core canvas, Web Speech API voice engine, graph, app controller
│   └── index.html        # Central command center HUD
├── skills/               # Extensible modular skill system (coding, filesystem, browser, vision, reminders, custom)
├── tests/                # Comprehensive unit, integration, security audit, and E2E test suites (45 tests)
├── scripts/              # Lifecycle automation (start.sh, stop.sh, test.sh, preflight.sh)
├── data/                 # SQLite database and scratch storage
├── logs/                 # Subprocess logs and audit trails
├── preflight.py          # Master system preflight verification (17 verification passes)
├── pytest.ini            # Pytest configuration
├── .env.example          # Environment variables template
└── README.md             # Complete master documentation
```

---

## 2. Installation & Quickstart

### Prerequisites
- **Operating System**: macOS (optimized for Apple Silicon `arm64` and Intel `x86_64`)
- **Python**: Version 3.10+
- **Node.js & Git**: Recommended for coding and web workflows

### Step 1: Clone or Navigate to the Workspace
```bash
cd /Users/ankitkumawat/.gemini/antigravity-ide/scratch/jarvis
```

### Step 2: Set Up Virtual Environment
```bash
# If venv is not yet initialized:
python3 -m venv venv
./venv/bin/pip install -r requirements.txt || ./venv/bin/pip install google-genai fastapi uvicorn pydantic pytest pytest-asyncio anyio requests websockets
```

### Step 3: Run the Preflight Verification
```bash
./preflight.sh
# Expected output: 17 PASS | 0 FAIL | 1 WARN (Gemini API key warning if offline)
```

### Step 4: Run the Complete Test Suite
```bash
./test.sh
# Runs all 45 automated unit, integration, security, and E2E tests
```

### Step 5: Launch JARVIS
```bash
./start.sh
```
Open your browser at: **[http://127.0.0.1:8010](http://127.0.0.1:8010)**

To stop JARVIS:
```bash
./stop.sh
```

---

## 3. Google Gemini Setup

JARVIS uses the official `google-genai` SDK and supports Google Gemini through a clean provider abstraction (`LLMProvider`).

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Set your API credentials in `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
4. **Free-First Offline Fallback**: If `GEMINI_API_KEY` is omitted or unconfigured, JARVIS automatically boots with `MockProvider`, allowing full offline development, task simulation, UI interaction, and test execution at ₹0 cost.

---

## 4. Security & Permission Architecture

Security is enforced at the architecture level, never left to prompt suggestions:

### Action Levels
- **LEVEL 0 — READ**: Read-only actions (read files, inspect git status, search memories, capture screen, system info). Executed automatically upon user request.
- **LEVEL 1 — SAFE WRITE**: Sandboxed filesystem writes and test commands inside the workspace. Executed automatically on explicit user intent.
- **LEVEL 2 — EXTERNAL ACTION**: Network calls, git push, or external operations. Requires confirmation unless standing permission is granted.
- **LEVEL 3 — HIGH RISK**: Destructive operations (`rm -rf`, disk formats, git hard resets, sensitive file access). **Always requires explicit authorization.**

### Narrow Single-Action Confirmation Tokens
- When an operation requires confirmation, the engine creates a unique `ConfirmationToken`.
- The token is tied strictly to `(tool_name, action, target)`.
- Authorizing a token for `./temp` does **NOT** authorize any other directory or tool.
- Tokens expire in 300 seconds and are destroyed immediately upon use (one-time execution).

### Prompt Injection & Untrusted Data Isolation
- Content from external websites, emails, or tool outputs is treated as **passive data**.
- All external data is automatically wrapped in `<UNTRUSTED_EXTERNAL_DATA>` boundaries with explicit instructions to the AI that system rules and policies cannot be overridden by external content.
- Common jailbreak patterns (`ignore previous instructions`, `developer mode`, `reveal secret`) are detected and blocked.

### Secret Redaction
- All terminal output, logs, and tool receipts are scrubbed using regex patterns to redact Gemini API keys (`AIza...`), tokens (`sk-...`), and private keys before rendering to the UI or logs.

---

## 5. Tool & Skill Abstraction

All operations pass through concrete `Tool` and `BaseSkill` implementations:

| Tool | Capabilities | Permission Level |
|---|---|---|
| `filesystem` | `list_dir`, `read_file`, `write_file`, `search_files`, `file_info`, `delete_file` | Level 0 (Read) / Level 1 (Write) / Level 3 (Delete) |
| `terminal` | Asynchronous shell commands with timeouts, captured stdout/stderr, and exit code checks | Level 1 (Safe) / Level 3 (Destructive Intercept) |
| `process` | Start, inspect, monitor, stop background processes with log file capture | Level 1 |
| `git` | Status, diff, log, branch, checkout, commit, push | Level 0 (Status/Log) / Level 1 (Commit) / Level 2 (Push) |
| `screen` | Native macOS `/usr/sbin/screencapture` for instantaneous screen vision | Level 0 |
| `browser` | HTTP fetching, semantic HTML cleanup, untrusted data wrapping | Level 0 |
| `system_info` | Darwin release, Apple Silicon detection, Node/Python/Git dependency inspection | Level 0 |

---

## 6. Memory & Epistemic Reasoning

JARVIS uses an atomic SQLite store (`data/jarvis_memory.db`) categorized into:
- **Short-Term Memory**: Ephemeral context during active tasks.
- **Long-Term Memory**: Important facts and preferences explicitly stated by the user.
- **Project Memory**: Information about projects, repositories, and workspaces.
- **Task Memory**: Scheduled reminders and background jobs.

### The "Remember" Command
Saying `"JARVIS, remember that my main project is ResumeIQ AI"` triggers:
1. Regex extraction of the core fact.
2. Immediate SQLite persistence.
3. Live WebSocket broadcast (`MEMORY_UPDATED`).
4. Instant UI HUD update without requiring a restart.

### Epistemic Separation
When preparing reasoning context, memories are strictly segregated:
