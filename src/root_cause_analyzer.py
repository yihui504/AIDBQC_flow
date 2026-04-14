"""
Root Cause Analyzer for AI-DB-QC

This module provides comprehensive root cause analysis capabilities for
system errors, integrating with the MRE Generator to analyze error patterns
and generate actionable insights.

Features:
- Error pattern recognition and classification
- Rule-based root cause analysis engine
- Fix suggestion generation for each error type
- Severity assessment (Critical/High/Medium/Low)
- Error knowledge base accumulation mechanism

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-04-14
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict

from src.mre_generator import (
    MinimalReproducibleExample,
    ErrorContext,
    MREGenerator
)
from src.critical_error_handler import (
    CriticalErrorType,
    CriticalityLevel,
    CriticalErrorHandler
)


# ============================================================================
# Root Cause Category Enum
# ============================================================================

class RootCauseCategory(Enum):
    """
    Categories of root causes for system errors.

    Each category represents a distinct type of system failure that
    requires different diagnostic and remediation approaches.
    """

    # Infrastructure & Container Issues
    DOCKER_PORT_CONFLICT = "docker_port_conflict"
    CONTAINER_FAILURE = "container_failure"
    DOCKER_RESOURCE_LIMIT = "docker_resource_limit"

    # API & Rate Limiting Issues
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    API_AUTH_FAILURE = "api_auth_failure"
    API_INVALID_RESPONSE = "api_invalid_response"

    # Resource Exhaustion
    MEMORY_EXHAUSTION = "memory_exhaustion"
    FILE_DESCRIPTOR_EXHAUSTION = "file_descriptor_exhaustion"
    DISK_SPACE_EXHAUSTION = "disk_space_exhaustion"
    CPU_EXHAUSTION = "cpu_exhaustion"

    # Database Issues
    DATABASE_CONNECTION_FAILURE = "database_connection_failure"
    DATABASE_TIMEOUT = "database_timeout"
    DATABASE_QUERY_ERROR = "database_query_error"
    DATABASE_RESOURCE_EXHAUSTION = "database_resource_exhaustion"

    # Configuration Issues
    CONFIG_INVALID = "config_invalid"
    CONFIG_MISSING = "config_missing"
    CONFIG_ENV_VAR_MISSING = "config_env_var_missing"

    # Timeout Issues
    OPERATION_TIMEOUT = "operation_timeout"
    NETWORK_TIMEOUT = "network_timeout"

    # System Issues
    SYSTEM_CORRUPTION = "system_corruption"
    SECURITY_BREACH = "security_breach"
    NETWORK_FAILURE = "network_failure"

    # Unknown
    UNKNOWN = "unknown"


# ============================================================================
# Severity Level Enum
# ============================================================================

class SeverityLevel(Enum):
    """
    Severity levels for root cause analysis results.

    Used to prioritize remediation efforts and escalation procedures.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def to_int(self) -> int:
        """Convert severity to numeric priority (lower = more severe)."""
        mapping = {
            SeverityLevel.CRITICAL: 1,
            SeverityLevel.HIGH: 2,
            SeverityLevel.MEDIUM: 3,
            SeverityLevel.LOW: 4
        }
        return mapping.get(self, 4)


# ============================================================================
# Root Cause Result DataClass
# ============================================================================

@dataclass
class RootCauseResult:
    """
    Result of root cause analysis.

    Attributes:
        root_cause_category: The category of the root cause
        severity: Severity level of the issue
        error_type: Error type based on exception or error message
        error_message: The original error message
        stack_trace: Stack trace if available
        root_cause_summary: Brief summary of the identified root cause
        detailed_analysis: Detailed technical analysis
        affected_components: List of components affected by this issue
        fix_suggestions: Actionable suggestions to fix the issue
        prevention_measures: Measures to prevent recurrence
        related_errors: Related historical errors from knowledge base
        confidence_score: Confidence score (0.0-1.0) for the analysis
        analysis_timestamp: Timestamp when analysis was performed
        mre_reference: Reference to associated MRE if available
    """

    root_cause_category: RootCauseCategory
    severity: SeverityLevel
    error_type: str
    error_message: str
    stack_trace: str = ""
    root_cause_summary: str = ""
    detailed_analysis: str = ""
    affected_components: List[str] = field(default_factory=list)
    fix_suggestions: List[str] = field(default_factory=list)
    prevention_measures: List[str] = field(default_factory=list)
    related_errors: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    analysis_timestamp: str = ""
    mre_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['root_cause_category'] = self.root_cause_category.value
        data['severity'] = self.severity.value
        return data

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================================
# Error Pattern Rule
# ============================================================================

