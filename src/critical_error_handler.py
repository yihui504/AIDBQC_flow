"""
Critical Error Handler for AI-DB-QC

This module provides critical error detection, classification, and immediate
interruption mechanisms for handling severe system errors that require
immediate system shutdown and cleanup.

Features:
- Critical error classification (Docker port conflicts, API rate limiting, resource exhaustion)
- Immediate interruption decision logic
- Comprehensive cleanup and shutdown procedures
- Detailed error information preservation

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-04-14
"""

import os
import sys
import json
import logging
import traceback
import signal
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from src.exceptions import (
    AIDBQCException,
    LLMRateLimitError,
    LLMTokenLimitError,
    DatabaseConnectionError,
    PoolExhaustedError,
    CircuitBreakerError,
    ErrorEvidence,
    capture_evidence
)


# ============================================================================
# Critical Error Classification
# ============================================================================

class CriticalErrorType(Enum):
    """Classification of critical error types."""
    
    DOCKER_PORT_CONFLICT = "docker_port_conflict"
    API_RATE_LIMIT = "api_rate_limit"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATABASE_FATAL = "database_fatal"
    SYSTEM_CORRUPTION = "system_corruption"
    SECURITY_BREACH = "security_breach"
    CONTAINER_FAILURE = "container_failure"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_FULL = "disk_full"
    NETWORK_FAILURE = "network_failure"
    UNKNOWN_CRITICAL = "unknown_critical"


class CriticalityLevel(Enum):
    """Criticality level determines interruption priority."""
    
    EMERGENCY = "emergency"      # Immediate shutdown required
    CRITICAL = "critical"        # Fast shutdown within 5 seconds
    SEVERE = "severe"           # Controlled shutdown within 30 seconds
    HIGH = "high"               # Graceful shutdown within 1 minute


# ============================================================================
# Error Detection Patterns
# ============================================================================

@dataclass
class ErrorPattern:
    """Pattern for matching critical errors."""
    
    error_type: CriticalErrorType
    priority: CriticalityLevel
    message_patterns: List[str]
    exception_types: List[type]
    requires_immediate_shutdown: bool = True
    cleanup_priority: int = 1  # Lower number = higher priority


# Predefined error patterns for critical error detection
CRITICAL_ERROR_PATTERNS = [
    # Docker Port Conflicts
    ErrorPattern(
        error_type=CriticalErrorType.DOCKER_PORT_CONFLICT,
        priority=CriticalityLevel.EMERGENCY,
        message_patterns=[
            "port is already allocated",
            "bind: address already in use",
            "port conflict",
            "address already in use"
        ],
        exception_types=[],
        requires_immediate_shutdown=True,
        cleanup_priority=1
    ),
    
    # API Rate Limiting
    ErrorPattern(
        error_type=CriticalErrorType.API_RATE_LIMIT,
        priority=CriticalityLevel.CRITICAL,
        message_patterns=[
            "rate limit exceeded",
            "too many requests",
            "quota exceeded",
            "429"
        ],
        exception_types=[LLMRateLimitError],
        requires_immediate_shutdown=True,
        cleanup_priority=2
    ),
    
    # Resource Exhaustion
    ErrorPattern(
        error_type=CriticalErrorType.RESOURCE_EXHAUSTION,
        priority=CriticalityLevel.CRITICAL,
        message_patterns=[
            "out of memory",
            "no space left on device",
            "resource temporarily unavailable",
            "cannot allocate memory"
        ],
        exception_types=[PoolExhaustedError, LLMTokenLimitError],
        requires_immediate_shutdown=True,
        cleanup_priority=3
    ),
    
    # Database Fatal Errors
    ErrorPattern(
        error_type=CriticalErrorType.DATABASE_FATAL,
        priority=CriticalityLevel.CRITICAL,
        message_patterns=[
            "connection refused",
            "connection timeout",
            "database is locked",
            "fatal database error"
        ],
        exception_types=[DatabaseConnectionError],
        requires_immediate_shutdown=True,
        cleanup_priority=4
    ),
    
    # System Corruption
    ErrorPattern(
        error_type=CriticalErrorType.SYSTEM_CORRUPTION,
        priority=CriticalityLevel.EMERGENCY,
        message_patterns=[
            "state corruption",
            "data corruption",
            "integrity check failed",
            "invalid state"
        ],
        exception_types=[CircuitBreakerError],
        requires_immediate_shutdown=True,
        cleanup_priority=1
    ),
    
    # Container Failures
    ErrorPattern(
        error_type=CriticalErrorType.CONTAINER_FAILURE,
        priority=CriticalityLevel.CRITICAL,
        message_patterns=[
            "container exited",
            "docker container crashed",
            "container not running",
            "unhealthy container"
        ],
        exception_types=[],
        requires_immediate_shutdown=True,
        cleanup_priority=2
    ),
    
    # Memory Exhaustion
    ErrorPattern(
        error_type=CriticalErrorType.MEMORY_EXHAUSTION,
        priority=CriticalityLevel.EMERGENCY,
        message_patterns=[
            "MemoryError",
            "cannot allocate memory",
            "out of heap space",
            "memory limit reached"
        ],
        exception_types=[MemoryError],
        requires_immediate_shutdown=True,
        cleanup_priority=1
    ),
    
    # Disk Full
    ErrorPattern(
        error_type=CriticalErrorType.DISK_FULL,
        priority=CriticalityLevel.CRITICAL,
        message_patterns=[
            "no space left on device",
            "disk full",
            "cannot write to disk",
            "ENOSPC"
        ],
        exception_types=[OSError],
        requires_immediate_shutdown=True,
        cleanup_priority=3
    ),
    
    # Network Failures
    ErrorPattern(
        error_type=CriticalErrorType.NETWORK_FAILURE,
        priority=CriticalityLevel.SEVERE,
        message_patterns=[
            "network unreachable",
            "connection reset",
            "timeout",
            "network error"
        ],
        exception_types=[ConnectionError, TimeoutError],
        requires_immediate_shutdown=False,
        cleanup_priority=5
    )
]


