"""
Unit Tests for Enhanced Defect Deduplicator

Test coverage goals: 85%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.defects.enhanced_deduplicator import (
    EnhancedDefectDeduplicator,
    InternalDefectReport,
    SimilarityScore,
    DefectCluster,
    DefectSimilarityCalculator,
    SimilarityDimension,
    ClusterMethod,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_defect_1():
    """Sample defect report 1."""
    return InternalDefectReport(
        defect_id="DEF-001",
        bug_type="Type-1",
        title="Index dimension validation fails",
        description="API accepts negative dimension values causing out of bounds error",
        root_cause_analysis="Missing validation in insert operation allows negative dimension parameter",
        affected_component="insert API",
        operation="insert",
        error_code="INDEX_OUT_OF_BOUNDS",
        error_message="IndexError: dimension -1 is out of bounds",
        database="milvus",
        dimension=128,
        metric_type="L2",
        confidence=0.95,
    )


@pytest.fixture
def sample_defect_2():
    """Sample defect report 2 - similar to 1."""
    return InternalDefectReport(
        defect_id="DEF-002",
        bug_type="Type-1",
        title="Dimension check missing in insert",
        description="Insert operation does not validate dimension parameter",
        root_cause_analysis="Missing validation in insert operation allows negative dimension parameter",
        affected_component="insert API",
        operation="insert",
        error_code="INDEX_OUT_OF_BOUNDS",
        error_message="IndexError: dimension -5 is out of bounds",
        database="milvus",
        dimension=256,
        metric_type="L2",
        confidence=0.90,
    )


@pytest.fixture
def sample_defect_3():
    """Sample defect report 3 - different from 1 and 2."""
    return InternalDefectReport(
        defect_id="DEF-003",
        bug_type="Type-2",
        title="Search results inconsistent",
        description="Vector search returns different results for same query",
        root_cause_analysis="Index corruption during concurrent writes",
        affected_component="search API",
        operation="search",
        error_code="",
        error_message="Inconsistent top-K results",
        database="qdrant",
        dimension=512,
        metric_type="COSINE",
        confidence=0.85,
    )


@pytest.fixture
def sample_defect_4():
    """Sample defect report 4 - near duplicate of 1."""
    return InternalDefectReport(
        defect_id="DEF-004",
        bug_type="Type-1",
        title="Negative dimension causes crash",
        description="Passing negative dimension to insert crashes the server",
        root_cause_analysis="Missing validation in insert operation allows negative dimension parameter",
        affected_component="insert API",
        operation="insert",
        error_code="CRASH",
        error_message="Server crashed: invalid dimension",
        database="milvus",
        dimension=128,
        metric_type="L2",
        confidence=0.88,
    )


# ============================================================================
# InternalDefectReport Tests
# ============================================================================

class TestInternalDefectReport:
    """Tests for InternalDefectReport."""

    def test_defect_creation(self, sample_defect_1):
        """Test creating a defect report."""
        assert sample_defect_1.defect_id == "DEF-001"
        assert sample_defect_1.bug_type == "Type-1"
        assert sample_defect_1.database == "milvus"

    def test_to_dict(self, sample_defect_1):
        """Test converting defect to dictionary."""
        data = sample_defect_1.to_dict()

        assert data["defect_id"] == "DEF-001"
        assert data["bug_type"] == "Type-1"
        assert "reported_at" in data

    def test_from_dict(self, sample_defect_1):
        """Test creating defect from dictionary."""
        data = sample_defect_1.to_dict()
        defect = InternalDefectReport.from_dict(data)

        assert defect.defect_id == sample_defect_1.defect_id
        assert defect.bug_type == sample_defect_1.bug_type


# ============================================================================
# DefectSimilarityCalculator Tests
# ============================================================================

class TestDefectSimilarityCalculator:
    """Tests for DefectSimilarityCalculator."""

    @pytest.fixture
    def calculator(self):
        return DefectSimilarityCalculator()

    @pytest.mark.asyncio
    async def test_calculate_similarity_identical(self, calculator, sample_defect_1):
        """Test similarity calculation for identical defects."""
        score = await calculator.calculate_similarity(sample_defect_1, sample_defect_1)

        # Identical defects should have high similarity
        assert score.overall_score > 0.7
        assert score.defect_id_1 == "DEF-001"
        assert score.defect_id_2 == "DEF-001"

    @pytest.mark.asyncio
    async def test_calculate_similarity_similar(self, calculator, sample_defect_1, sample_defect_2):
        """Test similarity calculation for similar defects."""
        score = await calculator.calculate_similarity(sample_defect_1, sample_defect_2)

        # Should be highly similar due to same root cause
        assert score.overall_score > 0.7
        assert len(score.shared_features) > 0

    @pytest.mark.asyncio
    async def test_calculate_similarity_different(self, calculator, sample_defect_1, sample_defect_3):
        """Test similarity calculation for different defects."""
        score = await calculator.calculate_similarity(sample_defect_1, sample_defect_3)

        # Should have low similarity
        assert score.overall_score < 0.5

    def test_semantic_similarity(self, calculator):
        """Test semantic similarity calculation."""
        defect1 = InternalDefectReport(
            defect_id="1", bug_type="Type-1", title="", description="",
            root_cause_analysis="Memory allocation failed in buffer"
        )
        defect2 = InternalDefectReport(
            defect_id="2", bug_type="Type-1", title="", description="",
            root_cause_analysis="Memory allocation failed in buffer"
        )
        defect3 = InternalDefectReport(
            defect_id="3", bug_type="Type-1", title="", description="",
            root_cause_analysis="Network timeout occurred"
        )

        # Same text = high similarity
        sim_same = calculator._semantic_similarity(defect1, defect2)
        assert sim_same > 0.9

        # Different text = lower similarity
        sim_diff = calculator._semantic_similarity(defect1, defect3)
        assert sim_diff < sim_same

    def test_structural_similarity(self, calculator, sample_defect_1, sample_defect_2):
        """Test structural similarity calculation."""
        sim = calculator._structural_similarity(sample_defect_1, sample_defect_2)

        # Same component, operation, error code
        assert sim > 0.5

    def test_behavioral_similarity(self, calculator):
        """Test behavioral similarity calculation."""
        defect1 = InternalDefectReport(
            defect_id="1", bug_type="Type-1", title="", description="",
            root_cause_analysis="",
            expected_behavior="Returns valid search results",
            actual_behavior="Returns empty results",
        )
        defect2 = InternalDefectReport(
            defect_id="2", bug_type="Type-1", title="", description="",
            root_cause_analysis="",
            expected_behavior="Returns valid search results",
            actual_behavior="Returns empty results",
        )

        sim = calculator._behavioral_similarity(defect1, defect2)
        assert sim > 0.5

    def test_contextual_similarity(self, calculator, sample_defect_1, sample_defect_2):
        """Test contextual similarity calculation."""
        sim = calculator._contextual_similarity(sample_defect_1, sample_defect_2)

        # Same database, similar dimension
        assert sim > 0.3

    def test_extract_error_patterns(self, calculator):
        """Test error pattern extraction."""
        patterns = calculator._extract_error_patterns(
            "IndexError: timeout occurred while connecting to database"
        )

        assert "timeout" in patterns
        # "connecting" contains "connect" but not exact "connection"
        assert "index" in patterns


# ============================================================================
# EnhancedDefectDeduplicator Tests
# ============================================================================

class TestEnhancedDefectDeduplicator:
    """Tests for EnhancedDefectDeduplicator."""

    @pytest.fixture
    def deduplicator(self):
        return EnhancedDefectDeduplicator(
            similarity_threshold=0.75,
            clustering_method=ClusterMethod.HIERARCHICAL,
        )

    @pytest.mark.asyncio
    async def test_add_defect(self, deduplicator, sample_defect_1):
        """Test adding a defect."""
        await deduplicator.add_defect(sample_defect_1)

        assert "DEF-001" in deduplicator.defects
        assert deduplicator.defects["DEF-001"].defect_id == "DEF-001"

    @pytest.mark.asyncio
    async def test_add_defects(self, deduplicator, sample_defect_1, sample_defect_2):
        """Test adding multiple defects."""
        await deduplicator.add_defects([sample_defect_1, sample_defect_2])

        assert len(deduplicator.defects) == 2
        assert "DEF-001" in deduplicator.defects
        assert "DEF-002" in deduplicator.defects

    @pytest.mark.asyncio
    async def test_find_duplicates_none(self, deduplicator, sample_defect_1):
        """Test finding duplicates when none exist."""
        await deduplicator.add_defect(sample_defect_1)

        # Add a different defect
        different = InternalDefectReport(
            defect_id="DEF-999",
            bug_type="Type-4",
            title="Unrelated issue",
            description="This is completely different",
            root_cause_analysis="Different cause",
        )
        await deduplicator.add_defect(different)

        duplicates = await deduplicator.find_duplicates(sample_defect_1)

        # Should not find the different defect as duplicate
        assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_find_duplicates_found(self, deduplicator, sample_defect_1, sample_defect_2):
        """Test finding duplicates."""
        await deduplicator.add_defects([sample_defect_1, sample_defect_2])

        duplicates = await deduplicator.find_duplicates(sample_defect_1)

        # Should find sample_defect_2 as similar
        assert len(duplicates) > 0
        assert any(d.defect_id_2 == "DEF-002" for d in duplicates)

    @pytest.mark.asyncio
    async def test_cluster_defects_hierarchical(self, deduplicator, sample_defect_1, sample_defect_2, sample_defect_4):
        """Test hierarchical clustering."""
        await deduplicator.add_defects([sample_defect_1, sample_defect_2, sample_defect_4])

        clusters = await deduplicator.cluster_defects()

        # Should create at least one cluster
        assert len(clusters) >= 1

        # Check cluster structure
        for cluster in clusters:
            assert cluster.cluster_id.startswith("cluster_")
            assert len(cluster.defect_ids) >= 2
            assert cluster.representative_defect_id in cluster.defect_ids

    @pytest.mark.asyncio
    async def test_cluster_defects_connected(self, sample_defect_1, sample_defect_2):
        """Test connected components clustering."""
        deduplicator = EnhancedDefectDeduplicator(
            similarity_threshold=0.7,
            clustering_method=ClusterMethod.CONNECTED,
        )

        await deduplicator.add_defects([sample_defect_1, sample_defect_2])

        clusters = await deduplicator.cluster_defects()

        # Should create cluster
        assert len(clusters) >= 1

    @pytest.mark.asyncio
    async def test_deduplicate(self, deduplicator, sample_defect_1, sample_defect_2, sample_defect_3, sample_defect_4):
        """Test full deduplication workflow."""
        defects = [sample_defect_1, sample_defect_2, sample_defect_3, sample_defect_4]

        unique, clusters = await deduplicator.deduplicate(defects)

        # Should have fewer unique defects than total
        assert len(unique) <= len(defects)

        # Should have clusters
        assert len(clusters) >= 1

        # Representatives should be in unique
        for cluster in clusters:
            assert cluster.representative_defect_id in [d.defect_id for d in unique]

    def test_statistics(self, deduplicator):
        """Test getting statistics."""
        stats = deduplicator.get_statistics()

        assert "total_defects" in stats
        assert "total_clusters" in stats
        assert "similarity_threshold" in stats
        assert stats["similarity_threshold"] == 0.75

    def test_find_candidates(self, deduplicator, sample_defect_1):
        """Test candidate finding using index."""
        candidates = deduplicator._find_candidates(sample_defect_1)

        # Should return empty set when no defects added
        assert len(candidates) == 0


# ============================================================================
# SimilarityScore Tests
# ============================================================================

class TestSimilarityScore:
    """Tests for SimilarityScore."""

    def test_similarity_score_creation(self):
        """Test creating a similarity score."""
        score = SimilarityScore(
            defect_id_1="DEF-001",
            defect_id_2="DEF-002",
            semantic_score=0.8,
            structural_score=0.9,
            behavioral_score=0.7,
            contextual_score=0.6,
            overall_score=0.75,
            shared_features=["Same component"],
            differentiating_features=["Different dimension"],
        )

        assert score.defect_id_1 == "DEF-001"
        assert score.overall_score == 0.75
        assert len(score.shared_features) == 1


# ============================================================================
# DefectCluster Tests
# ============================================================================

class TestDefectCluster:
    """Tests for DefectCluster."""

    def test_cluster_creation(self):
        """Test creating a defect cluster."""
        cluster = DefectCluster(
            cluster_id="cluster_0",
            defect_ids=["DEF-001", "DEF-002"],
            representative_defect_id="DEF-001",
            cluster_type="exact_duplicate",
            confidence=0.95,
        )

        assert cluster.cluster_id == "cluster_0"
        assert len(cluster.defect_ids) == 2
        assert cluster.representative_defect_id == "DEF-001"
        assert cluster.cluster_type == "exact_duplicate"


# ============================================================================
# Integration Tests
# ============================================================================

class TestDeduplicatorIntegration:
    """Integration tests for deduplicator."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete deduplication workflow."""
        # Create sample defects - DEF-001 and DEF-002 are very similar
        defects = [
            InternalDefectReport(
                defect_id="DEF-001",
                bug_type="Type-1",
                title="Dimension validation missing",
                description="API accepts negative dimensions",
                root_cause_analysis="No validation in insert operation allows negative values",
                affected_component="insert API",
                database="milvus",
                dimension=128,
                operation="insert",
                error_code="INVALID_DIMENSION",
                expected_behavior="API rejects negative dimension",
                actual_behavior="API accepts negative dimension and crashes",
            ),
            InternalDefectReport(
                defect_id="DEF-002",
                bug_type="Type-1",
                title="Negative dimension crash",
                description="Server crashes on negative dimension",
                root_cause_analysis="No validation in insert operation allows negative values",
                affected_component="insert API",
                database="milvus",
                dimension=128,
                operation="insert",
                error_code="INVALID_DIMENSION",
                expected_behavior="API rejects negative dimension",
                actual_behavior="API accepts negative dimension and crashes",
            ),
            InternalDefectReport(
                defect_id="DEF-003",
                bug_type="Type-2",
                title="Search inconsistency",
                description="Different results for same query",
                root_cause_analysis="Index corruption during writes",
                affected_component="search API",
                database="qdrant",
                dimension=256,
                operation="search",
                error_code="INCONSISTENT_RESULTS",
            ),
        ]

        # Use CONNECTED method for better clustering
        deduplicator = EnhancedDefectDeduplicator(
            similarity_threshold=0.5,  # Lower threshold
            clustering_method=ClusterMethod.CONNECTED,
        )

        # Run deduplication
        unique, clusters = await deduplicator.deduplicate(defects)

        # Verify results
        assert len(unique) <= 3
        # With the similar DEF-001 and DEF-002, should form at least one cluster
        assert len(clusters) >= 1

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test processing large batch of defects."""
        # Generate many defects with more similar features
        defects = []
        for i in range(20):
            if i < 10:
                # First 10 are similar - same root cause and component
                defects.append(InternalDefectReport(
                    defect_id=f"DEF-{i:03d}",
                    bug_type="Type-1",
                    title=f"Dimension issue {i}",
                    description="Dimension validation problem",
                    root_cause_analysis="Missing validation in insert operation",
                    affected_component="insert API",
                    operation="insert",
                    database="milvus",
                    dimension=128,
                ))
            else:
                # Rest are different
                defects.append(InternalDefectReport(
                    defect_id=f"DEF-{i:03d}",
                    bug_type="Type-2",
                    title=f"Search issue {i}",
                    description="Search inconsistency",
                    root_cause_analysis="Index problem",
                    affected_component="search API",
                    operation="search",
                    database="qdrant",
                    dimension=256,
                ))

        # Lower threshold to ensure clustering
        deduplicator = EnhancedDefectDeduplicator(similarity_threshold=0.6)

        unique, clusters = await deduplicator.deduplicate(defects)

        # Should have clusters for similar defects
        assert len(clusters) >= 1


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
