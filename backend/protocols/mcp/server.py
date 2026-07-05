"""
MCP Server Implementation
=========================
Model Context Protocol (MCP) server for the AgentForge platform.

Enables external AI agents and tools to interact with AgentForge through
the standardized MCP protocol. Supports registration of:
- Tools: Callable functions exposed to external agents
- Resources: Data sources accessible via URI templates
- Prompts: Reusable prompt templates for AI interactions

Based on the Anthropic MCP specification (2024-11-05).
"""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from utils.logger import get_logger

__all__ = ["MCPServer", "MCPTool", "MCPResource", "MCPPrompt"]

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Data Types
# ------------------------------------------------------------------

@dataclass
class MCPTool:
    """
    Represents a tool that can be called by MCP clients.

    A tool is a callable function with a JSON Schema describing its parameters.

    Attributes:
        name: Unique tool name (snake_case convention).
        description: Human-readable description shown to AI models.
        input_schema: JSON Schema for the tool's parameters.
        handler: Async callable that executes the tool logic.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class MCPResource:
    """
    Represents a data resource accessible via URI templates.

    Resources provide structured data to AI models without requiring
    tool invocation.

    Attributes:
        uri: URI template for the resource (e.g., 'project://{project_id}/tasks').
        name: Human-readable resource name.
        description: Description of the resource content.
        mime_type: Expected MIME type of the resource (e.g., 'application/json').
        handler: Async callable that resolves the URI to data.
    """

    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable[..., Any]


@dataclass
class MCPPrompt:
    """
    Represents a reusable prompt template for AI interactions.

    Prompts can include dynamic arguments resolved at invocation time.

    Attributes:
        name: Unique prompt name.
        description: When this prompt should be used.
        arguments: List of argument definitions with name, description, required flag.
        handler: Async callable that generates the prompt messages.
    """

    name: str
    description: str
    arguments: list[dict[str, Any]]
    handler: Callable[..., Any]


# ------------------------------------------------------------------
# MCP Server
# ------------------------------------------------------------------

class MCPServer:
    """
    Model Context Protocol server implementation.

    Handles the lifecycle of MCP tools, resources, and prompts.
    Provides JSON-RPC 2.0 compliant request handling over stdio,
    HTTP/SSE, or WebSocket transports.

    Transport support:
        - stdio (for CLI-based agents)
        - HTTP with Server-Sent Events (SSE) for web-based agents
        - WebSocket for persistent bidirectional connections

    Usage:
        server = MCPServer(name="agentforge", version="1.0.0")
        server.register_tool(my_tool)
        await server.run_stdio()
    """

    def __init__(
        self,
        name: str = "agentforge",
        version: str = "1.0.0",
    ) -> None:
        """
        Initialize the MCP server.

        Args:
            name: Server name reported in initialize response.
            version: Server version string.
        """
        self.name = name
        self.version = version

        # Registered capabilities
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}

        # Server state
        self._initialized: bool = False
        self._client_info: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(self, tool: MCPTool) -> None:
        """
        Register a callable tool that MCP clients can invoke.

        Args:
            tool: The MCPTool instance to register.

        Raises:
            ValueError: If a tool with the same name already exists.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info(f"MCP tool registered: {tool.name}")

    def register_resource(self, resource: MCPResource) -> None:
        """
        Register a data resource accessible via URI.

        Args:
            resource: The MCPResource instance to register.

        Raises:
            ValueError: If a resource with the same URI already exists.
        """
        if resource.uri in self._resources:
            raise ValueError(f"Resource '{resource.uri}' is already registered")
        self._resources[resource.uri] = resource
        logger.info(f"MCP resource registered: {resource.uri}")

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """
        Register a reusable prompt template.

        Args:
            prompt: The MCPPrompt instance to register.

        Raises:
            ValueError: If a prompt with the same name already exists.
        """
        if prompt.name in self._prompts:
            raise ValueError(f"Prompt '{prompt.name}' is already registered")
        self._prompts[prompt.name] = prompt
        logger.info(f"MCP prompt registered: {prompt.name}")

    def unregister_tool(self, name: str) -> bool:
        """
        Remove a registered tool.

        Args:
            name: The tool name to unregister.

        Returns:
            True if the tool was removed, False if it didn't exist.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"MCP tool unregistered: {name}")
            return True
        return False

    # ------------------------------------------------------------------
    # Capability Listing
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with their schemas.

        Returns:
            List of tool descriptors suitable for MCP tool listing.
        """
        tools_list: list[dict[str, Any]] = []
        for tool in self._tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            })
        return tools_list

    def list_resources(self) -> list[dict[str, Any]]:
        """
        List all registered resources.

        Returns:
            List of resource descriptors.
        """
        resources_list: list[dict[str, Any]] = []
        for resource in self._resources.values():
            resources_list.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type,
            })
        return resources_list

    def list_prompts(self) -> list[dict[str, Any]]:
        """
        List all registered prompts with their argument schemas.

        Returns:
            List of prompt descriptors.
        """
        prompts_list: list[dict[str, Any]] = []
        for prompt in self._prompts.values():
            prompts_list.append({
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            })
        return prompts_list

    # ------------------------------------------------------------------
    # JSON-RPC Request Handling
    # ------------------------------------------------------------------

    async def handle_request(self, raw_request: str | bytes) -> str:
        """
        Handle a raw JSON-RPC 2.0 request.

        Parses the request, dispatches to the appropriate handler,
        and returns the JSON-RPC response.

        Supported methods:
            - initialize: Client handshake
            - tools/list: List available tools
            - tools/call: Invoke a tool
            - resources/list: List available resources
            - resources/read: Read a resource by URI
            - prompts/list: List available prompts
            - prompts/get: Get a prompt template

        Args:
            raw_request: Raw JSON-RPC request string or bytes.

        Returns:
            JSON-RPC 2.0 response string.
        """
        try:
            request: dict[str, Any] = json.loads(raw_request)
        except json.JSONDecodeError as exc:
            return self._error_response(
                None, -32700, f"Parse error: {exc}"
            )

        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            result = await self._dispatch(method, params)
            return self._success_response(request_id, result)
        except Exception as exc:
            logger.error(f"MCP request error ({method}): {exc}")
            return self._error_response(request_id, -32603, str(exc))

    async def _dispatch(
        self,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        """
        Dispatch a method call to the appropriate handler.

        Args:
            method: The JSON-RPC method name.
            params: Method parameters.

        Returns:
            Method result.

        Raises:
            ValueError: For unknown or unimplemented methods.
        """
        match method:
            case "initialize":
                return await self._handle_initialize(params)
            case "initialized":
                return {}  # Notification — no response needed
            case "tools/list":
                return {"tools": self.list_tools()}
            case "tools/call":
                return await self._handle_tool_call(params)
            case "resources/list":
                return {"resources": self.list_resources()}
            case "resources/read":
                return await self._handle_resource_read(params)
            case "prompts/list":
                return {"prompts": self.list_prompts()}
            case "prompts/get":
                return await self._handle_prompt_get(params)
            case "ping":
                return {}
            case _:
                raise ValueError(f"Unknown method: {method}")

    async def _handle_initialize(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle the initialize handshake from a client.

        Args:
            params: Client initialization parameters including protocol version.

        Returns:
            Server capabilities and info.
        """
        self._client_info = params.get("clientInfo", {})
        self._initialized = True

        logger.info(
            f"MCP client initialized: {self._client_info.get('name', 'unknown')} "
            f"v{self._client_info.get('version', '?')}"
        )

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": len(self._tools) > 0},
                "resources": {"subscribe": False, "listChanged": len(self._resources) > 0},
                "prompts": {"listChanged": len(self._prompts) > 0},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }

    async def _handle_tool_call(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a tools/call request.

        Args:
            params: Must contain 'name' (tool name) and 'arguments' (tool params).

        Returns:
            Tool execution result.

        Raises:
            ValueError: If the tool is not found.
        """
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        logger.info(f"MCP tool call: {tool_name}")
        try:
            result = await tool.handler(**arguments) if inspect.iscoroutinefunction(tool.handler) else tool.handler(**arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }
                ]
            }
        except Exception as exc:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool '{tool_name}': {exc}",
                    }
                ],
                "isError": True,
            }

    async def _handle_resource_read(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a resources/read request.

        Args:
            params: Must contain 'uri' of the resource to read.

        Returns:
            Resource content.

        Raises:
            ValueError: If the resource is not found.
        """
        uri = params.get("uri", "")

        # Simple URI matching (exact match)
        resource = self._resources.get(uri)
        if resource is None:
            raise ValueError(f"Resource not found: {uri}")

        logger.info(f"MCP resource read: {uri}")
        data = await resource.handler(uri) if inspect.iscoroutinefunction(resource.handler) else resource.handler(uri)

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "text": json.dumps(data, ensure_ascii=False, default=str),
                }
            ]
        }

    async def _handle_prompt_get(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a prompts/get request.

        Args:
            params: Must contain 'name' (prompt name) and optional 'arguments'.

        Returns:
            Generated prompt messages.

        Raises:
            ValueError: If the prompt is not found.
        """
        prompt_name = params.get("name", "")
        arguments = params.get("arguments", {})

        prompt = self._prompts.get(prompt_name)
        if prompt is None:
            raise ValueError(f"Prompt not found: {prompt_name}")

        logger.info(f"MCP prompt get: {prompt_name}")
        messages = await prompt.handler(**arguments) if inspect.iscoroutinefunction(prompt.handler) else prompt.handler(**arguments)

        return {"messages": messages}

    # ------------------------------------------------------------------
    # JSON-RPC Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _success_response(request_id: Any, result: Any) -> str:
        """
        Build a JSON-RPC 2.0 success response.

        Args:
            request_id: The original request ID.
            result: The method result.

        Returns:
            JSON-RPC 2.0 response string.
        """
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def _error_response(
        request_id: Any,
        code: int,
        message: str,
    ) -> str:
        """
        Build a JSON-RPC 2.0 error response.

        Args:
            request_id: The original request ID.
            code: Error code (standard JSON-RPC or custom).
            message: Human-readable error message.

        Returns:
            JSON-RPC 2.0 error response string.
        """
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Transport Runners
    # ------------------------------------------------------------------

    async def run_stdio(self) -> None:
        """
        Run the MCP server over stdio transport.

        Reads JSON-RPC requests line-by-line from stdin and writes
        responses to stdout. Stderr is reserved for logging.

        This is the primary transport for CLI-based MCP clients.
        """
        import sys

        logger.info("MCP server starting on stdio transport")

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break  # EOF

                request_str = line.decode("utf-8").strip()
                if not request_str:
                    continue

                response_str = await self.handle_request(request_str)
                sys.stdout.write(response_str + "\n")
                sys.stdout.flush()

            except Exception as exc:
                logger.error(f"Stdio transport error: {exc}")
                break

        logger.info("MCP server stdio transport stopped")

    async def run_http(
        self,
        host: str = "127.0.0.1",
        port: int = 8090,
    ) -> None:
        """
        Run the MCP server over HTTP with SSE transport.

        Provides two endpoints:
            POST /mcp  → JSON-RPC request handling
            GET  /sse  → Server-Sent Events stream

        Args:
            host: Bind address.
            port: Bind port.
        """
        logger.info(f"MCP server starting on HTTP transport ({host}:{port})")
        # HTTP/SSE transport implementation depends on the web framework
        # integration. Placeholder for now — actual transport is handled
        # by the FastAPI integration layer.
        raise NotImplementedError(
            "HTTP transport requires FastAPI integration. "
            "Use stdio transport for standalone operation."
        )