@dataclass
class ErrorPatternRule:
    """
    Rule for matching error patterns to root cause categories.

    Attributes:
        category: The root cause category this rule matches
        severity: Default severity for matching errors
        error_patterns: List of regex patterns to match against error messages
        exception_types: List of exception class names to match
        keywords: Keywords to search for in error messages
        confidence_boost: Confidence score boost when this rule matches
    """

    category: RootCauseCategory
    severity: SeverityLevel
    error_patterns: List[str] = field(default_factory=list)
    exception_types: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    confidence_boost: float = 0.0

    def matches(self, error_type: str, error_message: str) -> Tuple[bool, float]:
        """
        Check if this rule matches the given error.

        Args:
            error_type: The exception/error type name
            error_message: The error message text

        Returns:
            Tuple of (matches, confidence_score)
        """
        error_message_lower = error_message.lower()
        confidence = 0.0

        # Check exception types
        if self.exception_types:
            if error_type in self.exception_types:
                confidence += 0.4

        # Check regex patterns
        if self.error_patterns:
            for pattern in self.error_patterns:
                if re.search(pattern, error_message_lower, re.IGNORECASE):
                    confidence += 0.3
                    break

        # Check keywords
        if self.keywords:
            keyword_matches = sum(
                1 for kw in self.keywords
                if kw.lower() in error_message_lower
            )
            if keyword_matches > 0:
                confidence += min(0.3, keyword_matches * 0.1)

        matches = confidence > 0
        if matches:
            confidence = min(1.0, confidence + self.confidence_boost)

        return matches, confidence


# ============================================================================
# Root Cause Analyzer
# ============================================================================

