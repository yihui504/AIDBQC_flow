"""
Evaluator Calibration Loop for AI-DB-QC

Implements Anthropic-style evaluator calibration:
- Run evaluator on known bug set (ground truth)
- Compare evaluator judgments with human labels
- Iteratively adjust prompts until aligned
- Track calibration metrics over time

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class CalibrationLabel(str, Enum):
    """Ground truth labels for calibration samples."""

    IS_BUG = "is_bug"  # Definitely a bug
    NOT_BUG = "not_bug"  # Definitely not a bug
    UNCERTAIN = "uncertain"  # Requires human review
    TYPE_1 = "Type-1"  # L1 API violation
    TYPE_2 = "Type-2"  # L2 Semantic violation
    TYPE_3 = "Type-3"  # Environment-specific
    TYPE_4 = "Type-4"  # False positive


@dataclass
class CalibrationSample:
    """A sample for evaluator calibration."""

    sample_id: str
    test_case: Dict[str, Any]
    execution_result: Dict[str, Any]
    ground_truth: CalibrationLabel
    human_confidence: float  # 0.0 to 1.0
    human_reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_id": self.sample_id,
            "test_case": self.test_case,
            "execution_result": self.execution_result,
            "ground_truth": self.ground_truth.value,
            "human_confidence": self.human_confidence,
            "human_reasoning": self.human_reasoning,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationSample":
        """Create from dictionary."""
        return cls(
            sample_id=data["sample_id"],
            test_case=data["test_case"],
            execution_result=data["execution_result"],
            ground_truth=CalibrationLabel(data["ground_truth"]),
            human_confidence=data["human_confidence"],
            human_reasoning=data.get("human_reasoning", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvaluationJudgment:
    """Evaluator's judgment on a sample."""

    sample_id: str
    is_bug: bool
    bug_type: Optional[str]  # Type-1/2/3/4
    confidence: float
    reasoning: str
    scores: Dict[str, float]  # Individual criterion scores
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_id": self.sample_id,
            "is_bug": self.is_bug,
            "bug_type": self.bug_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "scores": self.scores,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CalibrationRound:
    """A single round of calibration."""

    round_id: int
    prompt_template: str
    samples_evaluated: int
    correct: int
    incorrect: int
    uncertain: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    judgments: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "round_id": self.round_id,
            "prompt_template": self.prompt_template,
            "samples_evaluated": self.samples_evaluated,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "uncertain": self.uncertain,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "timestamp": self.timestamp.isoformat(),
            "judgments": self.judgments,
        }


@dataclass
class CalibrationResult:
    """Result of calibration process."""

    final_round: CalibrationRound
    rounds_completed: int
    converged: bool
    target_precision: float
    target_recall: float
    final_precision: float
    final_recall: float
    final_f1: float
    improvement: Dict[str, float]  # Improvement from round 1 to final
    recommended_prompt: str


