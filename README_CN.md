# AgentForge

<div align="center">

**多Agent聚合协作GUI平台**

*组建AI智能体团队，协作完成软件开发项目*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Electron](https://img.shields.io/badge/Electron-28.x-47848F?logo=electron)](https://www.electronjs.org/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

</div>

---

## 项目概述

**AgentForge** 是一个基于 **Electron + React + Python FastAPI** 的桌面应用程序，让开发者能够配置多个 AI 智能体（Agent）——每个拥有不同角色和能力——组成团队，自主协作完成复杂的软件工程项目。相当于给每个开发者配备一支运行在本地的 AI 特战队。

### 痛点分析

现代 AI 编程智能体（Claude Code、Codex、Cursor 等）各自都很强大，但它们存在关键局限：

- **单智能体脆弱性**：一个智能体陷入 Bug 循环后无法自救。
- **缺乏审查机制**：生成的代码没有第二双眼睛把关。
- **角色混淆**：单个智能体同时扮演开发者、审查者、测试者和部署者——哪个都做不精。
- **配置地狱**：每个 CLI 智能体需要单独设置、API 密钥和工具访问权限。
- **无法协作**：没有内置机制让多个专业智能体在同一个代码库上协同工作。

### 解决方案

AgentForge 通过编排一支**专业 AI 智能体团队**来解决这些问题，团队按照结构化工作流协作：

```
开发者智能体 → 审查者智能体 → 修复者智能体 → 测试者智能体 → 部署者智能体
      ↑                                                          |
      └─────────────────── 反馈循环 ────────────────────────────┘
```

每个智能体扮演专门角色，使用各自底层的 AI 模型和工具集，通过 AgentForge 编排引擎进行通信。结果：更高的代码质量、更少的 Bug、以及大幅减少的人工干预。

---

## 5W1H 分析

| 维度 | 详情 |
|------|------|
| **WHAT（是什么）** | 面向本地开发环境的多智能体协作编排 GUI 平台 |
| **WHY（为什么）** | 单智能体编程工具出 Bug、缺乏审查、无法自愈；角色分工的多智能体团队能系统性地解决这些弱点 |
| **WHO（给谁用）** | 软件开发者、工程团队、独立开发者、任何希望 AI 辅助交付项目并保证质量的人 |
| **WHERE（在哪用）** | 本地 Windows / macOS / Linux 桌面环境，以 Electron 应用形式运行 |
| **WHEN（何时用）** | 覆盖整个软件开发生命周期——从项目脚手架到生产部署 |
| **HOW（怎么做）** | Electron + React 构建 GUI 层；Python FastAPI 后端负责智能体编排、工作流状态管理和基于 WebSocket 的实时通信 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Electron 外壳                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              React 前端 (Vite + TS)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │  项目    │  │ 智能体   │ │   工作流画布     │  │  │
│  │  │  管理器  │  │ 注册中心 │ │  (ReactFlow)     │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │  HTTP + WebSocket                 │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │           Python FastAPI 后端                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │  工作流  │  │ 智能体   │ │  任务队列与     │  │  │
│  │  │  引擎    │  │ 管理器   │ │  状态机         │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │  MCP     │  │  Git     │ │  日志与         │  │  │
│  │  │  协议    │  │  适配器  │ │  监控           │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │  子进程 / API                     │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │           AI 智能体运行时 (CLI)                    │  │
│  │  Claude Code │ Codex │ Trae │ OpenClaw │ Gemini   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 协作流程

```
1. 用户创建项目并定义需求
         │
         ▼
2. 开发者智能体 生成/编辑代码
         │
         ▼
3. 审查者智能体 检查变更，标记问题
         │
         ▼
4. 修复者智能体 解决标记的问题
         │
         ▼
5. 测试者智能体 运行测试并验证
         │
    ┌────┴────┐
    │  通过？ │
    └────┬────┘
    否   │   是
    ▼    │    ▼
回到第2步│ 部署者智能体
         │ 打包并部署
```

---

## 支持的智能体

| 智能体 | 角色 | 底层 CLI | 优势 |
|-------|------|----------|------|
| **Claude Code** | 开发者 / 审查者 | `claude` | 强大的代码理解能力，超大上下文窗口 |
| **Codex** | 开发者 / 修复者 | `codex` | OpenAI 驱动，快速迭代 |
| **Trae** | 开发者 / 测试者 | `trae` | 字节跳动生态，代码生成能力强 |
| **OpenClaw** | 审查者 / 修复者 | `openclaw` | 开源，可自定义审查规则 |
| **Hermess** | 开发者 / 部署者 | `hermess` | 部署自动化，CI/CD 集成 |
| **OpenCode** | 开发者 / 修复者 | `opencode` | 开源编码智能体，可扩展 |
| **Gemini CLI** | 审查者 / 测试者 | `gemini` | Google 生态，分析能力强大 |

智能体可以自由组合——你完全可以用 Claude Code 做开发、Gemini CLI 做审查、Codex 做修复，打造一个跨模型团队，发挥每个模型的独特优势。

---

## 功能特性

### 核心功能

- **可视化工作流设计器**：在 ReactFlow 画布上拖拽智能体节点，设计协作流水线。
- **智能体注册中心**：注册和配置多个 AI 智能体，包括角色分配、API 密钥和工具访问权限。
- **实时协作监控**：通过 WebSocket 实时观看智能体工作——代码生成、审查和修复过程一目了然。
- **Git 原生集成**：所有智能体工作在 Git 跟踪目录中进行，支持自动分支和类 PR 审查流程。
- **任务状态机**：健壮的状态跟踪（pending → running → reviewing → fixing → testing → completed / failed），支持重试和回滚。

### 质量保障

- **自动代码审查**：审查者智能体检查每次变更后才允许合入代码库。
- **自动修复流水线**：测试失败或审查标记自动触发修复者智能体介入。
- **测试生成**：测试者智能体可以为项目生成和维护测试套件。
- **质量关卡**：每个工作流阶段可配置通过/失败条件。

### 开发者体验

- **项目模板**：预置 Web 应用、CLI 工具、库、微服务等工作流模板。
- **热重载**：开发时前端改动即时生效。
- **暗色模式**：内置暗色主题，深夜编码不刺眼。
- **跨平台**：Windows、macOS、Linux 统一体验。

---

## 技术栈

### 前端
| 技术 | 用途 |
|-----------|---------|
| **Electron 28** | 桌面应用外壳 |
| **React 18** | UI 框架 |
| **TypeScript 5** | 类型安全的 JavaScript |
| **Vite 5** | 构建工具和开发服务器 |
| **ReactFlow** | 可视化工作流 / 节点图画布 |
| **Zustand** | 轻量级状态管理 |
| **TailwindCSS 3** | 实用优先的 CSS 框架 |

### 后端
| 技术 | 用途 |
|-----------|---------|
| **Python 3.11+** | 运行时环境 |
| **FastAPI** | REST API + WebSocket 服务端 |
| **Pydantic v2** | 数据验证与序列化 |
| **SQLAlchemy 2** | SQLite ORM |
| **aiosqlite** | 异步 SQLite 驱动 |
| **httpx** | 异步 HTTP 客户端，用于智能体 API 调用 |
| **MCP 协议** | 模型上下文协议，智能体-工具集成 |
| **Uvicorn** | ASGI 服务器 |

---

## 快速开始

### 前置条件

- **Node.js** >= 18.0.0
- **Python** >= 3.11
- **Git** >= 2.40
- **pnpm** >= 8（推荐）或 npm >= 9

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/agentforge.git
cd agentforge

# 安装前端依赖
pnpm install

# 创建 Python 虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装后端依赖
pip install -r backend/requirements.txt

# 复制并配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API 密钥和偏好设置
```

### 开发运行

```bash
# 启动后端服务（终端 1）
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8765

# 启动 Electron + Vite 开发服务器（终端 2）
pnpm dev
```

### 构建打包

```bash
# 为当前平台构建
pnpm build

# 为特定平台构建
pnpm build:win    # Windows
pnpm build:mac    # macOS
pnpm build:linux  # Linux
```

---

## 项目结构

```
agentforge/
├── README.md                    # 本文件（英文版）
├── README_CN.md                 # 中文版 README
├── LICENSE                      # MIT 许可证
├── package.json                 # Node.js 依赖和脚本配置
├── tsconfig.json                # TypeScript 配置
├── vite.config.ts              # Vite 构建配置
├── tailwind.config.ts          # TailwindCSS 设计系统
├── postcss.config.js           # PostCSS 插件配置
├── electron-builder.yml        # Electron 打包配置
├── .gitignore                  # Git 忽略规则
├── docs/
│   ├── 5W1H_ANALYSIS.md        # 详细 5W1H 分析（双语）
│   └── ARCHITECTURE.md         # 技术架构文档
├── src/                        # React 前端源码
│   ├── main/                   # Electron 主进程
│   ├── renderer/               # React 渲染进程
│   │   ├── components/         # 可复用 UI 组件
│   │   ├── pages/              # 路由页面
│   │   ├── stores/             # Zustand 状态仓库
│   │   ├── hooks/              # 自定义 React Hooks
│   │   ├── layouts/            # 页面布局组件
│   │   └── styles/             # 全局样式
│   └── preload/                # Electron 预加载脚本
├── backend/                    # Python FastAPI 后端
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py              # 配置管理
│   ├── requirements.txt       # Python 依赖清单
│   ├── models/                # SQLAlchemy 数据模型
│   ├── routers/               # API 路由处理
│   ├── services/              # 业务逻辑层
│   └── engine/                # 智能体编排引擎
└── tests/                     # 测试套件
```

---

## 智能体配置

AgentForge 使用声明式 YAML 格式的智能体注册表。每个智能体需定义角色、能力和工具访问权限：

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

## 工作流示例

以下是一个实际示例，展示 AgentForge 如何处理一个功能需求：

1. **用户提交**："为 Express API 添加限流中间件"
2. **开发者智能体（Claude Code）**：读取现有中间件，生成限流代码，编写测试。
3. **审查者智能体（Gemini CLI）**：检查 Diff，标记限流器中的潜在竞态条件。
4. **修复者智能体（Codex）**：接收审查意见，重构限流器使用原子计数器，更新测试。
5. **测试者智能体（Trae）**：运行全量测试套件——全部通过。额外生成突发流量边界测试。
6. **部署者智能体（Hermess）**：提交变更，创建 Git 标签，触发 CI/CD 流水线。

用户只写了一行需求，AgentForge 处理了其余一切。

---

## 参与贡献

欢迎贡献！请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交变更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

## 许可证

本项目采用 MIT 许可证——详见 [LICENSE](LICENSE) 文件。

---

## 致谢

AgentForge 基于以下开源社区的卓越工作：

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) —— Anthropic
- [Codex](https://github.com/openai/codex) —— OpenAI
- [ReactFlow](https://reactflow.dev/) —— xyflow
- [FastAPI](https://fastapi.tiangolo.com/) —— Sebastián Ramírez
- [Electron](https://www.electronjs.org/) —— OpenJS Foundation

---

<div align="center">
  <strong>AgentForge</strong> —— 锻造你的 AI 团队，交付更优质的软件。
</div>
