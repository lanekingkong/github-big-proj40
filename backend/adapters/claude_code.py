"""
Claude Code Adapter
===================
Adapter for Anthropic's Claude Code CLI (claude).

Integrates the claude CLI tool with AgentForge's unified agent interface.
Supports both interactive and non-interactive modes, file editing,
and structured output parsing.

CLI Reference: https://docs.anthropic.com/en/docs/claude-code
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
    AgentAdapterError,
    AgentAuthenticationError,
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


class ClaudeCodeAdapter(BaseAgentAdapter):
    """
    Adapter for Anthropic's Claude Code CLI.

    Claude Code is an agentic coding tool that runs in the terminal.
    It can understand codebases, edit files, run commands, and manage
    git workflows through natural language instructions.

    Features:
    - Full codebase understanding
    - File read/write/edit operations
    - Terminal command execution
    - Git operations
    - Structured output (JSON mode)

    Authentication:
        Requires ANTHROPIC_API_KEY environment variable or API key
        passed via constructor.
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
            cli_name="claude",
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            config=config or {},
        )
        self._max_turns = self.config.get("max_turns", 50)
        self._permission_mode = self.config.get("permission_mode", "acceptEdits")  # acceptEdits | bypassPermissions | default | plan

    # ===== Health Check =====

    async def check_health(self) -> HealthCheckResult:
        """Check if claude CLI is installed and authenticated."""
        try:
            # Check CLI existence
            cli_cmd = str(self.cli_path) if self.cli_path else "claude"
            if not shutil.which(cli_cmd):
                return HealthCheckResult(
                    status=AgentStatus.NOT_FOUND,
                    cli_name="claude",
                    error_message=f"Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
                )

            # Get version
            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )

            if code != 0:
                return HealthCheckResult(
                    status=AgentStatus.UNHEALTHY,
                    cli_name="claude",
                    error_message=stderr.strip() or "Unknown error",
                )

            version = stdout.strip().split("\n")[0]

            # Verify authentication via a minimal API call
            if self._api_key:
                import os
                if not self._api_key.startswith("sk-"):
                    return HealthCheckResult(
                        status=AgentStatus.CONFIG_ERROR,
                        cli_name="claude",
                        cli_version=version,
                        error_message="API key format invalid (should start with 'sk-')",
                    )

            return HealthCheckResult(
                status=AgentStatus.HEALTHY,
                cli_name="claude",
                cli_version=version,
                cli_path=cli_cmd,
                model_name=self.model_name,
            )

        except Exception as e:
            logger.exception("Claude health check failed: %s", e)
            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name="claude",
                error_message=str(e),
            )

    # ===== Task Execution =====

    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """
        Execute a task using Claude Code.

        Uses claude -p (print mode) for non-interactive task execution.
        The --model flag specifies the Claude model variant.
        """
        started_at = datetime.now(timezone.utc)
        cli_cmd = str(self.cli_path) if self.cli_path else "claude"

        # Build CLI arguments
        cmd = [
            cli_cmd,
            "-p",  # Print mode (non-interactive)
            task_input.description,
            "--model", self.model_name,
            "--max-turns", str(self._max_turns),
            "--permission-mode", self._permission_mode,
            "--output-format", "text",  # Use text for general tasks
        ]

        # Add task-specific context files
        if task_input.context_documents:
            for doc in task_input.context_documents:
                cmd.extend(["--file", doc])

        # Add extra CLI args from config
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
            errors = []

            if stderr.strip():
                errors.append(stderr.strip())

            # Extract token usage from output if available
            token_usage = self._extract_token_usage(stdout)
            # Extract any artifacts (file paths mentioned in output)
            artifacts = self._extract_artifacts(stdout, context.workspace_path)

            return TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.SUCCESS if success else TaskResultStatus.FAILED,
                agent_name=self.name,
                agent_role=self.role,
                output=output,
                summary=self._summarize_output(output, max_len=500),
                artifacts=artifacts,
                errors=errors if not success else [],
                warnings=self._extract_warnings(stdout),
                execution_time_seconds=execution_time,
                token_usage=token_usage,
                started_at=started_at,
                metrics={
                    "exit_code": returncode,
                    "model": self.model_name,
                    "max_turns": self._max_turns,
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
        """
        Review code changes using Claude Code.

        Builds a structured review prompt and parses the response into
        ReviewComment objects.
        """
        # Build review prompt
        review_prompt = self._build_review_prompt(task_input, context, review_rules)

        cli_cmd = str(self.cli_path) if self.cli_path else "claude"

        cmd = [
            cli_cmd,
            "-p", review_prompt,
            "--model", self.model_name,
            "--max-turns", "20",
            "--output-format", "text",
        ]

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                cmd,
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

            # Parse structured review output
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
        """Stream Claude's output in real-time."""
        cli_cmd = str(self.cli_path) if self.cli_path else "claude"

        cmd = [
            cli_cmd,
            "-p", "Continue the last task.",
            "--model", self.model_name,
            "--output-format", "stream-json",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(context.workspace_path),
        )

        if process.stdout:
            async for line in process.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    # Claude stream-json format
                    try:
                        data = json.loads(decoded)
                        if "text" in data:
                            yield data["text"]
                    except json.JSONDecodeError:
                        yield decoded

        await process.wait()

    # ===== Cancellation =====

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running Claude task by killing the subprocess."""
        await self.cleanup()
        self._current_task_id = None
        return True

    # ===== Review Helpers =====

    def _build_review_prompt(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
        review_rules: Optional[List[str]] = None,
    ) -> str:
        """Build a structured review prompt for Claude."""
        rules_text = ""
        if review_rules:
            rules_text = "Review Rules:\n" + "\n".join(f"- {r}" for r in review_rules)

        return f"""You are a code reviewer. Review the following changes and provide structured feedback.

Task: {task_input.description}

{rules_text}

Respond in the following format:

## Overall Score
<score from 0.0 to 10.0>

## Verdict
<APPROVED or NEEDS_WORK>

## Issues
For each issue:
- **File**: <file path>
- **Lines**: <line range or N/A>
- **Severity**: <critical|error|warning|info>
- **Category**: <bug|security|performance|style|architecture|docs>
- **Message**: <description>
- **Suggestion**: <how to fix>

## Summary
<brief summary>

## Fixer Instructions
<detailed instructions for the fixer agent>"""

    def _parse_review_output(self, output: str, task_id: str) -> ReviewResult:
        """Parse Claude's review output into structured ReviewResult."""
        result = ReviewResult(
            task_id=task_id,
            agent_name=self.name,
        )

        # Extract overall score
        score_match = re.search(r"Overall Score\s*\n\s*(\d+(?:\.\d+)?)", output, re.IGNORECASE)
        if score_match:
            result.overall_score = float(score_match.group(1))

        # Extract verdict
        if "APPROVED" in output.upper() and "NEEDS_WORK" not in output.upper():
            result.is_approved = True

        # Extract issues
        issue_pattern = re.compile(
            r"[-*]\s*\*\*File\*\*:\s*(.+?)\n"
            r"[-*]\s*\*\*Lines\*\*:\s*(.+?)\n"
            r"[-*]\s*\*\*Severity\*\*:\s*(.+?)\n"
            r"[-*]\s*\*\*Category\*\*:\s*(.+?)\n"
            r"[-*]\s*\*\*Message\*\*:\s*(.+?)\n"
            r"(?:[-*]\s*\*\*Suggestion\*\*:\s*(.+?)\n)?",
            re.IGNORECASE,
        )

        for match in issue_pattern.finditer(output):
            result.comments.append(ReviewComment(
                file_path=match.group(1).strip(),
                line_start=None,  # Parse from "Lines" field
                severity=match.group(3).strip().lower(),
                category=match.group(4).strip().lower(),
                message=match.group(5).strip(),
                suggestion=match.group(6).strip() if match.group(6) else None,
            ))

        # Extract summary
        summary_match = re.search(r"## Summary\s*\n(.+?)(?=\n##|\Z)", output, re.DOTALL | re.IGNORECASE)
        if summary_match:
            result.summary = summary_match.group(1).strip()

        # Extract fixer instructions
        fixer_match = re.search(r"## Fixer Instructions\s*\n(.+)", output, re.DOTALL | re.IGNORECASE)
        if fixer_match:
            result.suggestion_for_fixer = fixer_match.group(1).strip()

        return result

    # ===== Output Parsing =====

    def _extract_token_usage(self, output: str) -> Optional[Dict[str, int]]:
        """Extract token usage statistics from Claude's output."""
        usage = {}

        # Claude sometimes reports token usage in the output
        input_match = re.search(r"Input tokens:\s*(\d+)", output, re.IGNORECASE)
        if input_match:
            usage["input_tokens"] = int(input_match.group(1))

        output_match = re.search(r"Output tokens:\s*(\d+)", output, re.IGNORECASE)
        if output_match:
            usage["output_tokens"] = int(output_match.group(1))

        return usage if usage else None

    def _extract_artifacts(self, output: str, workspace: Path) -> List[str]:
        """Extract file paths mentioned in Claude's output."""
        artifacts = []

        # Look for common file path patterns
        patterns = [
            r"(?:created|modified|updated|wrote|written to)\s+[`'\"]?([^\s`'\"]+)[`'\"]?",
            r"(?:file|path):\s*[`'\"]?([^\s`'\"]+)[`'\"]?",
            r"Wrote contents to\s+[`'\"]?([^\s`'\"]+)[`'\"]?",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                fpath = match.group(1).strip()
                # Resolve relative to workspace
                if fpath and not fpath.startswith("/"):
                    resolved = workspace / fpath
                    if resolved.exists():
                        artifacts.append(str(resolved))
                elif fpath:
                    artifacts.append(fpath)

        return list(set(artifacts))  # Deduplicate

    def _extract_warnings(self, output: str) -> List[str]:
        """Extract warnings from Claude's output."""
        warnings = []
        for line in output.splitlines():
            if "warning" in line.lower() or "note:" in line.lower():
                warnings.append(line.strip())
        return warnings[:10]  # Limit

    def _summarize_output(self, output: str, max_len: int = 500) -> str:
        """Generate a summary from Claude's output."""
        if not output:
            return ""
        # Return first meaningful chunk
        lines = output.strip().splitlines()
        summary_lines = []
        length = 0
        for line in lines:
            if line.strip():
                summary_lines.append(line)
                length += len(line)
                if length >= max_len:
                    break
        result = "\n".join(summary_lines)
        return result + ("..." if len(result) < len(output) else "")
