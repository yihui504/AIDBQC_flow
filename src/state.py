from typing import List, Dict, Any, Optional, Literal, Tuple
from pathlib import Path
from pydantic import BaseModel, Field
import gzip
import zlib
from collections import Counter
import json
import hashlib
import struct
import logging
from datetime import datetime, date
import time
import base64

logger = logging.getLogger(__name__)

class DatabaseConfig(BaseModel):
    """Database configuration and connection details."""
    db_name: str = Field(description="Name of the target vector database (e.g., Milvus, Qdrant)")
    version: str = Field(description="Version of the target database")
    endpoint: Optional[str] = Field(default=None, description="Connection endpoint")
    credentials: Optional[Dict[str, str]] = Field(default=None, description="Connection credentials")
    docs_context: str = Field(default="", description="Scraped documentation context for the specific version")

class Contract(BaseModel):
    """Parsed contracts for test generation."""
    l3_application: Dict[str, Any] = Field(default_factory=dict, description="L3 Application Contracts")
    l2_semantic: Dict[str, Any] = Field(default_factory=dict, description="L2 Semantic Contracts")
    l1_api: Dict[str, Any] = Field(default_factory=dict, description="L1 API Contracts")

class TestCase(BaseModel):
    """Structure of a generated test case."""
    case_id: str
    query_vector: Optional[List[float]] = None
    query_text: Optional[str] = None
    dimension: int
    expected_l1_legal: bool = True
    expected_l2_ready: bool = True
    semantic_intent: str = ""
    is_adversarial: bool = False
    is_negative_test: bool = False
    expected_ground_truth: List[Dict[str, Any]] = Field(default_factory=list, description="Specific data samples that should be found for this query")
    assigned_source_url: Optional[str] = None

class ExecutionResult(BaseModel):
    """Result from executing a test case against the target database."""
    case_id: str
    success: bool
    l1_passed: bool
    l2_passed: bool
    error_message: Optional[str] = None
    raw_response: Optional[Any] = None
    execution_time_ms: float = 0.0
    underlying_logs: Optional[str] = Field(default=None, description="Logs captured directly from Docker for deep observability")
    l1_warning: Optional[str] = Field(default=None, description="L1 warning message for dimension mismatch - indicates potential Type-1 bug")
    l2_result: Optional[dict] = Field(default=None, description="L2 runtime readiness check result with passed/reason details")
    l1_violation_details: Optional[Dict[str, Any]] = Field(default=None, description="Structured L1 violation info with violation_type, actual_value, expected_range, severity")

class DimensionConstraint(BaseModel):
    """Dual-mode dimension constraint extracted from official documentation."""
    mode: Literal["list", "range"] = "range"
    values: Optional[List[int]] = None
    min: Optional[int] = None
    max: Optional[int] = None

    def contains(self, dimension: int) -> bool:
        """Check if a dimension value satisfies this constraint."""
        if self.mode == "list" and self.values is not None:
            return dimension in self.values
        lo = self.min if self.min is not None else 0
        hi = self.max if self.max is not None else float('inf')
        return lo <= dimension <= hi

class OracleValidation(BaseModel):
    """Result from the Oracle Coordinator."""
    case_id: str
    passed: bool
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""

class L1Contract(BaseModel):
    """L1 API Contracts (Strong constraints from docs)"""
    allowed_dimensions: List[int] = Field(description="List of allowed vector dimensions")
    dimension_constraint: Optional[DimensionConstraint] = Field(
        default=None,
        description="Dual-mode dimension constraint (list or range) from official docs"
    )
    supported_metrics: List[str] = Field(description="Supported distance metrics (e.g., L2, IP, COSINE)")
    max_top_k: int = Field(description="Maximum allowed value for top_k parameter")
    max_collection_name_length: int = Field(default=255, description="Maximum allowed length for collection names")
    max_payload_size_bytes: int = Field(default=65535, description="Maximum payload size in bytes")
    supported_index_types: List[str] = Field(default=["hnsw", "ivf_flat", "flat"], description="Supported indexing algorithms (lowercase, database-agnostic names)")
    state_constraints: List[str] = Field(default=["collection_exists", "data_ready"], description="Pre-conditions for execution (database-agnostic: collection must exist, data/index must be ready)")
    source_urls: Dict[str, str] = Field(default_factory=dict)
    exhaustive_constraints: Dict[str, Any] = Field(default_factory=dict)

