"""
Task Scheduler
==============
Intelligent task scheduler for AgentForge.

Manages task queues with DAG-based dependency resolution,
concurrency control, priority ordering, and resource-aware
scheduling. Integrates with AgentTeam for execution.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar

from adapters.base_adapter import ExecutionContext, TaskInput, TaskResult, TaskResultStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Data Types
# =============================================================================

class TaskState(Enum):
    """Lifecycle states for a scheduled task."""
    PENDING = auto()      # Waiting to be scheduled
    QUEUED = auto()       # In queue, waiting for executor
    RUNNING = auto()      # Currently executing
    COMPLETED = auto()    # Successfully completed
    FAILED = auto()       # Execution failed
    CANCELLED = auto()    # User-cancelled
    BLOCKED = auto()      # Blocked by unmet dependencies
    SKIPPED = auto()      # Skipped due to upstream failure


class ScheduleStrategy(Enum):
    """Task scheduling strategy."""
    FIFO = auto()         # First In, First Out
    PRIORITY = auto()     # Higher priority first
    DEPENDENCY_FIRST = auto()  # Resolve dependencies first
    BALANCED = auto()     # Priority-weighted with fairness


@dataclass(order=True)
class PrioritizedTask:
    """A task with scheduling priority for heap-based ordering."""
    priority: int
    timestamp: float
    task_id: str = field(compare=False)
    task_input: TaskInput = field(compare=False)


@dataclass
class ScheduledTask:
    """A task tracked by the scheduler."""
    task_id: str
    task_input: TaskInput
    state: TaskState = TaskState.PENDING
    dependencies: List[str] = field(default_factory=list)  # task_ids this depends on
    dependents: List[str] = field(default_factory=list)     # task_ids that depend on this
    result: Optional[TaskResult] = None
    assigned_agent: Optional[str] = None  # agent_name
    retries_remaining: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in (
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
            TaskState.SKIPPED,
        )

    @property
    def is_blocked(self) -> bool:
        return self.state == TaskState.BLOCKED


# =============================================================================
# DAG Resolver
# =============================================================================

class DAGResolver:
    """
    Resolves task dependency DAGs.

    Detects cycles, performs topological sorting, and determines
    which tasks are ready for execution at any given point.
    """

    @staticmethod
    def detect_cycles(tasks: Dict[str, ScheduledTask]) -> Optional[List[str]]:
        """
        Detect cycles in the task dependency graph using DFS.

        Returns:
            A cycle path if found, or None if the graph is acyclic.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = defaultdict(int)

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            color[node] = GRAY
            path.append(node)
            for dep in tasks[node].dependencies:
                if dep not in tasks:
                    continue  # external dependency, skip
                if color[dep] == GRAY:
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
                if color[dep] == WHITE:
                    result = dfs(dep, path)
                    if result:
                        return result
            path.pop()
            color[node] = BLACK
            return None

        for task_id in tasks:
            if color[task_id] == WHITE:
                cycle = dfs(task_id, [])
                if cycle:
                    return cycle
        return None

    @staticmethod
    def get_ready_tasks(tasks: Dict[str, ScheduledTask]) -> List[str]:
        """
        Find all tasks whose dependencies are satisfied.

        Returns:
            List of task IDs ready for execution.
        """
        ready = []
        for task_id, task in tasks.items():
            if task.state != TaskState.PENDING:
                continue
            if all(
                dep not in tasks or tasks[dep].state == TaskState.COMPLETED
                for dep in task.dependencies
            ):
                ready.append(task_id)
        return ready

    @staticmethod
    def topological_order(tasks: Dict[str, ScheduledTask]) -> List[List[str]]:
        """
        Generate a topological ordering of tasks in batched levels.

        Each level contains tasks that can execute in parallel.

        Returns:
            List of task ID batches in execution order.
        """
        in_degree: Dict[str, int] = {tid: 0 for tid in tasks}
        adj: Dict[str, List[str]] = defaultdict(list)

        for tid, task in tasks.items():
            for dep in task.dependencies:
                if dep in tasks:
                    in_degree[tid] += 1
                    adj[dep].append(tid)

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        levels: List[List[str]] = []

        while queue:
            level = list(queue)
            levels.append(level)
            queue.clear()
            for tid in level:
                for dependent in adj[tid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Add any unprocessed tasks (cycles/detached)
        remaining = [tid for tid in tasks if tid not in sum(levels, [])]
        if remaining:
            levels.append(remaining)

        return levels

    @staticmethod
    def validate_dag(tasks: Dict[str, ScheduledTask]) -> Tuple[bool, Optional[str]]:
        """
        Validate the task DAG.

        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check for cycles
        cycle = DAGResolver.detect_cycles(tasks)
        if cycle:
            return False, f"Circular dependency detected: {' → '.join(cycle)}"

        # Check for missing dependencies (external refs that don't exist)
        for tid, task in tasks.items():
            missing = [dep for dep in task.dependencies if dep not in tasks]
            if missing:
                return False, f"Task '{tid}' depends on unknown tasks: {missing}"

        return True, None


# =============================================================================
# Task Queue
# =============================================================================

class TaskQueue:
    """
    Priority-ordered task queue with support for FIFO, priority-based,
    and balanced scheduling strategies.
    """

    def __init__(self, strategy: ScheduleStrategy = ScheduleStrategy.PRIORITY):
        self._strategy = strategy
        self._heap: List[PrioritizedTask] = []
        self._fifo_queue: deque[PrioritizedTask] = deque()
        self._counter = 0  # Tiebreaker for stable ordering

    @property
    def strategy(self) -> ScheduleStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: ScheduleStrategy) -> None:
        self._strategy = value

    def push(self, task: ScheduledTask) -> None:
        """Add a task to the queue."""
        pt = PrioritizedTask(
            priority=task.task_input.priority,
            timestamp=task.created_at.timestamp(),
            task_id=task.task_id,
            task_input=task.task_input,
        )
        if self._strategy == ScheduleStrategy.FIFO:
            self._fifo_queue.append(pt)
        else:
            self._counter += 1
            heapq.heappush(self._heap, (self._compute_key(pt), self._counter, pt))

    def pop(self) -> Optional[PrioritizedTask]:
        """Pop the next task according to the current strategy."""
        if self._strategy == ScheduleStrategy.FIFO:
            if not self._fifo_queue:
                return None
            return self._fifo_queue.popleft()
        else:
            if not self._heap:
                return None
            _, _, pt = heapq.heappop(self._heap)
            return pt

    def peek(self) -> Optional[PrioritizedTask]:
        """Peek at the next task without removing it."""
        if self._strategy == ScheduleStrategy.FIFO:
            return self._fifo_queue[0] if self._fifo_queue else None
        else:
            return self._heap[0][2] if self._heap else None

    def remove(self, task_id: str) -> bool:
        """Remove a specific task from the queue."""
        if self._strategy == ScheduleStrategy.FIFO:
            for i, pt in enumerate(self._fifo_queue):
                if pt.task_id == task_id:
                    del self._fifo_queue[i]
                    return True
            return False
        else:
            for i, (_, _, pt) in enumerate(self._heap):
                if pt.task_id == task_id:
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return True
            return False

    def is_empty(self) -> bool:
        return len(self._fifo_queue) == 0 and len(self._heap) == 0

    def size(self) -> int:
        return len(self._fifo_queue) + len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._fifo_queue.clear()

    def _compute_key(self, pt: PrioritizedTask) -> Tuple[int, float]:
        """Compute sort key based on strategy."""
        if self._strategy == ScheduleStrategy.PRIORITY:
            return (-pt.priority, pt.timestamp)
        elif self._strategy == ScheduleStrategy.DEPENDENCY_FIRST:
            # Higher priority first, then FIFO
            return (-pt.priority, pt.timestamp)
        elif self._strategy == ScheduleStrategy.BALANCED:
            # Weighted: strong priority bias but with FIFO fairness
            return (-pt.priority * 1000 + int(pt.timestamp * 1000) % 1000, pt.timestamp)
        return (-pt.priority, pt.timestamp)


# =============================================================================
# Task Scheduler
# =============================================================================

class TaskScheduler:
    """
    Central task scheduler for AgentForge.

    Manages the lifecycle of scheduled tasks:
    1. Accept tasks with optional DAG dependencies.
    2. Enqueue ready tasks respecting priority/strategy.
    3. Dispatch tasks to agents with concurrency control.
    4. Handle completion, failure, cancellation, and retries.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        strategy: ScheduleStrategy = ScheduleStrategy.PRIORITY,
        default_retries: int = 3,
    ):
        self.max_concurrent = max_concurrent
        self.default_retries = default_retries
        self._strategy = strategy

        # State
        self._tasks: Dict[str, ScheduledTask] = {}
        self._queue = TaskQueue(strategy)
        self._running: Set[str] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Callbacks
        self._executor: Optional[Callable[[TaskInput, ExecutionContext], asyncio.Task[TaskResult]]] = None
        self._on_task_complete: List[Callable[[ScheduledTask], Any]] = []
        self._on_task_fail: List[Callable[[ScheduledTask], Any]] = []
        self._on_task_state_change: List[Callable[[ScheduledTask, TaskState, TaskState], Any]] = []

        # Control
        self._paused = False
        self._cancel_event = asyncio.Event()
        self._scheduler_task: Optional[asyncio.Task] = None

        logger.info("TaskScheduler initialized (max_concurrent=%d, strategy=%s)", max_concurrent, strategy.name)

    # ===== Configuration =====

    def set_executor(
        self,
        executor: Callable[[TaskInput, ExecutionContext], asyncio.Task[TaskResult]],
    ) -> None:
        """Set the task executor function."""
        self._executor = executor

    @property
    def strategy(self) -> ScheduleStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: ScheduleStrategy) -> None:
        self._strategy = value
        self._queue.strategy = value

    # ===== Task Management =====

    def add_task(
        self,
        task_input: TaskInput,
        dependencies: Optional[List[str]] = None,
        retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Add a task to the scheduler.

        Args:
            task_input: The task definition.
            dependencies: List of task_ids this task depends on.
            retries: Number of retries on failure. Uses default if None.
            metadata: Optional metadata.

        Returns:
            The scheduled task object.

        Raises:
            ValueError: If a task with this ID already exists.
        """
        if task_input.task_id in self._tasks:
            raise ValueError(f"Task '{task_input.task_id}' already exists")

        task = ScheduledTask(
            task_id=task_input.task_id,
            task_input=task_input,
            dependencies=dependencies or [],
            retries_remaining=retries if retries is not None else self.default_retries,
            metadata=metadata or {},
        )
        self._tasks[task.task_id] = task

        # Register as dependent
        for dep_id in task.dependencies:
            if dep_id in self._tasks:
                self._tasks[dep_id].dependents.append(task.task_id)

        logger.debug("Added task '%s' (priority=%d, deps=%s)", task.task_id, task.task_input.priority, task.dependencies)
        return task

    def add_tasks_batch(
        self,
        task_inputs: List[TaskInput],
        dependency_map: Optional[Dict[str, List[str]]] = None,
    ) -> List[ScheduledTask]:
        """Add multiple tasks at once.

        Args:
            task_inputs: List of task definitions.
            dependency_map: Optional mapping of task_id → list of dependency task_ids.

        Returns:
            List of scheduled task objects.
        """
        dep_map = dependency_map or {}
        tasks = []
        for ti in task_inputs:
            task = self.add_task(ti, dependencies=dep_map.get(ti.task_id))
            tasks.append(task)
        return tasks

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it is not yet terminal."""
        task = self._tasks.get(task_id)
        if not task or task.is_terminal:
            return False

        old_state = task.state
        task.state = TaskState.CANCELLED
        self._queue.remove(task_id)
        self._running.discard(task_id)
        self._fire_state_change(task, old_state, TaskState.CANCELLED)
        logger.info("Cancelled task '%s'", task_id)
        return True

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the scheduler entirely."""
        task = self._tasks.pop(task_id, None)
        if task:
            self._queue.remove(task_id)
            self._running.discard(task_id)
            logger.debug("Removed task '%s'", task_id)
            return True
        return False

    # ===== Scheduling =====

    async def start(self, context: ExecutionContext) -> None:
        """Start the scheduler loop.

        Args:
            context: The shared execution context for all tasks.
        """
        if self._scheduler_task and not self._scheduler_task.done():
            raise RuntimeError("Scheduler is already running")

        # Validate DAG
        is_valid, error = DAGResolver.validate_dag(self._tasks)
        if not is_valid:
            logger.error("DAG validation failed: %s", error)
            raise ValueError(f"Invalid task DAG: {error}")

        # Enqueue ready tasks
        self._enqueue_ready()

        logger.info("Scheduler started with %d tasks (%d ready)", len(self._tasks), self._queue.size())
        self._scheduler_task = asyncio.create_task(self._run_loop(context))

    async def _run_loop(self, context: ExecutionContext) -> None:
        """Main scheduler loop."""
        try:
            while not self._cancel_event.is_set():
                if self._paused:
                    await asyncio.sleep(0.1)
                    continue

                # Check if all done
                if self._queue.is_empty() and not self._running:
                    logger.info("Scheduler: all tasks completed")
                    break

                # Dispatch ready tasks
                async with self._semaphore:
                    pt = self._queue.pop()
                    if pt is None:
                        await asyncio.sleep(0.05)
                        continue

                    task = self._tasks.get(pt.task_id)
                    if not task or task.is_terminal:
                        continue

                    old_state = task.state
                    task.state = TaskState.QUEUED
                    self._fire_state_change(task, old_state, TaskState.QUEUED)

                    # Execute
                    self._running.add(task.task_id)
                    asyncio.create_task(self._execute_task(task, context))

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception:
            logger.exception("Scheduler loop error")

    async def _execute_task(self, task: ScheduledTask, context: ExecutionContext) -> None:
        """Execute a single task and handle its result."""
        if not self._executor:
            logger.error("No executor set, cannot execute task '%s'", task.task_id)
            return

        old_state = task.state
        task.state = TaskState.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self._fire_state_change(task, old_state, TaskState.RUNNING)

        try:
            result = await self._executor(task.task_input, context)

            if result.is_successful:
                task.state = TaskState.COMPLETED
                task.result = result
                for cb in self._on_task_complete:
                    try:
                        cb(task)
                    except Exception as e:
                        logger.exception("Task complete callback failed: %s", e)
                logger.info("Task '%s' completed successfully", task.task_id)
            else:
                await self._handle_failure(task, result)

        except asyncio.CancelledError:
            task.state = TaskState.CANCELLED
            logger.info("Task '%s' cancelled during execution", task.task_id)
        except Exception as e:
            logger.exception("Task '%s' execution error: %s", task.task_id, e)
            await self._handle_failure(task, None)

        finally:
            task.completed_at = datetime.now(timezone.utc)
            self._running.discard(task.task_id)
            # Enqueue newly unblocked tasks
            self._enqueue_ready()

    async def _handle_failure(self, task: ScheduledTask, result: Optional[TaskResult]) -> None:
        """Handle task failure with retry logic."""
        if task.retries_remaining > 0:
            task.retries_remaining -= 1
            old_state = task.state
            task.state = TaskState.PENDING
            self._fire_state_change(task, old_state, TaskState.PENDING)
            logger.info(
                "Task '%s' failed, retrying (%d retries left)",
                task.task_id, task.retries_remaining,
            )
            self._queue.push(task)
        else:
            task.state = TaskState.FAILED
            task.result = result
            for cb in self._on_task_fail:
                try:
                    cb(task)
                except Exception as e:
                    logger.exception("Task fail callback failed: %s", e)

            # Cascade skip dependents
            self._skip_dependents(task.task_id)
            logger.warning("Task '%s' permanently failed", task.task_id)

    def _skip_dependents(self, failed_task_id: str) -> None:
        """Mark all dependents of a failed task as SKIPPED."""
        stack = [failed_task_id]
        while stack:
            tid = stack.pop()
            task = self._tasks.get(tid)
            if not task:
                continue
            for dep_id in task.dependents:
                dep_task = self._tasks.get(dep_id)
                if dep_task and dep_task.state == TaskState.PENDING:
                    dep_task.state = TaskState.SKIPPED
                    logger.info("Skipped task '%s' (upstream '%s' failed)", dep_id, tid)
                    stack.append(dep_id)

    def _enqueue_ready(self) -> None:
        """Find and enqueue all ready tasks."""
        ready = DAGResolver.get_ready_tasks(self._tasks)
        for task_id in ready:
            task = self._tasks[task_id]
            self._queue.push(task)
            logger.debug("Enqueued ready task '%s'", task_id)

    # ===== Control =====

    async def pause(self) -> None:
        """Pause scheduling."""
        self._paused = True
        logger.info("Scheduler paused")

    async def resume(self) -> None:
        """Resume scheduling."""
        self._paused = False
        logger.info("Scheduler resumed")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._cancel_event.set()
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    # ===== Statistics =====

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        state_counts = defaultdict(int)
        for task in self._tasks.values():
            state_counts[task.state.name] += 1

        return {
            "total_tasks": len(self._tasks),
            "by_state": dict(state_counts),
            "queued": self._queue.size(),
            "running": len(self._running),
            "paused": self._paused,
            "max_concurrent": self.max_concurrent,
            "strategy": self._strategy.name,
        }

    def get_task_graph(self) -> Dict[str, Any]:
        """Get the task dependency graph for visualization."""
        nodes = []
        edges = []
        for tid, task in self._tasks.items():
            nodes.append({
                "id": tid,
                "label": task.task_input.title,
                "state": task.state.name,
                "priority": task.task_input.priority,
            })
            for dep in task.dependencies:
                edges.append({"from": dep, "to": tid})
        return {"nodes": nodes, "edges": edges}

    # ===== Callbacks =====

    def on_task_complete(self, callback: Callable[[ScheduledTask], Any]) -> Callable:
        """Register a callback for task completion."""
        self._on_task_complete.append(callback)
        return callback

    def on_task_fail(self, callback: Callable[[ScheduledTask], Any]) -> Callable:
        """Register a callback for task failure."""
        self._on_task_fail.append(callback)
        return callback

    def on_state_change(
        self,
        callback: Callable[[ScheduledTask, TaskState, TaskState], Any],
    ) -> Callable:
        """Register a callback for task state changes."""
        self._on_task_state_change.append(callback)
        return callback

    def _fire_state_change(self, task: ScheduledTask, old: TaskState, new: TaskState) -> None:
        for cb in self._on_task_state_change:
            try:
                cb(task, old, new)
            except Exception as e:
                logger.exception("State change callback failed: %s", e)

    # ===== Cleanup =====

    async def shutdown(self) -> None:
        """Cleanup the scheduler."""
        await self.stop()
        self._queue.clear()
        self._tasks.clear()
        self._running.clear()
        logger.info("TaskScheduler shutdown complete")
