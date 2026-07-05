"""
OpenCode Adapter
================
Adapter for OpenCode CLI (opencode).

OpenCode is an open-source terminal-based AI coding agent that supports
multiple LLM backends. Integrates with AgentForge through the standard
agent adapter interface.

Repository: https://github.com/sst/opencode
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from adapters.base_adapter import (
    AgentExecutionError,
    AgentStatus,
    AgentTimeoutError,
    BaseAgentAdapter,
    ExecutionContext,
    HealthCheckResult,
    ReviewComment,
    ReviewResult,
    TaskInput,
    TaskResult,
    TaskResultStatus,
)

logger = logging.getLogger(__name__)


class OpenCodeAdapter(BaseAgentAdapter):
    """
    Adapter for OpenCode CLI.

    OpenCode is an open-source terminal AI coding tool that supports
    multiple LLM providers (OpenAI, Anthropic, Google, local models).
    It provides a unified interface for agentic code operations.

    Supported Backends:
    - OpenAI (GPT-4o, o4-mini)
    - Anthropic (Claude Sonnet, Claude Opus)
    - Google (Gemini 2.5 Pro)
    - Ollama (local models)
    - Any OpenAI-compatible API

    Configuration:
        Set the OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY
        depending on the chosen backend.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "claude-sonnet-4-20250514",
        cli_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            cli_name="opencode",
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            config=config or {},
        )

        # OpenCode specific settings
        self._provider = self.config.get("provider", "anthropic")  # anthropic | openai | google | ollama
        self._base_url = self.config.get("base_url")  # For custom API endpoints
        self._temperature = self.config.get("temperature", 0.0)
        self._max_tokens = self.config.get("max_tokens", 32000)

    # ===== Health Check =====

    async def check_health(self) -> HealthCheckResult:
        """Check if OpenCode CLI is installed and configured."""
        try:
            cli_cmd = str(self.cli_path) if self.cli_path else "opencode"
            if not shutil.which(cli_cmd):
                return HealthCheckResult(
                    status=AgentStatus.NOT_FOUND,
                    cli_name="opencode",
                    error_message="OpenCode CLI not found. Install: npm install -g opencode",
                )

            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )

            if code != 0:
                return HealthCheckResult(
                    status=AgentStatus.UNHEALTHY,
                    cli_name="opencode",
                    error_message=stderr.strip() or "Version check failed",
                )

            version = stdout.strip().split("\n")[0]

            return HealthCheckResult(
                status=AgentStatus.HEALTHY,
                cli_name="opencode",
                cli_version=version,
                cli_path=cli_cmd,
                model_name=self.model_name,
            )

        except FileNotFoundError:
            return HealthCheckResult(
                status=AgentStatus.NOT_FOUND,
                cli_name="opencode",
                error_message="OpenCode CLI not found in PATH",
            )
        except Exception as e:
            logger.exception("OpenCode health check failed: %s", e)
            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name="opencode",
                error_message=str(e),
            )

    # ===== Task Execution =====

    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute a task using OpenCode CLI."""
        started_at = datetime.now(timezone.utc)
        cli_cmd = str(self.cli_path) if self.cli_path else "opencode"

        # Build command
        cmd = [
            cli_cmd,
            "run",  # Non-interactive run mode
            task_input.description,
            "--provider", self._provider,
            "--model", self.model_name,
            "--temperature", str(self._temperature),
            "--max-tokens", str(self._max_tokens),
        ]

        if self._base_url:
            cmd.extend(["--base-url", self._base_url])

        if task_input.context_documents:
            for doc in task_input.context_documents:
                cmd.extend(["--context", doc])

        if "extra_cli_args" in self.config:
            cmd.extend(self.config["extra_cli_args"])

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                cmd,
                cwd=context.workspace_path,
                timeout_seconds=task_input.timeout_seconds,
            )

            execution_time = (datetime.now(timezone.utc) - started_at).total_seconds()
            success = returncode == 0
            output = stdout.strip()

            return TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.SUCCESS if success else TaskResultStatus.FAILED,
                agent_name=self.name,
                agent_role=self.role,
                output=output,
                summary=output[:500] + ("..." if len(output) > 500 else ""),
                artifacts=self._extract_artifacts(output, context.workspace_path),
                errors=[stderr.strip()] if stderr.strip() and not success else [],
                execution_time_seconds=execution_time,
                started_at=started_at,
                metrics={
                    "exit_code": returncode,
                    "model": self.model_name,
                    "provider": self._provider,
                    "temperature": self._temperature,
                },
            )

        except asyncio.TimeoutError:
            raise AgentTimeoutError(task_input.task_id, task_input.timeout_seconds, self.name)
        except Exception as e:
            raise AgentExecutionError(task_input.task_id, -1, str(e), self.name)

    # ===== Code Review =====

    async def review_code(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
        review_rules: Optional[List[str]] = None,
    ) -> ReviewResult:
        """Review code using OpenCode."""
        rules = "\n".join(f"- {r}" for r in (review_rules or ["Standard best practices"]))
        review_prompt = f"""Act as a code reviewer. Review the code changes and output a JSON report.

