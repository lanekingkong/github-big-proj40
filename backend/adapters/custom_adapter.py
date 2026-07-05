"""
Custom Agent Adapter
====================
Flexible adapter for integrating custom or third-party AI agents.

Supports any agent CLI tool that follows a basic contract:
1. Accepts a task description as the first positional argument.
2. Optionally supports --model, --timeout, --output flags.
3. Returns results on stdout (success=exit code 0).

Configuration allows full customization of the CLI interface
through a mapping of AgentForge concepts to CLI arguments.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from adapters.base_adapter import (
    AgentAdapterError,
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


class CustomAgentAdapter(BaseAgentAdapter):
    """
    Adapter for custom / third-party AI agent CLIs.

    This adapter can wrap any command-line AI agent tool by configuring
    how AgentForge concepts map to CLI arguments. It supports:

    - Arbitrary CLI commands
    - Custom argument templates
    - Output parsing via regex or JSON
    - Environment variable injection
    - Pre/post processing hooks

    Configuration Options:
        cli_cmd (str):
            The actual CLI command to execute. Defaults to self.cli_name.

        arg_template (List[str]):
            Template for CLI arguments. Use placeholders:
            {description} - The task description text
            {model} - The model name
            {workspace} - Working directory path
            {timeout} - Timeout in seconds
            {task_type} - Task type (development/review/fix/test/deploy)
            {role} - Agent role

        output_parser (str):
            How to parse CLI output: "raw" | "json" | "regex:<pattern>"

        output_parser_config (Dict):
            Configuration for the chosen parser.

        env_vars (Dict[str, str]):
            Additional environment variables to set.

        pre_exec_hook (str):
            Shell command to run before each task execution.

        post_exec_hook (str):
            Shell command to run after each task execution.

        success_codes (List[int]):
            List of exit codes that indicate success. Default: [0].

        review_support (bool):
            Whether this agent supports code review. Default: False.

        stream_support (bool):
            Whether this agent supports output streaming. Default: False.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model_name: str = "default",
        cli_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            cli_name=config.get("cli_cmd", "custom-agent") if config else "custom-agent",
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            config=config or {},
        )

        # CLI configuration
        self._cli_cmd = self.config.get("cli_cmd", self.cli_name)
        self._arg_template = self.config.get("arg_template", ["{description}"])
        self._output_parser = self.config.get("output_parser", "raw")
        self._output_parser_config = self.config.get("output_parser_config", {})
        self._success_codes = self.config.get("success_codes", [0])
        self._can_stream = self.config.get("stream_support", False)
        self._supports_review = self.config.get("review_support", False)

        # Environment
        self._extra_env = self.config.get("env_vars", {})

        # Hooks
        self._pre_exec_hook = self.config.get("pre_exec_hook")
        self._post_exec_hook = self.config.get("post_exec_hook")

        # Lifecycle hooks
        self._on_before_execute = self.config.get("on_before_execute")
        self._on_after_execute = self.config.get("on_after_execute")

        logger.info(
            "CustomAgentAdapter '%s' initialized (cli=%s, parser=%s)",
            name, self._cli_cmd, self._output_parser,
        )

    # ===== Health Check =====

    async def check_health(self) -> HealthCheckResult:
        """Check if the custom CLI is installed and responsive."""
        try:
            # Check if CLI exists
            if not shutil.which(self._cli_cmd):
                # Try the configured path
                if self.cli_path and self.cli_path.exists():
                    pass  # Will use absolute path
                else:
                    return HealthCheckResult(
                        status=AgentStatus.NOT_FOUND,
                        cli_name=self._cli_cmd,
                        error_message=f"Custom agent CLI '{self._cli_cmd}' not found in PATH",
                    )

            # Test basic execution
            cli_cmd = str(self.cli_path) if self.cli_path else self._cli_cmd
            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )

            if code in self._success_codes:
                return HealthCheckResult(
                    status=AgentStatus.HEALTHY,
                    cli_name=self._cli_cmd,
                    cli_version=stdout.strip().split("\n")[0] if stdout else "unknown",
                    cli_path=cli_cmd,
                    model_name=self.model_name,
                )

            # --version might not be supported; try --help or simple execution
            code2, stdout2, stderr2 = await self._run_subprocess(
                [cli_cmd, "--help"],
                timeout_seconds=10.0,
            )

            if code2 in self._success_codes:
                return HealthCheckResult(
                    status=AgentStatus.HEALTHY,
                    cli_name=self._cli_cmd,
                    cli_version="unknown",
                    cli_path=cli_cmd,
                    model_name=self.model_name,
                )

            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name=self._cli_cmd,
                error_message=stderr2.strip() or "CLI did not respond to --version or --help",
            )

        except FileNotFoundError:
            return HealthCheckResult(
                status=AgentStatus.NOT_FOUND,
                cli_name=self._cli_cmd,
                error_message=f"Custom agent CLI not found: {self._cli_cmd}",
            )
        except Exception as e:
            logger.exception("Custom agent health check failed: %s", e)
            return HealthCheckResult(
                status=AgentStatus.UNHEALTHY,
                cli_name=self._cli_cmd,
                error_message=str(e),
            )

    # ===== Task Execution =====

    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute a task using the custom CLI."""
        started_at = datetime.now(timezone.utc)

        # Pre-execution hook
        if self._pre_exec_hook:
            await self._run_hook(self._pre_exec_hook, context)

        # Build command from template
        cmd = self._build_command(task_input, context)

        try:
            returncode, stdout, stderr = await self._run_subprocess(
                cmd,
                cwd=context.workspace_path,
                env=self._extra_env,
                timeout_seconds=task_input.timeout_seconds,
            )

            execution_time = (datetime.now(timezone.utc) - started_at).total_seconds()
            success = returncode in self._success_codes

            # Parse output
            output = self._parse_output(stdout)

            # Post-execution hook
            if self._post_exec_hook:
                await self._run_hook(self._post_exec_hook, context)

            return TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.SUCCESS if success else TaskResultStatus.FAILED,
                agent_name=self.name,
                agent_role=self.role,
                output=output,
                summary=self._summarize_output(output, 500),
                artifacts=self._extract_artifacts(output, stdout, context.workspace_path),
                errors=[stderr.strip()] if stderr.strip() and not success else [],
                warnings=self._extract_warnings(stderr),
                execution_time_seconds=execution_time,
                started_at=started_at,
                metrics={
                    "exit_code": returncode,
                    "model": self.model_name,
                    "cli": self._cli_cmd,
                    "parser": self._output_parser,
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
        """Attempt code review if supported.

        If review_support is False, returns a default ReviewResult.
        """
        if not self._supports_review:
            return ReviewResult(
                task_id=task_input.task_id,
                agent_name=self.name,
                overall_score=5.0,
                is_approved=True,  # Default to approved if agent doesn't support review
                summary="This agent does not support code review. Defaulting to approved.",
            )

        # Build review task
        review_task = TaskInput(
            task_id=f"{task_input.task_id}_review",
            title=f"Review: {task_input.title}",
            description=f"""Review the following code changes. Output valid JSON:

