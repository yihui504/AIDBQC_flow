from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ANNApproximationRule:
    index_type: str
    metric_type: str
    description: str
    expected_behavior: str
    is_approximate: bool = True
    recall_threshold: float = 0.0
    notes: str = ""


_ANN_WHITELIST = [
    ANNApproximationRule(
        index_type="IVF_FLAT",
        metric_type="*",
        description="IVF_FLAT uses inverted file index with flat quantization, which is approximate by nature",
        expected_behavior="recall < 100% is normal; top-k results may miss some true nearest neighbors",
        is_approximate=True,
        recall_threshold=0.9,
        notes="nprobe parameter controls recall/latency tradeoff. Low nprobe = lower recall but faster.",
    ),
    ANNApproximationRule(
        index_type="IVF_SQ8",
        metric_type="*",
        description="IVF_SQ8 uses scalar quantization (8-bit), which introduces quantization error",
        expected_behavior="Distance values may differ slightly from exact computation due to quantization",
        is_approximate=True,
        recall_threshold=0.9,
        notes="Quantization error is expected. Distances will not match exact float32 computation.",
    ),
    ANNApproximationRule(
        index_type="IVF_PQ",
        metric_type="*",
        description="IVF_PQ uses product quantization, which is highly approximate",
        expected_behavior="recall < 100% and distance values are approximate",
        is_approximate=True,
        recall_threshold=0.85,
        notes="PQ is designed for memory efficiency at the cost of accuracy.",
    ),
    ANNApproximationRule(
        index_type="HNSW",
        metric_type="*",
        description="HNSW uses hierarchical navigable small world graphs, which is approximate",
        expected_behavior="recall < 100% is normal; ef parameter controls recall/latency tradeoff",
        is_approximate=True,
        recall_threshold=0.95,
        notes="Higher ef_search = higher recall but slower. Default ef_search=64 typically gives >95% recall.",
    ),
    ANNApproximationRule(
        index_type="DISKANN",
        metric_type="*",
        description="DISKANN is a disk-based ANN index, which is approximate",
        expected_behavior="recall < 100% is normal; search_list_size controls recall",
        is_approximate=True,
        recall_threshold=0.9,
        notes="Disk-based index with memory-mapped files. Latency varies with cache hit rate.",
    ),
    ANNApproximationRule(
        index_type="SCANN",
        metric_type="*",
        description="SCANN uses scored asymmetric distance, which is approximate",
        expected_behavior="recall < 100% is normal",
        is_approximate=True,
        recall_threshold=0.9,
        notes="Google's SCANN algorithm. Approximate by design.",
    ),
    ANNApproximationRule(
        index_type="*",
        metric_type="COSINE",
        description="COSINE metric uses normalized vectors; small floating-point differences are expected",
        expected_behavior="COSINE distances may differ by small epsilon from exact mathematical cosine distance",
        is_approximate=False,
        recall_threshold=1.0,
        notes="Not ANN approximation, but floating-point precision differences are expected.",
    ),
]


class ANNWhitelistChecker:
    def __init__(self, rules: list[ANNApproximationRule] | None = None):
        self.rules = rules or _ANN_WHITELIST

    def is_approximate(self, index_type: str, metric_type: str = "L2") -> bool:
        specific_match = None
        wildcard_match = None
        for rule in self.rules:
            type_match = rule.index_type == index_type
            wildcard_type = rule.index_type == "*"
            metric_match = rule.metric_type == metric_type
            wildcard_metric = rule.metric_type == "*"

            if type_match and (metric_match or wildcard_metric):
                specific_match = rule
                break
            if wildcard_type and (metric_match or wildcard_metric):
                if wildcard_match is None:
                    wildcard_match = rule

        if specific_match:
            return specific_match.is_approximate
        if wildcard_match:
            return wildcard_match.is_approximate
        return False

    def check_recall_claim(self, index_type: str, metric_type: str,
                            observed_recall: float) -> dict:
        matching_rule = None
        for rule in self.rules:
            if rule.index_type == index_type or rule.index_type == "*":
                if rule.metric_type == metric_type or rule.metric_type == "*":
                    if rule.index_type != "*":
                        matching_rule = rule
                        break
                    elif matching_rule is None:
                        matching_rule = rule

        if matching_rule is None:
            return {
                "is_ann_related": False,
                "is_expected": True,
                "is_potential_bug": True,
                "reason": "No ANN whitelist rule found for this index type",
            }

        is_approximate = matching_rule.is_approximate
        if not is_approximate:
            return {
                "is_ann_related": False,
                "is_expected": observed_recall >= matching_rule.recall_threshold,
                "is_potential_bug": observed_recall < matching_rule.recall_threshold,
                "reason": f"Non-approximate index: expected recall >= {matching_rule.recall_threshold}",
            }

        if observed_recall >= matching_rule.recall_threshold:
            return {
                "is_ann_related": True,
                "is_expected": True,
                "is_potential_bug": False,
                "reason": f"ANN approximation: recall {observed_recall:.2%} >= threshold {matching_rule.recall_threshold:.2%} is expected for {index_type}",
            }

        return {
            "is_ann_related": True,
            "is_expected": False,
            "is_potential_bug": True,
            "reason": f"ANN recall {observed_recall:.2%} < threshold {matching_rule.recall_threshold:.2%} for {index_type}. {matching_rule.notes}",
        }

    def get_guidance(self, index_type: str) -> str:
        for rule in self.rules:
            if rule.index_type == index_type:
                return f"[ANN WHITELIST] {rule.description}. {rule.expected_behavior}. {rule.notes}"
        return ""

    def get_all_approximate_indices(self) -> list[str]:
        return list(set(r.index_type for r in self.rules if r.is_approximate and r.index_type != "*"))
