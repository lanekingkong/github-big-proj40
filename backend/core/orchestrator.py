"""
Agent Orchestration Engine
===========================
Core orchestration engine for AgentForge.
Provides the AgentTeam class and four collaboration modes:
- SEQUENTIAL: Agents execute one after another, each building on previous results.
- PARALLEL: Agents execute simultaneously on independent subtasks.
- REVIEW_LOOP: Developer → Reviewer → Fixer feedback loop until quality gates pass.
- COMMITTEE: Multiple agents independently solve the same problem, results are aggregated.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple, Type

from adapters.base_adapter import (
    BaseAgentAdapter,
    ExecutionContext,
    HealthCheckResult,
    ReviewResult,
    TaskInput,
    TaskResult,
    TaskResultStatus,
)
from core.result_aggregator import ResultAggregator, AggregatedResult

logger = logging.getLogger(__name__)


# =============================================================================
# Collaboration Modes
# =============================================================================

class CollaborationMode(Enum):
    """
    Defines how agents collaborate within a team.

    SEQUENTIAL:
        Agents execute in a defined order. Output of Agent N becomes context
        for Agent N+1. Best for linear workflows like: develop → review → fix.

    PARALLEL:
        Agents execute simultaneously on independent subtasks. Best for
        tasks that can be decomposed into non-interdependent units.

    REVIEW_LOOP:
        Developer generates code → Reviewer inspects → Fixer resolves issues.
        Loops until review score meets threshold or max iterations reached.
        Mirrors human code review workflow.

    COMMITTEE:
        Multiple agents independently solve the same problem. Results are
        aggregated, conflicts detected, and the best solution is selected
        via quality scoring. Best for critical decisions needing consensus.
    """
    SEQUENTIAL = auto()
    PARALLEL = auto()
    REVIEW_LOOP = auto()
    COMMITTEE = auto()


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class TeamConfig:
    """Configuration for an AgentTeam."""
    mode: CollaborationMode = CollaborationMode.SEQUENTIAL
    max_iterations: int = 10
    review_threshold: float = 7.0  # Minimum review score to break REVIEW_LOOP
    require_approval: bool = False  # Whether to require human approval before proceeding
    timeout_per_agent_seconds: float = 600.0
    total_timeout_seconds: float = 3600.0
    failure_strategy: str = "stop"  # stop | skip | retry
    max_retries_per_agent: int = 3
    parallel_max_concurrent: int = 5


@dataclass
class TeamExecutionResult:
    """Result of a complete team execution."""
    mode: CollaborationMode
    task_outputs: List[TaskResult] = field(default_factory=list)
    review_results: List[ReviewResult] = field(default_factory=list)
    aggregated_result: Optional[AggregatedResult] = None
    iterations_completed: int = 0
    is_successful: bool = False
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_agent_time_seconds(self) -> float:
        return sum(
            r.execution_time_seconds or 0.0
            for r in self.task_outputs
        )

    @property
    def failed_tasks(self) -> List[TaskResult]:
        return [r for r in self.task_outputs if not r.is_successful]


@dataclass
class AgentDescriptor:
    """Descriptor for an agent within a team."""
    adapter: BaseAgentAdapter
    role: str
    assigned_tasks: List[TaskInput] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # role names this depends on


# =============================================================================
# Task Pipeline
# =============================================================================

class TaskPipeline:
    """
    A pipeline of tasks to be executed by agents.
    Supports chaining, branching, and conditional task generation.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._stages: List[TaskPipelineStage] = []
        self._on_complete_callbacks: List[Callable] = []

    def add_stage(
        self,
        stage_name: str,
        agent_role: str,
        task_factory: Callable[[List[TaskResult]], TaskInput],
        depends_on: Optional[List[str]] = None,
    ) -> TaskPipeline:
        """Add a pipeline stage.

        Args:
            stage_name: Unique stage identifier.
            agent_role: Role of agent that executes this stage.
            task_factory: Function that generates TaskInput from previous results.
            depends_on: Stage names this stage depends on.
        """
        self._stages.append(TaskPipelineStage(
            name=stage_name,
            agent_role=agent_role,
            task_factory=task_factory,
            depends_on=depends_on or [],
        ))
        return self

    def on_complete(self, callback: Callable[[TeamExecutionResult], Any]) -> TaskPipeline:
        """Register a callback to invoke on pipeline completion."""
        self._on_complete_callbacks.append(callback)
        return self

    async def execute(
        self,
        team: "AgentTeam",
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """Execute the pipeline using the given team."""
        results: Dict[str, TaskResult] = {}
        completed_stages: Set[str] = set()
        stage_results: List[TaskResult] = []

        while len(completed_stages) < len(self._stages):
            for stage in self._stages:
                if stage.name in completed_stages:
                    continue
                if not all(dep in completed_stages for dep in stage.depends_on):
                    continue

                logger.info("Pipeline '%s': executing stage '%s'", self.name, stage.name)

                resolved_results = [results[name] for name in stage.depends_on if name in results]
                task_input = stage.task_factory(resolved_results)

                agent = team.get_agent_by_role(stage.agent_role)
                if not agent:
                    logger.warning("No agent found for role '%s' in stage '%s'", stage.agent_role, stage.name)
                    continue

                result = await agent.execute_task(task_input, context)
                results[stage.name] = result
                stage_results.append(result)
                completed_stages.add(stage.name)
                break  # Re-evaluate which stages are now ready

        execution_result = TeamExecutionResult(
            mode=CollaborationMode.SEQUENTIAL,
            task_outputs=stage_results,
            iterations_completed=len(stage_results),
            is_successful=all(r.is_successful for r in stage_results),
        )

        for callback in self._on_complete_callbacks:
            try:
                callback(execution_result)
            except Exception as e:
                logger.exception("Pipeline callback failed: %s", e)

        return execution_result


@dataclass
class TaskPipelineStage:
    """A single stage within a TaskPipeline."""
    name: str
    agent_role: str
    task_factory: Callable[[List[TaskResult]], TaskInput]
    depends_on: List[str] = field(default_factory=list)


# =============================================================================
# AgentTeam — Core Orchestration Class
# =============================================================================

class AgentTeam:
    """
    The central orchestration class for AgentForge.

    An AgentTeam manages a collection of agent adapters with assigned roles
    and orchestrates their collaboration through one of four modes:
    SEQUENTIAL, PARALLEL, REVIEW_LOOP, or COMMITTEE.

    Usage:
        team = AgentTeam("my-team", config=TeamConfig(mode=CollaborationMode.REVIEW_LOOP))
        team.add_agent(claude_adapter, role="developer")
        team.add_agent(gemini_adapter, role="reviewer")
        team.add_agent(codex_adapter, role="fixer")
        result = await team.execute(task_inputs, context)
    """

    def __init__(
        self,
        name: str,
        config: Optional[TeamConfig] = None,
        result_aggregator: Optional[ResultAggregator] = None,
    ):
        self.name = name
        self.config = config or TeamConfig()
        self._agents: Dict[str, AgentDescriptor] = {}  # role → descriptor
        self._result_aggregator = result_aggregator or ResultAggregator()
        self._health_cache: Dict[str, HealthCheckResult] = {}
        self._cancel_event = asyncio.Event()

        logger.info("AgentTeam '%s' initialized with mode=%s", name, self.config.mode)

    # ===== Agent Management =====

    def add_agent(
        self,
        adapter: BaseAgentAdapter,
        role: str,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """Register an agent in the team with a specific role.

        Args:
            adapter: The agent adapter instance.
            role: The agent's role (developer, reviewer, fixer, tester, deployer).
            dependencies: Other roles this agent depends on.

        Raises:
            ValueError: If the role is already taken.
        """
        if role in self._agents:
            raise ValueError(f"Role '{role}' is already assigned to agent '{self._agents[role].adapter.name}'")

        self._agents[role] = AgentDescriptor(
            adapter=adapter,
            role=role,
            dependencies=dependencies or [],
        )
        logger.info("Team '%s': added agent '%s' as '%s'", self.name, adapter.name, role)

    def remove_agent(self, role: str) -> Optional[BaseAgentAdapter]:
        """Remove an agent from the team by role."""
        descriptor = self._agents.pop(role, None)
        if descriptor:
            logger.info("Team '%s': removed agent '%s' (role=%s)", self.name, descriptor.adapter.name, role)
            return descriptor.adapter
        return None

    def get_agent_by_role(self, role: str) -> Optional[BaseAgentAdapter]:
        """Get the agent adapter for a given role."""
        descriptor = self._agents.get(role)
        return descriptor.adapter if descriptor else None

    def list_agents(self) -> Dict[str, str]:
        """Return a mapping of role → agent name."""
        return {role: desc.adapter.name for role, desc in self._agents.items()}

    def list_roles(self) -> List[str]:
        """Return all assigned roles in dependency order."""
        return self._topological_sort()

    # ===== Health Checks =====

    async def check_all_health(self) -> Dict[str, HealthCheckResult]:
        """Run health checks on all agents in parallel."""
        async def check_one(role: str, adapter: BaseAgentAdapter) -> Tuple[str, HealthCheckResult]:
            result = await adapter.check_health()
            return role, result

        tasks = [
            check_one(role, desc.adapter)
            for role, desc in self._agents.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_map: Dict[str, HealthCheckResult] = {}
        for item in results:
            if isinstance(item, Exception):
                logger.error("Health check error: %s", item)
                continue
            role, result = item
            health_map[role] = result

        self._health_cache = health_map
        return health_map

    @property
    def all_healthy(self) -> bool:
        """Check if all agents are healthy."""
        return all(r.is_healthy for r in self._health_cache.values())

    # ===== Execution =====

    async def execute(
        self,
        task_inputs: List[TaskInput],
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """Execute tasks using the team's collaboration mode.

        Args:
            task_inputs: List of tasks to execute.
            context: Shared execution context.

        Returns:
            TeamExecutionResult with all agent outputs.
        """
        self._cancel_event.clear()

        mode_dispatcher = {
            CollaborationMode.SEQUENTIAL: self._execute_sequential,
            CollaborationMode.PARALLEL: self._execute_parallel,
            CollaborationMode.REVIEW_LOOP: self._execute_review_loop,
            CollaborationMode.COMMITTEE: self._execute_committee,
        }

        handler = mode_dispatcher.get(self.config.mode)
        if not handler:
            raise ValueError(f"Unknown collaboration mode: {self.config.mode}")

        logger.info(
            "Team '%s': starting execution with mode=%s, tasks=%d",
            self.name, self.config.mode.name, len(task_inputs),
        )

        try:
            result = await asyncio.wait_for(
                handler(task_inputs, context),
                timeout=self.config.total_timeout_seconds,
            )
            result.started_at = context.metadata.get("started_at")
            result.completed_at = datetime.now(timezone.utc)
            logger.info(
                "Team '%s': execution complete, successful=%s, time=%.1fs",
                self.name, result.is_successful,
                (result.completed_at - (result.started_at or result.completed_at)).total_seconds(),
            )
            return result
        except asyncio.TimeoutError:
            logger.error("Team '%s': total timeout exceeded (%.1fs)", self.name, self.config.total_timeout_seconds)
            return TeamExecutionResult(
                mode=self.config.mode,
                is_successful=False,
                error_message=f"Team execution timed out after {self.config.total_timeout_seconds}s",
            )

    async def cancel(self) -> None:
        """Cancel all running team operations."""
        self._cancel_event.set()
        for desc in self._agents.values():
            await desc.adapter.cleanup()
        logger.warning("Team '%s': all operations cancelled", self.name)

    # ===== Mode Implementations =====

    async def _execute_sequential(
        self,
        task_inputs: List[TaskInput],
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """SEQUENTIAL mode: agents execute one after another, passing results forward."""
        results: List[TaskResult] = []
        ordered_roles = self.list_roles()

        for task_input in task_inputs:
            role = task_input.agent_role
            agent = self.get_agent_by_role(role)
            if not agent:
                logger.warning("No agent for role '%s', skipping task '%s'", role, task_input.task_id)
                continue

            # Enrich context with previous results
            enriched_context = ExecutionContext(
                project_path=context.project_path,
                workspace_path=context.workspace_path,
                task_id=task_input.task_id,
                previous_results=[r.__dict__ for r in results],
                environment=context.environment,
                constraints=context.constraints,
                metadata=context.metadata,
            )

            result = await self._execute_with_retry(agent, task_input, enriched_context)
            results.append(result)

            if not result.is_successful and self.config.failure_strategy == "stop":
                break

        return TeamExecutionResult(
            mode=CollaborationMode.SEQUENTIAL,
            task_outputs=results,
            is_successful=all(r.is_successful for r in results),
        )

    async def _execute_parallel(
        self,
        task_inputs: List[TaskInput],
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """PARALLEL mode: agents execute simultaneously on independent tasks."""
        semaphore = asyncio.Semaphore(self.config.parallel_max_concurrent)

        async def run_one(task_input: TaskInput) -> TaskResult:
            async with semaphore:
                agent = self.get_agent_by_role(task_input.agent_role)
                if not agent:
                    return TaskResult(
                        task_id=task_input.task_id,
                        status=TaskResultStatus.FAILED,
                        agent_name="unknown",
                        agent_role=task_input.agent_role,
                        errors=[f"No agent for role '{task_input.agent_role}'"],
                    )
                return await self._execute_with_retry(agent, task_input, context)

        tasks = [run_one(ti) for ti in task_inputs]
        results = await asyncio.gather(*tasks)

        return TeamExecutionResult(
            mode=CollaborationMode.PARALLEL,
            task_outputs=list(results),
            is_successful=all(r.is_successful for r in results),
        )

    async def _execute_review_loop(
        self,
        task_inputs: List[TaskInput],
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """REVIEW_LOOP mode: Developer → Reviewer → Fixer loop."""
        developer = self.get_agent_by_role("developer")
        reviewer = self.get_agent_by_role("reviewer")
        fixer = self.get_agent_by_role("fixer")

        if not developer:
            return TeamExecutionResult(
                mode=CollaborationMode.REVIEW_LOOP,
                is_successful=False,
                error_message="No developer agent configured",
            )

        all_results: List[TaskResult] = []
        review_results: List[ReviewResult] = []

        # Find the primary development task
        dev_task = next((t for t in task_inputs if t.agent_role == "developer"), None)
        if not dev_task:
            dev_task = task_inputs[0] if task_inputs else None
        if not dev_task:
            return TeamExecutionResult(
                mode=CollaborationMode.REVIEW_LOOP,
                is_successful=False,
                error_message="No tasks provided",
            )

        for iteration in range(self.config.max_iterations):
            if self._cancel_event.is_set():
                break

            logger.info("Review loop iteration %d/%d", iteration + 1, self.config.max_iterations)

            # Phase 1: Develop (or Fix)
            if iteration == 0:
                result = await self._execute_with_retry(developer, dev_task, context)
            else:
                if not fixer:
                    logger.warning("No fixer agent, breaking review loop")
                    break
                fix_task = TaskInput(
                    task_id=f"{dev_task.task_id}_fix_{iteration}",
                    title=f"Fix issues (iteration {iteration})",
                    description=f"Fix the following review issues:\n{last_review.suggestion_for_fixer or 'See review comments'}",
                    task_type="fix",
                    agent_role="fixer",
                    timeout_seconds=dev_task.timeout_seconds,
                )
                result = await self._execute_with_retry(fixer, fix_task, context)

            all_results.append(result)

            # Phase 2: Review
            if not reviewer or not result.is_successful:
                break

            review = await reviewer.review_code(dev_task, context)
            review_results.append(review)

            logger.info(
                "Review score: %.1f/10 (threshold: %.1f), approved=%s",
                review.overall_score, self.config.review_threshold, review.is_approved,
            )

            if review.overall_score >= self.config.review_threshold or review.is_approved:
                logger.info("Review loop passed after %d iterations", iteration + 1)
                break

            last_review = review

        return TeamExecutionResult(
            mode=CollaborationMode.REVIEW_LOOP,
            task_outputs=all_results,
            review_results=review_results,
            iterations_completed=len(all_results),
            is_successful=all_results[-1].is_successful if all_results else False,
        )

    async def _execute_committee(
        self,
        task_inputs: List[TaskInput],
        context: ExecutionContext,
    ) -> TeamExecutionResult:
        """COMMITTEE mode: multiple agents solve the same problem, results aggregated."""
        primary_task = task_inputs[0] if task_inputs else None
        if not primary_task:
            return TeamExecutionResult(
                mode=CollaborationMode.COMMITTEE,
                is_successful=False,
                error_message="No tasks provided",
            )

        # Assign all agents the same task
        async def run_agent(role: str, adapter: BaseAgentAdapter) -> Tuple[str, TaskResult]:
            task_copy = TaskInput(
                task_id=f"{primary_task.task_id}_{role}",
                title=primary_task.title,
                description=primary_task.description,
                task_type=primary_task.task_type,
                agent_role=role,
                priority=primary_task.priority,
                timeout_seconds=primary_task.timeout_seconds,
                extra_params=primary_task.extra_params,
            )
            result = await self._execute_with_retry(adapter, task_copy, context)
            return role, result

        tasks = [
            run_agent(role, desc.adapter)
            for role, desc in self._agents.items()
        ]
        role_results = await asyncio.gather(*tasks)

        results = [r for _, r in role_results]
        role_map = {role: r for role, r in role_results}

        # Aggregate results
        aggregated = self._result_aggregator.aggregate(results)

        return TeamExecutionResult(
            mode=CollaborationMode.COMMITTEE,
            task_outputs=results,
            aggregated_result=aggregated,
            is_successful=aggregated.is_successful if aggregated else False,
        )

    # ===== Helpers =====

    async def _execute_with_retry(
        self,
        agent: BaseAgentAdapter,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute a task with retry logic."""
        last_error: Optional[str] = None

        for attempt in range(self.config.max_retries_per_agent + 1):
            try:
                logger.debug(
                    "Agent '%s' executing task '%s' (attempt %d/%d)",
                    agent.name, task_input.task_id, attempt + 1, self.config.max_retries_per_agent + 1,
                )
                result = await asyncio.wait_for(
                    agent.execute_task(task_input, context),
                    timeout=self.config.timeout_per_agent_seconds,
                )
                if result.is_successful or self.config.failure_strategy != "retry":
                    return result
                last_error = result.errors[0] if result.errors else "Unknown error"
            except asyncio.TimeoutError:
                last_error = f"Agent '{agent.name}' timed out"
                logger.warning(last_error)
            except Exception as e:
                last_error = str(e)
                logger.exception("Agent '%s' failed: %s", agent.name, e)

        return TaskResult(
            task_id=task_input.task_id,
            status=TaskResultStatus.FAILED,
            agent_name=agent.name,
            agent_role=agent.role,
            errors=[f"Failed after {self.config.max_retries_per_agent + 1} attempts: {last_error}"],
        )

    def _topological_sort(self) -> List[str]:
        """Sort roles by dependency order using Kahn's algorithm."""
        in_degree: Dict[str, int] = {role: 0 for role in self._agents}
        for role, desc in self._agents.items():
            for dep in desc.dependencies:
                if dep in in_degree:
                    in_degree[role] += 1

        queue = [role for role, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            role = queue.pop(0)
            result.append(role)
            for other, desc in self._agents.items():
                if role in desc.dependencies:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        return result


# =============================================================================
# Orchestrator — Top-Level Facade
# =============================================================================

class Orchestrator:
    """
    Top-level facade for the AgentForge orchestration engine.

    Manages multiple AgentTeams and provides a simplified API for
    creating teams, registering agents, and executing workflows.
    """

    def __init__(self):
        self._teams: Dict[str, AgentTeam] = {}
        self._adapters: Dict[str, BaseAgentAdapter] = {}
        logger.info("Orchestrator initialized")

    def register_adapter(self, adapter: BaseAgentAdapter) -> None:
        """Register an agent adapter for use in teams."""
        self._adapters[adapter.name] = adapter
        logger.info("Registered adapter: %s", adapter.name)

    def unregister_adapter(self, name: str) -> Optional[BaseAgentAdapter]:
        """Remove a registered adapter."""
        return self._adapters.pop(name, None)

    def create_team(
        self,
        name: str,
        config: Optional[TeamConfig] = None,
    ) -> AgentTeam:
        """Create a new agent team.

        Args:
            name: Unique team name.
            config: Team configuration. Defaults to SEQUENTIAL mode.

        Returns:
            The created AgentTeam instance.

        Raises:
            ValueError: If a team with this name already exists.
        """
        if name in self._teams:
            raise ValueError(f"Team '{name}' already exists")
        team = AgentTeam(name, config)
        self._teams[name] = team
        return team

    def get_team(self, name: str) -> Optional[AgentTeam]:
        """Get a team by name."""
        return self._teams.get(name)

    def remove_team(self, name: str) -> Optional[AgentTeam]:
        """Remove a team."""
        return self._teams.pop(name, None)

    def list_teams(self) -> Dict[str, CollaborationMode]:
        """List all teams and their modes."""
        return {name: team.config.mode for name, team in self._teams.items()}

    async def health_check_all(self) -> Dict[str, Dict[str, HealthCheckResult]]:
        """Run health checks on all teams."""
        results = {}
        for name, team in self._teams.items():
            results[name] = await team.check_all_health()
        return results

    async def shutdown(self) -> None:
        """Cleanup all teams and adapters."""
        for team in self._teams.values():
            await team.cancel()
        for adapter in self._adapters.values():
            await adapter.cleanup()
        logger.info("Orchestrator shutdown complete")