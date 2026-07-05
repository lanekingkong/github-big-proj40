"""
Pipeline Engine
===============
Predefined pipeline templates and a flexible Pipeline class for AgentForge.

Provides reusable pipelines for common workflows:
- code_generation: Plan → Develop → Test
- code_review: Develop → Review → Fix → Verify
- full_project: Plan → Develop → Review → Fix → Test → Deploy

Each pipeline is configurable and composable.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from adapters.base_adapter import (
    BaseAgentAdapter,
    ExecutionContext,
    ReviewResult,
    TaskInput,
    TaskResult,
    TaskResultStatus,
)
from core.orchestrator import AgentTeam, CollaborationMode, TeamConfig, TeamExecutionResult
from core.result_aggregator import AggregatedResult, ResultAggregator

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Types
# =============================================================================

class PipelineState(Enum):
    """Lifecycle states for a pipeline execution."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class PipelineStage:
    """
    A single stage in a pipeline.

    Each stage defines:
    - A role that executes it
    - How to construct the task from previous results
    - Whether human approval is needed before/after
    - Skip conditions for intelligent flow control
    """
    name: str
    role: str
    description: str = ""
    task_type: str = "development"
    priority: int = 1
    timeout_seconds: int = 600
    require_prior_results: bool = True
    require_approval: bool = False
    skip_if: Optional[Callable[[List[TaskResult]], bool]] = None
    task_factory: Optional[Callable[[List[TaskResult], ExecutionContext], TaskInput]] = None
    on_start: Optional[Callable[[PipelineStage, ExecutionContext], Any]] = None
    on_complete: Optional[Callable[[PipelineStage, TaskResult], Any]] = None
    on_error: Optional[Callable[[PipelineStage, Exception], Any]] = None


@dataclass
class PipelineExecutionResult:
    """Complete result of a pipeline execution."""
    pipeline_name: str
    state: PipelineState
    stage_results: Dict[str, TaskResult] = field(default_factory=dict)
    aggregated_result: Optional[AggregatedResult] = None
    stage_order: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.state == PipelineState.COMPLETED

    @property
    def execution_time_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# =============================================================================
# Pipeline Class
# =============================================================================

