"""
MCP Client Implementation
=========================
Model Context Protocol (MCP) client for connecting to external MCP servers.

Enables AgentForge agents to interact with external tools, resources, and
prompts exposed by third-party MCP-compatible servers. Supports:
- Server capability negotiation via initialize handshake
- Tool discovery and invocation
- Resource reading via URI templates
- Prompt template retrieval
- Multiple transport backends (stdio subprocess, HTTP/SSE)

Based on the Anthropic MCP specification (2024-11-05).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass
from typing import Any

from utils.logger import get_logger

__all__ = ["MCPClient", "MCPClientConfig", "MCPToolInfo"]

logger = get_logger(__name__)


@dataclass
class MCPClientConfig:
    """
    Configuration for connecting to an MCP server.

    Attributes:
        server_name: Human-readable name for this server connection.
        transport: Transport type ('stdio' or 'http').
        command: For stdio transport, the command to launch the server process.
        args: Arguments for the server process.
        env: Environment variables for the server process.
        url: For HTTP transport, the server URL.
    """

    server_name: str
    transport: str = "stdio"
    command: str = ""
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str = ""


@dataclass
class MCPToolInfo:
    """
    Metadata about a tool available on a remote MCP server.

    Attributes:
        name: Tool name on the remote server.
        description: Human-readable tool description.
        input_schema: JSON Schema for the tool's parameters.
        server_name: Which server provides this tool.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


