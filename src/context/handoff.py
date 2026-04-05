"""
Handoff Manager for AI-DB-QC

Implements structured handoff between agents using WorkflowState.
Based on Anthropic's best practices for agent coordination.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.state import WorkflowState


class HandoffPriority(str, Enum):
    """Priority levels for handoff artifacts."""

    CRITICAL = "critical"  # Must be preserved across resets
    HIGH = "high"  # Important for continuity
    MEDIUM = "medium"  # Useful but not essential
    LOW = "low"  # Optional context


@dataclass
class HandoffArtifact:
    """
    Structured artifact for agent handoff.

    Represents a piece of state/context that needs to be passed
    between agents or preserved across context resets.
    """

    key: str
    value: Any
    priority: HandoffPriority = HandoffPriority.MEDIUM
    description: str = ""
    source_agent: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "priority": self.priority.value,
            "description": self.description,
            "source_agent": self.source_agent,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffArtifact":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            priority=HandoffPriority(data.get("priority", "medium")),
            description=data.get("description", ""),
            source_agent=data.get("source_agent", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class HandoffConfig(BaseModel):
    """Configuration for handoff behavior."""

    # Artifact selection
    preserve_critical_artifacts: bool = Field(default=True, description="Always preserve CRITICAL artifacts")
    preserve_high_artifacts: bool = Field(default=True, description="Preserve HIGH artifacts on reset")
    preserve_medium_artifacts: bool = Field(default=False, description="Preserve MEDIUM artifacts on reset")
    preserve_low_artifacts: bool = Field(default=False, description="Preserve LOW artifacts on reset")

    # Compression
    compress_artifacts: bool = Field(default=True, description="Compress artifact data")
    max_artifact_size_bytes: int = Field(default=10240, description="Max size for single artifact")

    # Validation
    validate_on_handoff: bool = Field(default=True, description="Validate artifacts before handoff")
    validate_on_restore: bool = Field(default=True, description="Validate artifacts after restore")


class HandoffManager:
    """
    Manages structured handoff between agents and across context resets.

    Key features:
    1. Artifact-based state transfer
    2. Priority-based preservation
    3. Validation and serialization
    4. Traceability (who created what, when)
    """

    def __init__(self, config: Optional[HandoffConfig] = None):
        self.config = config or HandoffConfig()
        self._artifacts: Dict[str, HandoffArtifact] = {}
        self._handoff_history: List[Dict[str, Any]] = []

    def create_artifact(
        self,
        key: str,
        value: Any,
        priority: HandoffPriority = HandoffPriority.MEDIUM,
        description: str = "",
        source_agent: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HandoffArtifact:
        """
        Create a new handoff artifact.

        Args:
            key: Unique identifier for the artifact
            value: Artifact value (any serializable type)
            priority: Preservation priority
            description: Human-readable description
            source_agent: Which agent created this
            metadata: Additional metadata

        Returns:
            Created HandoffArtifact
        """
        artifact = HandoffArtifact(
            key=key,
            value=value,
            priority=priority,
            description=description,
            source_agent=source_agent,
            metadata=metadata or {},
        )

        # Validate if configured
        if self.config.validate_on_handoff:
            self._validate_artifact(artifact)

        self._artifacts[key] = artifact
        return artifact

    def get_artifact(self, key: str) -> Optional[HandoffArtifact]:
        """Get an artifact by key."""
        return self._artifacts.get(key)

    def has_artifact(self, key: str) -> bool:
        """Check if an artifact exists."""
        return key in self._artifacts

    def remove_artifact(self, key: str) -> bool:
        """Remove an artifact by key."""
        if key in self._artifacts:
            del self._artifacts[key]
            return True
        return False

    def list_artifacts(
        self,
        priority: Optional[HandoffPriority] = None,
        source_agent: Optional[str] = None,
    ) -> List[HandoffArtifact]:
        """
        List artifacts with optional filtering.

        Args:
            priority: Filter by priority level
            source_agent: Filter by source agent

        Returns:
            List of matching artifacts
        """
        artifacts = list(self._artifacts.values())

        if priority:
            artifacts = [a for a in artifacts if a.priority == priority]

        if source_agent:
            artifacts = [a for a in artifacts if a.source_agent == source_agent]

        return artifacts

    def create_from_workflow_state(
        self,
        state: WorkflowState,
        source_agent: str = "",
    ) -> List[HandoffArtifact]:
        """
        Create handoff artifacts from WorkflowState.

        Extracts important state into artifacts for handoff.

        Args:
            state: Current workflow state
            source_agent: Agent creating these artifacts

        Returns:
            List of created artifacts
        """
        artifacts = []

        # Critical: Run identification and database config
        if state.run_id:
            artifacts.append(self.create_artifact(
                key="run_id",
                value=state.run_id,
                priority=HandoffPriority.CRITICAL,
                description="Unique run identifier",
                source_agent=source_agent,
            ))

        if state.db_config:
            artifacts.append(self.create_artifact(
                key="db_config",
                value=state.db_config.model_dump(),
                priority=HandoffPriority.CRITICAL,
                description="Database configuration",
                source_agent=source_agent,
            ))

        # High: Contracts and target info
        if state.contracts:
            artifacts.append(self.create_artifact(
                key="contracts",
                value=state.contracts.model_dump(),
                priority=HandoffPriority.HIGH,
                description="Parsed test contracts",
                source_agent=source_agent,
            ))

        artifacts.append(self.create_artifact(
            key="target_db_input",
            value=state.target_db_input,
            priority=HandoffPriority.HIGH,
            description="User-specified target database",
            source_agent=source_agent,
        ))

        # High: Defect reports (important for continuity)
        if state.defect_reports:
            artifacts.append(self.create_artifact(
                key="defect_reports",
                value=[r.model_dump() for r in state.defect_reports],
                priority=HandoffPriority.HIGH,
                description="Discovered defect reports",
                source_agent=source_agent,
            ))

        # Medium: Progress tracking
        artifacts.append(self.create_artifact(
            key="iteration_count",
            value=state.iteration_count,
            priority=HandoffPriority.MEDIUM,
            description="Current iteration count",
            source_agent=source_agent,
        ))

        # Medium: Sample of history for coverage continuity
        if state.history_vectors:
            sample_size = min(20, len(state.history_vectors))
            artifacts.append(self.create_artifact(
                key="history_sample",
                value=state.history_vectors[-sample_size:],
                priority=HandoffPriority.MEDIUM,
                description=f"Last {sample_size} history vectors for coverage",
                source_agent=source_agent,
            ))

        # Low: Feedback and external knowledge
        if state.fuzzing_feedback:
            artifacts.append(self.create_artifact(
                key="fuzzing_feedback",
                value=state.fuzzing_feedback,
                priority=HandoffPriority.LOW,
                description="Feedback from oracle to generator",
                source_agent=source_agent,
            ))

        if state.external_knowledge:
            artifacts.append(self.create_artifact(
                key="external_knowledge",
                value=state.external_knowledge,
                priority=HandoffPriority.LOW,
                description="Knowledge from web search",
                source_agent=source_agent,
            ))

        return artifacts

    def restore_to_workflow_state(
        self,
        state: WorkflowState,
        priority_threshold: HandoffPriority = HandoffPriority.HIGH,
    ) -> int:
        """
        Restore artifacts to WorkflowState.

        Args:
            state: Target workflow state
            priority_threshold: Only restore artifacts at or above this priority

        Returns:
            Number of artifacts restored
        """
        restored = 0

        for artifact in self._artifacts.values():
            # Check priority threshold
            priority_order = {
                HandoffPriority.CRITICAL: 4,
                HandoffPriority.HIGH: 3,
                HandoffPriority.MEDIUM: 2,
                HandoffPriority.LOW: 1,
            }

            if priority_order[artifact.priority] < priority_order[priority_threshold]:
                continue

            # Restore based on key
            try:
                if artifact.key == "run_id":
                    state.run_id = artifact.value
                    restored += 1

                elif artifact.key == "db_config":
                    from src.state import DatabaseConfig
                    state.db_config = DatabaseConfig(**artifact.value)
                    restored += 1

                elif artifact.key == "contracts":
                    from src.state import Contract
                    state.contracts = Contract(**artifact.value)
                    restored += 1

                elif artifact.key == "target_db_input":
                    state.target_db_input = artifact.value
                    restored += 1

                elif artifact.key == "defect_reports":
                    from src.state import DefectReport
                    state.defect_reports = [DefectReport(**r) for r in artifact.value]
                    restored += 1

                elif artifact.key == "iteration_count":
                    state.iteration_count = artifact.value
                    restored += 1

                elif artifact.key == "history_sample":
                    state.history_vectors = artifact.value
                    restored += 1

                elif artifact.key == "fuzzing_feedback":
                    state.fuzzing_feedback = artifact.value
                    restored += 1

                elif artifact.key == "external_knowledge":
                    state.external_knowledge = artifact.value
                    restored += 1

                # Validate if configured
                if self.config.validate_on_restore:
                    self._validate_restored_state(state, artifact)

            except Exception as e:
                # Log but don't fail on individual artifact errors
                pass

        return restored

    def filter_for_reset(self) -> List[HandoffArtifact]:
        """
        Filter artifacts to preserve across context reset.

        Returns artifacts that should be kept based on priority configuration.
        """
        artifacts = []

        if self.config.preserve_critical_artifacts:
            artifacts.extend(self.list_artifacts(HandoffPriority.CRITICAL))

        if self.config.preserve_high_artifacts:
            artifacts.extend(self.list_artifacts(HandoffPriority.HIGH))

        if self.config.preserve_medium_artifacts:
            artifacts.extend(self.list_artifacts(HandoffPriority.MEDIUM))

        if self.config.preserve_low_artifacts:
            artifacts.extend(self.list_artifacts(HandoffPriority.LOW))

        return artifacts

    def clear_except_preserved(self):
        """Clear all artifacts except those configured for preservation."""
        preserved = self.filter_for_reset()
        preserved_keys = {a.key for a in preserved}

        keys_to_remove = [k for k in self._artifacts if k not in preserved_keys]
        for key in keys_to_remove:
            del self._artifacts[key]

    def export_artifacts(self, priority_threshold: HandoffPriority = HandoffPriority.MEDIUM) -> str:
        """
        Export artifacts as JSON string.

        Args:
            priority_threshold: Only export artifacts at or above this priority

        Returns:
            JSON string of artifacts
        """
        # Priority ordering for comparison
        priority_order = {
            HandoffPriority.CRITICAL: 4,
            HandoffPriority.HIGH: 3,
            HandoffPriority.MEDIUM: 2,
            HandoffPriority.LOW: 1,
        }

        threshold_value = priority_order.get(priority_threshold, 0)
        artifacts = [
            a for a in self._artifacts.values()
            if priority_order.get(a.priority, 0) >= threshold_value
        ]

        return json.dumps([a.to_dict() for a in artifacts], indent=2)

    def import_artifacts(self, json_data: str) -> int:
        """
        Import artifacts from JSON string.

        Args:
            json_data: JSON string of artifact data

        Returns:
            Number of artifacts imported
        """
        data = json.loads(json_data)
        count = 0

        for item in data:
            artifact = HandoffArtifact.from_dict(item)
            self._artifacts[artifact.key] = artifact
            count += 1

        return count

    def record_handoff(
        self,
        from_agent: str,
        to_agent: str,
        artifact_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a handoff event for traceability."""
        self._handoff_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "artifact_count": artifact_count,
            "metadata": metadata or {},
        })

    def get_handoff_history(self) -> List[Dict[str, Any]]:
        """Get history of all handoff events."""
        return self._handoff_history.copy()

    def _validate_artifact(self, artifact: HandoffArtifact):
        """Validate an artifact before storage."""
        # Check size
        serialized = json.dumps(artifact.value)
        if len(serialized.encode('utf-8')) > self.config.max_artifact_size_bytes:
            raise ValidationError(
                f"Artifact {artifact.key} exceeds size limit: "
                f"{len(serialized)} > {self.config.max_artifact_size_bytes}"
            )

        # Check serializability
        try:
            json.dumps(artifact.value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Artifact {artifact.key} is not JSON-serializable: {e}"
            )

    def _validate_restored_state(self, state: WorkflowState, artifact: HandoffArtifact):
        """Validate state after artifact restoration."""
        # Basic validation - ensure required fields are set
        if artifact.key == "run_id" and not state.run_id:
            raise ValidationError(f"Restored run_id is empty")

        if artifact.key == "iteration_count" and state.iteration_count < 0:
            raise ValidationError(f"Invalid iteration_count: {state.iteration_count}")


class ValidationError(Exception):
    """Raised when artifact validation fails."""
    pass