# ============================================================================
# Critical Error Information
# ============================================================================

@dataclass
class CriticalErrorInfo:
    """Comprehensive information about a critical error."""
    
    error_type: CriticalErrorType
    criticality_level: CriticalityLevel
    error_message: str
    exception_type: str
    traceback: str
    timestamp: str
    requires_immediate_shutdown: bool
    cleanup_priority: int
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ============================================================================
# Critical Error Handler
# ============================================================================

class CriticalErrorHandler:
    """
    Handles critical error detection, classification, and immediate interruption.
    
    This class provides:
    - Critical error pattern matching
    - Immediate shutdown decision logic
    - Comprehensive cleanup procedures
    - Error information preservation
    """
    
    def __init__(
        self,
        log_dir: str = ".trae/logs",
        state_dir: str = ".trae/runs",
        enable_auto_cleanup: bool = True,
        max_shutdown_time_seconds: int = 30
    ):
        """
        Initialize the critical error handler.
        
        Args:
            log_dir: Directory for storing critical error logs
            state_dir: Directory for run state files
            enable_auto_cleanup: Whether to automatically trigger cleanup
            max_shutdown_time_seconds: Maximum time to wait for shutdown
        """
        self.log_dir = Path(log_dir)
        self.state_dir = Path(state_dir)
        self.enable_auto_cleanup = enable_auto_cleanup
        self.max_shutdown_time_seconds = max_shutdown_time_seconds
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.CRITICAL)
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup handlers registry
        self._cleanup_handlers: List[Callable] = []
        
        # Shutdown flag
        self._is_shutting_down = False
        
        # Register signal handlers for emergency shutdown
        self._register_signal_handlers()
        
        self.logger.info("CriticalErrorHandler initialized")
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for emergency shutdown."""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception as e:
            self.logger.warning(f"Failed to register signal handlers: {e}")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle emergency signals."""
        self.logger.critical(f"Received signal {signum}, initiating emergency shutdown")
        self.trigger_emergency_shutdown(
            error_type=CriticalErrorType.UNKNOWN_CRITICAL,
            error_message=f"Received termination signal {signum}",
            exception_type="SignalInterrupt",
            traceback="Signal interrupt"
        )
    
    def register_cleanup_handler(self, handler: Callable) -> None:
        """
        Register a cleanup handler to be called during shutdown.
        
        Args:
            handler: Callable that performs cleanup operations
        """
        if handler not in self._cleanup_handlers:
            self._cleanup_handlers.append(handler)
            self.logger.info(f"Registered cleanup handler: {handler.__name__}")
    
    def classify_critical_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[CriticalErrorInfo]:
        """
        Classify an exception as a critical error.
        
        Args:
            exception: The exception to classify
            context: Additional context information
            
        Returns:
            CriticalErrorInfo if the error is critical, None otherwise
        """
        error_message = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Check against predefined patterns
        for pattern in CRITICAL_ERROR_PATTERNS:
            # Check exception type match (if specified)
            exception_type_match = False
            if pattern.exception_types:
                exception_type_match = isinstance(exception, tuple(pattern.exception_types))
              
            # Check message pattern match
            message_match = any(
                msg_pattern.lower() in error_message 
                for msg_pattern in pattern.message_patterns
            )
              
            # Match if exception type matches OR message pattern matches
            # This allows specific exception types or generic exceptions with matching messages
            if exception_type_match or message_match:
                # Extract additional context from exception
                error_context = context or {}
                
                # Add evidence if available
                if isinstance(exception, AIDBQCException) and exception.evidence:
                    error_context.update(exception.evidence.context)
                
                # Generate recovery suggestions
                recovery_suggestions = self._generate_recovery_suggestions(
                    pattern.error_type, error_message
                )
                
                return CriticalErrorInfo(
                    error_type=pattern.error_type,
                    criticality_level=pattern.priority,
                    error_message=str(exception),
                    exception_type=exception_type,
                    traceback=traceback.format_exc(),
                    timestamp=datetime.now().isoformat(),
                    requires_immediate_shutdown=pattern.requires_immediate_shutdown,
                    cleanup_priority=pattern.cleanup_priority,
                    context=error_context,
                    recovery_suggestions=recovery_suggestions
                )
        
        return None
    
    def _generate_recovery_suggestions(
        self,
        error_type: CriticalErrorType,
        error_message: str
    ) -> List[str]:
        """
        Generate recovery suggestions for the given error type.
        
        Args:
            error_type: The type of critical error
            error_message: The error message
            
        Returns:
            List of recovery suggestions
        """
        suggestions = []
        
        if error_type == CriticalErrorType.DOCKER_PORT_CONFLICT:
            suggestions.extend([
                "Check for running Docker containers using the conflicting port",
                "Stop or remove conflicting containers",
                "Use a different port configuration",
                "Clean up orphaned Docker containers"
            ])
        
        elif error_type == CriticalErrorType.API_RATE_LIMIT:
            suggestions.extend([
                "Wait for rate limit to reset",
                "Reduce API request frequency",
                "Implement exponential backoff",
                "Check API quota and limits",
                "Consider upgrading API plan"
            ])
        
        elif error_type == CriticalErrorType.RESOURCE_EXHAUSTION:
            suggestions.extend([
                "Free up system memory",
                "Increase available system resources",
                "Reduce concurrent operations",
                "Check for memory leaks",
                "Increase swap space"
            ])
        
        elif error_type == CriticalErrorType.DATABASE_FATAL:
            suggestions.extend([
                "Check database service status",
                "Verify database connection parameters",
                "Restart database service if needed",
                "Check database logs for details",
                "Verify network connectivity to database"
            ])
        
        elif error_type == CriticalErrorType.SYSTEM_CORRUPTION:
            suggestions.extend([
                "Check system integrity",
                "Restore from backup if available",
                "Clear corrupted state files",
                "Restart the application",
                "Investigate root cause of corruption"
            ])
        
        elif error_type == CriticalErrorType.CONTAINER_FAILURE:
            suggestions.extend([
                "Check Docker container logs",
                "Restart failed containers",
                "Verify container configuration",
                "Check container resource limits",
                "Review container health checks"
            ])
        
        elif error_type == CriticalErrorType.MEMORY_EXHAUSTION:
            suggestions.extend([
                "Increase system memory",
                "Reduce memory usage",
                "Kill unnecessary processes",
                "Increase swap space",
                "Optimize application memory usage"
            ])
        
        elif error_type == CriticalErrorType.DISK_FULL:
            suggestions.extend([
                "Free up disk space",
                "Clean up temporary files",
                "Remove old logs and data",
                "Expand disk capacity",
                "Archive old data"
            ])
        
        elif error_type == CriticalErrorType.NETWORK_FAILURE:
            suggestions.extend([
                "Check network connectivity",
                "Verify network configuration",
                "Retry the operation",
                "Check firewall settings",
                "Contact network administrator"
            ])
        
        else:
            suggestions.extend([
                "Review error logs for details",
                "Check system status",
                "Restart the application",
                "Contact support if issue persists"
            ])
        
        return suggestions
    
    def is_critical_error(self, exception: Exception) -> bool:
        """
        Check if an exception is a critical error.
        
        Args:
            exception: The exception to check
            
        Returns:
            True if the error is critical, False otherwise
        """
        return self.classify_critical_error(exception) is not None
    
    def should_interrupt_immediately(self, exception: Exception) -> bool:
        """
        Determine if an exception requires immediate interruption.
        
        Args:
            exception: The exception to evaluate
            
        Returns:
            True if immediate interruption is required, False otherwise
        """
        critical_info = self.classify_critical_error(exception)
        if critical_info:
            return critical_info.requires_immediate_shutdown
        return False
    
    def handle_critical_error(
        self,
        exception: Exception,
        run_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> CriticalErrorInfo:
        """
        Handle a critical error with full classification and response.
        
        Args:
            exception: The critical exception to handle
            run_id: Optional run ID for tracking
            additional_context: Additional context information
            
        Returns:
            CriticalErrorInfo object with full error details
        """
        # Classify the error
        critical_info = self.classify_critical_error(exception, additional_context)
        
        if critical_info is None:
            # Create a generic critical error info
            critical_info = CriticalErrorInfo(
                error_type=CriticalErrorType.UNKNOWN_CRITICAL,
                criticality_level=CriticalityLevel.SEVERE,
                error_message=str(exception),
                exception_type=type(exception).__name__,
                traceback=traceback.format_exc(),
                timestamp=datetime.now().isoformat(),
                requires_immediate_shutdown=False,
                cleanup_priority=10,
                context=additional_context or {}
            )
        
        # Log the critical error
        self.logger.critical(f"CRITICAL ERROR DETECTED: {critical_info.error_type.value}")
        self.logger.critical(f"Message: {critical_info.error_message}")
        self.logger.critical(f"Criticality: {critical_info.criticality_level.value}")
        
        # Save critical error information
        self._save_critical_error_info(critical_info, run_id)
        
        # Determine if immediate shutdown is required
        if critical_info.requires_immediate_shutdown:
            self.trigger_emergency_shutdown(
                error_type=critical_info.error_type,
                error_message=critical_info.error_message,
                exception_type=critical_info.exception_type,
                traceback=critical_info.traceback,
                run_id=run_id
            )
        
        return critical_info
    
    def _save_critical_error_info(
        self,
        critical_info: CriticalErrorInfo,
        run_id: Optional[str] = None
    ) -> str:
        """
        Save critical error information to disk.
        
        Args:
            critical_info: The critical error information to save
            run_id: Optional run ID for organization
            
        Returns:
            Path to the saved error file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if run_id:
            error_filename = f"critical_error_{run_id}_{timestamp}.json"
        else:
            error_filename = f"critical_error_{timestamp}.json"
        
        error_file_path = self.log_dir / error_filename
        
        try:
            with open(error_file_path, 'w', encoding='utf-8') as f:
                f.write(critical_info.to_json())
            
            self.logger.info(f"Critical error information saved to {error_file_path}")
            return str(error_file_path)
        
        except Exception as e:
            self.logger.error(f"Failed to save critical error information: {e}")
            return ""
    
    def trigger_emergency_shutdown(
        self,
        error_type: CriticalErrorType,
        error_message: str,
        exception_type: str,
        traceback: str,
        run_id: Optional[str] = None
    ) -> None:
        """
        Trigger emergency shutdown procedures.
        
        Args:
            error_type: The type of critical error
            error_message: The error message
            exception_type: The exception type
            traceback: The stack traceback
            run_id: Optional run ID for tracking
        """
        if self._is_shutting_down:
            self.logger.warning("Emergency shutdown already in progress")
            return
        
        self._is_shutting_down = True
        self.logger.critical("=" * 80)
        self.logger.critical("EMERGENCY SHUTDOWN INITIATED")
        self.logger.critical(f"Error Type: {error_type.value}")
        self.logger.critical(f"Error Message: {error_message}")
        self.logger.critical(f"Exception Type: {exception_type}")
        self.logger.critical("=" * 80)
        
        # Execute cleanup handlers
        if self.enable_auto_cleanup:
            self._execute_cleanup_handlers(run_id)
        
        # Save final state if run_id is provided
        if run_id:
            self._save_final_emergency_state(error_type, error_message, run_id)
        
        # Terminate the process
        self._terminate_process(error_type)
    
    def _execute_cleanup_handlers(self, run_id: Optional[str] = None) -> None:
        """Execute all registered cleanup handlers in priority order."""
        self.logger.critical("Executing cleanup handlers...")
        
        # Sort handlers by priority (if they have a priority attribute)
        sorted_handlers = sorted(
            self._cleanup_handlers,
            key=lambda h: getattr(h, 'cleanup_priority', 10)
        )
        
        for handler in sorted_handlers:
            try:
                handler_name = getattr(handler, '__name__', str(handler))
                self.logger.critical(f"Executing cleanup handler: {handler_name}")
                handler(run_id=run_id)
                self.logger.critical(f"Cleanup handler {handler_name} completed")
            except Exception as e:
                self.logger.error(f"Cleanup handler {handler_name} failed: {e}")
    
    def _save_final_emergency_state(
        self,
        error_type: CriticalErrorType,
        error_message: str,
        run_id: str
    ) -> None:
        """Save final emergency state information."""
        try:
            emergency_state = {
                "run_id": run_id,
                "error_type": error_type.value,
                "error_message": error_message,
                "shutdown_timestamp": datetime.now().isoformat(),
                "shutdown_reason": "emergency_critical_error",
                "status": "emergency_shutdown"
            }
            
            emergency_file = self.state_dir / run_id / "emergency_shutdown.json"
            emergency_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(emergency_file, 'w', encoding='utf-8') as f:
                json.dump(emergency_state, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Emergency state saved to {emergency_file}")
        
        except Exception as e:
            self.logger.error(f"Failed to save emergency state: {e}")
    
    def _terminate_process(self, error_type: CriticalErrorType) -> None:
        """Terminate the process with appropriate exit code."""
        exit_code = 1  # Default error exit code
        
        # Set specific exit codes based on error type
        exit_codes = {
            CriticalityLevel.EMERGENCY: 1,
            CriticalityLevel.CRITICAL: 2,
            CriticalityLevel.SEVERE: 3,
            CriticalityLevel.HIGH: 4
        }
        
        if error_type in exit_codes:
            exit_code = exit_codes[error_type]
        
        self.logger.critical(f"Terminating process with exit code {exit_code}")
        sys.exit(exit_code)


# ============================================================================
# Decorators for Critical Error Handling
# ============================================================================

def handle_critical_errors(
    error_handler: CriticalErrorHandler,
    run_id: Optional[str] = None
):
    """
    Decorator for automatically handling critical errors in functions.
    
    Args:
        error_handler: The critical error handler instance
        run_id: Optional run ID for tracking
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if this is a critical error
                if error_handler.is_critical_error(e):
                    error_handler.handle_critical_error(
                        exception=e,
                        run_id=run_id,
                        additional_context={"function": func.__name__}
                    )
                # Re-raise non-critical errors
                raise
        return wrapper
    return decorator


# ============================================================================
# Global Critical Error Handler Instance
# ============================================================================

_global_critical_error_handler: Optional[CriticalErrorHandler] = None


def get_global_critical_error_handler() -> CriticalErrorHandler:
    """
    Get the global critical error handler instance.
    
    Returns:
        The global CriticalErrorHandler instance
    """
    global _global_critical_error_handler
    if _global_critical_error_handler is None:
        _global_critical_error_handler = CriticalErrorHandler()
    return _global_critical_error_handler


def initialize_global_critical_error_handler(
    log_dir: str = ".trae/logs",
    state_dir: str = ".trae/runs",
    enable_auto_cleanup: bool = True,
    max_shutdown_time_seconds: int = 30
) -> CriticalErrorHandler:
    """
    Initialize the global critical error handler with custom parameters.
    
    Args:
        log_dir: Directory for storing critical error logs
        state_dir: Directory for run state files
        enable_auto_cleanup: Whether to automatically trigger cleanup
        max_shutdown_time_seconds: Maximum time to wait for shutdown
        
    Returns:
        The initialized CriticalErrorHandler instance
    """
    global _global_critical_error_handler
    _global_critical_error_handler = CriticalErrorHandler(
        log_dir=log_dir,
        state_dir=state_dir,
        enable_auto_cleanup=enable_auto_cleanup,
        max_shutdown_time_seconds=max_shutdown_time_seconds
    )
    return _global_critical_error_handler