class MCPClient:
    """
    Client for connecting to and interacting with external MCP servers.

    Handles the full lifecycle:
    1. Launch server subprocess (stdio) or establish HTTP connection
    2. Perform initialize handshake to negotiate capabilities
    3. Discover tools, resources, and prompts
    4. Invoke tools and read resources on demand
    5. Graceful shutdown

    Usage:
        config = MCPClientConfig(
            server_name="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )
        client = MCPClient(config)
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "/tmp/test.txt"})
        await client.disconnect()
    """

    def __init__(self, config: MCPClientConfig) -> None:
        """
        Initialize the MCP client.

        Args:
            config: Connection configuration for the target MCP server.
        """
        self.config = config
        self._process: subprocess.Popen[bytes] | None = None
        self._request_id: int = 0
        self._connected: bool = False
        self._server_capabilities: dict[str, Any] = {}
        self._response_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        # Background reader task
        self._reader_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Connection Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Establish connection to the MCP server.

        Launches the server process for stdio transport or connects
        via HTTP for HTTP transport. Performs the initialize handshake.

        Raises:
            RuntimeError: If connection fails or server rejects initialization.
        """
        if self._connected:
            logger.warning("MCP client is already connected")
            return

        if self.config.transport == "stdio":
            await self._connect_stdio()
        elif self.config.transport == "http":
            await self._connect_http()
        else:
            raise ValueError(f"Unknown transport: {self.config.transport}")

        # Perform initialize handshake
        init_result = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "agentforge",
                    "version": "1.0.0",
                },
            },
        )

        self._server_capabilities = init_result.get("capabilities", {})
        server_info = init_result.get("serverInfo", {})
        logger.info(
            f"Connected to MCP server: {server_info.get('name', 'unknown')} "
            f"v{server_info.get('version', '?')}"
        )

        # Send initialized notification
        await self._send_notification("initialized", {})
        self._connected = True

    async def disconnect(self) -> None:
        """
        Gracefully disconnect from the MCP server.

        Terminates the server process for stdio transport or closes
        the HTTP connection for HTTP transport.
        """
        if not self._connected:
            return

        # Cancel reader task
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        # Terminate process (stdio)
        if self._process is not None:
            try:
                self._process.stdin.close()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            except Exception as exc:
                logger.error(f"Error terminating MCP server process: {exc}")
            finally:
                self._process = None

        self._connected = False
        logger.info(f"Disconnected from MCP server: {self.config.server_name}")

    async def _connect_stdio(self) -> None:
        """
        Launch the MCP server as a subprocess and establish stdio pipes.
        """
        cmd = [self.config.command] + (self.config.args or [])
        logger.info(f"Launching MCP server: {' '.join(cmd)}")

        env = {**__import__("os").environ, **(self.config.env or {})}

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Start background reader for stdout
        self._reader_task = asyncio.create_task(self._read_stdio_responses())

    async def _connect_http(self) -> None:
        """
        Establish HTTP/SSE connection to the MCP server.
        """
        raise NotImplementedError(
            "HTTP transport not yet implemented. Use stdio transport."
        )

    async def _read_stdio_responses(self) -> None:
        """
        Background task: read JSON-RPC responses from the server's stdout.

        Each response is a single JSON line. Responses are pushed to the
        response queue for matching with pending requests.
        """
        if self._process is None or self._process.stdout is None:
            return

        loop = asyncio.get_event_loop()

        async def read_line() -> bytes:
            return await loop.run_in_executor(None, self._process.stdout.readline)

        while self._process is not None and self._process.poll() is None:
            try:
                line = await read_line()
                if not line:
                    break  # EOF — process exited

                response = json.loads(line.decode("utf-8").strip())
                await self._response_queue.put(response)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error reading MCP server response: {exc}")
                break

    # ------------------------------------------------------------------
    # JSON-RPC Communication
    # ------------------------------------------------------------------

    def _next_request_id(self) -> int:
        """
        Generate the next unique request ID.

        Returns:
            Incrementing integer ID.
        """
        self._request_id += 1
        return self._request_id

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Send a JSON-RPC request and await the response.

        Args:
            method: The RPC method name.
            params: Method parameters.

        Returns:
            The result from the response.

        Raises:
            RuntimeError: If the server returns an error or connection fails.
        """
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        await self._write_request(request)

        # Wait for matching response
        while True:
            response = await asyncio.wait_for(
                self._response_queue.get(),
                timeout=30.0,
            )
            if response.get("id") == request_id:
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(
                        f"MCP server error ({error.get('code')}): {error.get('message')}"
                    )
                return response.get("result")
            else:
                # Put back non-matching responses (e.g., notifications)
                await self._response_queue.put(response)

    async def _send_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Send a JSON-RPC notification (no response expected).

        Args:
            method: The notification method name.
            params: Notification parameters.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self._write_request(notification)

    async def _write_request(self, request: dict[str, Any]) -> None:
        """
        Write a JSON-RPC request to the server's stdin.

        Args:
            request: The request dictionary to serialize and send.

        Raises:
            RuntimeError: If the server process is no longer running.
        """
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("MCP server process is not running")

        request_str = json.dumps(request, ensure_ascii=False) + "\n"
        loop = asyncio.get_event_loop()

        def write() -> None:
            if self._process is not None and self._process.stdin is not None:
                self._process.stdin.write(request_str.encode("utf-8"))
                self._process.stdin.flush()

        await loop.run_in_executor(None, write)

    # ------------------------------------------------------------------
    # Tool Operations
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[MCPToolInfo]:
        """
        Discover all tools available on the remote MCP server.

        Returns:
            List of MCPToolInfo objects describing available tools.
        """
        result = await self._send_request("tools/list", {})
        tools: list[MCPToolInfo] = []
        for tool_data in result.get("tools", []):
            tools.append(MCPToolInfo(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=self.config.server_name,
            ))
        logger.info(
            f"Discovered {len(tools)} tools from MCP server '{self.config.server_name}'"
        )
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on the remote MCP server.

        Args:
            tool_name: The name of the tool to invoke.
            arguments: Tool-specific arguments matching the input schema.

        Returns:
            The tool execution result as a dictionary.

        Raises:
            RuntimeError: If the tool execution fails on the server.
        """
        logger.info(f"Calling MCP tool '{tool_name}' on '{self.config.server_name}'")
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result

    # ------------------------------------------------------------------
    # Resource Operations
    # ------------------------------------------------------------------

    async def list_resources(self) -> list[dict[str, Any]]:
        """
        Discover all resources available on the remote MCP server.

        Returns:
            List of resource descriptors.
        """
        result = await self._send_request("resources/list", {})
        resources = result.get("resources", [])
        logger.info(
            f"Discovered {len(resources)} resources from MCP server '{self.config.server_name}'"
        )
        return resources

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """
        Read a resource by URI from the remote MCP server.

        Args:
            uri: The resource URI to read.

        Returns:
            Resource content.

        Raises:
            RuntimeError: If the resource read fails.
        """
        logger.info(f"Reading MCP resource '{uri}' from '{self.config.server_name}'")
        result = await self._send_request("resources/read", {"uri": uri})
        return result

    # ------------------------------------------------------------------
    # Prompt Operations
    # ------------------------------------------------------------------

    async def list_prompts(self) -> list[dict[str, Any]]:
        """
        Discover all prompt templates available on the remote MCP server.

        Returns:
            List of prompt descriptors.
        """
        result = await self._send_request("prompts/list", {})
        prompts = result.get("prompts", [])
        logger.info(
            f"Discovered {len(prompts)} prompts from MCP server '{self.config.server_name}'"
        )
        return prompts

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get a rendered prompt template from the remote MCP server.

        Args:
            prompt_name: The prompt template name.
            arguments: Arguments to fill into the template.

        Returns:
            Rendered prompt messages.

        Raises:
            RuntimeError: If the prompt retrieval fails.
        """
        logger.info(f"Getting MCP prompt '{prompt_name}' from '{self.config.server_name}'")
        result = await self._send_request("prompts/get", {
            "name": prompt_name,
            "arguments": arguments or {},
        })
        return result

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Check if the client is currently connected to the server."""
        return self._connected

    @property
    def server_capabilities(self) -> dict[str, Any]:
        """Return the server's advertised capabilities."""
        return self._server_capabilities.copy()