Review rules:
{rules}

Output format (JSON only):
{{
  "overall_score": <0.0-10.0>,
  "is_approved": <true/false>,
  "issues": [
    {{
      "file": "<path>",
      "line": <number or null>,
      "severity": "<critical|error|warning|info>",
      "category": "<bug|security|performance|style|architecture|docs>",
      "message": "<description>",
      "suggestion": "<fix>"
    }}
  ],
  "summary": "<summary>",
  "fixer_instructions": "<guidance>"
}}

Task: {task_input.description}"""

        cli_cmd = str(self.cli_path) if self.cli_path else "opencode"

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                [
                    cli_cmd, "run", review_prompt,
                    "--provider", self._provider,
                    "--model", self.model_name,
                    "--temperature", "0.0",
                ],
                cwd=context.workspace_path,
                timeout_seconds=task_input.timeout_seconds,
            )

            if returncode != 0:
                return ReviewResult(
                    task_id=task_input.task_id,
                    agent_name=self.name,
                    overall_score=0.0,
                    is_approved=False,
                    summary=f"Review failed: {stderr[:500]}",
                )

            return self._parse_review_json(stdout, task_input.task_id)

        except asyncio.TimeoutError:
            return ReviewResult(
                task_id=task_input.task_id,
                agent_name=self.name,
                overall_score=0.0,
                is_approved=False,
                summary="Review timed out",
            )

    # ===== Streaming =====

    async def stream_output(
        self,
        task_id: str,
        context: ExecutionContext,
    ) -> AsyncIterator[str]:
        """Stream OpenCode output in real-time."""
        cli_cmd = str(self.cli_path) if self.cli_path else "opencode"

        process = await asyncio.create_subprocess_exec(
            cli_cmd, "run", "--stream",
            "--provider", self._provider,
            "--model", self.model_name,
            "Continue the task.",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(context.workspace_path),
        )

        if process.stdout:
            async for line in process.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    yield decoded

        await process.wait()

    # ===== Cancellation =====

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel running OpenCode task."""
        await self.cleanup()
        self._current_task_id = None
        return True

    # ===== Review Parsing =====

    def _parse_review_json(self, output: str, task_id: str) -> ReviewResult:
        """Parse OpenCode JSON review output."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', output)
            if not json_match:
                return self._fallback_parse(output, task_id)

            data = json.loads(json_match.group())

            result = ReviewResult(
                task_id=task_id,
                agent_name=self.name,
                overall_score=float(data.get("overall_score", 0)),
                is_approved=data.get("is_approved", False),
                summary=data.get("summary", ""),
                suggestion_for_fixer=data.get("fixer_instructions"),
            )

            for issue in data.get("issues", []):
                result.comments.append(ReviewComment(
                    file_path=issue.get("file", ""),
                    line_start=issue.get("line"),
                    severity=issue.get("severity", "info"),
                    category=issue.get("category", "style"),
                    message=issue.get("message", ""),
                    suggestion=issue.get("suggestion"),
                ))

            return result

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse OpenCode JSON review: %s", e)
            return self._fallback_parse(output, task_id)

    def _fallback_parse(self, output: str, task_id: str) -> ReviewResult:
        """Fallback text-based review parsing."""
        result = ReviewResult(task_id=task_id, agent_name=self.name)
        score_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", output)
        if score_match:
            result.overall_score = float(score_match.group(1))
        result.is_approved = "approve" in output.lower() or result.overall_score >= 7.0
        result.summary = output[:1000]
        return result

    # ===== Output Helpers =====

    def _extract_artifacts(self, output: str, workspace: Path) -> List[str]:
        """Extract file artifact paths."""
        paths = set()
        patterns = [
            r"(?:created|wrote|modified|updated)\s+[`'\"]?([^\s`'\"]+\.[a-zA-Z]+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                fpath = match.group(1).strip()
                resolved = workspace / fpath
                if resolved.exists():
                    paths.add(str(resolved))
        return list(paths)