class Pipeline:
    """
    Configurable execution pipeline for orchestrating multi-stage workflows.

    A Pipeline chains multiple PipelineStage objects and executes them
    using an AgentTeam. Supports:
    - Sequential and conditional stage execution
    - Result passing between stages
    - Approval gates
    - Error handling with configurable strategies
    - Progress tracking and event hooks

    Usage:
        pipeline = Pipeline("code_review")
        pipeline.add_stage(develop_stage)
        pipeline.add_stage(review_stage, depends_on=["develop"])
        result = await pipeline.run(team, context)
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        team: Optional[AgentTeam] = None,
    ):
        self.name = name
        self.description = description
        self._team = team
        self._stages: Dict[str, PipelineStage] = {}
        self._stage_order: List[str] = []
        self._dependencies: Dict[str, List[str]] = {}  # stage_name → list of stage names it depends on

        # Configuration
        self.continue_on_error: bool = False
        self.require_approval: bool = False
        self.max_total_timeout_seconds: float = 3600.0

        # Hooks
        self._on_start_hooks: List[Callable] = []
        self._on_complete_hooks: List[Callable] = []
        self._on_error_hooks: List[Callable] = []

        # State
        self.state: PipelineState = PipelineState.IDLE
        self._cancel_event = asyncio.Event()

        logger.info("Pipeline '%s' created", name)

    # ===== Stage Management =====

    def add_stage(
        self,
        stage: PipelineStage,
        depends_on: Optional[List[str]] = None,
        after: Optional[str] = None,
    ) -> Pipeline:
        """Add a stage to the pipeline.

        Args:
            stage: The pipeline stage to add.
            depends_on: Stages that must complete before this one.
            after: Convenience: insert after this stage name.

        Returns:
            self for chaining.

        Raises:
            ValueError: If a stage with this name already exists.
        """
        if stage.name in self._stages:
            raise ValueError(f"Stage '{stage.name}' already exists in pipeline '{self.name}'")

        self._stages[stage.name] = stage
        self._dependencies[stage.name] = depends_on or []

        # Handle 'after' convenience parameter
        if after and after in self._stage_order:
            idx = self._stage_order.index(after)
            self._stage_order.insert(idx + 1, stage.name)
        else:
            self._stage_order.append(stage.name)

        logger.debug("Pipeline '%s': added stage '%s' (role=%s)", self.name, stage.name, stage.role)
        return self

    def remove_stage(self, stage_name: str) -> bool:
        """Remove a stage from the pipeline."""
        if stage_name not in self._stages:
            return False
        del self._stages[stage_name]
        self._dependencies.pop(stage_name, None)
        if stage_name in self._stage_order:
            self._stage_order.remove(stage_name)
        logger.debug("Pipeline '%s': removed stage '%s'", self.name, stage_name)
        return True

    def get_stage(self, stage_name: str) -> Optional[PipelineStage]:
        """Get a stage by name."""
        return self._stages.get(stage_name)

    def list_stages(self) -> List[PipelineStage]:
        """List all stages in execution order."""
        return [self._stages[name] for name in self._stage_order]

    # ===== Team Binding =====

    def set_team(self, team: AgentTeam) -> None:
        """Bind an AgentTeam to this pipeline."""
        self._team = team
        logger.info("Pipeline '%s': bound to team '%s'", self.name, team.name)

    # ===== Execution =====

    async def run(
        self,
        team: Optional[AgentTeam] = None,
        context: Optional[ExecutionContext] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> PipelineExecutionResult:
        """Execute the pipeline.

        Args:
            team: The AgentTeam to use. Overrides any previously bound team.
            context: The execution context.
            extra_params: Additional parameters passed to task factories.

        Returns:
            PipelineExecutionResult with stage results.

        Raises:
            ValueError: If no team is provided and none was bound.
            RuntimeError: If the pipeline is already running.
        """
        if self.state == PipelineState.RUNNING:
            raise RuntimeError(f"Pipeline '{self.name}' is already running")

        active_team = team or self._team
        if not active_team:
            raise ValueError(f"No team bound to pipeline '{self.name}'")

        ctx = context or ExecutionContext(
            project_path=Path("."),
            workspace_path=Path("."),
            task_id=f"pipeline_{self.name}",
        )

        if extra_params:
            ctx.metadata.update(extra_params)

        self.state = PipelineState.RUNNING
        self._cancel_event.clear()

        result = PipelineExecutionResult(
            pipeline_name=self.name,
            state=PipelineState.RUNNING,
            stage_order=list(self._stage_order),
            started_at=datetime.now(timezone.utc),
        )

        # Fire start hooks
        for hook in self._on_start_hooks:
            try:
                hook(self, ctx)
            except Exception as e:
                logger.exception("Start hook failed: %s", e)

        logger.info("Pipeline '%s': starting execution (%d stages)", self.name, len(self._stages))

        try:
            completed_stages: Set[str] = set()
            stage_results: Dict[str, TaskResult] = {}

            async with asyncio.timeout(self.max_total_timeout_seconds):
                while len(completed_stages) < len(self._stages):
                    if self._cancel_event.is_set():
                        result.state = PipelineState.CANCELLED
                        break

                    progress_made = False
                    for stage_name in self._stage_order:
                        if stage_name in completed_stages:
                            continue

                        stage = self._stages[stage_name]
                        deps = self._dependencies.get(stage_name, [])

                        # Check dependencies
                        if not all(dep in completed_stages for dep in deps):
                            continue

                        # Check skip condition
                        prior_results = [stage_results[name] for name in self._stage_order if name in stage_results]
                        if stage.skip_if and stage.skip_if(prior_results):
                            logger.info("Pipeline '%s': skipping stage '%s'", self.name, stage_name)
                            completed_stages.add(stage_name)
                            continue

                        # Execute stage
                        logger.info("Pipeline '%s': executing stage '%s'", self.name, stage_name)
                        stage_result = await self._execute_stage(stage, ctx, prior_results, active_team)
                        stage_results[stage_name] = stage_result
                        completed_stages.add(stage_name)
                        progress_made = True

                        if not stage_result.is_successful and not self.continue_on_error:
                            result.state = PipelineState.FAILED
                            result.errors.append(f"Stage '{stage_name}' failed: {stage_result.errors}")
                            break

                    if not progress_made and not self._cancel_event.is_set():
                        logger.error("Pipeline '%s': deadlock detected – no stage can progress", self.name)
                        result.state = PipelineState.FAILED
                        result.errors.append("Deadlock: no stage can progress")
                        break

            result.stage_results = stage_results
            if result.state == PipelineState.RUNNING:
                result.state = PipelineState.COMPLETED

            # Aggregate results
            if len(stage_results) > 1:
                result.aggregated_result = ResultAggregator().aggregate(list(stage_results.values()))

        except asyncio.TimeoutError:
            logger.error("Pipeline '%s': timeout after %.1fs", self.name, self.max_total_timeout_seconds)
            result.state = PipelineState.FAILED
            result.errors.append(f"Pipeline timed out after {self.max_total_timeout_seconds}s")
        except Exception as e:
            logger.exception("Pipeline '%s': error: %s", self.name, e)
            result.state = PipelineState.FAILED
            result.errors.append(str(e))

            for hook in self._on_error_hooks:
                try:
                    hook(self, e)
                except Exception as he:
                    logger.exception("Error hook failed: %s", he)

        finally:
            result.completed_at = datetime.now(timezone.utc)
            self.state = result.state

            # Fire complete hooks
            for hook in self._on_complete_hooks:
                try:
                    hook(self, result)
                except Exception as e:
                    logger.exception("Complete hook failed: %s", e)

            logger.info(
                "Pipeline '%s': finished (state=%s, stages=%d/%d, time=%.1fs)",
                self.name,
                result.state.name,
                len(result.stage_results),
                len(self._stages),
                result.execution_time_seconds or 0.0,
            )

        return result

    async def _execute_stage(
        self,
        stage: PipelineStage,
        context: ExecutionContext,
        prior_results: List[TaskResult],
        team: AgentTeam,
    ) -> TaskResult:
        """Execute a single pipeline stage."""
        # Fire stage start hook
        if stage.on_start:
            try:
                stage.on_start(stage, context)
            except Exception as e:
                logger.exception("Stage start hook failed: %s", e)

        # Build task input
        if stage.task_factory:
            task_input = stage.task_factory(prior_results, context)
        else:
            task_input = TaskInput(
                task_id=f"{self.name}_{stage.name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                title=stage.name,
                description=stage.description,
                task_type=stage.task_type,
                agent_role=stage.role,
                priority=stage.priority,
                timeout_seconds=stage.timeout_seconds,
            )

        # Handle approval if required
        if stage.require_approval or self.require_approval:
            logger.info("Pipeline '%s': stage '%s' requires approval", self.name, stage.name)
            # Approval logic to be integrated with the UI layer
            # For now, log and proceed

        # Execute via team
        agent = team.get_agent_by_role(stage.role)
        if not agent:
            return TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.FAILED,
                agent_name="unknown",
                agent_role=stage.role,
                errors=[f"No agent with role '{stage.role}' in team"],
            )

        enriched_context = ExecutionContext(
            project_path=context.project_path,
            workspace_path=context.workspace_path,
            task_id=task_input.task_id,
            previous_results=[r.__dict__ for r in prior_results],
            environment=context.environment,
            constraints=context.constraints,
            metadata=context.metadata,
        )

        try:
            result = await agent.execute_task(task_input, enriched_context)
        except Exception as e:
            result = TaskResult(
                task_id=task_input.task_id,
                status=TaskResultStatus.FAILED,
                agent_name=agent.name,
                agent_role=stage.role,
                errors=[str(e)],
            )
            if stage.on_error:
                try:
                    stage.on_error(stage, e)
                except Exception as he:
                    logger.exception("Stage error hook failed: %s", he)

        # Fire stage complete hook
        if stage.on_complete:
            try:
                stage.on_complete(stage, result)
            except Exception as e:
                logger.exception("Stage complete hook failed: %s", e)

        return result

    # ===== Control =====

    async def cancel(self) -> None:
        """Cancel pipeline execution."""
        self._cancel_event.set()
        logger.info("Pipeline '%s': cancellation requested", self.name)

    async def reset(self) -> None:
        """Reset pipeline to IDLE state."""
        if self.state == PipelineState.RUNNING:
            await self.cancel()
        self.state = PipelineState.IDLE
        self._cancel_event.clear()
        logger.info("Pipeline '%s': reset to IDLE", self.name)

    # ===== Hooks =====

    def on_start(self, hook: Callable) -> Callable:
        self._on_start_hooks.append(hook)
        return hook

    def on_complete(self, hook: Callable) -> Callable:
        self._on_complete_hooks.append(hook)
        return hook

    def on_error(self, hook: Callable) -> Callable:
        self._on_error_hooks.append(hook)
        return hook


# =============================================================================
# Predefined Pipeline Templates
# =============================================================================

class PipelineTemplates:
    """
    Factory class providing predefined pipeline templates for common workflows.
    """

    @staticmethod
    def code_generation(name: str = "code_generation") -> Pipeline:
        """
        Plan → Develop → Test pipeline.

        Suitable for:
        - Greenfield feature development
        - Module implementation from design specs
        - Code generation with quality verification
        """
        pipeline = Pipeline(
            name=name,
            description="Plan → Develop → Test workflow",
        )
        pipeline.add_stage(PipelineStage(
            name="plan",
            role="developer",
            description="Analyze requirements and create implementation plan",
            task_type="development",
            priority=1,
            timeout_seconds=300,
        ))
        pipeline.add_stage(PipelineStage(
            name="develop",
            role="developer",
            description="Implement the code according to the plan",
            task_type="development",
            priority=1,
            timeout_seconds=900,
            require_prior_results=True,
        ), depends_on=["plan"])
        pipeline.add_stage(PipelineStage(
            name="test",
            role="tester",
            description="Write and run tests for the implemented code",
            task_type="test",
            priority=2,
            timeout_seconds=600,
        ), depends_on=["develop"])
        pipeline.add_stage(PipelineStage(
            name="fix",
            role="fixer",
            description="Fix any test failures",
            task_type="fix",
            priority=2,
            timeout_seconds=600,
            skip_if=lambda results: PipelineTemplates._all_tests_passed(results),
        ), depends_on=["test"])
        return pipeline

    @staticmethod
    def code_review(name: str = "code_review") -> Pipeline:
        """
        Develop → Review → Fix → Verify pipeline.

        Suitable for:
        - Pull request reviews
        - Code quality audits
        - Refactoring with quality gates
        """
        pipeline = Pipeline(
            name=name,
            description="Develop → Review → Fix → Verify workflow",
        )
        pipeline.add_stage(PipelineStage(
            name="develop",
            role="developer",
            description="Write or modify the code",
            task_type="development",
            priority=1,
            timeout_seconds=900,
        ))
        pipeline.add_stage(PipelineStage(
            name="review",
            role="reviewer",
            description="Review code for quality, security, and best practices",
            task_type="review",
            priority=1,
            timeout_seconds=600,
        ), depends_on=["develop"])
        pipeline.add_stage(PipelineStage(
            name="fix",
            role="fixer",
            description="Address review findings and suggestions",
            task_type="fix",
            priority=2,
            timeout_seconds=600,
            skip_if=lambda results: PipelineTemplates._review_approved(results),
        ), depends_on=["review"])
        pipeline.add_stage(PipelineStage(
            name="verify",
            role="tester",
            description="Verify fixes and run regression tests",
            task_type="test",
            priority=2,
            timeout_seconds=600,
        ), depends_on=["fix"])
        return pipeline

    @staticmethod
    def full_project(name: str = "full_project") -> Pipeline:
        """
        Plan → Develop → Review → Fix → Test → Deploy pipeline.

        Suitable for:
        - End-to-end project development
        - Feature delivery from spec to production
        - Major releases
        """
        pipeline = Pipeline(
            name=name,
            description="End-to-end: Plan → Develop → Review → Fix → Test → Deploy",
        )
        pipeline.add_stage(PipelineStage(
            name="plan",
            role="developer",
            description="Analyze requirements, design architecture, create task breakdown",
            task_type="development",
            priority=1,
            timeout_seconds=600,
        ))
        pipeline.add_stage(PipelineStage(
            name="develop",
            role="developer",
            description="Implement all planned tasks",
            task_type="development",
            priority=1,
            timeout_seconds=1800,
        ), depends_on=["plan"])
        pipeline.add_stage(PipelineStage(
            name="review",
            role="reviewer",
            description="Comprehensive code review",
            task_type="review",
            priority=1,
            timeout_seconds=900,
        ), depends_on=["develop"])
        pipeline.add_stage(PipelineStage(
            name="fix",
            role="fixer",
            description="Resolve review findings",
            task_type="fix",
            priority=2,
            timeout_seconds=900,
        ), depends_on=["review"])
        pipeline.add_stage(PipelineStage(
            name="test",
            role="tester",
            description="Full test suite execution and coverage analysis",
            task_type="test",
            priority=2,
            timeout_seconds=1200,
        ), depends_on=["fix"])
        pipeline.add_stage(PipelineStage(
            name="deploy",
            role="deployer",
            description="Deploy to staging/production environment",
            task_type="deploy",
            priority=3,
            timeout_seconds=600,
            require_approval=True,
        ), depends_on=["test"])
        return pipeline

    @staticmethod
    def quick_fix(name: str = "quick_fix") -> Pipeline:
        """
        Analyze → Fix → Verify pipeline for bug fixes.

        Suitable for:
        - Urgent bug fixes
        - Hotfix deployment
        - Minor corrections
        """
        pipeline = Pipeline(
            name=name,
            description="Quick: Analyze → Fix → Verify",
        )
        pipeline.add_stage(PipelineStage(
            name="analyze",
            role="developer",
            description="Analyze the bug and identify root cause",
            task_type="development",
            priority=1,
            timeout_seconds=300,
        ))
        pipeline.add_stage(PipelineStage(
            name="fix",
            role="fixer",
            description="Implement the fix",
            task_type="fix",
            priority=1,
            timeout_seconds=600,
        ), depends_on=["analyze"])
        pipeline.add_stage(PipelineStage(
            name="verify",
            role="tester",
            description="Verify the fix with targeted tests",
            task_type="test",
            priority=2,
            timeout_seconds=300,
        ), depends_on=["fix"])
        return pipeline

    @staticmethod
    def committee_review(name: str = "committee_review") -> Pipeline:
        """
        Multiple agents independently review the same code changes.

        Suitable for:
        - Critical code reviews
        - Security audits
        - Architecture decisions
        """
        pipeline = Pipeline(
            name=name,
            description="Multi-agent independent review and consensus",
        )
        pipeline.add_stage(PipelineStage(
            name="develop",
            role="developer",
            description="Present the code changes for review",
            task_type="development",
            priority=1,
            timeout_seconds=300,
        ))
        pipeline.add_stage(PipelineStage(
            name="review_committee",
            role="reviewer",
            description="Multiple reviewers independently assess changes",
            task_type="review",
            priority=1,
            timeout_seconds=1200,
        ), depends_on=["develop"])
        pipeline.add_stage(PipelineStage(
            name="aggregate",
            role="reviewer",
            description="Aggregate review findings and produce consensus report",
            task_type="review",
            priority=2,
            timeout_seconds=300,
        ), depends_on=["review_committee"])
        pipeline.add_stage(PipelineStage(
            name="fix",
            role="fixer",
            description="Address all review findings",
            task_type="fix",
            priority=2,
            timeout_seconds=900,
        ), depends_on=["aggregate"])
        return pipeline

    # ===== Template Helpers =====

    @staticmethod
    def _all_tests_passed(results: List[TaskResult]) -> bool:
        """Check if the test stage passed all tests."""
        for r in results:
            if "test" in getattr(r, "task_id", "").lower() and r.is_successful:
                # Check if there were any test failures in the output
                output = (r.output or "").lower()
                if "fail" in output or "error" in output:
                    return False
                return True
        return False

    @staticmethod
    def _review_approved(results: List[TaskResult]) -> bool:
        """Check if the review stage approved the changes."""
        for r in results:
            if "review" in getattr(r, "task_id", "").lower():
                metrics = getattr(r, "metrics", {}) or {}
                return metrics.get("approved", False) or metrics.get("score", 0) >= 7.0
        return True  # No review found, skip fix

    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """List all available pipeline templates with descriptions."""
        return {
            "code_generation": "Plan → Develop → Test workflow",
            "code_review": "Develop → Review → Fix → Verify workflow",
            "full_project": "Plan → Develop → Review → Fix → Test → Deploy",
            "quick_fix": "Quick: Analyze → Fix → Verify",
            "committee_review": "Multi-agent independent review and consensus",
        }

    @classmethod
    def create(cls, template_name: str, name: Optional[str] = None) -> Pipeline:
        """
        Create a pipeline from a template.

        Args:
            template_name: One of: code_generation, code_review, full_project,
                          quick_fix, committee_review.
            name: Custom pipeline name. Defaults to template name.

        Returns:
            A configured Pipeline instance.

        Raises:
            ValueError: If template_name is not recognized.
        """
        templates = {
            "code_generation": cls.code_generation,
            "code_review": cls.code_review,
            "full_project": cls.full_project,
            "quick_fix": cls.quick_fix,
            "committee_review": cls.committee_review,
        }
        factory = templates.get(template_name)
        if not factory:
            raise ValueError(f"Unknown template '{template_name}'. Available: {list(templates.keys())}")
        return factory(name or template_name)
