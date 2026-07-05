"""
OpenAI Codex Adapter
====================
Adapter for OpenAI's Codex CLI (codex).

Integrates the codex CLI tool with AgentForge. Codex is OpenAI's
agentic coding tool that runs in the terminal and can read, write,
and modify code using OpenAI models (GPT-4o, o4-mini, etc.).

CLI Reference: https://github.com/openai/codex
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
    AgentNotFoundError,
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


class CodexAdapter(BaseAgentAdapter):
    """
    Adapter for OpenAI's Codex CLI.

    Codex is a terminal-based agentic coding tool powered by OpenAI models.
    It can execute multi-step coding tasks, run shell commands, and navigate
    codebases.

    Supported Models:
    - gpt-4o / gpt-4o-mini
    - o4-mini
    - o3 / o3-mini

    Authentication:
        Requires OPENAI_API_KEY environment variable or API key
        passed via constructor.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "gpt-4o",
        cli_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            cli_name="codex",
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            config=config or {},
        )
        self._sandbox_mode = self.config.get("sandbox_mode", "workspace")  # workspace | strict | off
        self._approval_mode = self.config.get("approval_mode", "default")  # default | auto_edit | yolo

    # ===== Health Check =====

    async def check_health(self) -> HealthCheckResult:
        """Check if Codex CLI is installed and authenticated."""
        try:
            cli_cmd = str(self.cli_path) if self.cli_path else "codex"
            if not shutil.which(cli_cmd):
                return HealthCheckResult(
                    status=AgentStatus.NOT_FOUND,
                    cli_name="codex",
                    error_message="Codex CLI not found. Install with: npm install -g @openai/codex",
                )

            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )

            if code != 0:
                return HealthCheckResult(
                    status=AgentStatus.UNHEALTHY,
                    cli_name="codex",
                    error_message=stderr.strip() or "Version check failed",
                )

            version = stdout.strip().split("\n")[0]

            # Verify API key format
            if self._api_key and not self._api_key.startswith("sk-"):
                return HealthCheckResult(
                    status=AgentStatus.CONFIG_ERROR,
                    cli_name="codex",
                    cli_version=version,
                    error_message="Invalid API key format",
                )

            return HealthCheckResult(
                status=AgentStatus.HEALTHY,
                cli_name="codex",
                cli_version=version,
                cli_path=cli_cmd,
                model_name=self.model_name,
            )

        except Exception as e:
            logger.exception("Codex health check failed: %s", e)
            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name="codex",
                error_message=str(e),
            )

    # ===== Task Execution =====

    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute a task using Codex CLI."""
        started_at = datetime.now(timezone.utc)
        cli_cmd = str(self.cli_path) if self.cli_path else "codex"

        cmd = [
            cli_cmd,
            "exec",  # Execute mode
            task_input.description,
            "--model", self.model_name,
            "--sandbox", self._sandbox_mode,
            "--approval-mode", self._approval_mode,
        ]

        if task_input.context_documents:
            for doc in task_input.context_documents:
                cmd.extend(["--file", doc])

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
                summary=self._summarize(output, 500),
                artifacts=self._extract_file_paths(output, context.workspace_path),
                errors=[stderr.strip()] if stderr.strip() and not success else [],
                warnings=self._extract_warnings(stderr),
                execution_time_seconds=execution_time,
                started_at=started_at,
                metrics={
                    "exit_code": returncode,
                    "model": self.model_name,
                    "sandbox": self._sandbox_mode,
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
        """Review code using Codex with a structured review prompt."""
        rules = review_rules or []
        rules_section = "\n".join(f"- {r}" for r in rules) if rules else "Use standard best practices."

        review_prompt = f"""Review the current code changes.

Review criteria:
{rules_section}

Output a JSON object with:
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
            "suggestion": "<fix suggestion>"
        }}
    ],
    "summary": "<brief summary>",
    "fixer_instructions": "<guidance for fixer agent>"
}}

Task context: {task_input.description}"""

        cli_cmd = str(self.cli_path) if self.cli_path else "codex"

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "exec", review_prompt, "--model", self.model_name, "--sandbox", "workspace"],
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

            return self._parse_json_review(stdout, task_input.task_id)

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
        """Stream Codex output."""
        cli_cmd = str(self.cli_path) if self.cli_path else "codex"

        process = await asyncio.create_subprocess_exec(
            cli_cmd, "exec", "--stream", "--model", self.model_name,
            "Continue the task.",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(context.workspace_path),
        )

        if process.stdout:
            buffer = b""
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if decoded:
                        yield decoded

        await process.wait()

    # ===== Cancellation =====

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel Codex task."""
        await self.cleanup()
        self._current_task_id = None
        return True

    # ===== Review Parsing =====

    def _parse_json_review(self, output: str, task_id: str) -> ReviewResult:
        """Parse Codex JSON review output."""
        try:
            # Find JSON block in output
            json_match = re.search(r'\{[\s\S]*\}', output)
            if not json_match:
                return self._fallback_review_parse(output, task_id)

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
            logger.warning("Failed to parse Codex JSON review: %s", e)
            return self._fallback_review_parse(output, task_id)

    def _fallback_review_parse(self, output: str, task_id: str) -> ReviewResult:
        """Fallback text-based review parsing."""
        result = ReviewResult(task_id=task_id, agent_name=self.name)
        score_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", output)
        if score_match:
            result.overall_score = float(score_match.group(1))
        result.is_approved = "approved" in output.lower() or result.overall_score >= 7.0
        result.summary = output[:1000]
        return result

    # ===== Output Helpers =====

    def _extract_file_paths(self, output: str, workspace: Path) -> List[str]:
        """Extract file paths from Codex output."""
        paths = set()
        patterns = [
            r"(?:Creating|Writing|Updating|Modified)\s+[`'\"]?([^\s`'\"]+\.[a-zA-Z]+)",
            r"File:\s*[`'\"]?([^\s`'\"]+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                fpath = match.group(1).strip()
                if not fpath.startswith("/") and not fpath.startswith("\\"):
                    resolved = workspace / fpath
                    if resolved.exists():
                        paths.add(str(resolved))
                else:
                    paths.add(fpath)
        return list(paths)

    def _extract_warnings(self, stderr: str) -> List[str]:
        """Extract warnings from stderr."""
        if not stderr:
            return []
        return [line.strip() for line in stderr.splitlines() if line.strip()][:10]

    def _summarize(self, output: str, max_len: int) -> str:
        """Create a summary of the output."""
        if not output:
            return ""
        if len(output) <= max_len:
            return output
        return output[:max_len] + "..."