class DefectReport(BaseModel):
    """Classified defect report."""
    case_id: str
    bug_type: str = Field(description="Type-1, Type-2, Type-3, or Type-4")
    evidence_level: str = Field(description="L1, L2, or L3 evidence level")
    root_cause_analysis: str
    source_url: Optional[str] = None
    
    # New fields for better deduplication and reporting
    title: str = Field(default="", description="Short descriptive title of the bug")
    operation: str = Field(default="", description="The operation that triggered the bug (e.g., search, insert)")
    error_message: str = Field(default="", description="The raw error message from the database")
    database: str = Field(default="", description="The target database name and version")
    l1_violation_details: Optional[Dict[str, Any]] = Field(default=None, description="L1 contract violation details propagated from execution result")

    is_verified: bool = False
    mre_code: Optional[str] = Field(default=None, description="Minimal Reproducible Example")
    issue_url: Optional[str] = None
    validated_references: List[Dict[str, Any]] = Field(default_factory=list, description="Validated documentation references")
    verification_status: str = Field(default="pending", description="Status of MRE verification: pending, success, failed")
    verification_log: str = Field(default="", description="Log from MRE verification process")
    verifier_verdict: str = Field(default="pending", description="Verifier verdict: pending, reproduced_bug, expected_rejection, false_positive, invalid_report, inconclusive")
    false_positive: bool = Field(default=False, description="Whether verifier concluded this is a false positive")
    reproduced_bug: bool = Field(default=False, description="Whether the bug was reproduced by MRE verification")

class WorkflowState(BaseModel):
    """
    Global State Schema for LangGraph.
    This state object is passed between all agents in the pipeline.
    """
    run_id: str = Field(description="Unique identifier for the current test run")
    iteration_count: int = Field(default=0, description="Current fuzzing loop iteration")
    max_iterations: int = Field(default=10, description="Maximum allowed fuzzing loops")
    
    # Inputs
    target_db_input: str = Field(description="User input for target DB, e.g., 'Milvus v2.6.12'")
    business_scenario: str = Field(default="", description="Optional business scenario provided by user")
    
    # Context & Configs
    db_config: Optional[DatabaseConfig] = None
    contracts: Optional[Contract] = None
    
    # Runtime Data
    current_test_cases: List[TestCase] = Field(default_factory=list)
    execution_results: List[ExecutionResult] = Field(default_factory=list)
    oracle_results: List[OracleValidation] = Field(default_factory=list)
    
    # Outputs & Feedback
    defect_reports: List[DefectReport] = Field(default_factory=list)
    verified_defects: List[DefectReport] = Field(default_factory=list, description="Defects confirmed as reproducible by verifier")
    fuzzing_feedback: str = Field(default="", description="Feedback from Agent 5 to Agent 2 for the next loop")
    external_knowledge: str = Field(default="", description="Knowledge retrieved from Web Search Agent")
    history_vectors: List[List[float]] = Field(default_factory=list, description="Store historical vectors for semantic coverage tracking")
    
    # Control Flags & Budgets
    from_scratch: bool = Field(
        default=False,
        description="If true, disables hot sandbox reuse and forces a fresh Docker environment startup"
    )
    should_terminate: bool = Field(default=False, description="Flag to gracefully terminate the loop")
    total_tokens_used: int = Field(default=0, description="Cumulative tokens consumed by LLMs")
    max_token_budget: int = Field(default=100000, description="Maximum token budget before circuit breaking")
    consecutive_failures: int = Field(default=0, description="Counter for consecutive generation or gating failures")
    max_consecutive_failures: int = Field(default=3, description="Threshold to trigger circuit breaker")

    # Document Preprocessing
    docs_validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Document validation results from preprocessing pipeline"
    )

    # L2 Runtime Gating State
    current_collection: Optional[str] = Field(
        default=None,
        description="Active collection name for L2 runtime readiness check"
    )
    data_inserted: bool = Field(
        default=False,
        description="Whether data has been inserted into the active collection"
    )


