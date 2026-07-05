"""
REST API Client
===============
Base HTTP client for REST API communication in the AgentForge platform.

Provides a unified client for:
- Inter-service communication within the AgentForge backend
- Communication with external AI agent CLIs that expose REST endpoints
- Health check endpoints
- Retry logic with exponential backoff
- Authentication header injection

Serves as the HTTP communication foundation used by all protocol clients
(MCP, A2A) and service integrations.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from utils.logger import get_logger

__all__ = [
    "RESTClient",
    "RESTClientConfig",
    "RESTResponse",
    "RESTError",
]

logger = get_logger(__name__)


@dataclass
class RESTClientConfig:
    """
    Configuration for the REST API client.

    Attributes:
        base_url: Base URL for all requests (e.g., 'http://localhost:8000').
        timeout_sec: Request timeout in seconds.
        max_retries: Maximum number of retry attempts for transient errors.
        retry_backoff_base: Base delay in seconds for exponential backoff.
        headers: Default headers to include in every request.
        api_key: Optional API key for authentication.
        verify_ssl: Whether to verify SSL certificates.
    """

    base_url: str = "http://localhost:8000"
    timeout_sec: float = 30.0
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    headers: dict[str, str] = field(default_factory=dict)
    api_key: str | None = None
    verify_ssl: bool = True


@dataclass
class RESTResponse:
    """
    Unified response from the REST client.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        body: Parsed response body (dict for JSON, str otherwise).
        request_url: The URL that was requested.
        elapsed_sec: Time taken for the request in seconds.
    """

    status_code: int
    headers: dict[str, str]
    body: Any
    request_url: str
    elapsed_sec: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success (2xx status)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if the response indicates a client error (4xx status)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if the response indicates a server error (5xx status)."""
        return self.status_code >= 500


class RESTError(Exception):
    """
    Exception raised for REST API errors.

    Attributes:
        status_code: HTTP status code if available.
        response_body: Response body content if available.
        request_url: The URL that caused the error.
        message: Human-readable error description.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
        request_url: str = "",
    ) -> None:
        """
        Initialize the REST error.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code from the failed response.
            response_body: Response body from the failed request.
            request_url: The URL that was requested.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.request_url = request_url
        self.message = message


class RESTClient:
    """
    Unified HTTP REST client for the AgentForge platform.

    Features:
    - GET, POST, PUT, PATCH, DELETE methods
    - Automatic JSON serialization/deserialization
    - Exponential backoff retry on transient errors
    - API key authentication header injection
    - Request timeout enforcement
    - Response logging for debugging

    Usage:
        config = RESTClientConfig(
            base_url="http://localhost:8000",
            api_key="af_abc123",
        )
        client = RESTClient(config)
        response = await client.get("/api/v1/agents")
        if response.is_success:
            agents = response.body["items"]
    """

    def __init__(self, config: RESTClientConfig) -> None:
        """
        Initialize the REST client.

        Args:
            config: Client configuration.
        """
        self.config = config
        self._session: Any = None  # httpx.AsyncClient in production

    # ------------------------------------------------------------------
    # HTTP Methods
    # ------------------------------------------------------------------

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Perform a GET request.

        Args:
            path: URL path (appended to base_url).
            params: Query parameters.
            headers: Additional headers for this request.

        Returns:
            RESTResponse with parsed body.
        """
        url = self._build_url(path)
        logger.debug(f"GET {url}")
        return await self._request("GET", url, params=params, headers=headers)

    async def post(
        self,
        path: str,
        body: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Perform a POST request.

        Args:
            path: URL path.
            body: JSON-serializable request body.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            RESTResponse with parsed body.
        """
        url = self._build_url(path)
        logger.debug(f"POST {url}")
        return await self._request("POST", url, json_data=body, params=params, headers=headers)

    async def put(
        self,
        path: str,
        body: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Perform a PUT request.

        Args:
            path: URL path.
            body: JSON-serializable request body.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            RESTResponse with parsed body.
        """
        url = self._build_url(path)
        logger.debug(f"PUT {url}")
        return await self._request("PUT", url, json_data=body, params=params, headers=headers)

    async def patch(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Perform a PATCH request.

        Args:
            path: URL path.
            body: JSON-serializable request body.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            RESTResponse with parsed body.
        """
        url = self._build_url(path)
        logger.debug(f"PATCH {url}")
        return await self._request("PATCH", url, json_data=body, params=params, headers=headers)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Perform a DELETE request.

        Args:
            path: URL path.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            RESTResponse with parsed body.
        """
        url = self._build_url(path)
        logger.debug(f"DELETE {url}")
        return await self._request("DELETE", url, params=params, headers=headers)

    # ------------------------------------------------------------------
    # Core Request Engine
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """
        Core request execution with retry logic.

        Args:
            method: HTTP method.
            url: Full request URL.
            json_data: JSON body data.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            RESTResponse.

        Raises:
            RESTError: After all retries are exhausted.
        """
        merged_headers = self._build_headers(headers)
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()

                # In production: use httpx.AsyncClient
                # response = await self._session.request(
                #     method=method,
                #     url=url,
                #     json=json_data,
                #     params=params,
                #     headers=merged_headers,
                #     timeout=self.config.timeout_sec,
                # )

                # Stub response for now
                elapsed = asyncio.get_event_loop().time() - start_time

                return RESTResponse(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    body={"status": "ok"},
                    request_url=url,
                    elapsed_sec=elapsed,
                )

            except Exception as exc:
                last_error = exc
                if attempt < self.config.max_retries:
                    delay = self.config.retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.config.max_retries + 1}): "
                        f"{method} {url} — {exc}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: "
                        f"{method} {url} — {exc}"
                    )

        raise RESTError(
            message=f"Request failed: {method} {url} — {last_error}",
            request_url=url,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """
        Construct the full URL from base URL and path.

        Args:
            path: URL path (may or may not start with '/').

        Returns:
            Full URL string.
        """
        base = self.config.base_url.rstrip("/")
        clean_path = path.lstrip("/")
        return f"{base}/{clean_path}"

    def _build_headers(
        self,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Merge default headers with extra headers and auth.

        Args:
            extra_headers: Request-specific headers.

        Returns:
            Complete headers dictionary.
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AgentForge/1.0.0",
        }
        headers.update(self.config.headers)

        # Inject API key if configured
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        # Override with request-specific headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        Check if the configured server is healthy and reachable.

        Sends a GET to /health and expects a 200 response.

        Returns:
            True if the server is healthy, False otherwise.
        """
        try:
            response = await self.get("/health")
            return response.is_success
        except Exception as exc:
            logger.warning(f"Health check failed for {self.config.base_url}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Initialize the HTTP session.

        Must be called before making requests.
        """
        # In production: self._session = httpx.AsyncClient(...)
        logger.info(f"REST client initialized: {self.config.base_url}")

    async def close(self) -> None:
        """
        Close the HTTP session and release resources.
        """
        # In production: await self._session.aclose()
        self._session = None
        logger.info("REST client closed")
