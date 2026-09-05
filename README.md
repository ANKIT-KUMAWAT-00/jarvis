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