class CompressionUtils:
    """
    Utility class for data compression and optimization.
    """

    @staticmethod
    def compress_data(data: bytes, algorithm: str = "gzip") -> bytes:
        """
        Compress data using specified algorithm.

        Args:
            data: Raw data to compress
            algorithm: Compression algorithm ('gzip' or 'zlib')

        Returns:
            Compressed data
        """
        if algorithm == "gzip":
            return gzip.compress(data, compresslevel=9)
        elif algorithm == "zlib":
            return zlib.compress(data, level=9)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")

    @staticmethod
    def decompress_data(compressed_data: bytes, algorithm: str = "gzip") -> bytes:
        """
        Decompress data using specified algorithm.

        Args:
            compressed_data: Compressed data
            algorithm: Compression algorithm ('gzip' or 'zlib')

        Returns:
            Decompressed data
        """
        if algorithm == "gzip":
            return gzip.decompress(compressed_data)
        elif algorithm == "zlib":
            return zlib.decompress(compressed_data)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")

    @staticmethod
    def compress_vectors(vectors: List[List[float]]) -> bytes:
        """
        Compress vector data efficiently using binary format.

        Args:
            vectors: List of vectors to compress

        Returns:
            Compressed binary data
        """
        if not vectors:
            return b""

        # Convert to binary format for better compression
        # Format: [num_vectors][dimension][vector1_floats][vector2_floats]...
        num_vectors = len(vectors)
        dimension = len(vectors[0])

        # Pack as binary floats.
        #
        # IMPORTANT:
        # - Use float64 ("d", 8 bytes) to preserve precision for round-trips.
        #   Unit tests expect <= 1e-6 absolute error which float32 may violate
        #   for values around ~1e2.
        binary_data = struct.pack(f"!II", num_vectors, dimension)
        for vector in vectors:
            # Ensure all vectors have same dimension
            if len(vector) != dimension:
                raise ValueError("All vectors must have the same dimension")
            # Pack floats as 64-bit floats
            binary_data += struct.pack(f"!{dimension}d", *vector)

        # Compress the binary data
        return CompressionUtils.compress_data(binary_data, algorithm="gzip")

    @staticmethod
    def normalize_vectors(
        vectors: List[List[float]],
        target_dimension: Optional[int] = None,
        pad_value: float = 0.0,
    ) -> Tuple[List[List[float]], int]:
        """
        Normalize vectors to a fixed dimension via pad/truncate.

        Strategy:
        - If target_dimension is provided, use it.
        - Otherwise, infer the dominant (most frequent) non-zero dimension.
          In case of tie, use the larger dimension to reduce truncation risk.

        Args:
            vectors: Raw vectors (potentially mixed dimensions)
            target_dimension: Optional fixed target dimension
            pad_value: Value used for right-padding shorter vectors

        Returns:
            (normalized_vectors, target_dimension)
        """
        if not vectors:
            return [], 0

        if target_dimension is None:
            lengths = [len(v) for v in vectors if isinstance(v, list) and len(v) > 0]
            if not lengths:
                return [[] for _ in vectors], 0
            length_counter = Counter(lengths)
            max_freq = max(length_counter.values())
            candidates = [dim for dim, freq in length_counter.items() if freq == max_freq]
            target_dimension = max(candidates)

        if target_dimension < 0:
            raise ValueError("target_dimension must be >= 0")

        normalized: List[List[float]] = []
        for vector in vectors:
            vec = list(vector) if isinstance(vector, list) else []
            current_dim = len(vec)

            if current_dim < target_dimension:
                vec = vec + [pad_value] * (target_dimension - current_dim)
            elif current_dim > target_dimension:
                vec = vec[:target_dimension]

            normalized.append(vec)

        return normalized, target_dimension

    @staticmethod
    def decompress_vectors(compressed_data: bytes) -> List[List[float]]:
        """
        Decompress vector data from binary format.

        Args:
            compressed_data: Compressed binary data

        Returns:
            List of vectors
        """
        if not compressed_data:
            return []

        # Decompress first
        binary_data = CompressionUtils.decompress_data(compressed_data, algorithm="gzip")

        # Unpack header
        num_vectors, dimension = struct.unpack("!II", binary_data[:8])

        # Unpack vectors (float64)
        vectors = []
        offset = 8
        for _ in range(num_vectors):
            vector = list(struct.unpack(f"!{dimension}d", binary_data[offset:offset + dimension * 8]))
            vectors.append(vector)
            offset += dimension * 8

        return vectors

    @staticmethod
    def calculate_hash(data: bytes) -> str:
        """
        Calculate SHA-256 hash of data.

        Args:
            data: Data to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()


class DockerContainerPool:
    """
    Docker container connection pool for reusing containers across tests.
    
    Features:
    - Container reuse to reduce creation/destruction overhead
    - Idle timeout cleanup
    - Orphaned container cleanup
    - Configurable pool size limits
    """
    
    def __init__(
        self,
        docker_client=None,
        min_connections: int = 1,
        max_connections: int = 3,
        idle_timeout_minutes: int = 10
    ):
        self.docker_client = docker_client
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.idle_timeout_minutes = idle_timeout_minutes
        
        self.containers = {}
        self.enabled = False
        self.config = None
        
        self.container_name_prefix = "ai_db_qc_"
        
        if self.docker_client is None:
            try:
                import docker
                self.docker_client = docker.from_env()
            except Exception as e:
                logger.error(f"[DockerContainerPool] Failed to initialize Docker client: {e}")
    
    def set_config(self, config):
        """Set configuration loader and check if pool is enabled."""
        self.config = config
        self.enabled = config.get_bool("docker_pool.enabled", default=False)
        if self.enabled:
            logger.info(f"[DockerContainerPool] Pool ENABLED (min={self.min_connections}, max={self.max_connections}, idle_timeout={self.idle_timeout_minutes}min)")
            self.cleanup_orphaned_containers()
        else:
            logger.info("[DockerContainerPool] Pool DISABLED")
    
    def _generate_container_name(self, image_name: str) -> str:
        """Generate a unique container name."""
        import time
        timestamp = int(time.time())
        image_hash = hashlib.md5(image_name.encode()).hexdigest()[:8]
        return f"{self.container_name_prefix}{timestamp}_{image_hash}"
    
    def get_container(
        self,
        image_name: str,
        env_vars: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        command: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get a container from the pool or create a new one.
        
        Args:
            image_name: Docker image name
            env_vars: Environment variables
            ports: Port mappings
            command: Container command
            
        Returns:
            Container object or None if failed
        """
        if not self.enabled or not self.docker_client:
            logger.debug("[DockerContainerPool] Pool disabled or no Docker client")
            return None
        
        try:
            if self.docker_client is None:
                import docker
                self.docker_client = docker.from_env()
            
            self._cleanup_idle_containers()
            
            available_container = self._find_available_container(image_name)
            
            if available_container:
                container_id = available_container.id
                self.containers[container_id]["idle"] = False
                self.containers[container_id]["last_used"] = time.time()
                logger.info(f"[DockerContainerPool] Container REUSED: {container_id[:12]} (image={image_name}, pool_size={len(self.containers)}/{self.max_connections})")
                return available_container
            elif len(self.containers) < self.max_connections:
                new_container = self._create_container(
                    image_name, env_vars, ports, command
                )
                if new_container:
                    container_id = new_container.id
                    self.containers[container_id] = {
                        "container": new_container,
                        "last_used": time.time(),
                        "idle": False,
                        "image_name": image_name
                    }
                    logger.info(f"[DockerContainerPool] Container CREATED: {container_id[:12]} (image={image_name}, pool_size={len(self.containers)}/{self.max_connections})")
                    return new_container
            
            logger.warning(f"[DockerContainerPool] Pool FULL: cannot create container (pool_size={len(self.containers)}/{self.max_connections})")
            return None
            
        except Exception as e:
            logger.error(f"[DockerContainerPool] Error getting container: {e}")
            return None
    
    def _find_available_container(self, image_name: str) -> Optional[Any]:
        """Find an available container for the given image."""
        for container_id, container_info in self.containers.items():
            container = container_info["container"]
            
            try:
                if container_info["image_name"] == image_name:
                    container.reload()
                    if container.status == "running":
                        return container
                    else:
                        self._remove_container(container_id)
            except Exception:
                self._remove_container(container_id)
        
        return None
    
    def _create_container(
        self,
        image_name: str,
        env_vars: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        command: Optional[str] = None
    ) -> Optional[Any]:
        """Create a new container."""
        try:
            env_list = [f"{k}={v}" for k, v in (env_vars or {}).items()]
            port_bindings = {k: v for k, v in (ports or {}).items()}
            
            container = self.docker_client.containers.create(
                image=image_name,
                environment=env_list if env_list else None,
                ports=port_bindings if port_bindings else None,
                command=command,
                name=self._generate_container_name(image_name),
                detach=True
            )
            container.start()
            return container
            
        except Exception as e:
            logger.error(f"[DockerContainerPool] Error creating container for image {image_name}: {e}")
            return None
    
    def release_container(self, container_id: str):
        """
        Release a container back to the pool.
        
        Args:
            container_id: Container ID
        """
        if not self.enabled:
            return
        
        if container_id in self.containers:
            self.containers[container_id]["idle"] = True
            self.containers[container_id]["last_used"] = time.time()
            logger.info(f"[DockerContainerPool] Container RELEASED: {container_id[:12]} (pool_size={len(self.containers)}/{self.max_connections})")
    
    def _cleanup_idle_containers(self):
        """Clean up containers that have been idle for too long."""
        if not self.enabled:
            return
        
        current_time = time.time()
        timeout_seconds = self.idle_timeout_minutes * 60
        
        containers_to_remove = []
        
        for container_id, container_info in self.containers.items():
            if container_info["idle"]:
                idle_time = current_time - container_info["last_used"]
                if idle_time > timeout_seconds:
                    containers_to_remove.append(container_id)
        
        for container_id in containers_to_remove:
            idle_duration = (current_time - self.containers[container_id]["last_used"]) / 60
            self._remove_container(container_id)
            logger.info(f"[DockerContainerPool] Container CLEANED UP (idle): {container_id[:12]} (idle_duration={idle_duration:.1f}min, pool_size={len(self.containers)}/{self.max_connections})")
    
    def _remove_container(self, container_id: str):
        """Remove a container from the pool."""
        if container_id in self.containers:
            container_info = self.containers[container_id]
            container = container_info["container"]
            
            try:
                container.reload()
                if container.status == "running":
                    container.stop(timeout=5)
                container.remove()
            except Exception as e:
                logger.error(f"[DockerContainerPool] Error removing container {container_id[:12]}: {e}")
            
            del self.containers[container_id]
    
    def cleanup_orphaned_containers(self):
        """Clean up orphaned containers from previous runs."""
        if not self.enabled or not self.docker_client:
            return
        
        try:
            all_containers = self.docker_client.containers.list(all=True)
            orphaned = [
                c for c in all_containers
                if c.name and c.name.startswith(self.container_name_prefix)
            ]
            
            cleaned_count = 0
            for container in orphaned:
                try:
                    container.reload()
                    if container.status != "running":
                        container.remove()
                        cleaned_count += 1
                        logger.debug(f"[DockerContainerPool] Cleaned up orphaned container: {container.name}")
                except Exception as e:
                    logger.error(f"[DockerContainerPool] Error cleaning up orphaned container {container.name}: {e}")
            
            if orphaned:
                logger.info(f"[DockerContainerPool] Orphaned containers CLEANED: {cleaned_count}/{len(orphaned)}")
            
        except Exception as e:
            logger.error(f"[DockerContainerPool] Error cleaning up orphaned containers: {e}")
    
    def shutdown(self):
        """Shutdown the pool and remove all containers."""
        if not self.enabled:
            return
        
        container_count = len(self.containers)
        container_ids = list(self.containers.keys())
        for container_id in container_ids:
            self._remove_container(container_id)
        
        logger.info(f"[DockerContainerPool] Pool SHUTDOWN: removed {container_count} container(s)")