class RootCauseAnalyzer:
    """
    Analyzes errors and determines root causes using rule-based analysis.

    This class provides comprehensive root cause analysis including:
    - Pattern-based error classification
    - Knowledge base integration for historical error tracking
    - Automated fix suggestion generation
    - Severity assessment
    - Integration with MRE Generator for detailed context
    """

    # Default analysis rules
    DEFAULT_RULES: List[ErrorPatternRule] = [
        # Docker Port Conflict
        ErrorPatternRule(
            category=RootCauseCategory.DOCKER_PORT_CONFLICT,
            severity=SeverityLevel.CRITICAL,
            error_patterns=[
                r"port.*already.*allocated",
                r"bind.*address.*already.*in.*use",
                r"port.*conflict",
                r"address.*already.*in.*use",
                r"docker.*port.*conflict"
            ],
            exception_types=["OSError", "DockerException"],
            keywords=["port", "docker", "allocate", "bind", "conflict"],
            confidence_boost=0.1
        ),

        # API Rate Limit
        ErrorPatternRule(
            category=RootCauseCategory.API_RATE_LIMIT,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"rate.*limit.*exceeded",
                r"too.*many.*requests",
                r"quota.*exceeded",
                r"429",
                r"rate.*limit"
            ],
            exception_types=["LLMRateLimitError", "RateLimitError"],
            keywords=["rate", "limit", "throttle", "429", "quota"],
            confidence_boost=0.1
        ),

        # API Timeout
        ErrorPatternRule(
            category=RootCauseCategory.API_TIMEOUT,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"timeout",
                r"timed.*out",
                r"request.*timeout",
                r"connection.*timeout"
            ],
            exception_types=["LLMTimeoutError", "TimeoutError", "asyncio.TimeoutError"],
            keywords=["timeout", "timed out", "deadline"],
            confidence_boost=0.0
        ),

        # Memory Exhaustion
        ErrorPatternRule(
            category=RootCauseCategory.MEMORY_EXHAUSTION,
            severity=SeverityLevel.CRITICAL,
            error_patterns=[
                r"out.*of.*memory",
                r"memory.*error",
                r"cannot.*allocate.*memory",
                r"oom",
                r"heap.*space"
            ],
            exception_types=["MemoryError"],
            keywords=["memory", "oom", "heap", "allocate"],
            confidence_boost=0.1
        ),

        # File Descriptor Exhaustion
        ErrorPatternRule(
            category=RootCauseCategory.FILE_DESCRIPTOR_EXHAUSTION,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"too.*many.*open.*files",
                r"file.*descriptor.*exhausted",
                r"ulimit",
                r"EMFILE"
            ],
            exception_types=["OSError"],
            keywords=["file descriptor", "ulimit", "too many open"],
            confidence_boost=0.1
        ),

        # Disk Space Exhaustion
        ErrorPatternRule(
            category=RootCauseCategory.DISK_SPACE_EXHAUSTION,
            severity=SeverityLevel.CRITICAL,
            error_patterns=[
                r"no.*space.*left.*device",
                r"disk.*full",
                r"ENOSPC",
                r"cannot.*write.*disk"
            ],
            exception_types=["OSError"],
            keywords=["disk", "space", "enospc", "full"],
            confidence_boost=0.1
        ),

        # Database Connection Failure
        ErrorPatternRule(
            category=RootCauseCategory.DATABASE_CONNECTION_FAILURE,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"connection.*refused",
                r"connection.*failed",
                r"cannot.*connect.*database",
                r"database.*unavailable"
            ],
            exception_types=["DatabaseConnectionError", "ConnectionError"],
            keywords=["database", "connection", "connect", "refused"],
            confidence_boost=0.1
        ),

        # Database Timeout
        ErrorPatternRule(
            category=RootCauseCategory.DATABASE_TIMEOUT,
            severity=SeverityLevel.MEDIUM,
            error_patterns=[
                r"database.*timeout",
                r"query.*timeout",
                r"operation.*timed.*out"
            ],
            exception_types=["DatabaseTimeoutError"],
            keywords=["database", "timeout", "query"],
            confidence_boost=0.0
        ),

        # Configuration Errors
        ErrorPatternRule(
            category=RootCauseCategory.CONFIG_INVALID,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"config.*invalid",
                r"configuration.*error",
                r"invalid.*config"
            ],
            exception_types=["ConfigurationError", "ConfigurationValidationError"],
            keywords=["config", "configuration", "invalid"],
            confidence_boost=0.1
        ),

        # Missing Configuration
        ErrorPatternRule(
            category=RootCauseCategory.CONFIG_MISSING,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"config.*missing",
                r"required.*config.*not.*found",
                r"missing.*configuration"
            ],
            exception_types=["ConfigurationMissingError"],
            keywords=["config", "missing", "required"],
            confidence_boost=0.1
        ),

        # Network Timeout
        ErrorPatternRule(
            category=RootCauseCategory.NETWORK_TIMEOUT,
            severity=SeverityLevel.MEDIUM,
            error_patterns=[
                r"network.*timeout",
                r"connection.*timeout",
                r"read.*timeout"
            ],
            exception_types=["TimeoutError", "ConnectionError"],
            keywords=["network", "timeout", "connection"],
            confidence_boost=0.0
        ),

        # Container Failure
        ErrorPatternRule(
            category=RootCauseCategory.CONTAINER_FAILURE,
            severity=SeverityLevel.HIGH,
            error_patterns=[
                r"container.*exited",
                r"container.*crashed",
                r"container.*not.*running",
                r"docker.*container.*fail"
            ],
            exception_types=[],
            keywords=["container", "docker", "exited", "crashed"],
            confidence_boost=0.1
        ),
    ]

    def __init__(
        self,
        knowledge_base_dir: str = ".trae/error_knowledge_base",
        enable_kb: bool = True,
        rules: Optional[List[ErrorPatternRule]] = None
    ):
        """
        Initialize the Root Cause Analyzer.

        Args:
            knowledge_base_dir: Directory for storing error knowledge base
            enable_kb: Whether to enable knowledge base integration
            rules: Custom analysis rules (uses defaults if not provided)
        """
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.enable_kb = enable_kb
        self.rules = rules or self.DEFAULT_RULES

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Create knowledge base directory
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)

        # Initialize knowledge base
        self._kb_errors: List[Dict[str, Any]] = []
        self._kb_categories: Dict[str, int] = defaultdict(int)

        if self.enable_kb:
            self._load_knowledge_base()

        self.logger.info("RootCauseAnalyzer initialized")

    def _load_knowledge_base(self) -> None:
        """Load knowledge base from disk."""
        kb_file = self.knowledge_base_dir / "error_knowledge_base.json"

        if kb_file.exists():
            try:
                with open(kb_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._kb_errors = data.get('errors', [])
                    self._kb_categories = defaultdict(
                        int,
                        data.get('categories', {})
                    )
                self.logger.info(
                    f"Loaded {len(self._kb_errors)} errors from knowledge base"
                )
            except Exception as e:
                self.logger.warning(f"Failed to load knowledge base: {e}")
                self._kb_errors = []
                self._kb_categories = defaultdict(int)

    def _save_knowledge_base(self) -> None:
        """Save knowledge base to disk."""
        if not self.enable_kb:
            return

        kb_file = self.knowledge_base_dir / "error_knowledge_base.json"

        try:
            data = {
                'errors': self._kb_errors[-1000:],  # Keep last 1000 errors
                'categories': dict(self._kb_categories),
                'last_updated': datetime.now().isoformat()
            }

            with open(kb_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug("Knowledge base saved")
        except Exception as e:
            self.logger.error(f"Failed to save knowledge base: {e}")

    def analyze_error(
        self,
        exception: Exception,
        error_context: Optional[ErrorContext] = None,
        mre: Optional[MinimalReproducibleExample] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> RootCauseResult:
        """
        Analyze an error and determine its root cause.

        Args:
            exception: The exception to analyze
            error_context: Optional error context from MRE Generator
            mre: Optional MRE for additional context
            additional_context: Additional context information

        Returns:
            RootCauseResult with analysis results
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = ""

        try:
            import traceback
            stack_trace = traceback.format_exc()
        except Exception:
            pass

        # Use error_context if provided
        if error_context:
            if error_context.error_type:
                error_type = error_context.error_type
            if error_context.error_message:
                error_message = error_context.error_message
            if error_context.stack_trace:
                stack_trace = error_context.stack_trace

        # Apply analysis rules
        category, severity, confidence = self._apply_rules(
            error_type, error_message
        )

        # Generate analysis details
        root_cause_summary, detailed_analysis = self._generate_analysis(
            category, error_type, error_message, mre
        )

        # Generate fix suggestions
        fix_suggestions = self._generate_fix_suggestions(category, error_message)

        # Generate prevention measures
        prevention_measures = self._generate_prevention_measures(category)

        # Find related errors from knowledge base
        related_errors = self._find_related_errors(category, error_message)

        # Determine affected components
        affected_components = self._determine_affected_components(
            category, error_context, mre
        )

        result = RootCauseResult(
            root_cause_category=category,
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause_summary=root_cause_summary,
            detailed_analysis=detailed_analysis,
            affected_components=affected_components,
            fix_suggestions=fix_suggestions,
            prevention_measures=prevention_measures,
            related_errors=related_errors,
            confidence_score=confidence,
            analysis_timestamp=datetime.now().isoformat(),
            mre_reference=mre.mre_id if mre else None
        )

        # Store in knowledge base
        if self.enable_kb:
            self._add_to_knowledge_base(result)

        return result

    def _apply_rules(
        self,
        error_type: str,
        error_message: str
    ) -> Tuple[RootCauseCategory, SeverityLevel, float]:
        """
        Apply analysis rules to determine root cause category.

        Args:
            error_type: The exception/error type name
            error_message: The error message text

        Returns:
            Tuple of (category, severity, confidence)
        """
        best_match = None
        best_confidence = 0.0

        for rule in self.rules:
            matches, confidence = rule.matches(error_type, error_message)

            if matches and confidence > best_confidence:
                best_match = rule
                best_confidence = confidence

        if best_match:
            return best_match.category, best_match.severity, best_confidence

        # Default to UNKNOWN
        return RootCauseCategory.UNKNOWN, SeverityLevel.MEDIUM, 0.0

    def _generate_analysis(
        self,
        category: RootCauseCategory,
        error_type: str,
        error_message: str,
        mre: Optional[MinimalReproducibleExample]
    ) -> Tuple[str, str]:
        """
        Generate root cause summary and detailed analysis.

        Args:
            category: The determined root cause category
            error_type: The exception/error type
            error_message: The error message
            mre: Optional MRE for context

        Returns:
            Tuple of (summary, detailed_analysis)
        """
        summary_templates = {
            RootCauseCategory.DOCKER_PORT_CONFLICT:
                "Docker container failed to start due to port conflict. "
                "Another container or process is using the same host port.",
            RootCauseCategory.API_RATE_LIMIT:
                "API request was rejected due to rate limiting. "
                "The client has exceeded the allowed number of requests per time window.",
            RootCauseCategory.API_TIMEOUT:
                "API request timed out waiting for response. "
                "The service may be overloaded or network connectivity is impaired.",
            RootCauseCategory.MEMORY_EXHAUSTION:
                "System ran out of available memory. "
                "The process could not allocate memory for its operations.",
            RootCauseCategory.FILE_DESCRIPTOR_EXHAUSTION:
                "Process reached the limit of open file descriptors. "
                "Too many files or network connections are open.",
            RootCauseCategory.DISK_SPACE_EXHAUSTION:
                "System ran out of disk space. "
                "Cannot write new data to disk.",
            RootCauseCategory.DATABASE_CONNECTION_FAILURE:
                "Failed to establish database connection. "
                "The database server may be down or network connectivity is blocked.",
            RootCauseCategory.DATABASE_TIMEOUT:
                "Database operation timed out. "
                "Query took too long to complete or database is under heavy load.",
            RootCauseCategory.CONFIG_INVALID:
                "Configuration validation failed. "
                "One or more configuration values are invalid or out of allowed range.",
            RootCauseCategory.CONFIG_MISSING:
                "Required configuration is missing. "
                "A necessary configuration key or environment variable was not found.",
            RootCauseCategory.NETWORK_TIMEOUT:
                "Network operation timed out. "
                "Remote service is not responding within the expected time.",
            RootCauseCategory.CONTAINER_FAILURE:
                "Docker container terminated unexpectedly. "
                "The container process crashed or was killed.",
            RootCauseCategory.UNKNOWN:
                "An unexpected error occurred. "
                "The root cause could not be automatically determined.",
        }

        summary = summary_templates.get(category, summary_templates[RootCauseCategory.UNKNOWN])

        # Build detailed analysis
        detailed_parts = [
            f"Error Type: {error_type}",
            f"Error Category: {category.value}",
            f"Error Message: {error_message}",
            "",
            "Analysis:",
            summary,
        ]

        if mre:
            detailed_parts.extend([
                "",
                "MRE Context:",
                f"  - MRE ID: {mre.mre_id}",
                f"  - Timestamp: {mre.timestamp}",
                f"  - Component: {mre.error_context.component if mre.error_context else 'Unknown'}",
            ])

            if mre.environment_info:
                detailed_parts.extend([
                    "",
                    "Environment:",
                    f"  - OS: {mre.environment_info.operating_system}",
                    f"  - Python: {mre.environment_info.python_version}",
                ])

        detailed = "\n".join(detailed_parts)

        return summary, detailed

    def _generate_fix_suggestions(
        self,
        category: RootCauseCategory,
        error_message: str
    ) -> List[str]:
        """
        Generate actionable fix suggestions for the given error category.

        Args:
            category: The root cause category
            error_message: The error message for context-specific suggestions

        Returns:
            List of fix suggestions
        """
        suggestions = {
            RootCauseCategory.DOCKER_PORT_CONFLICT: [
                "Check for running containers using the conflicting port: "
                "`docker ps --format \"{{.Names}}\\t{{.Ports}}\"`",
                "Stop or remove the conflicting container: "
                "`docker stop <container_name>`",
                "Use a different host port in your configuration",
                "Clean up orphaned Docker containers: `docker container prune`",
                "Check for other processes using the port: `netstat -ano | grep <port>`"
            ],
            RootCauseCategory.API_RATE_LIMIT: [
                "Implement exponential backoff for retry logic",
                "Reduce request frequency by adding delays between calls",
                "Check current API quota and usage in provider dashboard",
                "Consider upgrading to a higher API tier with higher limits",
                "Cache responses when possible to reduce API calls",
                f"Original error hint: {error_message[:100]}"
            ],
            RootCauseCategory.API_TIMEOUT: [
                "Increase timeout duration for API requests",
                "Check network connectivity to the API endpoint",
                "Verify the API service status and try again later",
                "Implement retry logic with exponential backoff",
                "Consider breaking large requests into smaller chunks"
            ],
            RootCauseCategory.MEMORY_EXHAUSTION: [
                "Free up available system memory by closing other applications",
                "Increase swap space if possible",
                "Reduce memory usage by lowering batch sizes or concurrency",
                "Check for memory leaks in the application",
                "Profile memory usage to identify high-consumption areas",
                "Consider scaling horizontally instead of vertically"
            ],
            RootCauseCategory.FILE_DESCRIPTOR_EXHAUSTION: [
                "Increase the file descriptor limit: `ulimit -n <new_limit>`",
                "Check for unclosed file handles or connections in the code",
                "Close unnecessary database connections or file handles",
                "Review and optimize resource cleanup logic",
                "Check current limits: `ulimit -a`"
            ],
            RootCauseCategory.DISK_SPACE_EXHAUSTION: [
                "Free up disk space by removing unnecessary files",
                "Clean up log files: `find . -name \"*.log\" -delete`",
                "Remove temporary files: `rm -rf /tmp/*`",
                "Archive old data to external storage",
                "Expand disk capacity if running in a VM",
                "Check for large core dump files: `find . -name \"core\" -size +100M`"
            ],
            RootCauseCategory.DATABASE_CONNECTION_FAILURE: [
                "Verify database service is running: `systemctl status <db_service>`",
                "Check database connection parameters (host, port, credentials)",
                "Verify network connectivity to the database server",
                "Check database logs for additional error details",
                "Ensure database is not in maintenance mode",
                "Verify firewall rules allow connection to database port"
            ],
            RootCauseCategory.DATABASE_TIMEOUT: [
                "Optimize slow queries using EXPLAIN or query analysis",
                "Add appropriate indexes to frequently queried columns",
                "Reduce query complexity or result set size",
                "Consider using connection pooling for better resource management",
                "Check database server load and resource availability",
                "Increase database timeout settings if appropriate"
            ],
            RootCauseCategory.CONFIG_INVALID: [
                "Review configuration documentation for valid value ranges",
                "Check for typos in configuration keys and values",
                "Validate configuration against schema if available",
                "Ensure all required fields are properly configured",
                "Compare with known working configuration as reference"
            ],
            RootCauseCategory.CONFIG_MISSING: [
                "Set the required environment variable",
                "Add the missing configuration to your config file",
                "Check if the configuration key name is correct",
                "Verify the configuration file path is correct",
                "Ensure all required dependencies are installed"
            ],
            RootCauseCategory.NETWORK_TIMEOUT: [
                "Check network connectivity with `ping` or `traceroute`",
                "Verify firewall or proxy settings",
                "Check if the remote service is accessible",
                "Increase network timeout values in configuration",
                "Retry the operation after checking network stability"
            ],
            RootCauseCategory.CONTAINER_FAILURE: [
                "Check container logs: `docker logs <container_name>`",
                "Verify container image is not corrupted",
                "Check container resource limits are sufficient",
                "Review container health check configuration",
                "Restart the container: `docker restart <container_name>`",
                "Ensure required volumes and networks are properly configured"
            ],
            RootCauseCategory.UNKNOWN: [
                "Collect full error logs and stack traces",
                "Check system resources (CPU, memory, disk, network)",
                "Review recent system changes or deployments",
                "Search for similar issues in error knowledge base",
                "Contact support with error details for further analysis"
            ],
        }

        return suggestions.get(category, suggestions[RootCauseCategory.UNKNOWN])

    def _generate_prevention_measures(
        self,
        category: RootCauseCategory
    ) -> List[str]:
        """
        Generate prevention measures for the given error category.

        Args:
            category: The root cause category

        Returns:
            List of prevention measures
        """
        measures = {
            RootCauseCategory.DOCKER_PORT_CONFLICT: [
                "Implement port allocation tracking in deployment scripts",
                "Use Docker Compose with explicit port mappings",
                "Reserve ports in configuration to avoid conflicts",
                "Implement health checks to detect port conflicts early",
                "Use port scanning before container startup"
            ],
            RootCauseCategory.API_RATE_LIMIT: [
                "Implement robust rate limiting with exponential backoff",
                "Monitor API usage and set up alerts at 80% quota",
                "Use API key rotation for high-volume workloads",
                "Implement request queuing and throttling",
                "Cache responses to reduce unnecessary API calls"
            ],
            RootCauseCategory.API_TIMEOUT: [
                "Set appropriate timeout values with buffer margin",
                "Implement circuit breaker pattern for external API calls",
                "Monitor API latency and set up alerts for degradation",
                "Use async operations with proper timeout handling",
                "Implement retry logic with jitter"
            ],
            RootCauseCategory.MEMORY_EXHAUSTION: [
                "Implement memory usage monitoring and alerts",
                "Use resource limits in container orchestration",
                "Profile application memory usage regularly",
                "Implement memory-efficient data structures",
                "Set up automatic scaling based on memory usage"
            ],
            RootCauseCategory.FILE_DESCRIPTOR_EXHAUSTION: [
                "Monitor file descriptor usage with alerts",
                "Implement proper resource cleanup in finally blocks",
                "Use connection pooling for database and HTTP connections",
                "Set appropriate ulimit values at system level",
                "Close resources promptly when no longer needed"
            ],
            RootCauseCategory.DISK_SPACE_EXHAUSTION: [
                "Implement log rotation and retention policies",
                "Monitor disk usage with automated alerts",
                "Set up regular cleanup jobs for temporary files",
                "Use external storage for large data files",
                "Implement disk usage quotas for applications"
            ],
            RootCauseCategory.DATABASE_CONNECTION_FAILURE: [
                "Implement connection retry logic with backoff",
                "Use connection pooling for database connections",
                "Set up database health checks and monitoring",
                "Implement graceful degradation when DB is unavailable",
                "Use read replicas for read-heavy workloads"
            ],
            RootCauseCategory.DATABASE_TIMEOUT: [
                "Optimize slow queries and add proper indexes",
                "Implement query timeout limits",
                "Use async query execution for long operations",
                "Monitor query performance with alerts for slow queries",
                "Implement database connection timeout settings"
            ],
            RootCauseCategory.CONFIG_INVALID: [
                "Implement configuration validation at startup",
                "Use configuration schemas (JSON Schema, Pydantic)",
                "Document all configuration options with valid ranges",
                "Provide configuration templates with examples",
                "Implement configuration versioning"
            ],
            RootCauseCategory.CONFIG_MISSING: [
                "Implement configuration validation at startup",
                "Use environment variable validation libraries",
                "Provide clear error messages for missing config",
                "Use configuration management tools (Ansible, Chef, etc.)",
                "Document all required configuration options"
            ],
            RootCauseCategory.NETWORK_TIMEOUT: [
                "Implement proper timeout handling for all network calls",
                "Use circuit breaker pattern for external dependencies",
                "Set up network latency monitoring and alerts",
                "Implement retry logic with exponential backoff",
                "Use CDN or edge caching for static resources"
            ],
            RootCauseCategory.CONTAINER_FAILURE: [
                "Implement container health checks and restart policies",
                "Monitor container resource usage and set limits",
                "Use container orchestration (Kubernetes, Docker Swarm)",
                "Implement graceful shutdown handling in containers",
                "Regularly update container images for security patches"
            ],
            RootCauseCategory.UNKNOWN: [
                "Implement comprehensive error logging and monitoring",
                "Set up alerts for unusual error patterns",
                "Conduct regular system health checks",
                "Maintain runbooks for common error scenarios",
                "Implement chaos engineering to identify weaknesses"
            ],
        }

        return measures.get(category, measures[RootCauseCategory.UNKNOWN])

    def _find_related_errors(
        self,
        category: RootCauseCategory,
        error_message: str
    ) -> List[Dict[str, Any]]:
        """
        Find related errors from the knowledge base.

        Args:
            category: The root cause category
            error_message: The error message for similarity matching

        Returns:
            List of related error records
        """
        if not self.enable_kb or not self._kb_errors:
            return []

        related = []
        message_lower = error_message.lower()

        # Find errors in same category
        for error in self._kb_errors:
            if error.get('root_cause_category') == category.value:
                related.append(error)

        # If too few, also search by message similarity
        if len(related) < 3:
            for error in self._kb_errors:
                if error in related:
                    continue

                # Simple keyword matching
                old_message = error.get('error_message', '').lower()
                if old_message:
                    common_words = set(message_lower.split()) & set(old_message.split())
                    if len(common_words) >= 3:
                        related.append(error)

        # Return top 5 most recent
        return related[-5:]

    def _determine_affected_components(
        self,
        category: RootCauseCategory,
        error_context: Optional[ErrorContext],
        mre: Optional[MinimalReproducibleExample]
    ) -> List[str]:
        """
        Determine which components are affected by the error.

        Args:
            category: The root cause category
            error_context: Error context if available
            mre: MRE if available

        Returns:
            List of affected component names
        """
        components = set()

        # Map categories to typical affected components
        category_components = {
            RootCauseCategory.DOCKER_PORT_CONFLICT: ["docker", "container_runtime"],
            RootCauseCategory.API_RATE_LIMIT: ["api_client", "rate_limiter"],
            RootCauseCategory.API_TIMEOUT: ["api_client", "network"],
            RootCauseCategory.MEMORY_EXHAUSTION: ["system", "python_runtime"],
            RootCauseCategory.FILE_DESCRIPTOR_EXHAUSTION: ["system", "file_handler"],
            RootCauseCategory.DISK_SPACE_EXHAUSTION: ["system", "storage"],
            RootCauseCategory.DATABASE_CONNECTION_FAILURE: ["database_adapter", "db_pool"],
            RootCauseCategory.DATABASE_TIMEOUT: ["database_adapter", "query_executor"],
            RootCauseCategory.CONFIG_INVALID: ["config_manager", "validator"],
            RootCauseCategory.CONFIG_MISSING: ["config_manager", "env_loader"],
            RootCauseCategory.NETWORK_TIMEOUT: ["network", "api_client"],
            RootCauseCategory.CONTAINER_FAILURE: ["docker", "container_runtime"],
        }

        components.update(category_components.get(category, []))

        # Add from error_context
        if error_context and error_context.component:
            components.add(error_context.component)

        # Add from MRE
        if mre and mre.error_context and mre.error_context.component:
            components.add(mre.error_context.component)

        return sorted(list(components))

    def _add_to_knowledge_base(self, result: RootCauseResult) -> None:
        """
        Add analysis result to the knowledge base.

        Args:
            result: The root cause analysis result
        """
        error_record = {
            'timestamp': result.analysis_timestamp,
            'root_cause_category': result.root_cause_category.value,
            'severity': result.severity.value,
            'error_type': result.error_type,
            'error_message': result.error_message,
            'root_cause_summary': result.root_cause_summary,
            'confidence_score': result.confidence_score,
            'mre_reference': result.mre_reference
        }

        self._kb_errors.append(error_record)
        self._kb_categories[result.root_cause_category.value] += 1

        # Periodically save
        if len(self._kb_errors) % 10 == 0:
            self._save_knowledge_base()

    def generate_analysis_report(
        self,
        result: RootCauseResult,
        format: str = "markdown"
    ) -> str:
        """
        Generate a formatted analysis report.

        Args:
            result: The root cause analysis result
            format: Output format ('markdown' or 'json')

        Returns:
            Formatted report string
        """
        if format == "json":
            return result.to_json()

        # Markdown format
        report_lines = [
            "# Root Cause Analysis Report",
            "",
            f"**Analysis Timestamp:** {result.analysis_timestamp}",
            f"**MRE Reference:** {result.mre_reference or 'N/A'}",
            "",
            "## Error Information",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Error Type | {result.error_type} |",
            f"| Severity | {result.severity.value.upper()} |",
            f"| Root Cause Category | {result.root_cause_category.value} |",
            f"| Confidence Score | {result.confidence_score:.2f} |",
            "",
            "## Error Message",
            "",
            "```",
            result.error_message,
            "```",
            "",
            "## Root Cause Summary",
            "",
            result.root_cause_summary,
            "",
            "## Detailed Analysis",
            "",
            result.detailed_analysis,
            "",
            "## Affected Components",
            "",
        ]

        if result.affected_components:
            for comp in result.affected_components:
                report_lines.append(f"- {comp}")
        else:
            report_lines.append("_No specific components identified_")

        report_lines.extend([
            "",
            "## Fix Suggestions",
            "",
        ])

        for i, suggestion in enumerate(result.fix_suggestions, 1):
            report_lines.append(f"{i}. {suggestion}")

        report_lines.extend([
            "",
            "## Prevention Measures",
            "",
        ])

        for i, measure in enumerate(result.prevention_measures, 1):
            report_lines.append(f"{i}. {measure}")

        if result.related_errors:
            report_lines.extend([
                "",
                "## Related Historical Errors",
                "",
                "| Timestamp | Category | Error Message |",
                "|-----------|----------|---------------|",
            ])

            for error in result.related_errors[-5:]:
                msg_preview = error.get('error_message', '')[:50] + '...'
                report_lines.append(
                    f"| {error.get('timestamp', 'N/A')} | "
                    f"{error.get('root_cause_category', 'N/A')} | "
                    f"{msg_preview} |"
                )

        report_lines.extend([
            "",
            "## Stack Trace",
            "",
            "```",
            result.stack_trace or "No stack trace available",
            "```",
        ])

        return "\n".join(report_lines)


# ============================================================================
# Utility Functions
# ============================================================================

def analyze_error_simple(exception: Exception) -> RootCauseResult:
    """
    Convenience function to analyze an exception with default settings.

    Args:
        exception: The exception to analyze

    Returns:
        RootCauseResult with analysis
    """
    analyzer = RootCauseAnalyzer()
    return analyzer.analyze_error(exception)


def analyze_error_with_mre(
    exception: Exception,
    mre: MinimalReproducibleExample
) -> RootCauseResult:
    """
    Analyze an exception with MRE context.

    Args:
        exception: The exception to analyze
        mre: The associated MRE

    Returns:
        RootCauseResult with analysis
    """
    analyzer = RootCauseAnalyzer()
    return analyzer.analyze_error(
        exception=exception,
        error_context=mre.error_context if hasattr(mre, 'error_context') else None,
        mre=mre
    )