# AgentForge User Guide

## Getting Started

### Installation

**Prerequisites:**
- Node.js 18+
- Python 3.10+
- npm 9+

**Quick Start:**
```bash
# Clone and install
cd agentforge
npm install
pip install -r requirements.txt

# Start development
npm run dev        # Frontend + Electron
cd backend && python main.py  # Backend API
```

### Creating Your First Agent

1. Open the **Agents** tab in the sidebar
2. Click **+** button to create a new agent
3. Fill in the form:
   - **Name**: e.g., "CodeReviewer"
   - **Description**: What this agent does
   - **Role**: orchestrator / assistant / executor / reviewer
   - **Model**: Choose your LLM model
   - **System Prompt**: Define the agent's behavior
   - **Capabilities**: Check applicable skills
4. Click **Create Agent** to save

### Building a Pipeline

1. Open a project and go to the **Forge** tab
2. Drag agents from the **Agent Panel** (right sidebar) onto the canvas
3. Connect agent nodes by dragging from output handles to input handles
4. Use the toolbar to:
   - **Auto-layout**: Auto-arrange nodes
   - **Save**: Persist your pipeline
   - **Run**: Execute the pipeline (opens Run Dialog)

### Running a Pipeline

1. Click **Run** in the Forge toolbar
2. Select a **collaboration mode**:
   - **Sequential**: Agents execute one after another
   - **Parallel**: All agents run simultaneously
   - **Conditional**: Branch based on previous output
   - **Iterative**: Loop until termination condition
3. Choose which agents to include
4. Click **Start Run**

### Monitoring Execution

- Real-time logs stream in the **LiveMonitor** panel
- Each agent shows its current status (idle/running/completed/failed)
- Aggregate progress bar shows overall completion
- The **TaskTimeline** shows Gantt-style execution timeline

### Importing & Exporting

- **Export**: Click export icon in toolbar → downloads pipeline as JSON
- **Import**: Click import icon → select a `.json` file

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save pipeline |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Delete | Remove selected node |
| Scroll | Zoom in/out |
| Middle-drag | Pan canvas |
