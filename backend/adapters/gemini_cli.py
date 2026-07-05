"""
Gemini CLI Adapter
==================
Adapter for Google's Gemini CLI (gemini).

Integrates the Google Gemini CLI tool with AgentForge. Gemini CLI
provides agentic coding capabilities powered by Google's Gemini models
(gemini-2.5-pro, gemini-2.5-flash, etc.).

CLI Reference: https://github.com/google-gemini/gemini-cli
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


class GeminiCLIAdapter(BaseAgentAdapter):
    """
    Adapter for Google's Gemini CLI.

    Gemini CLI brings Google's Gemini models to the terminal with
    agentic coding capabilities, including file operations, shell
    commands, and multi-turn conversations.

    Supported Models:
    - gemini-2.5-pro
    - gemini-2.5-flash
    - gemini-2.0-flash

    Authentication:
        Requires GOOGLE_API_KEY environment variable or API key
        passed via constructor. Can also use gcloud auth.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "gemini-2.5-pro",
        cli_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            cli_name="gemini",
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            config=config or {},
        )
        self._yolo_mode = self.config.get("yolo_mode", False)
        self._max_session_turns = self.config.get("max_session_turns", 100)

    # ===== Health Check =====

    async def check_health(self) -> HealthCheckResult:
        """Check if Gemini CLI is installed and authenticated."""
        try:
            cli_cmd = str(self.cli_path) if self.cli_path else "gemini"
            if not shutil.which(cli_cmd):
                return HealthCheckResult(
                    status=AgentStatus.NOT_FOUND,
                    cli_name="gemini",
                    error_message="Gemini CLI not found. Install: npm install -g @google/gemini-cli",
                )

            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )

            if code != 0:
                return HealthCheckResult(
                    status=AgentStatus.UNHEALTHY,
                    cli_name="gemini",
                    error_message=stderr.strip() or "Version check failed",
                )

            version = stdout.strip().split("\n")[0]

            # Check authentication
            if self._api_key:
                auth_check_code, _, auth_stderr = await self._run_subprocess(
                    [cli_cmd, "auth", "status"],
                    timeout_seconds=10.0,
                )
                if auth_check_code != 0:
                    return HealthCheckResult(
                        status=AgentStatus.UNAUTHORIZED,
                        cli_name="gemini",
                        cli_version=version,
                        error_message=f"Authentication failed: {auth_stderr.strip()}",
                    )

            return HealthCheckResult(
                status=AgentStatus.HEALTHY,
                cli_name="gemini",
                cli_version=version,
                cli_path=cli_cmd,
                model_name=self.model_name,
            )

        except Exception as e:
            logger.exception("Gemini health check failed: %s", e)
            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name="gemini",
                error_message=str(e),
            )

    # ===== Task Execution =====

    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute a task using Gemini CLI."""
        started_at = datetime.now(timezone.utc)
        cli_cmd = str(self.cli_path) if self.cli_path else "gemini"

        cmd = [
            cli_cmd,
            "-p",  # Prompt mode (non-interactive)
            task_input.description,
            "--model", self.model_name,
            "--max-session-turns", str(self._max_session_turns),
        ]

        if self._yolo_mode:
            cmd.append("--yolo")

        if task_input.context_documents:
            for doc in task_input.context_documents:
                cmd.extend(["--include", doc])

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

            # Parse Gemini output format
            parsed_output, artifacts = self._parse_gemini_output(output, context.workspace_path)

            return TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.SUCCESS if success else TaskResultStatus.FAILED,
                agent_name=self.name,
                agent_role=self.role,
                output=parsed_output or output,
                summary=self._truncate(parsed_output or output, 500),
                artifacts=artifacts,
                errors=[stderr.strip()] if stderr.strip() and not success else [],
                execution_time_seconds=execution_time,
                started_at=started_at,
                metrics={
                    "exit_code": returncode,
                    "model": self.model_name,
                    "yolo_mode": self._yolo_mode,
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
        """Review code using Gemini CLI."""
        rules = "\n".join(f"- {r}" for r in (review_rules or ["Standard code quality criteria"]))

        review_prompt = f"""You are a code reviewer. Analyze the code changes and return a JSON report.

Criteria:
{rules}

Return ONLY a JSON object (no markdown, no code fences):
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
      "suggestion": "<how to fix>"
    }}
  ],
  "summary": "<brief review summary>",
  "fixer_instructions": "<guidance for fixer>"
}}

Task: {task_input.description}"""

        cli_cmd = str(self.cli_path) if self.cli_path else "gemini"

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "-p", review_prompt, "--model", self.model_name],
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

            return self._parse_review_output(stdout, task_input.task_id)

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
        """Stream Gemini output."""
        cli_cmd = str(self.cli_path) if self.cli_path else "gemini"

        process = await asyncio.create_subprocess_exec(
            cli_cmd, "-p", "--stream", "--model", self.model_name,
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
        """Cancel Gemini task."""
        await self.cleanup()
        self._current_task_id = None
        return True

    # ===== Review Parsing =====

    def _parse_review_output(self, output: str, task_id: str) -> ReviewResult:
        """Parse Gemini review JSON output."""
        try:
            # Gemini may wrap JSON in ```json fences
            json_str = output
            fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output)
            if fence_match:
                json_str = fence_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', output)
                if json_match:
                    json_str = json_match.group()

            data = json.loads(json_str)

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
            logger.warning("Failed to parse Gemini JSON review: %s", e)
            return ReviewResult(
                task_id=task_id,
                agent_name=self.name,
                overall_score=5.0,
                is_approved=False,
                summary=output[:1000],
            )

    # ===== Output Helpers =====

    def _parse_gemini_output(self, output: str, workspace: Path) -> tuple[str, List[str]]:
        """Parse Gemini CLI output format. Returns (cleaned_output, artifacts)."""
        artifacts: List[str] = []

        # Extract file paths mentioned as artifacts
        patterns = [
            r"(?:created|wrote|modified|updated)\s+[`'\"]?([^\s`'\"]+\.[a-zA-Z0-9]+)",
            r"File:\s*[`'\"]?([^\s`'\"]+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                fpath = match.group(1).strip()
                resolved = workspace / fpath
                if resolved.exists():
                    artifacts.append(str(resolved))

        # Clean up output (remove ANSI codes if any)
        clean = re.sub(r'\x1b\[[0-9;]*m', '', output)

        return clean, artifacts

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max_len with ellipsis."""
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."
