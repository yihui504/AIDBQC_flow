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
    max_top_k: int = 16384  # Operational default; Milvus API has no strict upper bound on search limit
    max_collection_name_length: int = 255
    max_field_name_length: int = 128
    supported_index_types: List[str] = None  # Will be set in __post_init__
    
    # L2 Semantic Constraints (common defaults)
    operational_sequences: List[str] = None  # Will be set in __post_init__
    
    def __post_init__(self):
        if self.allowed_dimensions is None:
            self.allowed_dimensions = [
                2, 4, 8, 16, 32, 64, 96, 128, 192, 256, 384,
                512, 768, 960, 1024, 1200, 1536, 1792, 2048,
                3072, 3584, 4096, 7168, 7680, 12288, 16384,
                19968, 24576, 32768
            ]

        self.dimension_constraint = {"mode": "range", "min": 2, "max": 32768}

        if self.supported_metrics is None:
            # Per Milvus docs: L2/IP/COSINE for float vectors, HAMMING/JACCARD/TANIMOTO for binary vectors
            # BM25 is a full-text search metric (SPARSE_INVERTED_INDEX), NOT a vector distance metric
            self.supported_metrics = ["L2", "IP", "COSINE", "HAMMING", "JACCARD", "TANIMOTO"]
        
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


@dataclass
class QdrantContractDefaults:
    """Qdrant-specific contract default values."""
    
    # L1 API Constraints
    allowed_dimensions: List[int] = None  # Will be set in __post_init__
    supported_metrics: List[str] = None   # Will be set in __post_init__
    max_top_k: int = 10000  # Operational default; no strict doc limit
    max_collection_name_length: int = 255
    max_field_name_length: int = 128
    supported_index_types: List[str] = None  # Will be set in __post_init__
    
    # L2 Semantic Constraints (common defaults)
    operational_sequences: List[str] = None  # Will be set in __post_init__
    
    def __post_init__(self):
        if self.allowed_dimensions is None:
            self.allowed_dimensions = [
                64, 128, 256, 384, 512, 768, 1024, 1536, 2048, 4096, 8192
            ]

        self.dimension_constraint = {"mode": "range", "min": 1, "max": 65535}

        if self.supported_metrics is None:
            # Per Qdrant docs: https://qdrant.tech/documentation/concepts/search/#distance-metrics
            self.supported_metrics = ["Cosine", "Euclid", "Dot"]
        
        if self.supported_index_types is None:
            self.supported_index_types = ["HNSW", "Flat"]
        
        if self.operational_sequences is None:
            self.operational_sequences = [
                "create_collection -> upsert -> search",
                "create_collection -> upsert -> scroll",
                "create_collection -> upsert -> delete -> search",
                "delete_collection -> search (should fail)",
                "upsert -> search (without collection, should fail)"
            ]


@dataclass
class WeaviateContractDefaults:
    """Weaviate-specific contract default values."""

    allowed_dimensions: List[int] = None
    supported_metrics: List[str] = None
    max_top_k: int = 10000  # Operational default; no strict doc limit
    max_collection_name_length: int = 255
    max_field_name_length: int = 128
    supported_index_types: List[str] = None
    operational_sequences: List[str] = None

    def __post_init__(self):
        if self.allowed_dimensions is None:
            self.allowed_dimensions = [
                128, 256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096
            ]

        self.dimension_constraint = {"mode": "range", "min": 1, "max": 65535}

        if self.supported_metrics is None:
            # Per Weaviate docs: https://weaviate.io/developers/weaviate/configurations/distances#available-distances
            self.supported_metrics = ["cosine", "l2-squared", "dot", "manhattan", "hamming"]

        if self.supported_index_types is None:
            self.supported_index_types = ["hnsw", "flat"]

        if self.operational_sequences is None:
            self.operational_sequences = [
                "create_collection -> insert -> search",
                "create_collection -> insert -> near_vector -> search",
                "create_collection -> batch_insert -> search",
                "delete_collection -> search (should fail)",
                "create_collection -> delete -> search (should fail)"
            ]


# Registry of fallback rules for different databases
FALLBACK_REGISTRY: Dict[str, type] = {
    "milvus": MilvusContractDefaults,
    "qdrant": QdrantContractDefaults,
    "weaviate": WeaviateContractDefaults,
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

    if not l1.get("dimension_constraint"):
        fb_dc = getattr(fallbacks, 'dimension_constraint', None)
        if fb_dc:
            l1_updated["dimension_constraint"] = fb_dc
            fields_applied.append("dimension_constraint")
        else:
            l1_updated["dimension_constraint"] = {"mode": "range", "min": 2, "max": 32768}
    else:
        l1_updated["dimension_constraint"] = l1.get("dimension_constraint")

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
