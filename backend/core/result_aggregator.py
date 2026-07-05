"""
Result Aggregator
=================
Multi-agent output aggregation, conflict detection, and quality scoring.

Aggregates outputs from multiple agents, detects conflicting conclusions,
computes quality scores, and produces a unified result with confidence
metrics for the orchestration engine.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from adapters.base_adapter import ReviewResult, TaskResult, TaskResultStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

class ConflictSeverity(Enum):
    """Severity of conflicting agent outputs."""
    NONE = "none"
    MINOR = "minor"       # Style/taste differences, no impact
    MODERATE = "moderate"  # Different approaches, one is clearly better
    MAJOR = "major"       # Fundamental disagreement, needs human review
    CRITICAL = "critical"  # Contradictory conclusions, cannot merge safely


class ConsensusLevel(Enum):
    """Degree of agreement among agents."""
    FULL = "full"              # All agents agree
    STRONG = "strong"          # 75%+ agreement
    MODERATE = "moderate"      # 50-75% agreement
    WEAK = "weak"              # < 50% agreement
    NO_CONSENSUS = "no_consensus"  # No agreement pattern found


@dataclass
class Conflict:
    """A detected conflict between agent outputs."""
    severity: ConflictSeverity
    category: str  # code, architecture, design, logic, security, style
    description: str
    agent_positions: Dict[str, str] = field(default_factory=dict)
    resolution_suggestion: Optional[str] = None
    affected_files: List[str] = field(default_factory=list)


@dataclass
class QualityScore:
    """Quality assessment of agent outputs."""
    overall: float = 0.0  # 0.0 - 10.0
    correctness: float = 0.0
    completeness: float = 0.0
    efficiency: float = 0.0
    readability: float = 0.0
    security: float = 0.0
    test_coverage: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class AggregatedResult:
    """Unified result from multiple agent outputs."""
    task_ids: List[str] = field(default_factory=list)
    is_successful: bool = False
    consensus_level: ConsensusLevel = ConsensusLevel.NO_CONSENSUS
    final_output: Optional[str] = None
    summary: Optional[str] = None
    conflicts: List[Conflict] = field(default_factory=list)
    quality_score: Optional[QualityScore] = None
    individual_results: List[TaskResult] = field(default_factory=list)
    winner_agent: Optional[str] = None  # Agent with highest quality score
    winner_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    aggregated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def has_critical_conflicts(self) -> bool:
        return any(c.severity == ConflictSeverity.CRITICAL for c in self.conflicts)

    @property
    def all_successful(self) -> bool:
        return all(r.is_successful for r in self.individual_results)


# =============================================================================
# Result Aggregator
# =============================================================================

class ResultAggregator:
    """
    Aggregates outputs from multiple agents into a unified result.

    Performs:
    - Content merging and conflict detection
    - Quality scoring across dimensions
    - Consensus level computation
    - Best-result selection

    Supports both TaskResult and ReviewResult inputs.
    """

    def __init__(
        self,
        conflict_threshold: float = 0.3,
        consensus_threshold: float = 0.75,
        min_agents_for_consensus: int = 2,
    ):
        self.conflict_threshold = conflict_threshold
        self.consensus_threshold = consensus_threshold
        self.min_agents_for_consensus = min_agents_for_consensus

    # ===== Main Aggregation =====

    def aggregate(
        self,
        results: List[TaskResult],
    ) -> AggregatedResult:
        """Aggregate multiple task results into a unified result.

        Args:
            results: Individual agent task results.

        Returns:
            AggregatedResult with merged output and analysis.
        """
        if not results:
            return AggregatedResult(is_successful=False, summary="No results to aggregate")

        if len(results) == 1:
            return self._single_result_aggregation(results[0])

        return self._multi_result_aggregation(results)

    def aggregate_reviews(
        self,
        review_results: List[ReviewResult],
    ) -> AggregatedResult:
        """Aggregate multiple review results."""
        if not review_results:
            return AggregatedResult(is_successful=False, summary="No reviews to aggregate")

        # Convert reviews to task results for unified processing
        task_results = []
        for rr in review_results:
            tr = TaskResult(
                task_id=rr.task_id,
                status=TaskResultStatus.SUCCESS,
                agent_name=rr.agent_name,
                agent_role="reviewer",
                output=rr.summary or "",
                metrics={
                    "overall_score": rr.overall_score,
                    "is_approved": rr.is_approved,
                    "comment_count": len(rr.comments),
                },
            )
            task_results.append(tr)

        return self.aggregate(task_results)

    # ===== Single Result =====

    def _single_result_aggregation(self, result: TaskResult) -> AggregatedResult:
        """Handle aggregation for a single result."""
        quality = self._score_quality(result)
        return AggregatedResult(
            task_ids=[result.task_id],
            is_successful=result.is_successful,
            consensus_level=ConsensusLevel.FULL,
            final_output=result.output,
            summary=result.summary,
            quality_score=quality,
            individual_results=[result],
            winner_agent=result.agent_name,
            winner_output=result.output,
            conflicts=[],
        )

    # ===== Multi-Result Aggregation =====

    def _multi_result_aggregation(
        self,
        results: List[TaskResult],
    ) -> AggregatedResult:
        """Aggregate multiple results with full analysis."""
        # Score each result
        scored_results: List[Tuple[float, TaskResult]] = []
        for result in results:
            quality = self._score_quality(result)
            scored_results.append((quality.overall, result))

        # Select winner
        scored_results.sort(key=lambda x: x[0], reverse=True)
        winner_score, winner = scored_results[0]

        # Detect conflicts
        conflicts = self._detect_conflicts(results)

        # Compute consensus
        consensus = self._compute_consensus(results)

        # Build final output
        final_output = self._build_final_output(results, conflicts)

        # Build summary
        summary_lines = [
            f"Aggregated {len(results)} agent outputs.",
            f"Consensus: {consensus.name}.",
            f"Winner: {winner.agent_name} (score: {winner_score:.1f}/10).",
            f"Conflicts: {len(conflicts)} found.",
        ]
        if conflicts:
            summary_lines.append(f"Critical conflicts: {sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)}")

        return AggregatedResult(
            task_ids=[r.task_id for r in results],
            is_successful=any(r.is_successful for r in results),
            consensus_level=consensus,
            final_output=final_output,
            summary="\n".join(summary_lines),
            conflicts=conflicts,
            quality_score=QualityScore(overall=winner_score),
            individual_results=results,
            winner_agent=winner.agent_name,
            winner_output=winner.output,
        )

    # ===== Quality Scoring =====

    def _score_quality(self, result: TaskResult) -> QualityScore:
        """Compute quality score for a task result."""
        score = QualityScore()

        if not result.output:
            return score

        output = result.output
        output_len = len(output)

        # Correctness: based on success status
        score.correctness = 10.0 if result.is_successful else 3.0

        # Completeness: based on output length and structure
        if output_len > 5000:
            score.completeness = 9.0
        elif output_len > 2000:
            score.completeness = 7.5
        elif output_len > 500:
            score.completeness = 5.0
        else:
            score.completeness = 3.0

        # Readability: detect code blocks, markdown, comments
        score.readability = self._compute_readability(output)

        # Efficiency: from metrics if available
        if result.metrics:
            score.efficiency = result.metrics.get("efficiency_score", 7.0)
            score.security = result.metrics.get("security_score", 7.0)
            score.test_coverage = result.metrics.get("test_coverage", 0.0)

        # Overall: weighted average
        weights = {
            "correctness": 0.30,
            "completeness": 0.25,
            "efficiency": 0.15,
            "readability": 0.15,
            "security": 0.10,
            "test_coverage": 0.05,
        }
        score.overall = round(
            score.correctness * weights["correctness"]
            + score.completeness * weights["completeness"]
            + score.efficiency * weights["efficiency"]
            + score.readability * weights["readability"]
            + score.security * weights["security"]
            + score.test_coverage * weights["test_coverage"],
            1,
        )

        return score

    def _compute_readability(self, output: str) -> float:
        """Compute readability score based on content structure."""
        score = 5.0  # baseline

        if "```" in output:
            score += 1.5  # Has code blocks
        if output.count("#") > 2:
            score += 1.0  # Has markdown headers
        if "\n\n" in output:
            score += 0.5  # Has paragraph breaks
        if "//" in output or "# " in output:
            score += 0.5  # Has comments
        if output.count("\n") > 20:
            score += 0.5  # Reasonable length

        return min(score, 10.0)

    # ===== Conflict Detection =====

    def _detect_conflicts(
        self,
        results: List[TaskResult],
    ) -> List[Conflict]:
        """Detect conflicts between agent outputs."""
        conflicts: List[Conflict] = []

        if len(results) < 2:
            return conflicts

        # Compare outputs pairwise
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                r1, r2 = results[i], results[j]
                if not r1.output or not r2.output:
                    continue

                pair_conflicts = self._compare_outputs(r1, r2)
                conflicts.extend(pair_conflicts)

        # Deduplicate similar conflicts
        return self._deduplicate_conflicts(conflicts)

    def _compare_outputs(
        self,
        r1: TaskResult,
        r2: TaskResult,
    ) -> List[Conflict]:
        """Compare two agent outputs for conflicts."""
        conflicts: List[Conflict] = []
        o1, o2 = r1.output or "", r2.output or ""

        # Simple heuristic: if outputs are very different in structure
        similarity = self._text_similarity(o1, o2)

        if similarity < 0.3:
            # Very different outputs — likely a major conflict
            conflicts.append(Conflict(
                severity=ConflictSeverity.MAJOR,
                category="code",
                description=f"Outputs from '{r1.agent_name}' and '{r2.agent_name}' are fundamentally different (similarity: {similarity:.2f})",
                agent_positions={
                    r1.agent_name: o1[:500] + ("..." if len(o1) > 500 else ""),
                    r2.agent_name: o2[:500] + ("..." if len(o2) > 500 else ""),
                },
            ))
        elif similarity < 0.6:
            conflicts.append(Conflict(
                severity=ConflictSeverity.MODERATE,
                category="design",
                description=f"Moderate difference between '{r1.agent_name}' and '{r2.agent_name}' outputs (similarity: {similarity:.2f})",
                agent_positions={
                    r1.agent_name: o1[:300] + ("..." if len(o1) > 300 else ""),
                    r2.agent_name: o2[:300] + ("..." if len(o2) > 300 else ""),
                },
            ))

        # Check for contradictory status
        if r1.is_successful != r2.is_successful:
            conflicts.append(Conflict(
                severity=ConflictSeverity.MAJOR,
                category="logic",
                description=(
                    f"'{r1.agent_name}' reports {'success' if r1.is_successful else 'failure'}, "
                    f"but '{r2.agent_name}' reports {'success' if r2.is_successful else 'failure'}"
                ),
                agent_positions={
                    r1.agent_name: "Success" if r1.is_successful else "Failed",
                    r2.agent_name: "Success" if r2.is_successful else "Failed",
                },
            ))

        return conflicts

    def _deduplicate_conflicts(self, conflicts: List[Conflict]) -> List[Conflict]:
        """Deduplicate similar conflicts."""
        seen: Set[str] = set()
        unique: List[Conflict] = []
        for c in conflicts:
            key = f"{c.category}:{c.description[:80]}"
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    # ===== Consensus =====

    def _compute_consensus(self, results: List[TaskResult]) -> ConsensusLevel:
        """Compute the level of consensus among agent outputs."""
        if len(results) < self.min_agents_for_consensus:
            return ConsensusLevel.NO_CONSENSUS

        success_count = sum(1 for r in results if r.is_successful)
        ratio = success_count / len(results)

        if ratio >= 0.95:
            return ConsensusLevel.FULL
        elif ratio >= self.consensus_threshold:
            return ConsensusLevel.STRONG
        elif ratio >= 0.5:
            return ConsensusLevel.MODERATE
        elif ratio > 0:
            return ConsensusLevel.WEAK
        else:
            return ConsensusLevel.NO_CONSENSUS

    # ===== Output Building =====

    def _build_final_output(
        self,
        results: List[TaskResult],
        conflicts: List[Conflict],
    ) -> Optional[str]:
        """Build a combined final output from all results."""
        successful = [r for r in results if r.is_successful]
        if not successful:
            return None

        if len(successful) == 1:
            return successful[0].output

        # Multi-agent output: concatenate with headers
        parts = []
        for r in successful:
            header = f"## Output from {r.agent_name} ({r.agent_role})"
            parts.append(header)
            parts.append(r.output or "(no output)")
            parts.append("")

        if conflicts:
            parts.append("## Conflicts Detected")
            for c in conflicts:
                parts.append(f"- [{c.severity.value.upper()}] {c.description}")

        return "\n\n".join(parts)

    # ===== Utility =====

    def _text_similarity(self, a: str, b: str) -> float:
        """Compute a simple text similarity score (0.0 - 1.0)."""
        if not a or not b:
            return 0.0

        # Simple line-based Jaccard similarity
        lines_a = set(a.splitlines())
        lines_b = set(b.splitlines())

        if not lines_a or not lines_b:
            return 0.0

        intersection = lines_a & lines_b
        union = lines_a | lines_b

        return len(intersection) / len(union) if union else 0.0

    def compute_confidence(self, results: List[TaskResult]) -> Dict[str, float]:
        """Compute confidence metrics for aggregated results.

        Returns:
            Dict with confidence metrics:
            - agreement_score: How well agents agree (0-1)
            - quality_score: Average quality of outputs (0-10)
            - reliability_score: How reliable the aggregation is (0-1)
        """
        if not results:
            return {"agreement_score": 0.0, "quality_score": 0.0, "reliability_score": 0.0}

        # Agreement: based on success rate
        success_rate = sum(1 for r in results if r.is_successful) / len(results)

        # Quality: average of individual quality scores
        qualities = [self._score_quality(r) for r in results]
        avg_quality = sum(q.overall for q in qualities) / len(qualities) if qualities else 0.0

        # Reliability: weighted combination
        reliability = 0.4 * success_rate + 0.3 * (avg_quality / 10.0) + 0.3 * (1.0 / max(len(results), 1))

        return {
            "agreement_score": round(success_rate, 3),
            "quality_score": round(avg_quality, 1),
            "reliability_score": round(reliability, 3),
        }


# =============================================================================
# Review Aggregator (Specialized)
# =============================================================================

class ReviewAggregator(ResultAggregator):
    """
    Specialized aggregator for code review results.

    Merges review comments, computes consensus scores, and produces
    a unified review report suitable for fixer agents.
    """

    def aggregate_review_with_details(
        self,
        review_results: List[ReviewResult],
    ) -> AggregatedResult:
        """
        Aggregate review results with full comment merging.

        Returns:
            AggregatedResult with merged comments, consensus score, and fixer suggestions.
        """
        if not review_results:
            return AggregatedResult(is_successful=False, summary="No reviews to aggregate")

        # Merge all comments
        all_comments = []
        for rr in review_results:
            all_comments.extend(rr.comments)

        # Remove duplicate comments (same file + line range + similar message)
        unique_comments = self._deduplicate_comments(all_comments)

        # Compute consensus score
        scores = [rr.overall_score for rr in review_results]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Determine consensus
        score_variance = max(scores) - min(scores) if len(scores) > 1 else 0.0
        if score_variance < 1.0:
            consensus = ConsensusLevel.STRONG
        elif score_variance < 2.5:
            consensus = ConsensusLevel.MODERATE
        else:
            consensus = ConsensusLevel.WEAK

        # Build fixer suggestion
        fixer_summary = self._build_fixer_suggestion(review_results, unique_comments)

        # Count by severity
        severity_counts = Counter(c.severity for c in unique_comments)

        return AggregatedResult(
            task_ids=[rr.task_id for rr in review_results],
            is_successful=True,
            consensus_level=consensus,
            summary=(
                f"Review aggregated from {len(review_results)} agents.\n"
                f"Average score: {avg_score:.1f}/10 (variance: {score_variance:.1f}).\n"
                f"Comments: {len(unique_comments)} unique ({len(all_comments)} total).\n"
                f"By severity: {dict(severity_counts)}.\n"
                f"Consensus: {consensus.name}."
            ),
            final_output=fixer_summary,
            quality_score=QualityScore(
                overall=avg_score,
                correctness=avg_score,
                completeness=7.0,
                efficiency=7.0,
                readability=7.0,
                security=7.0,
            ),
            conflicts=[],
            individual_results=[],
        )

    def _deduplicate_comments(self, comments: List) -> List:
        """Deduplicate review comments by proximity."""
        seen: Set[Tuple[str, int, int]] = set()
        unique = []
        for c in comments:
            key = (
                getattr(c, "file_path", ""),
                getattr(c, "line_start", 0) or 0,
                getattr(c, "line_end", 0) or 0,
            )
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _build_fixer_suggestion(
        self,
        review_results: List[ReviewResult],
        comments: List,
    ) -> str:
        """Build a consolidated fixer suggestion from all reviews."""
        lines = ["# Consolidated Review Report\n"]

        # Summary
        lines.append("## Summary")
        for rr in review_results:
            lines.append(f"- **{rr.agent_name}**: Score {rr.overall_score:.1f}/10 — {'Approved' if rr.is_approved else 'Needs Work'}")

        # Issues grouped by severity
        by_severity = defaultdict(list)
        for c in comments:
            severity = getattr(c, "severity", "info")
            by_severity[severity].append(c)

        severity_order = ["critical", "error", "warning", "info"]
        for severity in severity_order:
            group = by_severity.get(severity, [])
            if not group:
                continue
            lines.append(f"\n## {severity.upper()} Issues ({len(group)})")
            for c in group:
                file_path = getattr(c, "file_path", "unknown")
                line = getattr(c, "line_start", None)
                location = f"{file_path}" + (f":{line}" if line else "")
                message = getattr(c, "message", "")
                suggestion = getattr(c, "suggestion", "")
                lines.append(f"- **{location}**: {message}")
                if suggestion:
                    lines.append(f"  - Suggestion: {suggestion}")

        # Fixer instructions
        lines.append("\n## Fixer Instructions")
        lines.append("1. Address CRITICAL and ERROR issues first.")
        lines.append("2. For each issue, verify the fix against the reviewer's suggestion.")
        lines.append("3. After fixing, request a re-review for verification.")

        return "\n".join(lines)


# =============================================================================
# Convenience Factory
# =============================================================================

def aggregate_results(
    results: List[TaskResult],
    reviews: Optional[List[ReviewResult]] = None,
) -> AggregatedResult:
    """
    Convenience function to aggregate task and review results.

    Args:
        results: Task execution results.
        reviews: Optional review results.

    Returns:
        AggregatedResult.
    """
    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results)

    if reviews:
        review_aggregated = ReviewAggregator().aggregate_review_with_details(reviews)
        # Merge review info into the task aggregation
        aggregated.conflicts.extend(review_aggregated.conflicts)
        if review_aggregated.summary:
            aggregated.summary = (aggregated.summary or "") + "\n\n" + review_aggregated.summary

    return aggregated
