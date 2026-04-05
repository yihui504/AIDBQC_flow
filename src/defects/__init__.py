"""
Defects Module for AI-DB-QC

This module implements enhanced defect deduplication with multi-dimensional
similarity detection and hierarchical clustering.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

from src.defects.enhanced_deduplicator import (
    EnhancedDefectDeduplicator,
    InternalDefectReport,
    SimilarityScore,
    DefectCluster,
    DefectSimilarityCalculator,
    SimilarityDimension,
    ClusterMethod,
)

__all__ = [
    "EnhancedDefectDeduplicator",
    "InternalDefectReport",
    "SimilarityScore",
    "DefectCluster",
    "DefectSimilarityCalculator",
    "SimilarityDimension",
    "ClusterMethod",
]