{{
  "overall_score": <0.0-10.0>,
  "is_approved": <true/false>,
  "issues": [],
  "summary": "<summary>",
  "fixer_instructions": "<guidance>"
}}

Task: {task_input.description}""",
            task_type="review",
            agent_role=self.role,
            timeout_seconds=task_input.timeout_seconds,
        )

        result = await self.execute_task(review_task, context)
        return self._parse_review_from_task_result(result, task_input.task_id)

    # ===== Streaming =====

    async def stream_output(
        self,
        task_id: str,
        context: ExecutionContext,
    ) -> AsyncIterator[str]:
        """Stream output if supported."""
        if not self._can_stream:
            yield "Streaming not supported for this agent."
            return

        cli_cmd = str(self.cli_path) if self.cli_path else self._cli_cmd

        process = await asyncio.create_subprocess_exec(
            cli_cmd, "Continue the task.",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(context.workspace_path),
            env={**os.environ, **self._extra_env},
        )

        if process.stdout:
            async for line in process.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    yield decoded

        await process.wait()

    # ===== Cancellation =====

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel running task."""
        await self.cleanup()
        self._current_task_id = None
        return True

    # ===== Command Building =====

    def _build_command(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> List[str]:
        """Build the full CLI command from the argument template."""
        cli_cmd = str(self.cli_path) if self.cli_path else self._cli_cmd
        cmd = [cli_cmd]

        # Placeholder replacements
        placeholders = {
            "description": task_input.description,
            "model": self.model_name,
            "workspace": str(context.workspace_path),
            "timeout": str(task_input.timeout_seconds),
            "task_type": task_input.task_type,
            "role": self.role,
            "task_id": task_input.task_id,
            "title": task_input.title,
            "priority": str(task_input.priority),
        }

        for arg in self._arg_template:
            resolved = arg
            for key, value in placeholders.items():
                resolved = resolved.replace(f"{{{key}}}", value)
            cmd.append(resolved)

        logger.debug("Custom CLI command: %s", " ".join(cmd))
        return cmd

    # ===== Output Parsing =====

    def _parse_output(self, raw_output: str) -> str:
        """Parse raw CLI output according to the configured parser."""
        if self._output_parser == "raw":
            return raw_output

        if self._output_parser == "json":
            try:
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    data = json.loads(json_match.group())
                    # Extract the meaningful content based on config
                    content_key = self._output_parser_config.get("content_key", "output")
                    if content_key in data:
                        return str(data[content_key])
                    return json.dumps(data, indent=2)
                return raw_output
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON output, returning raw")
                return raw_output

        if self._output_parser.startswith("regex:"):
            pattern = self._output_parser[6:]
            match = re.search(pattern, raw_output, re.DOTALL)
            if match:
                group = self._output_parser_config.get("group", 0)
                try:
                    return match.group(group)
                except IndexError:
                    return match.group(0)
            return raw_output

        logger.warning("Unknown output parser: %s, returning raw", self._output_parser)
        return raw_output

    def _summarize_output(self, output: str, max_len: int) -> str:
        """Generate a summary from the output."""
        if not output:
            return ""
        if len(output) <= max_len:
            return output
        return output[:max_len] + "..."

    def _extract_artifacts(
        self,
        parsed_output: str,
        raw_output: str,
        workspace: Path,
    ) -> List[str]:
        """Extract artifact file paths from output."""
        artifacts = set()
        for text in [parsed_output, raw_output]:
            patterns = [
                r"(?:created|wrote|saved|written to)\s+[`'\"]?([^\s`'\"]+\.[a-zA-Z0-9]+)",
                r"Output\s+written\s+to\s+[`'\"]?([^\s`'\"]+)",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    fpath = match.group(1).strip()
                    resolved = workspace / fpath
                    if resolved.exists():
                        artifacts.add(str(resolved))
        return list(artifacts)

    def _extract_warnings(self, stderr: str) -> List[str]:
        """Extract warnings from stderr."""
        if not stderr:
            return []
        warnings = []
        for line in stderr.splitlines():
            stripped = line.strip()
            if stripped and ("warn" in stripped.lower() or "deprecated" in stripped.lower()):
                warnings.append(stripped)
        return warnings[:10]

    # ===== Review Parsing =====

    def _parse_review_from_task_result(
        self,
        result: TaskResult,
        task_id: str,
    ) -> ReviewResult:
        """Parse review data from a generic task result."""
        if not result.is_successful or not result.output:
            return ReviewResult(
                task_id=task_id,
                agent_name=self.name,
                overall_score=0.0,
                is_approved=False,
                summary="Review task failed",
            )

        try:
            json_match = re.search(r'\{[\s\S]*\}', result.output)
            if json_match:
                data = json.loads(json_match.group())
                review = ReviewResult(
                    task_id=task_id,
                    agent_name=self.name,
                    overall_score=float(data.get("overall_score", 5.0)),
                    is_approved=data.get("is_approved", True),
                    summary=data.get("summary", ""),
                    suggestion_for_fixer=data.get("fixer_instructions"),
                )
                for issue in data.get("issues", []):
                    review.comments.append(ReviewComment(
                        file_path=issue.get("file", ""),
                        line_start=issue.get("line"),
                        severity=issue.get("severity", "info"),
                        category=issue.get("category", "style"),
                        message=issue.get("message", ""),
                        suggestion=issue.get("suggestion"),
                    ))
                return review
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse review JSON: %s", e)

        return ReviewResult(
            task_id=task_id,
            agent_name=self.name,
            overall_score=5.0,
            is_approved=True,
            summary=result.output[:1000],
        )

    # ===== Hooks =====

    async def _run_hook(self, hook: str, context: ExecutionContext) -> None:
        """Run a pre/post execution hook command."""
        try:
            code, stdout, stderr = await self._run_subprocess(
                hook.split(),
                cwd=context.workspace_path,
                timeout_seconds=30.0,
            )
            logger.debug("Hook completed (exit=%d): %s", code, stdout[:200])
        except Exception as e:
            logger.warning("Hook failed: %s", e)