class CalibrationDataset(BaseModel):
    """Dataset of calibration samples."""

    samples: List[Dict[str, Any]] = Field(default_factory=list)
    total_samples: int = Field(default=0)
    bug_distribution: Dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_sample(self, sample: CalibrationSample):
        """Add a calibration sample."""
        self.samples.append(sample.to_dict())
        self.total_samples += 1

        # Update distribution
        label = sample.ground_truth.value
        self.bug_distribution[label] = self.bug_distribution.get(label, 0) + 1

        self.last_updated = datetime.now()

    def get_samples_by_label(self, label: CalibrationLabel) -> List[Dict[str, Any]]:
        """Get samples filtered by ground truth label."""
        return [
            s for s in self.samples
            if s["ground_truth"] == label.value
        ]

    def get_stratified_sample(
        self,
        n: int,
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get a stratified sample maintaining label distribution."""
        if n >= self.total_samples:
            return self.samples.copy()

        import random
        random.seed(seed)

        # Calculate samples per label
        result = []
        remaining = n

        for label, count in self.bug_distribution.items():
            if remaining <= 0:
                break

            proportion = count / self.total_samples
            label_samples = int(proportion * n)

            label_samples = min(label_samples, remaining)
            label_pool = [s for s in self.samples if s["ground_truth"] == label]

            result.extend(random.sample(label_pool, min(label_samples, len(label_pool))))
            remaining -= len(result) - len(result[:len(result) - label_samples])

        return result


class EvaluatorCalibrator:
    """
    Calibrates the evaluator against ground truth.

    Based on Anthropic's research on evaluator alignment:
    1. Evaluate on known bug set
    2. Compare with human judgments
    3. Adjust prompts iteratively
    4. Track convergence metrics
    """

    def __init__(
        self,
        target_precision: float = 0.90,
        target_recall: float = 0.85,
        max_rounds: int = 10,
        convergence_rounds: int = 3,
        min_samples_per_round: int = 50
    ):
        self.target_precision = target_precision
        self.target_recall = target_recall
        self.max_rounds = max_rounds
        self.convergence_rounds = convergence_rounds
        self.min_samples_per_round = min_samples_per_round

        self.dataset = CalibrationDataset()
        self.calibration_history: List[CalibrationRound] = []

        # Current prompt template
        self.current_prompt = self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Get default evaluator prompt template."""
        return """You are an expert test evaluator for vector database systems.

Evaluate the following test case and execution result:

**Test Case:**
{test_case}

**Execution Result:**
{execution_result}

**Evaluation Criteria:**
1. Test Diversity: Is this test semantically different from previous tests?
2. Defect Novelty: Is this a new bug or duplicate of known issues?
3. Contract Adherence: Does this follow L1/L2/L3 contract constraints?
4. Bug Realism: Is this a realistic bug or false positive?

Provide your evaluation as JSON:
{
    "is_bug": true/false,
    "bug_type": "Type-1/Type-2/Type-3/Type-4",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation",
    "scores": {
        "test_diversity": 0.0-1.0,
        "defect_novelty": 0.0-1.0,
        "contract_adherence": 0.0-1.0,
        "bug_realism": 0.0-1.0
    }
}"""

    def load_dataset_from_file(self, filepath: str) -> int:
        """Load calibration dataset from JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for sample_data in data.get("samples", []):
            sample = CalibrationSample.from_dict(sample_data)
            self.dataset.add_sample(sample)
            count += 1

        return count

    def save_dataset_to_file(self, filepath: str):
        """Save calibration dataset to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "samples": self.dataset.samples,
            "total_samples": self.dataset.total_samples,
            "bug_distribution": self.dataset.bug_distribution,
            "last_updated": self.dataset.last_updated.isoformat(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def run_calibration_round(
        self,
        round_id: int,
        llm_client: Any,
        sample_subset: Optional[List[Dict[str, Any]]] = None
    ) -> CalibrationRound:
        """
        Run a single calibration round.

        Args:
            round_id: Round number
            llm_client: LLM client for evaluation
            sample_subset: Optional subset of samples to evaluate

        Returns:
            CalibrationRound with results
        """
        # Get samples to evaluate
        if sample_subset is None:
            sample_subset = self.dataset.get_stratified_sample(
                self.min_samples_per_round
            )

        judgments = []
        correct = 0
        incorrect = 0
        uncertain = 0

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for sample_data in sample_subset:
            # Evaluate sample
            judgment = await self._evaluate_sample(
                sample_data,
                llm_client
            )
            judgments.append(judgment.to_dict())

            # Compare with ground truth
            ground_truth = sample_data["ground_truth"]

            if judgment.is_bug and ground_truth in ["is_bug", "Type-1", "Type-2", "Type-3"]:
                correct += 1
                true_positives += 1
            elif not judgment.is_bug and ground_truth == "not_bug":
                correct += 1
                true_negatives += 1
            elif judgment.is_bug and ground_truth == "not_bug":
                incorrect += 1
                false_positives += 1
            elif not judgment.is_bug and ground_truth in ["is_bug", "Type-1", "Type-2", "Type-3"]:
                incorrect += 1
                false_negatives += 1
            else:
                uncertain += 1

        # Calculate metrics
        total = correct + incorrect + uncertain
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = correct / total if total > 0 else 0.0

        round_result = CalibrationRound(
            round_id=round_id,
            prompt_template=self.current_prompt,
            samples_evaluated=len(sample_subset),
            correct=correct,
            incorrect=incorrect,
            uncertain=uncertain,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            judgments=judgments,
        )

        self.calibration_history.append(round_result)
        return round_result

    async def _evaluate_sample(
        self,
        sample_data: Dict[str, Any],
        llm_client: Any
    ) -> EvaluationJudgment:
        """Evaluate a single sample using the LLM."""
        test_case = sample_data["test_case"]
        execution_result = sample_data["execution_result"]
        sample_id = sample_data["sample_id"]

        # Format prompt
        prompt = self.current_prompt.format(
            test_case=json.dumps(test_case, indent=2),
            execution_result=json.dumps(execution_result, indent=2)
        )

        # Call LLM
        try:
            response = await llm_client.generate(prompt)

            # Parse JSON response
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Default if parsing fails
                result = {
                    "is_bug": False,
                    "bug_type": None,
                    "confidence": 0.5,
                    "reasoning": response[:200],
                    "scores": {
                        "test_diversity": 0.5,
                        "defect_novelty": 0.5,
                        "contract_adherence": 0.5,
                        "bug_realism": 0.5,
                    }
                }
        except Exception as e:
            # Default on error
            result = {
                "is_bug": False,
                "bug_type": None,
                "confidence": 0.3,
                "reasoning": f"Evaluation error: {str(e)}",
                "scores": {
                    "test_diversity": 0.5,
                    "defect_novelty": 0.5,
                    "contract_adherence": 0.5,
                    "bug_realism": 0.5,
                }
            }

        return EvaluationJudgment(
            sample_id=sample_id,
            is_bug=result.get("is_bug", False),
            bug_type=result.get("bug_type"),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", ""),
            scores=result.get("scores", {})
        )

    async def calibrate(
        self,
        llm_client: Any,
        prompt_adjuster: Optional[Callable[[str, CalibrationRound], str]] = None
    ) -> CalibrationResult:
        """
        Run full calibration loop.

        Args:
            llm_client: LLM client for evaluation
            prompt_adjuster: Optional function to adjust prompts based on results

        Returns:
            CalibrationResult with final metrics
        """
        first_round_precision = 0.0
        first_round_recall = 0.0

        for round_id in range(1, self.max_rounds + 1):
            round_result = await self.run_calibration_round(round_id, llm_client)

            # Save first round metrics for improvement calculation
            if round_id == 1:
                first_round_precision = round_result.precision
                first_round_recall = round_result.recall

            # Check convergence
            if self._check_convergence():
                break

            # Adjust prompt if adjuster provided
            if prompt_adjuster and round_id < self.max_rounds:
                self.current_prompt = prompt_adjuster(self.current_prompt, round_result)

        # Get final round
        final_round = self.calibration_history[-1]

        # Calculate improvement
        improvement = {
            "precision": final_round.precision - first_round_precision,
            "recall": final_round.recall - first_round_recall,
            "f1": final_round.f1_score - (self.calibration_history[0].f1_score if self.calibration_history else 0),
        }

        return CalibrationResult(
            final_round=final_round,
            rounds_completed=len(self.calibration_history),
            converged=self._check_convergence(),
            target_precision=self.target_precision,
            target_recall=self.target_recall,
            final_precision=final_round.precision,
            final_recall=final_round.recall,
            final_f1=final_round.f1_score,
            improvement=improvement,
            recommended_prompt=self.current_prompt,
        )

    def _check_convergence(self) -> bool:
        """Check if calibration has converged."""
        if len(self.calibration_history) < self.convergence_rounds:
            return False

        # Check last N rounds
        recent_rounds = self.calibration_history[-self.convergence_rounds:]

        # Converged if precision and recall are stable (low variance)
        precisions = [r.precision for r in recent_rounds]
        recalls = [r.recall for r in recent_rounds]

        precision_variance = max(precisions) - min(precisions)
        recall_variance = max(recalls) - min(recalls)

        # Also check if targets met
        avg_precision = sum(precisions) / len(precisions)
        avg_recall = sum(recalls) / len(recalls)

        targets_met = (
            avg_precision >= self.target_precision
            and avg_recall >= self.target_recall
        )

        return targets_met or (
            precision_variance < 0.05
            and recall_variance < 0.05
            and avg_precision >= self.target_precision * 0.9
        )

    def get_calibration_summary(self) -> Dict[str, Any]:
        """Get summary of calibration process."""
        if not self.calibration_history:
            return {
                "rounds_completed": 0,
                "converged": False,
                "final_metrics": None,
            }

        final_round = self.calibration_history[-1]

        return {
            "rounds_completed": len(self.calibration_history),
            "converged": self._check_convergence(),
            "final_metrics": {
                "precision": final_round.precision,
                "recall": final_round.recall,
                "f1_score": final_round.f1_score,
                "accuracy": final_round.accuracy,
            },
            "target_metrics": {
                "precision": self.target_precision,
                "recall": self.target_recall,
            },
            "round_history": [r.to_dict() for r in self.calibration_history],
        }
