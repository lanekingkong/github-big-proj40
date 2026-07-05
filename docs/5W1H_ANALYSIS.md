# AgentForge 5W1H Project Analysis / 5W1H 项目分析

> **Comprehensive project analysis document | 全面的项目分析文档**
>
> Language: 中文为主，关键术语保留英文 | Primarily Chinese with English terminology

---

## Table of Contents / 目录

1. [WHAT — 项目定义](#1-what--项目定义)
2. [WHY — 存在理由](#2-why--存在理由)
3. [WHO — 目标用户](#3-who--目标用户)
4. [WHERE — 使用场景与环境](#4-where--使用场景与环境)
5. [WHEN — 使用时机](#5-when--使用时机)
6. [HOW — 技术实现方案](#6-how--技术实现方案)
7. [附录：市场分析与竞品对比](#附录市场分析与竞品对比)

---

## 1. WHAT — 项目定义

### 1.1 一句话定义

**AgentForge 是一个基于 Electron + React 桌面 GUI 的多 Agent 聚合协作平台，让开发者通过可视化界面配置多个专业 AI Agent（Claude Code / Codex / Gemini CLI / Trae / OpenClaw / Hermess / OpenCode），组建分工明确的开发团队，自动完成从需求分析到代码部署的全流程软件交付。**

### 1.2 完整定义

AgentForge is a **Desktop Multi-Agent Orchestration Platform** that:

1. **Aggregates** multiple AI coding agents (Claude Code, Codex, Gemini CLI, Trae, OpenClaw, Hermess, OpenCode) under a unified interface.
2. **Orchestrates** them through structured collaboration workflows where each agent plays a specialized role.
3. **Visualizes** the entire development process through a ReactFlow-based node graph canvas.
4. **Automates** the software development lifecycle: coding → review → fix → test → deploy — with human-in-the-loop at key decision points.
5. **Runs locally** as an Electron desktop application, keeping all code and configuration on the user's machine.

### 1.3 核心名词定义

| 术语 | 英文 | 定义 |
|------|------|------|
| 智能体 | Agent | 拥有特定角色和能力的 AI 运行时实例，底层由 CLI 工具驱动（如 `claude`、`codex`）。 |
| 角色 | Role | Agent 在工作流中的职责分工：Developer / Reviewer / Fixer / Tester / Deployer。 |
| 项目 | Project | 一个被 Git 管理的代码仓库 + Agent 团队配置 + 任务列表。 |
| 工作流 | Workflow | Agent 之间的协作流水线，定义任务流转顺序和状态机。 |
| 任务 | Task | 最小工作单元，由特定角色的 Agent 执行，遵循状态机（pending → running → reviewing → ...）。 |
| 审查循环 | Review Loop | Developer → Reviewer → Fixer 之间的反馈闭环，直到代码质量达标。 |
| 节点画布 | Canvas | ReactFlow 驱动的可视化工作流编辑器，拖拽 Agent 节点构建协作流水线。 |
| 编排引擎 | Orchestration Engine | Python FastAPI 后端核心，管理任务分发、状态追踪、Agent 间通信。 |

### 1.4 项目范围（Scope）

**In Scope（包含）：**
- Electron 桌面 GUI 应用（Windows / macOS / Linux）
- React + TypeScript 前端，ReactFlow 工作流画布
- Python FastAPI 后端，SQLite 数据持久化
- 7 个 Agent CLI 的适配器（Claude Code / Codex / Trae / OpenClaw / Hermess / OpenCode / Gemini CLI）
- WebSocket 实时日志流
- Git 原生集成（自动分支、commit、PR 式 review）
- 本地数据存储，无云依赖

**Out of Scope（不包含）：**
- SaaS 云端托管版本（仅本地桌面）
- Agent CLI 本身的开开发和维护（仅做适配）
- 移动端应用
- 多人协同（单用户多 Agent）
- AI 模型训练或微调

---

## 2. WHY — 存在理由

### 2.1 核心痛点

#### Pain Point 1: 单 Agent 脆弱性（Single-Agent Fragility）

```
用户: "帮我实现一个用户认证模块"
Agent: 生成 500 行代码，包含 3 个安全漏洞
用户: "有 Bug，修一下"
Agent: 改了 A，引入了 B 的回归 Bug
用户: "B 又坏了！"
Agent: 修 B，A 又出问题...
→ 无限 debug 地狱
```

**本质问题**：单个 Agent 缺乏"他者视角"。就像程序员写代码自己不容易找出自己的 Bug，AI Agent 也面临相同困境。它无法对自己的输出进行有效的批判性审视。

#### Pain Point 2: 缺乏质量关卡（No Quality Gates）

传统 AI 编码工具的工作流是线性的：需求 → 生成 → 完成。缺少：

- **代码审查**：生成的代码无人把关，安全隐患、逻辑缺陷直接入库
- **自动化测试**：Agent 可能生成代码但不生成测试，或生成的测试覆盖不足
- **部署验证**：代码能跑 ≠ 能在生产环境安全运行

#### Pain Point 3: 角色混淆（Role Confusion）

单个 Agent 被迫同时扮演多个角色：

```
作为 Developer：写代码
作为 Reviewer：审查自己刚写的代码  ← 利益冲突
作为 Tester：测试自己的代码       ← 盲区
作为 DevOps：部署                ← 超出专业领域
```

这是编程领域的"利益冲突"问题——同一个人（Agent）不能同时担任开发者和审查者。类比现实世界：**你不会让同一个开发者 review 他自己的 PR，为什么让同一个 AI 既写代码又审查？**

#### Pain Point 4: 配置碎片化（Configuration Fragmentation）

当前 AI 编码工具生态现状：

```
~/.claude/config.json       ← Claude Code 配置
~/.codex/config.yaml        ← Codex 配置
~/.gemini/settings.toml     ← Gemini CLI 配置
.env 中的 OPENAI_API_KEY    ← 散落的 API 密钥
.env 中的 ANTHROPIC_API_KEY
.bashrc 中的别名和路径
```

每个 CLI 工具有独立的配置格式、API key 管理方式、工具权限体系。用户需要分别学习和维护。AgentForge 提供**统一的配置管理界面**，一键注册和管理所有 Agent。

#### Pain Point 5: 无协作机制（No Team Coordination）

现实软件开发是团队协作：

```
前端开发者 ←→ 后端开发者 ←→ QA 工程师 ←→ DevOps
     ↓           ↓           ↓           ↓
  写组件      写 API      写测试      部署上线
     ↓           ↓           ↓           ↓
            Code Review / PR / CI / CD
```

AI 编码工具完全缺失这种协作模式。AgentForge 将**人类软件工程的最佳实践**（团队分工、代码审查、CI/CD）引入 AI Agent 工作流。

### 2.2 价值主张（Value Proposition）

| 维度 | 单 Agent 方案 | AgentForge 方案 |
|------|--------------|-----------------|
| **代码质量** | 一个人写，无人把关 | Developer 写 → Reviewer 审 → Fixer 修，三道关卡 |
| **Bug 率** | 高，且难以自我修复 | Reviewer 捕获大部分缺陷，Fixer 自动修复 |
| **测试覆盖** | 依赖 Agent 自觉生成 | Tester Agent 强制生成和维护测试 |
| **配置管理** | 每个 CLI 独立配置 | 统一 GUI 注册中心 |
| **可视化** | 纯命令行交互 | ReactFlow 可视化工作流编排 |
| **审计追溯** | 难以追踪哪个 Agent 做了什么 | 完整的任务日志和 Git 历史 |

### 2.3 为什么是现在（Why Now）

1. **Agent CLI 生态成熟**：Claude Code、Codex、Gemini CLI 等高质量 AI 编码 CLI 工具已经稳定可用。
2. **模型能力突破**：Claude Sonnet 4、Gemini 2.5 Pro 等模型在代码理解和生成上达到生产可用水平。
3. **MCP 协议标准化**：Model Context Protocol 为 Agent-工具交互提供了统一标准。
4. **开发者痛点爆发**：越来越多人使用 AI 辅助编程，单 Agent 的局限性暴露无遗。

---

## 3. WHO — 目标用户

### 3.1 用户画像

| 画像 | 描述 | 使用场景 |
|------|------|----------|
| **独立开发者 / Indie Hacker** | 一个人维护多个项目，需要"虚拟团队"提效 | 用 AgentForge 组建 3-4 个 Agent 团队，自动化常规开发任务 |
| **全栈工程师** | 需要同时处理前后端，调试全链路问题 | Developer Agent 写后端，另一个 Agent 写前端，Tester Agent 全链路测试 |
| **技术 Leader / CTO** | 需要把控代码质量和项目进度 | 配置 Agent 团队执行标准化工作流，确保每个 PR 都经过 Review → Fix → Test 流程 |
| **开源项目维护者** | 面对大量 PR 和 Issue 无力逐一处理 | 用 AgentForge 自动 triage Issue、生成 fix、通过 test pipeline 后自动 merge |
| **编程学习者** | 学习软件工程最佳实践 | 观察 Agent 团队协作过程，学习 code review、测试驱动开发等工作流 |
| **初创团队** | 人手不足，需要 AI 补位 | 用 AgentForge 填补缺失角色（如没有专职 QA，用 Tester Agent） |

### 3.2 典型使用场景

**场景 1：独立开发者的"虚拟团队"**
```
用户（全栈开发者）
  → Developer Agent（Claude Code）：写 API 代码
  → Reviewer Agent（Gemini CLI）：审查代码安全性
  → Fixer Agent（Codex）：自动修复审查问题
  → Tester Agent（Trae）：生成和运行测试
  → Deployer Agent（Hermess）：部署到 Vercel
结果：一个人完成 5 人团队的工作量
```

**场景 2：开源维护者的 PR 审查流水线**
```
GitHub Webhook 触发新 PR
  → Reviewer Agent 自动审查代码变更
  → 生成 Review Comment 贴到 PR
  → 如果发现 Bug → Fixer Agent 自动生成修复 Commit
  → Tester Agent 运行 CI
  → 全部通过 → 自动 Merge
```

**场景 3：代码重构安全网**
```
用户: "把这个 Express 项目重构成 FastAPI"
  → Developer Agent 逐模块转换
  → Reviewer Agent 逐模块验证逻辑等价性
  → Tester Agent 确保 API 行为不变
  → Fixer Agent 修复兼容性问题
```

---

## 4. WHERE — 使用场景与环境

### 4.1 运行环境

| 维度 | 规格 |
|------|------|
| **操作系统** | Windows 10/11, macOS 13+, Ubuntu 22.04+ / Debian 12+ / Fedora 39+ |
| **架构** | x86_64, ARM64 (Apple Silicon) |
| **Node.js** | >= 18.0.0 |
| **Python** | >= 3.11 |
| **磁盘空间** | ~2GB（应用本体 + 各 CLI 工具 + 依赖） |
| **内存** | >= 8GB 推荐 |
| **GPU** | 不需要（Agent 推理在云端 API 完成） |

### 4.2 部署模式

**纯本地部署（Local-First）**：
- AgentForge 是桌面应用，所有数据存储在本地
- SQLite 数据库：`~/.agentforge/agentforge.db`（macOS/Linux）或 `%APPDATA%/agentforge/agentforge.db`（Windows）
- Agent CLI 工具由用户预先安装，AgentForge 只做编排
- API Key 以环境变量或 `.env` 文件管理，不上传云端

### 4.3 与其他工具的集成位置

```
┌───────────────────────────────────────────────────────┐
│                    开发者桌面                          │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ VS Code  │  │ Terminal │  │  AgentForge GUI  │   │
│  │ (编辑器) │  │  (Git)   │  │  (Agent 编排)    │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│       │              │                │               │
│       └──────────────┼────────────────┘               │
│                      │                                │
│              ┌───────▼────────┐                       │
│              │   代码仓库     │                       │
│              │  (~/projects/) │                       │
│              └────────────────┘                       │
└───────────────────────────────────────────────────────┘
```

AgentForge 定位为 VS Code 和 Terminal 的**协作伙伴**，不是替代品。你在 VS Code 写代码，在 Terminal 运行 Git，在 AgentForge 指挥 Agent 团队。

---

## 5. WHEN — 使用时机

### 5.1 全生命周期覆盖

AgentForge 覆盖软件开发的完整生命周期：

```
┌─────────────────────────────────────────────────────────┐
│              软件开发生命周期中的 AgentForge              │
├──────────────┬──────────────────────────────────────────┤
│ 阶段         │ AgentForge 如何参与                        │
├──────────────┼──────────────────────────────────────────┤
│ 1. 需求分析  │ 用户输入需求描述，AgentForge 生成任务拆解  │
│ 2. 架构设计  │ Developer Agent 生成架构方案，              │
│              │ Reviewer Agent 评审可行性                  │
│ 3. 编码实现  │ Developer Agent 逐模块编码                  │
│              │ Reviewer Agent 持续审查                    │
│              │ Fixer Agent 修复问题                       │
│ 4. 测试      │ Tester Agent 生成和运行测试                 │
│              │ 失败 → 回到编码阶段                        │
│ 5. 部署      │ Deployer Agent 打包、生成 Dockerfile、      │
│              │ 部署到目标环境                             │
│ 6. 维护      │ 新需求 → 回到步骤 1                        │
│              │ Bug 修复 → Fixer Agent 直接处理            │
└──────────────┴──────────────────────────────────────────┘
```

### 5.2 触发时机

你需要 AgentForge 当：

1. **项目初始化时** — 用 AgentForge 快速搭建项目脚手架和初始化代码
2. **功能开发时** — 指派 Developer Agent 完成 feature 开发
3. **代码审查时** — 用 Reviewer Agent 自动检查所有变更
4. **Bug 修复时** — 派 Fixer Agent 快速定位和修复问题
5. **测试补全时** — 用 Tester Agent 补充测试覆盖
6. **发布部署时** — 用 Deployer Agent 自动化打包和部署
7. **重构迁移时** — Agent 团队分工协作，保障重构安全

### 5.3 不需要 AgentForge 的情况

- 简单的单文件脚本修改（用单个 Agent 更快）
- 探索性实验（需要人类直觉判断）
- 安全敏感的代码（如加密算法、认证模块 — 需要人工审查每行代码）
- 需要深度领域知识的项目（Agent 可能产生看似正确但实质错误的代码）

---

## 6. HOW — 技术实现方案

### 6.1 技术架构总览

```
┌──────────────────────────────────────────────────────────┐
│                      Electron Shell                       │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                  Main Process                       │  │
│  │  ┌──────────────┐  ┌──────────────┐               │  │
│  │  │ Window Mgr   │  │ IPC Bridge   │               │  │
│  │  └──────────────┘  └──────┬───────┘               │  │
│  └───────────────────────────┼────────────────────────┘  │
│                              │ IPC                        │
│  ┌───────────────────────────┼────────────────────────┐  │
│  │                Renderer Process                     │  │
│  │  ┌────────────────────────▼─────────────────────┐  │  │
│  │  │           React Application                   │  │  │
│  │  │  ┌─────────┐ ┌──────────┐ ┌──────────────┐  │  │  │
│  │  │  │ Project │ │ Agent    │ │ Workflow     │  │  │  │
│  │  │  │ Page    │ │ Registry │ │ Canvas       │  │  │  │
│  │  │  │         │ │ Page     │ │ (ReactFlow)  │  │  │  │
│  │  │  └─────────┘ └──────────┘ └──────┬───────┘  │  │  │
│  │  │  ┌─────────┐ ┌──────────┐       │          │  │  │
│  │  │  │ Task    │ │ Log      │       │          │  │  │
│  │  │  │ Board   │ │ Viewer   │       │          │  │  │
│  │  │  └─────────┘ └──────────┘       │          │  │  │
│  │  │                                 │          │  │  │
│  │  │  State: Zustand Stores ─────────┘          │  │  │
│  │  │  HTTP: fetch() → FastAPI                   │  │  │
│  │  │  WS:   WebSocket → Agent Events            │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────┬───────────────────────────┘  │
└─────────────────────────┼──────────────────────────────┘
                          │ HTTP + WebSocket
┌─────────────────────────▼──────────────────────────────┐
│                   Python FastAPI Backend                 │
│                                                         │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  API Layer    │  │  WS Manager  │  │  Auth       │  │
│  │  (Routers)    │  │  (Events)    │  │  (API Key)  │  │
│  └───────┬───────┘  └──────┬───────┘  └─────────────┘  │
│          │                 │                             │
│  ┌───────▼─────────────────▼─────────────────────────┐  │
│  │              Orchestration Engine                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ Workflow │ │ Agent    │ │ Task State       │  │  │
│  │  │ Engine   │ │ Manager  │ │ Machine          │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │  │
│  │       │            │               │             │  │
│  │  ┌────▼─────┐ ┌────▼─────┐ ┌───────▼──────────┐  │  │
│  │  │ Pipeline │ │ CLI      │ │ Event            │  │  │
│  │  │ Builder  │ │ Adapters │ │ Dispatcher       │  │  │
│  │  └──────────┘ └────┬─────┘ └──────────────────┘  │  │
│  └────────────────────┼──────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │              Data Layer                             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ SQLAlch  │ │ Git      │ │ MCP Protocol     │  │  │
│  │  │ ORM      │ │ Adapter  │ │ Server           │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │  │
│  └───────┼────────────┼───────────────┼─────────────┘  │
└──────────┼────────────┼───────────────┼────────────────┘
           │            │               │
    ┌──────▼───┐  ┌─────▼──────┐  ┌─────▼──────────┐
    │  SQLite  │  │  Git Repo  │  │  Agent CLIs    │
    │  DB      │  │  (local)   │  │  (subprocess)  │
    └──────────┘  └────────────┘  └────────────────┘
```

### 6.2 核心技术选型 & 决策理由

#### 前端技术栈

| 技术 | 版本 | 理由 |
|------|------|------|
| **Electron** | 28.x | 跨平台桌面壳，成熟生态，大量企业级应用验证（VS Code, Figma, Slack） |
| **React** | 18.x | 生态最大、组件库最丰富、TypeScript 支持最好 |
| **TypeScript** | 5.x | 类型安全，大型项目必备 |
| **Vite** | 5.x | 极快的 HMR，比 Webpack 更适合 Electron 开发 |
| **ReactFlow** | 11.x | 最成熟的 React 节点图库，原生支持拖拽、缩放、连线，MIT 许可 |
| **Zustand** | 4.x | 极简状态管理，无 boilerplate，比 Redux 轻量 10x，天然支持 TypeScript |
| **TailwindCSS** | 3.x | 原子化 CSS，与组件化开发天然契合，自定义设计系统方便 |

**放弃的替代方案：**
- ~~Tauri~~ → 生态不如 Electron 成熟，Rust 门槛高，不适合 JS 全栈团队
- ~~Vue~~ → ReactFlow 等关键库的 Vue 版本滞后
- ~~Redux Toolkit~~ → 对于桌面应用过于复杂，Zustand 更轻量
- ~~D3.js~~ → 底层层级太低，需要大量自定义代码，ReactFlow 开箱即用

#### 后端技术栈

| 技术 | 版本 | 理由 |
|------|------|------|
| **Python 3.11** | 3.11+ | AI 生态第一语言，与 MCP 协议、AI CLI 工具天然兼容 |
| **FastAPI** | 0.115+ | 异步原生支持，自动 OpenAPI 文档，Pydantic 深度集成，WebSocket 一流支持 |
| **SQLAlchemy 2** | 2.0+ | 最成熟的 Python ORM，异步支持，迁移工具完善 |
| **aiosqlite** | 0.20+ | 纯异步 SQLite 驱动，不阻塞事件循环 |
| **Pydantic v2** | 2.7+ | Rust 核心，速度极快，与 FastAPI 无缝集成 |
| **httpx** | 0.27+ | 异步 HTTP 客户端，用于调用 Agent API |
| **Uvicorn** | 0.30+ | 最快的 ASGI 服务器，支持 HTTP/1.1 和 WebSocket |

**放弃的替代方案：**
- ~~Node.js Express~~ → AI 工具链以 Python 为主，用 Node 写适配器不如直接用 Python
- ~~Django~~ → 太重，同步模型不适合实时 WebSocket 场景
- ~~PostgreSQL~~ → 桌面应用不需要独立数据库服务，SQLite 零配置

### 6.3 Agent CLI 适配器设计

每个 Agent CLI 通过统一的适配器接口接入：

```python
class AgentAdapter(ABC):
    """Abstract base class for all Agent CLI adapters."""

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """Check if the CLI is installed and responsive."""
        ...

    @abstractmethod
    async def execute_task(
        self,
        task: Task,
        workspace: Path,
        context: ExecutionContext
    ) -> TaskResult:
        """Execute a task using the underlying CLI."""
        ...

    @abstractmethod
    async def stream_output(self, task_id: str) -> AsyncIterator[str]:
        """Stream real-time output from a running task."""
        ...

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        ...
```

**具体适配器实现：**

| CLI | 调用方式 | 特点 |
|-----|---------|------|
| Claude Code | `subprocess: claude --print "..."` | 通过 `--print` 模式获取结构化输出 |
| Codex | `subprocess: codex exec "..."` | 通过 `exec` 子命令执行任务 |
| Gemini CLI | `subprocess: gemini "..."` | 原生支持 JSON 输出模式 |
| Trae | `subprocess: trae run "..."` | 字节跳动内部工具标准接口 |
| OpenClaw | `subprocess: openclaw "..."` | 开源工具，可自定义 review rules |
| Hermess | `subprocess: hermess deploy "..."` | 专注于部署自动化 |
| OpenCode | `subprocess: opencode "..."` | 开源，可通过 MCP 协议扩展 |

### 6.4 工作流状态机

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
              ┌──────────┐     ┌──────────┐     ┌──────────┐    │
    START ──→ │ PENDING  │ ──→ │ RUNNING  │ ──→ │REVIEWING │    │
              └──────────┘     └────┬─────┘     └────┬─────┘    │
                    │               │                 │           │
                    │               │ fail            │ issues    │
                    ▼               ▼                 ▼           │
              ┌──────────┐     ┌──────────┐     ┌──────────┐    │
              │CANCELLED │     │  FAILED  │     │  FIXING  │────┘
              └──────────┘     └────┬─────┘     └──────────┘   (back to
                                    │                           RUNNING)
                                    │ retry
                                    ▼
                              ┌──────────┐
                              │ PENDING  │ (retry)
                              └──────────┘

              ┌──────────┐     ┌──────────┐
              │REVIEWING │ ──→ │ TESTING  │ (pass review → test)
              └──────────┘     └────┬─────┘
                                    │
                          ┌─────────┼─────────┐
                          │ pass    │ fail    │
                          ▼         ▼         │
                    ┌──────────┐ ┌──────────┐ │
                    │COMPLETED │ │  FIXING  │─┘
                    └──────────┘ └──────────┘
```

### 6.5 数据模型 ER 图

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   Project    │ 1──N │   AgentConfig     │ 1──N │    Task      │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ project_id   │       │ agent_id         │       │ task_id      │
│ name         │       │ name             │       │ title        │
│ description  │       │ role             │       │ status       │
│ repo_path    │       │ cli_name         │       │ agent_role   │
│ status       │       │ model_name       │       │ priority     │
│ workflow_    │       │ allowed_tools    │       │ result       │
│   config     │       │ project_id (FK)  │       │ project_id   │
│ created_at   │       │ is_active        │       │ agent_id     │
└──────────────┘       └──────────────────┘       │ parent_task  │
                                                   │ created_at   │
                                                   └──────────────┘
```

### 6.6 安全设计

| 层面 | 措施 |
|------|------|
| **数据存储** | SQLite 本地文件，不联网，不上传；API Key 通过环境变量注入，不存入数据库 |
| **Agent 执行** | 所有 Agent 在项目目录的沙箱内执行；工具权限按 Agent 角色最小化 |
| **网络** | CORS 限制 localhost；不做外部服务调用（Agent API 调用由用户配置） |
| **子进程** | Agent CLI 以子进程运行，超时自动 kill；限制文件系统访问范围 |

### 6.7 性能考量

| 场景 | 策略 |
|------|------|
| Agent 执行 | 异步子进程，不阻塞主线程 |
| Agent 间通信 | WebSocket 事件推送，避免 HTTP polling |
| 大型仓库 | lazy loading，按需读取文件 |
| ReactFlow 画布 | 虚拟化渲染，100+ 节点流畅 |
| SQLite | WAL 模式，读写并发 |

---

## 附录：市场分析与竞品对比

### 现有方案分析

| 方案 | 类型 | 优势 | 劣势 |
|------|------|------|------|
| **Claude Code** | 单 Agent CLI | 强大的代码理解，大上下文 | 无团队协作，无审查机制 |
| **Cursor** | AI IDE | 深度集成编辑器 | 单 Agent 模式，不支持多角色分工 |
| **GitHub Copilot** | AI 补全 | VS Code 集成，低延迟 | 补全级别，不能执行复杂任务 |
| **Devin** | AI 软件工程师 | 端到端自动化 | 闭源、云端、昂贵、不可定制 |
| **CrewAI** | Agent 框架（Python） | 多 Agent 协作，灵活 | 无 GUI，无桌面应用，需编程 |
| **AutoGen** | Agent 框架（Microsoft） | 对话式多 Agent | 无 GUI，配置复杂 |
| **AgentForge** | 桌面 GUI 编排平台 | **可视化 + 多 Agent + 本地运行** | 新产品，生态待建设 |

### AgentForge 的差异化

1. **Desktop-first**：CrewAI/AutoGen 是纯 Python 框架，AgentForge 是桌面 GUI，降低使用门槛
2. **Multi-model**：不是绑定单一模型，而是聚合 Claude、Gemini、Codex 等不同模型的 Agent 组成**跨模型团队**
3. **Opinionated workflow**：内置软件工程最佳实践（Code Review、CI/CD），不是通用 Agent 框架
4. **Local & Private**：所有数据在本地，不上传云端

---

> **Document Version**: 1.0
> **Last Updated**: 2024-06-26
> **Author**: AgentForge Project Team
> **License**: MIT
