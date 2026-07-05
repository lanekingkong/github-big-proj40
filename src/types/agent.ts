/**
 * Agent Type Definitions
 * ======================
 * Core types for Agent configuration, roles, status lifecycle,
 * and capability declarations.
 *
 * These types are shared between the React frontend and serve as
 * the contract with the Python backend API.
 */

// ---------------------------------------------------------------------------
// Agent Role Enumeration
// ---------------------------------------------------------------------------

/**
 * Predefined roles an Agent can assume within a Forge pipeline.
 * Each role implies a set of default capabilities and behavior.
 */
export enum AgentRole {
  /** Writes code, implements features, generates boilerplate */
  Developer = "Developer",

  /** Reviews code, provides feedback, catches bugs */
  Reviewer = "Reviewer",

  /** Fixes identified issues, applies patches, resolves conflicts */
  Fixer = "Fixer",

  /** Writes and executes tests, validates functionality */
  Tester = "Tester",

  /** Handles deployment, builds, and release management */
  Deployer = "Deployer",

  /** General-purpose agent with no specialization */
  Generalist = "Generalist",
}

// ---------------------------------------------------------------------------
// Agent Status
// ---------------------------------------------------------------------------

/**
 * Lifecycle status of an Agent instance.
 */
export enum AgentStatus {
  /** Agent is configured but not yet started */
  Idle = "idle",

  /** Agent is initializing (loading models, connecting services) */
  Initializing = "initializing",

  /** Agent is ready to receive tasks */
  Online = "online",

  /** Agent is actively working on a task */
  Busy = "busy",

  /** Agent encountered an error and needs attention */
  Error = "error",

  /** Agent has been deliberately paused */
  Paused = "paused",

  /** Agent is shutting down */
  Stopping = "stopping",

  /** Agent is disconnected or unreachable */
  Offline = "offline",
}

// ---------------------------------------------------------------------------
// Agent Capability
// ---------------------------------------------------------------------------

/**
 * Granular capability flag indicating what an Agent can do.
 * Used for capability-based routing of tasks.
 */
export enum AgentCapability {
  /** Generate or edit source code */
  CodeGeneration = "code_generation",

  /** Perform code review and static analysis */
  CodeReview = "code_review",

  /** Write and execute unit/integration tests */
  Testing = "testing",

  /** Debug and fix code issues */
  Debugging = "debugging",

  /** Build and compile projects */
  Build = "build",

  /** Deploy to staging/production environments */
  Deploy = "deploy",

  /** Generate documentation */
  Documentation = "documentation",

  /** Run security analysis */
  SecurityAudit = "security_audit",

  /** Execute shell commands */
  ShellExecution = "shell_execution",

  /** Read/write files on the local filesystem */
  FileAccess = "file_access",

  /** Make HTTP API calls */
  ApiAccess = "api_access",

  /** Interact with git repositories */
  GitOperations = "git_operations",

  /** Handle merge conflict resolution */
  ConflictResolution = "conflict_resolution",
}

// ---------------------------------------------------------------------------
// Model Configuration
// ---------------------------------------------------------------------------

/**
 * Configuration for the underlying language model backing an Agent.
 */
export interface ModelConfig {
  /** Provider name (e.g., "openai", "anthropic", "openrouter") */
  provider: string;

  /** Model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514") */
  model: string;

  /** API endpoint (optional, for custom deployments) */
  apiBase?: string;

  /** API key reference (never store raw keys — use key vault) */
  apiKeyRef?: string;

  /** Temperature (0.0 – 2.0). Controls randomness. */
  temperature: number;

  /** Maximum tokens to generate per response */
  maxTokens?: number;

  /** Top-p nucleus sampling (0.0 – 1.0) */
  topP?: number;

  /** Additional model parameters passed as-is */
  extraParams?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Tool Configuration
// ---------------------------------------------------------------------------

/**
 * A single tool or MCP server that an Agent can use.
 */
export interface ToolConfig {
  /** Unique tool name */
  name: string;

  /** Description for the model's tool-use prompt */
  description: string;

  /** Whether this tool is enabled */
  enabled: boolean;

  /** If provided via MCP, the MCP server name */
  mcpServer?: string;

  /** Tool parameters schema (JSON Schema) */
  parameters?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Agent Configuration
// ---------------------------------------------------------------------------

/**
 * Full configuration for an Agent instance.
 * This is the primary data object for agent CRUD operations.
 */
export interface AgentConfig {
  /** Unique identifier (UUID) */
  id: string;

  /** Human-readable display name */
  name: string;

  /** Assigned role determining default behavior */
  role: AgentRole;

  /** Optional description for the team dashboard */
  description?: string;

  /** Current lifecycle status */
  status: AgentStatus;

  /** Model configuration */
  model: ModelConfig;

  /** Granular capability flags */
  capabilities: AgentCapability[];

  /** Tools available to this agent */
  tools: ToolConfig[];

  /** Custom system prompt override */
  systemPrompt?: string;

  /** Maximum concurrent tasks this agent can handle */
  maxConcurrentTasks: number;

  /** Priority (higher = more important, default 0) */
  priority: number;

  /** Tags for grouping and filtering */
  tags: string[];

  /** Creation timestamp (ISO 8601) */
  createdAt: string;

  /** Last modification timestamp (ISO 8601) */
  updatedAt: string;
}

// ---------------------------------------------------------------------------
// Agent Instance (Runtime)
// ---------------------------------------------------------------------------

/**
 * Runtime representation of an Agent instance, extending the config
 * with live status information.
 */
export interface AgentInstance {
  /** Reference to the AgentConfig ID */
  configId: string;

  /** Live agent configuration (may be enriched at runtime) */
  config: AgentConfig;

  /** Current task ID if busy, null otherwise */
  currentTaskId: string | null;

  /** Uptime in seconds since last Online transition */
  uptime: number;

  /** Count of tasks completed in the current session */
  tasksCompleted: number;

  /** Count of errors encountered in the current session */
  errorCount: number;

  /** Last heartbeat timestamp (ISO 8601) */
  lastHeartbeat: string;
}

// ---------------------------------------------------------------------------
// Agent Registration DTO
// ---------------------------------------------------------------------------

/**
 * Data transfer object for registering a new Agent.
 */
export interface AgentRegistrationDTO {
  name: string;
  role: AgentRole;
  description?: string;
  model: ModelConfig;
  capabilities: AgentCapability[];
  tools?: ToolConfig[];
  systemPrompt?: string;
  maxConcurrentTasks?: number;
  tags?: string[];
}

// ---------------------------------------------------------------------------
// Agent Update DTO
// ---------------------------------------------------------------------------

/**
 * Data transfer object for updating an existing Agent.
 * All fields are optional — only provided fields are updated.
 */
export interface AgentUpdateDTO {
  name?: string;
  role?: AgentRole;
  description?: string;
  model?: Partial<ModelConfig>;
  capabilities?: AgentCapability[];
  tools?: ToolConfig[];
  systemPrompt?: string;
  maxConcurrentTasks?: number;
  priority?: number;
  tags?: string[];
}
