/**
 * MCP (Model Context Protocol) Service
 * ====================================
 * Client-side service for interacting with MCP servers.
 *
 * Responsibilities:
 * - Connecting to MCP server endpoints
 * - Discovering available tools, resources, and prompts
 * - Calling MCP tools on behalf of the frontend
 * - Managing MCP server connections lifecycle
 */

import type { ApiResponse } from "../types/common";

// ---------------------------------------------------------------------------
// MCP Types
// ---------------------------------------------------------------------------

/**
 * MCP server connection configuration.
 */
export interface McpServerConfig {
  /** Unique identifier for this MCP server connection */
  id: string;

  /** Display name */
  name: string;

  /** Server type: stdio process or HTTP SSE */
  transport: "stdio" | "sse";

  /** Command to launch (stdio transport) or URL (sse transport) */
  commandOrUrl: string;

  /** Command arguments (stdio only) */
  args?: string[];

  /** Environment variables for the server process (stdio only) */
  env?: Record<string, string>;

  /** Whether this server is enabled */
  enabled: boolean;

  /** Connection timeout in milliseconds */
  timeoutMs: number;
}

/**
 * MCP tool definition as advertised by a server.
 */
export interface McpTool {
  /** Unique tool name within the server */
  name: string;

  /** Human-readable description */
  description: string;

  /** JSON Schema for the tool's input parameters */
  inputSchema: Record<string, unknown>;
}

/**
 * MCP resource definition.
 */
export interface McpResource {
  /** Resource URI */
  uri: string;

  /** Display name */
  name: string;

  /** Optional description */
  description?: string;

  /** MIME type of the resource content */
  mimeType?: string;
}

/**
 * MCP prompt template definition.
 */
export interface McpPrompt {
  /** Prompt name */
  name: string;

  /** Optional description */
  description?: string;

  /** List of arguments the prompt accepts */
  arguments?: McpPromptArgument[];
}

/**
 * MCP prompt argument definition.
 */
export interface McpPromptArgument {
  /** Argument name */
  name: string;

  /** Optional description */
  description?: string;

  /** Whether the argument is required */
  required: boolean;
}

/**
 * Result of calling an MCP tool.
 */
export interface McpToolResult {
  /** Whether the call succeeded */
  isError: boolean;

  /** Content blocks returned by the tool */
  content: McpContentBlock[];
}

/**
 * A single content block in an MCP response.
 */
export interface McpContentBlock {
  /** Content type */
  type: "text" | "image" | "resource";

  /** Text content (when type is "text") */
  text?: string;

  /** Image data as base64 (when type is "image") */
  data?: string;

  /** MIME type (when type is "image") */
  mimeType?: string;

  /** Resource reference (when type is "resource") */
  resource?: {
    uri: string;
    mimeType?: string;
    text?: string;
  };
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

let BASE_URL = "http://127.0.0.1:18090/api/v1";

export function setMcpServiceBaseUrl(url: string): void {
  BASE_URL = url.replace(/\/$/, "");
}

// ---------------------------------------------------------------------------
// Request Helper
// ---------------------------------------------------------------------------

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers as Record<string, string>),
    },
  });
  if (!response.ok) {
    let msg = `HTTP ${response.status}`;
    try {
      const body: ApiResponse = await response.json();
      msg = body.error || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  const result: ApiResponse<T> = await response.json();
  if (!result.success) throw new Error(result.error || "Unknown error");
  return result.data as T;
}

// ---------------------------------------------------------------------------
// MCP Server Management
// ---------------------------------------------------------------------------

/**
 * Connect to an MCP server.
 *
 * @param config - MCP server config
 * @returns The registered server config
 */
export async function connectMcpServer(
  config: McpServerConfig
): Promise<McpServerConfig> {
  return request<McpServerConfig>("/mcp/servers", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

/**
 * Disconnect from an MCP server.
 *
 * @param serverId - Server ID
 */
export async function disconnectMcpServer(serverId: string): Promise<void> {
  return request<void>(`/mcp/servers/${serverId}`, {
    method: "DELETE",
  });
}

/**
 * List all connected MCP servers.
 */
export async function listMcpServers(): Promise<McpServerConfig[]> {
  return request<McpServerConfig[]>("/mcp/servers");
}

// ---------------------------------------------------------------------------
// Tool Discovery & Execution
// ---------------------------------------------------------------------------

/**
 * List all available tools from an MCP server.
 *
 * @param serverId - MCP server ID
 * @returns Array of tool definitions
 */
export async function listTools(serverId: string): Promise<McpTool[]> {
  return request<McpTool[]>(`/mcp/servers/${serverId}/tools`);
}

/**
 * Call a tool on an MCP server.
 *
 * @param serverId - MCP server ID
 * @param toolName - Name of the tool to call
 * @param args - Tool arguments
 * @returns The tool call result
 */
export async function callTool(
  serverId: string,
  toolName: string,
  args: Record<string, unknown>
): Promise<McpToolResult> {
  return request<McpToolResult>(`/mcp/servers/${serverId}/tools/call`, {
    method: "POST",
    body: JSON.stringify({ tool: toolName, arguments: args }),
  });
}

// ---------------------------------------------------------------------------
// Resource & Prompt Discovery
// ---------------------------------------------------------------------------

/**
 * List resources exposed by an MCP server.
 *
 * @param serverId - MCP server ID
 */
export async function listResources(
  serverId: string
): Promise<McpResource[]> {
  return request<McpResource[]>(`/mcp/servers/${serverId}/resources`);
}

/**
 * Read a resource from an MCP server.
 *
 * @param serverId - MCP server ID
 * @param uri - Resource URI
 */
export async function readResource(
  serverId: string,
  uri: string
): Promise<McpContentBlock[]> {
  return request<McpContentBlock[]>(
    `/mcp/servers/${serverId}/resources/read`,
    {
      method: "POST",
      body: JSON.stringify({ uri }),
    }
  );
}

/**
 * List prompt templates from an MCP server.
 *
 * @param serverId - MCP server ID
 */
export async function listPrompts(serverId: string): Promise<McpPrompt[]> {
  return request<McpPrompt[]>(`/mcp/servers/${serverId}/prompts`);
}

/**
 * Get a prompt from an MCP server with filled-in arguments.
 *
 * @param serverId - MCP server ID
 * @param promptName - Prompt template name
 * @param args - Argument values
 */
export async function getPrompt(
  serverId: string,
  promptName: string,
  args: Record<string, string>
): Promise<{ messages: McpContentBlock[] }> {
  return request<{ messages: McpContentBlock[] }>(
    `/mcp/servers/${serverId}/prompts/get`,
    {
      method: "POST",
      body: JSON.stringify({ name: promptName, arguments: args }),
    }
  );
}
