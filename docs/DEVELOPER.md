# AgentForge Developer Guide

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop Shell | Electron 28 |
| Frontend | React 18 + TypeScript |
| Styling | Tailwind CSS 3.4 |
| State | Zustand |
| Canvas | @xyflow/react (React Flow 12) |
| Backend | Python 3.10+ / FastAPI |
| WebSocket | FastAPI WebSocket + ws library |
| Agent Protocols | MCP + A2A |

## Project Setup

```bash
# Install frontend dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

## Development

**Start all services:**
```bash
npm run dev          # Vite dev server + Electron
```

**Start backend separately:**
```bash
cd backend
python main.py       # Starts on http://localhost:8899
```

**API docs:** http://localhost:8899/docs (auto-generated OpenAPI)

## State Management

Zustand stores are in `src/stores/`:

| Store | Purpose |
|-------|---------|
| `forgeStore` | Canvas nodes/edges, history, import/export |
| `projectStore` | Project CRUD, current project |
| `agentStore` | Agent registry, CRUD |
| `settingsStore` | User preferences, API keys |

## Adding a New Agent Adapter

1. Create adapter in `backend/agents/adapters/my_agent.py`:
```python
from backend.agents.base import AgentAdapter

class MyAgentAdapter(AgentAdapter):
    async def execute(self, task: Task) -> TaskResult:
        # Implementation
        pass
```

2. Register in `backend/core/agent_registry.py`:
```python
registry.register("my_agent", MyAgentAdapter)
```

## Adding a New Collaboration Mode

1. Add mode logic in `backend/core/orchestrator.py`:
```python
async def _execute_my_mode(self, pipeline, agents):
    # Custom execution logic
    pass
```

2. Add UI option in `src/utils/constants.ts` `COLLABORATION_MODES` array

## WebSocket Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `run:start` | Client→Server | Initiate pipeline run |
| `log` | Server→Client | Streaming log entry |
| `agent_status` | Server→Client | Agent state change |
| `progress` | Server→Client | Global progress update |
| `complete` | Server→Client | Run finished |
| `abort` | Client→Server | Cancel running pipeline |

## Building for Production

```bash
npm run build         # Production bundle
npm run electron:build # Package Electron app
```
