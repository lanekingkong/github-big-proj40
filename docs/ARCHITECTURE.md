# AgentForge Architecture

## Overview

AgentForge is a multi-agent collaboration GUI platform built as an Electron desktop application with a Python FastAPI backend. The frontend uses React + TypeScript + Tailwind CSS, and the agent orchestration is powered by React Flow for visual pipeline editing.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Electron Shell                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  Renderer Process                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│  │  │  React   │  │  Zustand │  │  React Flow    │  │  │
│  │  │  (UI)    │  │ (Store)  │  │  (Canvas)      │  │  │
│  │  └──────────┘  └──────────┘  └────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │              WebSocket Client                │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  Main Process                      │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │             Context Bridge (IPC)              │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               Python Backend (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │  Routes  │  │ Services │  │   Orchestrator       │  │
│  │ (REST)   │  │ (Logic)  │  │   ┌───────────────┐  │  │
│  └──────────┘  └──────────┘  │   │ Agent Registry│  │  │
│  ┌──────────┐  ┌──────────┐  │   ├───────────────┤  │  │
│  │  WebSocket│  │   MCP    │  │   │ Task Scheduler│  │  │
│  │  Server  │  │  Server  │  │   ├───────────────┤  │  │
│  └──────────┘  └──────────┘  │   │ Pipeline      │  │  │
│  ┌──────────┐  ┌──────────┐  │   ├───────────────┤  │  │
│  │   A2A    │  │  Adapters│  │   │Result Aggreg. │  │  │
│  │  Server  │  │  (6+)    │  │   └───────────────┘  │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

- **Electron + React**: Desktop-first with web-native stack
- **Zustand**: Lightweight state management (no Redux boilerplate)
- **React Flow**: Mature library for visual node-based editors
- **FastAPI**: High-performance async Python with automatic OpenAPI docs
- **4 Collaboration Modes**: Sequential, Parallel, Conditional, Iterative
- **Protocol Support**: MCP (Model Context Protocol) + A2A (Agent-to-Agent)

## Data Flow

1. User creates agents and assembles pipeline in Forge canvas
2. Pipeline JSON is saved via Zustand store → localStorage / backend API
3. On "Run", pipeline config is sent to backend via WebSocket
4. Orchestrator parses pipeline, resolves agent instances, executes per mode
5. Real-time logs and status are streamed back via WebSocket
6. Results are aggregated and displayed in LiveMonitor

## Directory Structure

```
agentforge/
├── src/
│   ├── components/       # React components
│   │   ├── layout/       # App shell (Sidebar, TopBar, StatusBar)
│   │   ├── dashboard/    # Project cards, stats
│   │   ├── forge/        # Visual pipeline editor
│   │   ├── agents/       # Agent CRUD forms
│   │   ├── monitor/      # Live run monitoring
│   │   └── common/       # Shared UI primitives
│   ├── hooks/            # Custom React hooks
│   ├── stores/           # Zustand stores
│   ├── services/         # API client layer
│   ├── types/            # TypeScript type definitions
│   └── utils/            # Validators, constants
├── electron/             # Electron main + preload
├── backend/
│   ├── api/              # FastAPI routes
│   ├── core/             # Orchestrator engine
│   ├── agents/           # Agent adapters
│   ├── services/         # Business logic
│   ├── protocols/        # MCP + A2A
│   └── utils/            # Logger, security
├── docs/                 # Documentation
└── scripts/              # Dev/setup scripts
```