class StateManager:
    """
    Manages state persistence and retrieval for AI-DB-QC runs.

    Provides methods to save and load workflow state from JSON files
    with compression and incremental update support.
    """

    def __init__(self, base_dir: str = "runs", compression_algorithm: str = "gzip"):
        """
        Initialize StateManager.

        Args:
            base_dir: Base directory for run state files
            compression_algorithm: Compression algorithm ('gzip' or 'zlib')
        """
        self.base_dir = Path(base_dir)
        self.compression_algorithm = compression_algorithm

    def save_state(self, run_id: str, state: WorkflowState, incremental: bool = True) -> Dict[str, Any]:
        """
        Save workflow state to compressed file with optional incremental updates.

        Args:
            run_id: Unique run identifier
            state: WorkflowState to save
            incremental: Whether to use incremental update (default: True)

        Returns:
            Dictionary with compression statistics
        """
        import os
        from pathlib import Path

        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        state_file = run_dir / "state.json.gz"
        metadata_file = run_dir / "metadata.json"

        # Custom encoder for datetime/date objects
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        # Prepare state data
        # - original_state_dict: as-is for "original_size" estimation
        # - state_dict: optimized payload to actually persist
        original_state_dict = state.model_dump()
        state_dict = dict(original_state_dict)

        # Compress vectors separately for both speed and better overall compression.
        # Store as base64 to avoid hex expansion (2x) while keeping JSON-safe string.
        vectors_meta: Dict[str, Any] = {}
        if state_dict.get("history_vectors"):
            vectors = state_dict["history_vectors"]
            normalized_vectors, target_dimension = CompressionUtils.normalize_vectors(vectors)
            compressed_vectors = CompressionUtils.compress_vectors(normalized_vectors)
            state_dict["history_vectors_compressed"] = base64.b64encode(compressed_vectors).decode("ascii")
            del state_dict["history_vectors"]
            original_dimensions = sorted({len(v) for v in vectors if isinstance(v, list)})
            vectors_meta = {
                "format": "base64",
                "algorithm": "gzip",
                "dtype": "float64",
                "target_dimension": target_dimension,
                "original_dimensions": original_dimensions,
                "normalized": len(original_dimensions) > 1,
            }

        # Convert to JSON without indentation for better compression
        original_json_bytes = json.dumps(
            original_state_dict, default=json_serial, separators=(",", ":")
        ).encode("utf-8")
        optimized_json_bytes = json.dumps(
            state_dict, default=json_serial, separators=(",", ":")
        ).encode("utf-8")

        # Compress the optimized JSON payload
        compressed_data = CompressionUtils.compress_data(optimized_json_bytes, self.compression_algorithm)

        # Stats:
        # - original_size: size of unoptimized JSON (incl. raw vectors) so compression ratio
        #   reflects "what user would have stored" without optimization.
        # - compressed_size: bytes actually persisted to disk.
        original_size = len(original_json_bytes)
        compressed_size = len(compressed_data)
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

        # Save compressed state
        try:
            with open(state_file, 'wb') as f:
                f.write(compressed_data)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[StateManager] Error saving compressed state: {e}")
            # Fallback to uncompressed JSON
            state_file_uncompressed = run_dir / "state.json"
            try:
                with open(state_file_uncompressed, 'w', encoding='utf-8') as f:
                    json.dump(state_dict, f, indent=2, default=json_serial)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e2:
                print(f"[StateManager] Fallback save also failed: {e2}")
                raise

        # Save metadata for incremental updates
        metadata = {
            "version": "2.0",
            "compression_algorithm": self.compression_algorithm,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "timestamp": datetime.now().isoformat(),
            "run_id": run_id,
            "has_compressed_vectors": "history_vectors_compressed" in state_dict,
            "vectors": vectors_meta or None,
        }

        # Handle incremental updates
        if incremental:
            previous_metadata = self._load_metadata(run_id)
            if previous_metadata:
                metadata["previous_hash"] = previous_metadata.get("current_hash", "")
                metadata["is_incremental"] = True
            else:
                metadata["is_incremental"] = False

        # Calculate current hash
        metadata["current_hash"] = CompressionUtils.calculate_hash(compressed_data)

        # Save metadata
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[StateManager] Error saving metadata: {e}")

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "algorithm": self.compression_algorithm
        }

    def _load_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load metadata for a run.

        Args:
            run_id: Unique run identifier

        Returns:
            Metadata dictionary or None if not found
        """
        metadata_file = self.base_dir / run_id / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[StateManager] Error loading metadata: {e}")
            return None

    def load_state(self, run_id: str) -> Optional[WorkflowState]:
        """
        Load workflow state from compressed file.

        Args:
            run_id: Unique run identifier

        Returns:
            WorkflowState if found, None otherwise
        """
        from pathlib import Path

        # Try compressed file first
        state_file = self.base_dir / run_id / "state.json.gz"

        if state_file.exists():
            try:
                with open(state_file, 'rb') as f:
                    compressed_data = f.read()

                # Decompress the data
                json_bytes = CompressionUtils.decompress_data(compressed_data, self.compression_algorithm)
                json_str = json_bytes.decode('utf-8')
                data = json.loads(json_str)

                # Decompress vectors if present
                if "history_vectors_compressed" in data:
                    encoded = data["history_vectors_compressed"]
                    # Backward compatible: accept both base64 (preferred) and hex (legacy)
                    try:
                        compressed_vectors = base64.b64decode(encoded.encode("ascii"), validate=True)
                    except Exception:
                        compressed_vectors = bytes.fromhex(encoded)
                    data["history_vectors"] = CompressionUtils.decompress_vectors(compressed_vectors)
                    del data["history_vectors_compressed"]
                    if "vectors" in data:
                        # metadata field; keep out of WorkflowState
                        del data["vectors"]

                return WorkflowState(**data)

            except Exception as e:
                print(f"[StateManager] Error loading compressed state: {e}")
                # Fall back to uncompressed file

        # Try uncompressed JSON file
        state_file_uncompressed = self.base_dir / run_id / "state.json"

        if state_file_uncompressed.exists():
            try:
                with open(state_file_uncompressed, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return WorkflowState(**data)
            except Exception as e:
                print(f"[StateManager] Error loading uncompressed state: {e}")
                return None

        return None

    def list_runs(self) -> List[str]:
        """
        List all available run IDs.

        Returns:
            List of run IDs
        """
        if not self.base_dir.exists():
            return []

        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def get_compression_stats(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get compression statistics for a run.

        Args:
            run_id: Unique run identifier

        Returns:
            Dictionary with compression statistics or None if not found
        """
        metadata = self._load_metadata(run_id)
        if not metadata:
            return None

        return {
            "original_size": metadata.get("original_size", 0),
            "compressed_size": metadata.get("compressed_size", 0),
            "compression_ratio": metadata.get("compression_ratio", 0),
            "algorithm": metadata.get("compression_algorithm", "unknown"),
            "timestamp": metadata.get("timestamp", ""),
            "is_incremental": metadata.get("is_incremental", False),
            "has_compressed_vectors": metadata.get("has_compressed_vectors", False)
        }

    def incremental_update(self, run_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform incremental update to existing state.

        Args:
            run_id: Unique run identifier
            updates: Dictionary of fields to update

        Returns:
            Dictionary with update statistics
        """
        # Load existing state
        state = self.load_state(run_id)
        if state is None:
            raise ValueError(f"Run {run_id} not found")

        # Apply updates
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                print(f"[StateManager] Warning: Field {key} not found in state")

        # Save updated state
        stats = self.save_state(run_id, state, incremental=True)

        return {
            "updated": True,
            "fields_updated": list(updates.keys()),
            **stats
        }

    def optimize_storage(self, run_id: str) -> Dict[str, Any]:
        """
        Optimize storage for a run by recompressing with current settings.

        Args:
            run_id: Unique run identifier

        Returns:
            Dictionary with optimization statistics
        """
        # Load existing state
        state = self.load_state(run_id)
        if state is None:
            raise ValueError(f"Run {run_id} not found")

        # Get old stats
        old_stats = self.get_compression_stats(run_id)
        old_size = old_stats.get("compressed_size", 0) if old_stats else 0

        # Save with current compression settings
        new_stats = self.save_state(run_id, state, incremental=False)

        return {
            "optimized": True,
            "old_size": old_size,
            "new_size": new_stats["compressed_size"],
            "size_reduction": old_size - new_stats["compressed_size"],
            "improvement_ratio": (1 - new_stats["compressed_size"] / old_size) * 100 if old_size > 0 else 0
        }

    def cleanup_old_versions(self, run_id: str, keep_versions: int = 3) -> int:
        """
        Clean up old state versions, keeping only the most recent ones.

        Args:
            run_id: Unique run identifier
            keep_versions: Number of versions to keep (default: 3)

        Returns:
            Number of files cleaned up
        """
        run_dir = self.base_dir / run_id
        if not run_dir.exists():
            return 0

        # Find all state files
        state_files = list(run_dir.glob("state*.json*"))
        state_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Keep only the most recent versions
        files_to_delete = state_files[keep_versions:]
        deleted_count = 0

        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"[StateManager] Error deleting {file_path}: {e}")

        return deleted_count
