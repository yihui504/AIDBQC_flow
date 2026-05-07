"""
Contract Fallback Rules for Vector Databases

When LLM extraction fails or returns empty values,
these fallback rules provide sensible defaults.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class MilvusContractDefaults:
    """Milvus-specific contract default values."""
    
    # L1 API Constraints
    allowed_dimensions: List[int] = None  # Will be set in __post_init__
    supported_metrics: List[str] = None   # Will be set in __post_init__
    max_top_k: int = 16384
    max_collection_name_length: int = 255
    max_field_name_length: int = 128
    supported_index_types: List[str] = None  # Will be set in __post_init__
    
    # L2 Semantic Constraints (common defaults)
    operational_sequences: List[str] = None  # Will be set in __post_init__
    
    def __post_init__(self):
        if self.allowed_dimensions is None:
            self.allowed_dimensions = [
                4, 8, 16, 32, 64, 96, 128, 192, 256, 384,
                512, 768, 960, 1024, 1200, 1536, 1792, 2048,
                3072, 3584, 4096, 7168, 7680, 12288, 16384,
                19968, 24576, 32768, 65536, 131072, 262144, 524288,
                1048576, 2097152, 32768
            ]
        
        if self.supported_metrics is None:
            self.supported_metrics = ["L2", "IP", "COSINE", "HAMMING", "JACCARD", "BM25"]
        
        if self.supported_index_types is None:
            self.supported_index_types = [
                "FLAT", "IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW",
                "DISKANN", "AUTOINDEX", "GPU_IVF_FLAT", "GPU_IVF_PQ",
                "GPU_CAGRA", "SCANN", "TRIE"
            ]
        
        if self.operational_sequences is None:
            self.operational_sequences = [
                "create_collection -> insert -> search",
                "create_collection -> create_index -> insert -> search",
                "create_collection -> insert -> flush -> load -> search",
                "create_collection -> release -> search (should fail)",
                "drop_collection -> search (should fail)"
            ]


# Registry of fallback rules for different databases
FALLBACK_REGISTRY: Dict[str, type] = {
    "milvus": MilvusContractDefaults,
}


def get_fallback_defaults(db_type: str) -> MilvusContractDefaults:
    """
    Get fallback defaults for a specific database type.

    Args:
        db_type: Database type (e.g., 'milvus', 'qdrant')

    Returns:
        Dataclass with default contract values

    Raises:
        ValueError: If db_type not in registry
    """
    if db_type.lower() not in FALLBACK_REGISTRY:
        raise ValueError(
            f"No fallback rules for database type: {db_type}. "
            f"Available: {list(FALLBACK_REGISTRY.keys())}"
        )

    return FALLBACK_REGISTRY[db_type.lower()]()


def apply_fallbacks(contract_dict: dict, db_type: str) -> dict:
    """
    Apply fallback values to a contract dictionary.

    For each field in the contract, if the value is empty/null,
    replace it with the fallback default.

    Args:
        contract_dict: The extracted contract dictionary
        db_type: Database type for selecting fallback rules

    Returns:
        Updated contract dictionary with fallbacks applied
    """
    import logging
    logger = logging.getLogger(__name__)

    fallbacks = get_fallback_defaults(db_type)
    updated = {}
    fields_applied = []

    # Handle L1 API section
    l1 = contract_dict.get("l1_api", {})
    l1_updated = {}

    if not l1.get("allowed_dimensions"):
        l1_updated["allowed_dimensions"] = fallbacks.allowed_dimensions
        fields_applied.append("allowed_dimensions")
    else:
        l1_updated["allowed_dimensions"] = l1.get("allowed_dimensions")

    if not l1.get("supported_metrics"):
        l1_updated["supported_metrics"] = fallbacks.supported_metrics
        fields_applied.append("supported_metrics")
    else:
        l1_updated["supported_metrics"] = l1.get("supported_metrics")

    if not l1.get("max_top_k"):
        l1_updated["max_top_k"] = fallbacks.max_top_k
        fields_applied.append("max_top_k")
    else:
        l1_updated["max_top_k"] = l1.get("max_top_k")

    if not l1.get("supported_index_types"):
        l1_updated["supported_index_types"] = fallbacks.supported_index_types
        fields_applied.append("supported_index_types")
    else:
        l1_updated["supported_index_types"] = l1.get("supported_index_types")

    l1_updated["source_urls"] = l1.get("source_urls", {})
    updated["l1_api"] = l1_updated

    # Handle L2 Semantic section
    l2 = contract_dict.get("l2_semantic", {})
    l2_updated = {}

    if not l2.get("operational_sequences"):
        l2_updated["operational_sequences"] = fallbacks.operational_sequences
        fields_applied.append("operational_sequences")
    else:
        l2_updated["operational_sequences"] = l2.get("operational_sequences")

    l2_updated["state_transitions"] = l2.get("state_transitions", [])
    l2_updated["expected_monotonicity"] = l2.get("expected_monotonicity", True)
    updated["l2_semantic"] = l2_updated

    # Handle L3 Application section (pass through)
    l3 = contract_dict.get("l3_application", {})
    updated["l3_application"] = l3

    if fields_applied:
        logger.warning(
            f"[Fallback] Applied fallback values to {len(fields_applied)} "
            f"empty fields: {fields_applied}"
        )

    return updated
