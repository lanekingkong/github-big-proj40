# AgentForge

<div align="center">

**Multi-Agent Collaborative Orchestration Platform**

*Build AI agent teams that ship projects together*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Electron](https://img.shields.io/badge/Electron-28.x-47848F?logo=electron)](https://www.electronjs.org/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

</div>

---

## Overview

**AgentForge** is a desktop application built with **Electron + React + Python FastAPI** that enables developers to configure multiple AI agents — each with distinct roles and capabilities — to collaborate as a team and autonomously complete complex software engineering projects. Think of it as giving every developer their own AI SWAT team operating locally on their machine.

### The Problem

Modern AI coding agents (Claude Code, Codex, Cursor, etc.) are powerful individually, but they have critical limitations:

- **Single-agent fragility**: One agent gets stuck in a bug loop and cannot self-rescue.
- **No review mechanism**: Code is generated without a second pair of eyes.
- **Role confusion**: A single agent tries to be developer, reviewer, tester, and deployer simultaneously — none of which it does perfectly.
- **Configuration hell**: Each CLI agent requires separate setup, API keys, and tool access configurations.
- **No teamwork**: There is no built-in way for multiple specialized agents to coordinate on a single codebase.

### The Solution

AgentForge solves these problems by orchestrating a **team of specialized AI agents** that collaborate through a structured workflow:

```
Developer Agent → Reviewer Agent → Fixer Agent → Tester Agent → Deployer Agent
      ↑                                                          |
      └─────────────────── feedback loop ───────────────────────┘
```

Each agent plays a dedicated role, uses its own underlying AI model and tool set, and communicates through the AgentForge orchestration engine. The result: higher code quality, fewer bugs, and dramatically reduced manual intervention.

---

## 5W1H Analysis

| Aspect | Detail |
|--------|--------|
| **WHAT** | A multi-agent collaborative orchestration GUI platform for local development environments |
| **WHY** | Single-agent coding tools produce bugs, lack review mechanisms, and cannot self-correct. A multi-agent team with role specialization addresses these weaknesses systematically. |
| **WHO** | Software developers, engineering teams, indie hackers, and anyone who wants AI-assisted project delivery with quality guarantees |
| **WHERE** | Runs locally on Windows / macOS / Linux desktops as an Electron application |
| **WHEN** | During the entire software development lifecycle — from initial scaffolding to production deployment |
| **HOW** | Electron + React for the GUI layer; Python FastAPI backend for agent orchestration, workflow state management, and WebSocket-based real-time communication |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Electron Shell                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │              React Frontend (Vite + TS)            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ Project  │  │ Agent    │ │ Workflow Canvas  │  │  │
│  │  │ Manager  │  │ Registry │ │   (ReactFlow)    │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │  HTTP + WebSocket                 │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │           Python FastAPI Backend                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ Workflow │  │ Agent    │ │ Task Queue &     │  │  │
│  │  │ Engine   │  │ Manager  │ │ State Machine    │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ MCP      │  │ Git      │ │ Logging &        │  │  │
│  │  │ Protocol │  │ Adapter  │ │ Monitoring       │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │  Subprocess / API                 │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │           AI Agent Runtimes (CLI)                  │  │
│  │  Claude Code │ Codex │ Trae │ OpenClaw │ Gemini   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Collaboration Flow

```
1. User creates a Project and defines requirements
         │
         ▼
2. Developer Agent generates/edits code
         │
         ▼
3. Reviewer Agent inspects changes, flags issues
         │
         ▼
4. Fixer Agent resolves flagged issues
         │
         ▼
5. Tester Agent runs test suites & validates
         │
    ┌────┴────┐
    │  Pass?  │
    └────┬────┘
    No   │   Yes
    ▼    │    ▼
Back to  │  Deployer Agent
Step 2   │  packages & deploys
```

---

## Supported Agents

| Agent | Role | Base CLI | Strengths |
|-------|------|----------|-----------|
| **Claude Code** | Developer / Reviewer | `claude` | Strong code understanding, large context window |
| **Codex** | Developer / Fixer | `codex` | OpenAI-powered, fast iteration |
| **Trae** | Developer / Tester | `trae` | ByteDance ecosystem, good at code generation |
| **OpenClaw** | Reviewer / Fixer | `openclaw` | Open-source, customizable review rules |
| **Hermess** | Developer / Deployer | `hermess` | Deployment automation, CI/CD integration |
| **OpenCode** | Developer / Fixer | `opencode` | Open-source coding agent, extensible |
| **Gemini CLI** | Reviewer / Tester | `gemini` | Google ecosystem, strong analysis capabilities |

Agents can be mixed and matched — you could use Claude Code as Developer, Gemini CLI as Reviewer, and Codex as Fixer, creating a cross-model team that leverages each model's unique strengths.

---

## Features

### Core Features

- **Visual Workflow Designer**: Drag-and-drop agent nodes onto a ReactFlow canvas to design collaboration pipelines.
- **Agent Registry**: Register and configure multiple AI agents with role assignments, API keys, and tool access permissions.
- **Real-time Collaboration**: Watch agents work in real-time via WebSocket streaming — see code being written, reviewed, and fixed live.
- **Git-native**: All agent work happens in git-tracked directories with automatic branching and PR-like review flows.
- **Task State Machine**: Robust state tracking (pending → running → reviewing → fixing → testing → completed / failed) with retry and rollback.

### Quality Assurance

- **Automatic Code Review**: Reviewer agent inspects every change set before it reaches the codebase.
- **Auto-fix Pipeline**: Failed tests or review flags automatically trigger the Fixer agent.
- **Test Generation**: Tester agent can generate and maintain test suites for your project.
- **Quality Gates**: Configurable pass/fail criteria per workflow stage.

### Developer Experience

- **Project Templates**: Pre-built workflow templates for web apps, CLI tools, libraries, and microservices.
- **Hot Reload**: Frontend changes are reflected instantly during development.
- **Dark Mode**: Built-in dark theme for comfortable late-night coding sessions.
- **Cross-platform**: Runs identically on Windows, macOS, and Linux.

---

## Tech Stack

### Frontend
| Technology | Purpose |
|-----------|---------|
| **Electron 28** | Desktop application shell |
| **React 18** | UI framework |
| **TypeScript 5** | Type-safe JavaScript |
| **Vite 5** | Build tool and dev server |
| **ReactFlow** | Visual workflow / node-graph canvas |
| **Zustand** | Lightweight state management |
| **TailwindCSS 3** | Utility-first CSS framework |

### Backend
| Technology | Purpose |
|-----------|---------|
| **Python 3.11+** | Runtime |
| **FastAPI** | REST API + WebSocket server |
| **Pydantic v2** | Data validation and serialization |
| **SQLAlchemy 2** | ORM for SQLite |
| **aiosqlite** | Async SQLite driver |
| **httpx** | Async HTTP client for agent API calls |
| **MCP Protocol** | Model Context Protocol for agent-tool integration |
| **Uvicorn** | ASGI server |

---

## Quick Start

### Prerequisites

- **Node.js** >= 18.0.0
- **Python** >= 3.11
- **Git** >= 2.40
- **pnpm** >= 8 (recommended) or npm >= 9

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/agentforge.git
cd agentforge

# Install frontend dependencies
pnpm install

# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys and preferences
```

### Development

```bash
# Start backend server (Terminal 1)
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8765

# Start Electron + Vite dev server (Terminal 2)
pnpm dev
```

### Build

```bash
# Build for your current platform
pnpm build

# Build for specific platforms
pnpm build:win    # Windows
pnpm build:mac    # macOS
pnpm build:linux  # Linux
```

---

## Project Structure

```
agentforge/
├── README.md                    # This file
├── README_CN.md                 # Chinese README
├── LICENSE                      # MIT License
├── package.json                 # Node.js dependencies and scripts
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts              # Vite bundler configuration
├── tailwind.config.ts          # TailwindCSS design system
├── postcss.config.js           # PostCSS plugins
├── electron-builder.yml        # Electron packaging config
├── .gitignore                  # Git ignore rules
├── docs/
│   ├── 5W1H_ANALYSIS.md        # Detailed 5W1H analysis (bilingual)
│   └── ARCHITECTURE.md         # Technical architecture documentation
├── src/                        # React frontend source
│   ├── main/                   # Electron main process
│   ├── renderer/               # React renderer process
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Route pages
│   │   ├── stores/             # Zustand stores
│   │   ├── hooks/              # Custom React hooks
│   │   ├── layouts/            # Page layout components
│   │   └── styles/             # Global styles
│   └── preload/                # Electron preload scripts
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # FastAPI application entry
│   ├── config.py              # Configuration management
│   ├── requirements.txt       # Python dependencies
│   ├── models/                # SQLAlchemy data models
│   ├── routers/               # API route handlers
│   ├── services/              # Business logic layer
│   └── engine/                # Agent orchestration engine
└── tests/                     # Test suites
```

---

## Configuration

AgentForge uses a declarative YAML-based agent registry. Each agent is defined with its role, capabilities, and tool access:

```yaml
agents:
  - name: "ClaudeDev"
    cli: "claude"
    role: "developer"
    model: "claude-sonnet-4-20250514"
    tools:
      - read_file
      - write_file
      - execute_command
      - search_codebase
    max_context_tokens: 200000

  - name: "GeminiReviewer"
    cli: "gemini"
    role: "reviewer"
    model: "gemini-2.5-pro"
    tools:
      - read_file
      - search_codebase
      - diff_viewer
    review_rules:
      - security_check
      - style_lint
      - complexity_analysis
```

---

## Workflow Example

Here is a practical example of AgentForge handling a feature request:

1. **User submits**: "Add rate limiting middleware to the Express API"
2. **Developer Agent (Claude Code)**: Reads existing middleware, generates rate-limiting code, writes tests.
3. **Reviewer Agent (Gemini CLI)**: Inspects the diff, flags a potential race condition in the rate limiter.
4. **Fixer Agent (Codex)**: Receives the review comment, refactors the rate limiter to use atomic counters, updates tests.
5. **Tester Agent (Trae)**: Runs the full test suite — all tests pass. Generates an edge-case test for burst traffic.
6. **Deployer Agent (Hermess)**: Commits the changes, creates a git tag, and triggers the CI/CD pipeline.

The user only wrote a one-line requirement. AgentForge handled everything else.

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

AgentForge builds upon the incredible work of the open-source community:

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic
- [Codex](https://github.com/openai/codex) by OpenAI
- [ReactFlow](https://reactflow.dev/) by xyflow
- [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez
- [Electron](https://www.electronjs.org/) by OpenJS Foundation

---

<div align="center">
  <strong>AgentForge</strong> — Forge your AI team. Ship better software.
</div>
