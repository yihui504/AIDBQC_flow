"""
Unit tests for Critical Error Handler

Tests the critical error detection, classification, and immediate interruption
mechanisms for the AI-DB-QC system.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.critical_error_handler import (
    CriticalErrorHandler,
    CriticalErrorType,
    CriticalityLevel,
    ErrorPattern,
    CriticalErrorInfo,
    get_global_critical_error_handler,
    initialize_global_critical_error_handler,
    handle_critical_errors
)
from src.exceptions import (
    LLMRateLimitError,
    LLMTokenLimitError,
    DatabaseConnectionError,
    PoolExhaustedError,
    CircuitBreakerError,
    ErrorEvidence
)


class TestCriticalErrorClassification(unittest.TestCase):
    """Test critical error classification functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = CriticalErrorHandler(
            log_dir=str(Path(self.temp_dir) / "logs"),
            state_dir=str(Path(self.temp_dir) / "runs"),
            enable_auto_cleanup=False  # Disable auto cleanup for tests
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_docker_port_conflict_detection(self):
        """Test detection of Docker port conflict errors."""
        error_message = "Error starting container: port is already allocated"
        exception = RuntimeError(error_message)
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertEqual(critical_info.error_type, CriticalErrorType.DOCKER_PORT_CONFLICT)
        self.assertEqual(critical_info.criticality_level, CriticalityLevel.EMERGENCY)
        self.assertTrue(critical_info.requires_immediate_shutdown)
    
    def test_api_rate_limit_detection(self):
        """Test detection of API rate limit errors."""
        error_message = "Rate limit exceeded: too many requests"
        exception = RuntimeError(error_message)
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertEqual(critical_info.error_type, CriticalErrorType.API_RATE_LIMIT)
        self.assertEqual(critical_info.criticality_level, CriticalityLevel.CRITICAL)
        self.assertTrue(critical_info.requires_immediate_shutdown)
    
    def test_llm_rate_limit_exception_detection(self):
        """Test detection of LLM rate limit exceptions."""
        exception = LLMRateLimitError(
            provider="openai",
            retry_after_seconds=60
        )
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertEqual(critical_info.error_type, CriticalErrorType.API_RATE_LIMIT)
        self.assertIn("openai", critical_info.context)
    
    def test_memory_exhaustion_detection(self):
        """Test detection of memory exhaustion errors."""
        error_message = "MemoryError: cannot allocate memory"
        exception = MemoryError(error_message)
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertEqual(critical_info.error_type, CriticalErrorType.MEMORY_EXHAUSTION)
        self.assertEqual(critical_info.criticality_level, CriticalityLevel.EMERGENCY)
    
    def test_disk_full_detection(self):
        """Test detection of disk full errors."""
        error_message = "OSError: [Errno 28] No space left on device"
        exception = OSError(28, "No space left on device")
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertEqual(critical_info.error_type, CriticalErrorType.DISK_FULL)
    
    def test_non_critical_error(self):
        """Test that non-critical errors are not classified as critical."""
        exception = ValueError("Invalid input parameter")
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNone(critical_info)
    
    def test_is_critical_error(self):
        """Test the is_critical_error method."""
        critical_error = RuntimeError("port is already allocated")
        non_critical_error = ValueError("Invalid input")
        
        self.assertTrue(self.handler.is_critical_error(critical_error))
        self.assertFalse(self.handler.is_critical_error(non_critical_error))
    
    def test_should_interrupt_immediately(self):
        """Test the should_interrupt_immediately method."""
        emergency_error = RuntimeError("port is already allocated")
        network_error = ConnectionError("Network timeout")
        
        self.assertTrue(self.handler.should_interrupt_immediately(emergency_error))
        self.assertFalse(self.handler.should_interrupt_immediately(network_error))
    
    def test_error_evidence_capture(self):
        """Test that error evidence is properly captured."""
        exception = LLMRateLimitError(
            provider="anthropic",
            retry_after_seconds=120
        )
        
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertIn("provider", critical_info.context)
        self.assertEqual(critical_info.context["provider"], "anthropic")
        self.assertIn("retry_after", critical_info.context)
    
    def test_recovery_suggestions_generation(self):
        """Test that recovery suggestions are generated for different error types."""
        # Test Docker port conflict
        exception = RuntimeError("port is already allocated")
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertTrue(len(critical_info.recovery_suggestions) > 0)
        self.assertTrue(any("Docker" in suggestion for suggestion in critical_info.recovery_suggestions))
        
        # Test API rate limit
        exception = RuntimeError("rate limit exceeded")
        critical_info = self.handler.classify_critical_error(exception)
        
        self.assertIsNotNone(critical_info)
        self.assertTrue(len(critical_info.recovery_suggestions) > 0)
        self.assertTrue(any("rate limit" in suggestion.lower() for suggestion in critical_info.recovery_suggestions))


class TestCriticalErrorHandler(unittest.TestCase):
    """Test the critical error handler functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = CriticalErrorHandler(
            log_dir=str(Path(self.temp_dir) / "logs"),
            state_dir=str(Path(self.temp_dir) / "runs"),
            enable_auto_cleanup=False
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_info_serialization(self):
        """Test that critical error info can be serialized to JSON."""
        critical_info = CriticalErrorInfo(
            error_type=CriticalErrorType.DOCKER_PORT_CONFLICT,
            criticality_level=CriticalityLevel.EMERGENCY,
            error_message="port is already allocated",
            exception_type="RuntimeError",
            traceback="Traceback...",
            timestamp=datetime.now().isoformat(),
            requires_immediate_shutdown=True,
            cleanup_priority=1,
            context={"port": 8080},
            recovery_suggestions=["Stop conflicting containers"]
        )
        
        # Test to_dict conversion
        info_dict = critical_info.to_dict()
        self.assertIsInstance(info_dict, dict)
        self.assertEqual(info_dict["error_type"], "docker_port_conflict")
        
        # Test to_json conversion
        info_json = critical_info.to_json()
        self.assertIsInstance(info_json, str)
        
        # Verify JSON can be parsed
        parsed_json = json.loads(info_json)
        self.assertEqual(parsed_json["error_type"], "docker_port_conflict")
    
    def test_critical_error_persistence(self):
        """Test that critical errors are persisted to disk."""
        exception = RuntimeError("port is already allocated")
        run_id = "test_run_123"
        
        critical_info = self.handler.handle_critical_error(
            exception=exception,
            run_id=run_id,
            additional_context={"test": True}
        )
        
        # Check that error file was created
        log_dir = Path(self.temp_dir) / "logs"
        error_files = list(log_dir.glob("critical_error_*.json"))
        
        self.assertTrue(len(error_files) > 0, "Critical error file should be created")
        
        # Verify error file content
        with open(error_files[0], 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["error_type"], "docker_port_conflict")
        self.assertEqual(saved_data["requires_immediate_shutdown"], True)
    
    def test_cleanup_handler_registration(self):
        """Test that cleanup handlers can be registered."""
        cleanup_called = []
        
        def test_cleanup(run_id=None):
            cleanup_called.append(run_id)
        
        self.handler.register_cleanup_handler(test_cleanup)
        
        # Verify handler was registered
        self.assertEqual(len(self.handler._cleanup_handlers), 1)
        self.assertEqual(self.handler._cleanup_handlers[0], test_cleanup)
    
    def test_multiple_cleanup_handlers(self):
        """Test that multiple cleanup handlers can be registered and executed."""
        cleanup_order = []
        
        def cleanup1(run_id=None):
            cleanup_order.append("cleanup1")
        
        def cleanup2(run_id=None):
            cleanup_order.append("cleanup2")
        
        self.handler.register_cleanup_handler(cleanup1)
        self.handler.register_cleanup_handler(cleanup2)
        
        # Simulate cleanup execution
        self.handler._execute_cleanup_handlers("test_run")
        
        # Verify both handlers were called
        self.assertEqual(len(cleanup_order), 2)
        self.assertIn("cleanup1", cleanup_order)
        self.assertIn("cleanup2", cleanup_order)


class TestGlobalErrorHandler(unittest.TestCase):
    """Test the global error handler instance."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global handler
        import src.critical_error_handler as ceh
        ceh._global_critical_error_handler = None
    
    def test_global_handler_initialization(self):
        """Test that global handler can be initialized."""
        handler = get_global_critical_error_handler()
        
        self.assertIsNotNone(handler)
        self.assertIsInstance(handler, CriticalErrorHandler)
    
    def test_global_handler_singleton(self):
        """Test that global handler is a singleton."""
        handler1 = get_global_critical_error_handler()
        handler2 = get_global_critical_error_handler()
        
        self.assertIs(handler1, handler2)
    
    def test_global_handler_custom_initialization(self):
        """Test that global handler can be initialized with custom parameters."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            handler = initialize_global_critical_error_handler(
                log_dir=str(Path(temp_dir) / "logs"),
                state_dir=str(Path(temp_dir) / "runs"),
                enable_auto_cleanup=False
            )
            
            self.assertIsNotNone(handler)
            self.assertIsInstance(handler, CriticalErrorHandler)
            
            # Verify the same instance is returned
            handler2 = get_global_critical_error_handler()
            self.assertIs(handler, handler2)
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            # Reset global handler
            import src.critical_error_handler as ceh
            ceh._global_critical_error_handler = None


class TestHandleCriticalErrorsDecorator(unittest.TestCase):
    """Test the handle_critical_errors decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = CriticalErrorHandler(
            log_dir=str(Path(self.temp_dir) / "logs"),
            state_dir=str(Path(self.temp_dir) / "runs"),
            enable_auto_cleanup=False
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_decorator_with_critical_error(self):
        """Test that decorator handles critical errors correctly."""
        @handle_critical_errors(self.handler, run_id="test_run")
        def test_function():
            raise RuntimeError("port is already allocated")
        
        # The function should raise the error (but handle it internally)
        with self.assertRaises(RuntimeError):
            test_function()
        
        # Verify error was classified
        # (In a real scenario, the handler would trigger shutdown)
    
    def test_decorator_with_non_critical_error(self):
        """Test that decorator lets non-critical errors pass through."""
        @handle_critical_errors(self.handler, run_id="test_run")
        def test_function():
            raise ValueError("Invalid input")
        
        # Non-critical errors should be re-raised
        with self.assertRaises(ValueError):
            test_function()
    
    def test_decorator_with_normal_execution(self):
        """Test that decorator doesn't interfere with normal execution."""
        @handle_critical_errors(self.handler, run_id="test_run")
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")


if __name__ == "__main__":
    unittest.main()