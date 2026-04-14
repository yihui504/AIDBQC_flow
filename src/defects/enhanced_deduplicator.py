"""
Enhanced Defect Deduplicator for AI-DB-QC

Implements multi-dimensional similarity detection and hierarchical clustering
for identifying duplicate bug reports.

Features:
- Multi-dimensional similarity (semantic, structural, behavioral)
- Hierarchical clustering for defect grouping
- Configurable similarity thresholds
- Fast similarity search with spatial indexing

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict
import hashlib
import os
import re

from pydantic import BaseModel, Field
import numpy as np


class SimilarityDimension(str, Enum):
    """Dimensions for similarity calculation."""

    SEMANTIC = "semantic"  # Text/embedding similarity
    STRUCTURAL = "structural"  # Code/structure similarity
    BEHAVAVIORAL = "behavioral"  # Behavior/output similarity
    CONTEXTUAL = "contextual"  # Context (DB, operation) similarity


class ClusterMethod(str, Enum):
    """Clustering methods."""

    HIERARCHICAL = "hierarchical"  # Hierarchical agglomerative
    DBSCAN = "dbscan"  # Density-based
    CONNECTED = "connected"  # Connected components


from src.state import DefectReport as StateDefectReport

@dataclass
class InternalDefectReport:
    """Internal representation for deduplication with extra metadata."""

    defect_id: str
    bug_type: str  # Type-1/2/3/4
    root_cause_analysis: str
    title: str = ""
    description: str = ""

    # Structural features
    affected_component: str = ""
    operation: str = ""
    error_code: str = ""
    error_message: str = ""

    # Behavioral features
    reproduction_steps: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""

    # Context features
    database: str = ""
    dimension: int = 0
    metric_type: str = ""
    collection_name: str = ""

    # Evidence
    evidence_level: str = "L1"  # L1/L2/L3
    confidence: float = 0.8

    # Vector embedding (optional)
    embedding: Optional[np.ndarray] = None

    # Metadata
    reported_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_state(cls, state_defect: StateDefectReport) -> "InternalDefectReport":
        """Create from StateDefectReport."""
        return cls(
            defect_id=state_defect.case_id,
            bug_type=state_defect.bug_type or "",
            root_cause_analysis=state_defect.root_cause_analysis or "",
            evidence_level=state_defect.evidence_level or "L1",
            error_message=getattr(state_defect, "error_message", "") or "",
            operation=getattr(state_defect, "operation", "") or ""
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "defect_id": self.defect_id,
            "bug_type": self.bug_type,
            "title": self.title,
            "description": self.description,
            "root_cause_analysis": self.root_cause_analysis,
            "affected_component": self.affected_component,
            "operation": self.operation,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "reproduction_steps": self.reproduction_steps,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "database": self.database,
            "dimension": self.dimension,
            "metric_type": self.metric_type,
            "collection_name": self.collection_name,
            "evidence_level": self.evidence_level,
            "confidence": self.confidence,
            "reported_at": self.reported_at.isoformat(),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InternalDefectReport":
        """Create from dictionary."""
        return cls(
            defect_id=data["defect_id"],
            bug_type=data["bug_type"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            root_cause_analysis=data.get("root_cause_analysis", ""),
            affected_component=data.get("affected_component", ""),
            operation=data.get("operation", ""),
            error_code=data.get("error_code", ""),
            error_message=data.get("error_message", ""),
            reproduction_steps=data.get("reproduction_steps", []),
            expected_behavior=data.get("expected_behavior", ""),
            actual_behavior=data.get("actual_behavior", ""),
            database=data.get("database", ""),
            dimension=data.get("dimension", 0),
            metric_type=data.get("metric_type", ""),
            collection_name=data.get("collection_name", ""),
            evidence_level=data.get("evidence_level", "L1"),
            confidence=data.get("confidence", 0.8),
            tags=data.get("tags", []),
        )


@dataclass
class SimilarityScore:
    """Multi-dimensional similarity score."""

    defect_id_1: str
    defect_id_2: str

    # Individual dimension scores
    semantic_score: float
    structural_score: float
    behavioral_score: float
    contextual_score: float

    # Combined score
    overall_score: float

    # Details
    shared_features: List[str] = field(default_factory=list)
    differentiating_features: List[str] = field(default_factory=list)


@dataclass
class DefectCluster:
    """A cluster of similar defects."""

    cluster_id: str
    defect_ids: List[str]
    representative_defect_id: str

    # Cluster characteristics
    cluster_type: str  # "exact_duplicate", "near_duplicate", "related"
    confidence: float

    # Common features
    common_bug_type: str = ""
    common_component: str = ""
    common_operation: str = ""
    common_error_pattern: str = ""

    # Similarity matrix (for small clusters)
    similarity_matrix: Optional[Dict[str, Dict[str, float]]] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


class DefectSimilarityCalculator:
    """
    Calculate multi-dimensional similarity between defect reports.

    Uses semantic, structural, behavioral, and contextual features.
    """

    def __init__(
        self,
        semantic_weight: float = 0.5,
        structural_weight: float = 0.3,
        behavioral_weight: float = 0.1,
        contextual_weight: float = 0.1,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.behavioral_weight = behavioral_weight
        self.contextual_weight = contextual_weight

        # Offline-safe / deterministic by default:
        # - Unit tests must pass without network access and without triggering model downloads.
        # - Enable SentenceTransformer only when explicitly requested via env var and the model
        #   is already available locally.
        self.model = None
        enable_embeddings = os.getenv("AI_DB_QC_ENABLE_EMBEDDINGS", "").strip().lower() in {"1", "true", "yes", "on"}
        if enable_embeddings:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
                # If the environment is truly offline, HuggingFace honors HF_HUB_OFFLINE=1.
                # We do not set it here to avoid surprising callers; we just fall back on errors.
                self.model = SentenceTransformer(model_name)
            except Exception:
                self.model = None

    async def calculate_similarity(
        self,
        defect1: InternalDefectReport,
        defect2: InternalDefectReport,
    ) -> SimilarityScore:
        """
        Calculate multi-dimensional similarity between two defects.

        Args:
            defect1: First defect report
            defect2: Second defect report

        Returns:
            SimilarityScore with all dimension scores
        """
        # Calculate individual dimensions
        semantic_score = self._semantic_similarity(defect1, defect2)
        structural_score = self._structural_similarity(defect1, defect2)
        behavioral_score = self._behavioral_similarity(defect1, defect2)
        contextual_score = self._contextual_similarity(defect1, defect2)

        # Calculate weighted overall score
        overall_score = (
            semantic_score * self.semantic_weight +
            structural_score * self.structural_weight +
            behavioral_score * self.behavioral_weight +
            contextual_score * self.contextual_weight
        )

        # Find shared and differentiating features
        shared_features, differentiating_features = self._compare_features(
            defect1, defect2
        )

        return SimilarityScore(
            defect_id_1=defect1.defect_id,
            defect_id_2=defect2.defect_id,
            semantic_score=semantic_score,
            structural_score=structural_score,
            behavioral_score=behavioral_score,
            contextual_score=contextual_score,
            overall_score=overall_score,
            shared_features=shared_features,
            differentiating_features=differentiating_features,
        )

    _TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text deterministically for similarity computation."""
        if not text:
            return ""
        return " ".join(text.lower().strip().split())

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        """Tokenize text deterministically (ASCII-ish word tokens)."""
        if not text:
            return []
        return cls._TOKEN_RE.findall(text.lower())

    @staticmethod
    def _hashing_vector(tokens: List[str], dim: int = 256) -> np.ndarray:
        """
        Deterministic hashing vectorizer (no external deps, no downloads).

        - Uses sha256(token) to map tokens into a fixed-size dense vector.
        - Applies signed hashing to reduce collisions.
        - L2-normalizes the output to enable cosine similarity.
        """
        if not tokens:
            return np.zeros(dim, dtype=np.float32)

        vec = np.zeros(dim, dtype=np.float32)
        for tok in tokens:
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            vec[idx] += sign

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for text.

        By default this is a deterministic offline hashing vector.
        If SentenceTransformer is enabled (AI_DB_QC_ENABLE_EMBEDDINGS=1) and available,
        it will be used; failures fall back to hashing.
        """
        text = self._normalize_text(text)
        if not text:
            return np.zeros(256, dtype=np.float32)

        if self.model is not None:
            try:
                # sentence-transformers returns np.ndarray when convert_to_numpy=True
                emb = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return np.asarray(emb, dtype=np.float32)
            except Exception:
                # Always remain functional offline / on missing model files
                pass

        tokens = self._tokenize(text)
        # Add bigrams to improve robustness for short texts.
        if len(tokens) >= 2:
            tokens = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        return self._hashing_vector(tokens, dim=256)

    def _semantic_similarity(self, defect1: InternalDefectReport, defect2: InternalDefectReport) -> float:
        """Calculate semantic similarity deterministically (offline-safe)."""
        text1 = self._normalize_text(" ".join([
            defect1.title,
            defect1.description,
            defect1.root_cause_analysis,
            defect1.error_message,
        ]))
        text2 = self._normalize_text(" ".join([
            defect2.title,
            defect2.description,
            defect2.root_cause_analysis,
            defect2.error_message,
        ]))

        if not text1 or not text2:
            return 0.0

        # Fast path: identical normalized text
        if text1 == text2:
            return 1.0

        # Cache embeddings on defect objects to speed up repeated comparisons.
        if defect1.embedding is None:
            defect1.embedding = self._get_embedding(text1)
        if defect2.embedding is None:
            defect2.embedding = self._get_embedding(text2)

        vec1 = defect1.embedding
        vec2 = defect2.embedding
        denom = float(np.linalg.norm(vec1) * np.linalg.norm(vec2))
        base = float(np.dot(vec1, vec2) / denom) if denom > 0 else 0.0

        # Deterministic boosts for key exact matches (keeps previous intent).
        boost = 0.0
        if defect1.root_cause_analysis and defect1.root_cause_analysis == defect2.root_cause_analysis:
            boost += 0.3
        if defect1.error_code and defect1.error_code == defect2.error_code:
            boost += 0.2

        return float(max(0.0, min(1.0, base + boost)))

    def _structural_similarity(self, defect1: InternalDefectReport, defect2: InternalDefectReport) -> float:
        """Calculate structural similarity based on code/structure features."""
        score = 0.0
        max_score = 5.0

        # Component match
        if defect1.affected_component and defect2.affected_component:
            if defect1.affected_component == defect2.affected_component:
                score += 1.0

        # Operation match
        if defect1.operation and defect2.operation:
            if defect1.operation == defect2.operation:
                score += 1.0

        # Error code match
        if defect1.error_code and defect2.error_code:
            if defect1.error_code == defect2.error_code:
                score += 1.5

        # Error message pattern match
        if defect1.error_message and defect2.error_message:
            # Extract error patterns (e.g., "IndexError", "timeout")
            patterns1 = self._extract_error_patterns(defect1.error_message)
            patterns2 = self._extract_error_patterns(defect2.error_message)

            if patterns1 & patterns2:
                score += 1.0

        # Bug type match
        if defect1.bug_type == defect2.bug_type:
            score += 0.5

        return score / max_score if max_score > 0 else 0.0

    def _behavioral_similarity(self, defect1: InternalDefectReport, defect2: InternalDefectReport) -> float:
        """Calculate behavioral similarity based on behavior/output."""
        score = 0.0
        max_score = 3.0

        # Expected behavior match
        if defect1.expected_behavior and defect2.expected_behavior:
            words1 = set(defect1.expected_behavior.lower().split())
            words2 = set(defect2.expected_behavior.lower().split())
            if words1 and words2:
                overlap = len(words1 & words2) / len(words1 | words2)
                if overlap > 0.5:
                    score += 1.0

        # Actual behavior match
        if defect1.actual_behavior and defect2.actual_behavior:
            words1 = set(defect1.actual_behavior.lower().split())
            words2 = set(defect2.actual_behavior.lower().split())
            if words1 and words2:
                overlap = len(words1 & words2) / len(words1 | words2)
                if overlap > 0.5:
                    score += 1.0

        # Reproduction steps similarity
        if defect1.reproduction_steps and defect2.reproduction_steps:
            steps1 = [s.lower() for s in defect1.reproduction_steps]
            steps2 = [s.lower() for s in defect2.reproduction_steps]
            common_steps = len(set(steps1) & set(steps2))
            if common_steps > 0:
                score += min(1.0, common_steps / max(len(steps1), len(steps2)))

        return score / max_score if max_score > 0 else 0.0

    def _contextual_similarity(self, defect1: InternalDefectReport, defect2: InternalDefectReport) -> float:
        """Calculate contextual similarity based on execution context."""
        score = 0.0
        max_score = 4.0

        # Database match
        if defect1.database and defect2.database:
            if defect1.database == defect2.database:
                score += 1.0

        # Collection match
        if defect1.collection_name and defect2.collection_name:
            if defect1.collection_name == defect2.collection_name:
                score += 1.0

        # Dimension similarity
        if defect1.dimension > 0 and defect2.dimension > 0:
            if defect1.dimension == defect2.dimension:
                score += 1.0
            elif abs(defect1.dimension - defect2.dimension) <= 128:
                score += 0.5

        # Metric type match
        if defect1.metric_type and defect2.metric_type:
            if defect1.metric_type == defect2.metric_type:
                score += 1.0

        return score / max_score if max_score > 0 else 0.0

    def _extract_error_patterns(self, error_message: str) -> Set[str]:
        """Extract error patterns from error message."""
        patterns = set()

        # Common error patterns
        error_keywords = [
            "timeout", "connection", "index", "dimension", "vector",
            "memory", "null", "undefined", "invalid", "not found",
            "permission", "authorization", "authentication",
            "key", "constraint", "violation",
        ]

        error_lower = error_message.lower()

        for keyword in error_keywords:
            if keyword in error_lower:
                patterns.add(keyword)

        return patterns

    def _compare_features(
        self,
        defect1: InternalDefectReport,
        defect2: InternalDefectReport,
    ) -> Tuple[List[str], List[str]]:
        """Compare features and find shared/differentiating ones."""
        shared = []
        differentiating = []

        # Check various features
        features_to_check = [
            ("Bug Type", defect1.bug_type, defect2.bug_type),
            ("Component", defect1.affected_component, defect2.affected_component),
            ("Operation", defect1.operation, defect2.operation),
            ("Error Code", defect1.error_code, defect2.error_code),
            ("Database", defect1.database, defect2.database),
        ]

        for name, val1, val2 in features_to_check:
            if val1 and val2:
                if val1 == val2:
                    shared.append(f"{name}: {val1}")
                else:
                    differentiating.append(f"{name}: {val1} vs {val2}")

        return shared, differentiating


class EnhancedDefectDeduplicator:
    """
    Enhanced defect deduplicator with multi-dimensional similarity.

    Features:
    - Multi-dimensional similarity calculation
    - Hierarchical clustering
    - Configurable thresholds
    - Fast similarity search
    """

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        clustering_method: ClusterMethod = ClusterMethod.HIERARCHICAL,
        min_cluster_size: int = 2,
    ):
        self.similarity_threshold = similarity_threshold
        self.clustering_method = clustering_method
        self.min_cluster_size = min_cluster_size

        # Components
        self.similarity_calculator = DefectSimilarityCalculator()
        self.defects: Dict[str, InternalDefectReport] = {}
        self.clusters: Dict[str, DefectCluster] = {}

        # Spatial index for fast search (simplified - use KDTree in production)
        self._defect_index: Dict[str, Set[str]] = defaultdict(set)

    async def add_defect(self, defect: InternalDefectReport) -> None:
        """
        Add a defect report to the deduplicator.

        Args:
            defect: Defect report to add
        """
        self.defects[defect.defect_id] = defect

        # Update index
        self._update_index(defect)

    async def add_defects(self, defects: List[InternalDefectReport]) -> None:
        """Add multiple defect reports."""
        for defect in defects:
            await self.add_defect(defect)

    def _update_index(self, defect: InternalDefectReport) -> None:
        """Update spatial index for fast search."""
        # Index by bug type
        self._defect_index[f"type:{defect.bug_type}"].add(defect.defect_id)

        # Index by component
        if defect.affected_component:
            self._defect_index[f"component:{defect.affected_component}"].add(defect.defect_id)

        # Index by database
        if defect.database:
            self._defect_index[f"db:{defect.database}"].add(defect.defect_id)

    async def find_duplicates(
        self,
        defect: InternalDefectReport,
        max_results: int = 10,
    ) -> List[SimilarityScore]:
        """
        Find potential duplicates for a defect.

        Args:
            defect: Defect to find duplicates for
            max_results: Maximum number of results

        Returns:
            List of similarity scores, sorted by overall score (descending)
        """
        # Use index to find candidates
        candidate_ids = self._find_candidates(defect)

        # Calculate similarity for each candidate
        similarities = []
        for candidate_id in candidate_ids:
            if candidate_id == defect.defect_id:
                continue

            candidate = self.defects.get(candidate_id)
            if candidate is None:
                continue

            similarity = await self.similarity_calculator.calculate_similarity(
                defect, candidate
            )
            similarities.append(similarity)

        # Sort by overall score
        similarities.sort(key=lambda s: s.overall_score, reverse=True)

        # Filter by threshold and limit results
        results = [
            s for s in similarities
            if s.overall_score >= self.similarity_threshold
        ][:max_results]

        return results

    def _find_candidates(self, defect: InternalDefectReport) -> Set[str]:
        """Find candidate defects using spatial index."""
        candidates = set()

        # Start with same bug type
        type_key = f"type:{defect.bug_type}"
        candidates.update(self._defect_index.get(type_key, set()))

        # Add same component
        if defect.affected_component:
            component_key = f"component:{defect.affected_component}"
            candidates.update(self._defect_index.get(component_key, set()))

        # Add same database
        if defect.database:
            db_key = f"db:{defect.database}"
            candidates.update(self._defect_index.get(db_key, set()))

        return candidates

    async def cluster_defects(
        self,
        defect_ids: Optional[List[str]] = None,
    ) -> List[DefectCluster]:
        """
        Cluster defects into duplicate groups.

        Args:
            defect_ids: Optional list of defect IDs to cluster (defaults to all)

        Returns:
            List of defect clusters
        """
        if defect_ids is None:
            defect_ids = list(self.defects.keys())

        if not defect_ids:
            return []

        if self.clustering_method == ClusterMethod.HIERARCHICAL:
            return await self._hierarchical_clustering(defect_ids)
        elif self.clustering_method == ClusterMethod.CONNECTED:
            return await self._connected_components_clustering(defect_ids)
        else:
            return await self._hierarchical_clustering(defect_ids)

    async def _hierarchical_clustering(
        self,
        defect_ids: List[str],
    ) -> List[DefectCluster]:
        """Hierarchical agglomerative clustering."""
        clusters = []
        assigned = set()

        for defect_id in defect_ids:
            if defect_id in assigned:
                continue

            defect = self.defects.get(defect_id)
            if defect is None:
                continue

            # Find similar defects
            similar = [defect_id]

            for other_id in defect_ids:
                if other_id == defect_id or other_id in assigned:
                    continue

                other = self.defects.get(other_id)
                if other is None:
                    continue

                similarity = await self.similarity_calculator.calculate_similarity(
                    defect, other
                )

                if similarity.overall_score >= self.similarity_threshold:
                    similar.append(other_id)

            # Create cluster if enough members
            if len(similar) >= self.min_cluster_size or len(similar) > 1:
                cluster_id = f"cluster_{len(clusters)}"

                # Determine cluster type
                avg_score = 0.0
                if len(similar) > 1:
                    scores = []
                    for i, id1 in enumerate(similar):
                        for id2 in similar[i+1:]:
                            d1 = self.defects[id1]
                            d2 = self.defects[id2]
                            sim = await self.similarity_calculator.calculate_similarity(d1, d2)
                            scores.append(sim.overall_score)
                    avg_score = sum(scores) / len(scores) if scores else 0.0

                if avg_score >= 0.9:
                    cluster_type = "exact_duplicate"
                elif avg_score >= 0.75:
                    cluster_type = "near_duplicate"
                else:
                    cluster_type = "related"

                cluster = DefectCluster(
                    cluster_id=cluster_id,
                    defect_ids=similar,
                    representative_defect_id=defect_id,
                    cluster_type=cluster_type,
                    confidence=avg_score,
                    common_bug_type=defect.bug_type,
                    common_component=defect.affected_component,
                )

                clusters.append(cluster)
                assigned.update(similar)

        return clusters

    async def _connected_components_clustering(
        self,
        defect_ids: List[str],
    ) -> List[DefectCluster]:
        """Connected components based clustering."""
        # Build adjacency list
        graph = defaultdict(set)

        for i, id1 in enumerate(defect_ids):
            for id2 in defect_ids[i+1:]:
                defect1 = self.defects.get(id1)
                defect2 = self.defects.get(id2)

                if defect1 is None or defect2 is None:
                    continue

                similarity = await self.similarity_calculator.calculate_similarity(
                    defect1, defect2
                )

                if similarity.overall_score >= self.similarity_threshold:
                    graph[id1].add(id2)
                    graph[id2].add(id1)

        # Find connected components
        visited = set()
        clusters = []

        for defect_id in defect_ids:
            if defect_id in visited:
                continue

            component = self._dfs_component(defect_id, graph, visited)

            if len(component) >= self.min_cluster_size or len(component) > 1:
                cluster_id = f"cluster_{len(clusters)}"

                # Find representative (most confident)
                representative = max(
                    component,
                    key=lambda d: self.defects.get(d, InternalDefectReport(
                        defect_id=d, bug_type="", root_cause_analysis=""
                    )).confidence
                )

                cluster = DefectCluster(
                    cluster_id=cluster_id,
                    defect_ids=list(component),
                    representative_defect_id=representative,
                    cluster_type="related",
                    confidence=0.8,
                )

                clusters.append(cluster)

        return clusters

    def _dfs_component(
        self,
        start: str,
        graph: Dict[str, Set[str]],
        visited: Set[str],
    ) -> Set[str]:
        """DFS to find connected component."""
        component = set()
        stack = [start]

        while stack:
            node = stack.pop()
            if node in visited:
                continue

            visited.add(node)
            component.add(node)

            # Add neighbors
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    stack.append(neighbor)

        return component

    async def deduplicate(
        self,
        defects: List[InternalDefectReport],
    ) -> Tuple[List[InternalDefectReport], List[DefectCluster]]:
        """
        Deduplicate a list of defects.

        Args:
            defects: List of defects to deduplicate

        Returns:
            Tuple of (unique defects, clusters)
        """
        # Add all defects
        await self.add_defects(defects)

        # Cluster defects
        clusters = await self.cluster_defects()

        # Select representative from each cluster
        seen = set()
        unique = []

        for defect in defects:
            is_duplicate = False

            for cluster in clusters:
                if defect.defect_id in cluster.defect_ids:
                    if defect.defect_id != cluster.representative_defect_id:
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique.append(defect)
                seen.add(defect.defect_id)

        return unique, clusters

    def get_statistics(self) -> Dict[str, Any]:
        """Get deduplicator statistics."""
        return {
            "total_defects": len(self.defects),
            "total_clusters": len(self.clusters),
            "similarity_threshold": self.similarity_threshold,
            "clustering_method": self.clustering_method.value,
            "index_keys": len(self._defect_index),
        }
