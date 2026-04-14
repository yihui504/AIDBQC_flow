"""
MRE (Minimal Reproducible Example) Generator for AI-DB-QC

This module provides comprehensive MRE generation capabilities for debugging
and reproducing issues in the AI-DB-QC system.

Features:
- Extract key context information from WorkflowState
- Generate minimal reproducible examples (config, test cases, contracts)
- Structured error information collection (stack traces, environment info, log snippets)
- Generate reproduction steps

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-04-14
"""

import os
import sys
import json
import logging
import traceback
import platform
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from src.state import WorkflowState, TestCase, ExecutionResult, DefectReport, Contract


# ============================================================================
# MRE Generation Configuration
# ============================================================================

class MREComplexity(Enum):
    """MRE complexity levels."""
    
    MINIMAL = "minimal"          # Only essential information
    STANDARD = "standard"        # Standard MRE with context
    COMPREHENSIVE = "comprehensive"  # Full context with environment details


@dataclass
class MREConfig:
    """Configuration for MRE generation."""
    
    complexity: MREComplexity = MREComplexity.STANDARD
    include_environment_info: bool = True
    include_system_logs: bool = True
    include_test_cases: bool = True
    include_execution_results: bool = True
    max_test_cases: int = 3
    max_log_lines: int = 50
    compress_large_data: bool = True


# ============================================================================
# MRE Components
# ============================================================================

@dataclass
class EnvironmentInfo:
    """Environment information for MRE."""
    
    operating_system: str
    python_version: str
    platform_details: str
    architecture: str
    environment_variables: Dict[str, str] = field(default_factory=dict)
    installed_packages: Dict[str, str] = field(default_factory=dict)
    docker_info: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ErrorContext:
    """Structured error context for MRE."""
    
    error_type: str
    error_message: str
    stack_trace: str
    error_code: str = ""
    error_category: str = ""
    component: str = ""
    timestamp: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MRETestConfiguration:
    """Test configuration for MRE."""
    
    target_db_input: str
    business_scenario: str
    max_iterations: int
    max_token_budget: int
    test_case_configs: List[Dict[str, Any]] = field(default_factory=list)
    contract_configs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ReproductionSteps:
    """Step-by-step reproduction instructions."""
    
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    additional_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MinimalReproducibleExample:
    """Complete MRE structure."""
    
    mre_id: str
    timestamp: str
    environment_info: EnvironmentInfo
    error_context: ErrorContext
    test_configuration: MRETestConfiguration
    reproduction_steps: ReproductionSteps
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    log_snippets: List[str] = field(default_factory=list)
    additional_artifacts: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================================
# MRE Generator
# ============================================================================

class MREGenerator:
    """
    Generates Minimal Reproducible Examples for debugging AI-DB-QC issues.
    
    This class provides comprehensive MRE generation capabilities including:
    - Environment information collection
    - Error context extraction
    - Test configuration generation
    - Reproduction step generation
    - Artifact collection
    """
    
    def __init__(
        self,
        config: Optional[MREConfig] = None,
        log_dir: str = ".trae/logs",
        mre_dir: str = ".trae/mres"
    ):
        """
        Initialize the MRE generator.
        
        Args:
            config: MRE generation configuration
            log_dir: Directory for MRE logs
            mre_dir: Directory for storing MRE files
        """
        self.config = config or MREConfig()
        self.log_dir = Path(log_dir)
        self.mre_dir = Path(mre_dir)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.mre_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("MREGenerator initialized")
    
    def generate_mre(
        self,
        exception: Exception,
        state: WorkflowState,
        run_id: str,
        node_name: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> MinimalReproducibleExample:
        """
        Generate a complete Minimal Reproducible Example.
        
        Args:
            exception: The exception that triggered MRE generation
            state: Current workflow state
            run_id: Run identifier
            node_name: Name of the node where error occurred
            additional_context: Additional context information
            
        Returns:
            MinimalReproducibleExample object
        """
        mre_id = f"mre_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()
        
        # Collect environment information
        env_info = self._collect_environment_info()
        
        # Extract error context
        error_context = self._extract_error_context(
            exception, node_name, additional_context
        )
        
        # Generate test configuration
        test_config = self._generate_test_configuration(state)
        
        # Generate reproduction steps
        repro_steps = self._generate_reproduction_steps(
            exception, state, error_context, test_config
        )
        
        # Collect test cases
        test_cases = self._collect_test_cases(state)
        
        # Collect execution results
        execution_results = self._collect_execution_results(state)
        
        # Collect log snippets
        log_snippets = self._collect_log_snippets(run_id)
        
        # Create MRE
        mre = MinimalReproducibleExample(
            mre_id=mre_id,
            timestamp=timestamp,
            environment_info=env_info,
            error_context=error_context,
            test_configuration=test_config,
            reproduction_steps=repro_steps,
            test_cases=test_cases,
            execution_results=execution_results,
            log_snippets=log_snippets
        )
        
        self.logger.info(f"Generated MRE: {mre_id}")
        return mre
    
    def _collect_environment_info(self) -> EnvironmentInfo:
        """
        Collect comprehensive environment information.
        
        Returns:
            EnvironmentInfo object with system details
        """
        env_info = EnvironmentInfo(
            operating_system=platform.system(),
            python_version=sys.version,
            platform_details=platform.platform(),
            architecture=platform.machine()
        )
        
        # Collect relevant environment variables
        relevant_env_vars = [
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "ZHIPUAI_API_KEY",
            "PATH",
            "PYTHONPATH",
            "DOCKER_HOST"
        ]
        
        for var in relevant_env_vars:
            if var in os.environ:
                # Mask sensitive information
                if "API_KEY" in var or "TOKEN" in var:
                    env_info.environment_variables[var] = "***MASKED***"
                else:
                    env_info.environment_variables[var] = os.environ[var]
        
        # Collect installed packages (key packages for AI-DB-QC)
        key_packages = [
            "langchain",
            "langgraph",
            "openai",
            "anthropic",
            "docker",
            "pydantic",
            "numpy",
            "requests"
        ]
        
        try:
            for package in key_packages:
                try:
                    result = subprocess.run(
                        ["pip", "show", package],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_line = [line for line in result.stdout.split('\n') 
                                     if line.startswith('Version:')]
                        if version_line:
                            version = version_line[0].split(':', 1)[1].strip()
                            env_info.installed_packages[package] = version
                except Exception:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to collect package info: {e}")
        
        # Collect Docker information
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                env_info.docker_info["docker_version"] = result.stdout.strip()
        except Exception:
            env_info.docker_info["docker_version"] = "Not available"
        
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                containers = [name for name in result.stdout.strip().split('\n') if name]
                env_info.docker_info["running_containers"] = containers
        except Exception:
            env_info.docker_info["running_containers"] = []
        
        return env_info
    
    def _extract_error_context(
        self,
        exception: Exception,
        node_name: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> ErrorContext:
        """
        Extract structured error context from exception.
        
        Args:
            exception: The exception to extract context from
            node_name: Name of the node where error occurred
            additional_context: Additional context information
            
        Returns:
            ErrorContext object with error details
        """
        error_context = ErrorContext(
            error_type=type(exception).__name__,
            error_message=str(exception),
            stack_trace=traceback.format_exc(),
            component=node_name,
            timestamp=datetime.now().isoformat()
        )
        
        # Extract error code if available
        if hasattr(exception, 'error_code'):
            error_context.error_code = exception.error_code
        
        # Categorize error
        error_context.error_category = self._categorize_error(exception)
        
        # Add additional context
        if additional_context:
            error_context.additional_context.update(additional_context)
        
        # Add exception-specific attributes
        if hasattr(exception, 'evidence'):
            error_context.additional_context['evidence'] = exception.evidence.to_dict()
        
        return error_context
    
    def _categorize_error(self, exception: Exception) -> str:
        """
        Categorize the error type.
        
        Args:
            exception: The exception to categorize
            
        Returns:
            Error category string
        """
        exception_type = type(exception).__name__
        error_message = str(exception).lower()
        
        # Check error categories based on type and message
        if "database" in exception_type.lower() or "connection" in error_message:
            return "database_error"
        elif "api" in exception_type.lower() or "rate limit" in error_message:
            return "api_error"
        elif "timeout" in exception_type.lower() or "timeout" in error_message:
            return "timeout_error"
        elif "memory" in exception_type.lower() or "out of memory" in error_message:
            return "resource_error"
        elif "docker" in exception_type.lower() or "container" in error_message:
            return "container_error"
        elif "contract" in exception_type.lower() or "violation" in error_message:
            return "contract_violation"
        elif "validation" in exception_type.lower():
            return "validation_error"
        else:
            return "unknown_error"
    
    def _generate_test_configuration(self, state: WorkflowState) -> MRETestConfiguration:
        """
        Generate test configuration from workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            MRETestConfiguration object
        """
        test_config = MRETestConfiguration(
            target_db_input=state.target_db_input,
            business_scenario=state.business_scenario,
            max_iterations=state.max_iterations,
            max_token_budget=state.max_token_budget
        )
        
        # Extract test case configurations
        if state.current_test_cases:
            for i, test_case in enumerate(state.current_test_cases[:self.config.max_test_cases]):
                test_config.test_case_configs.append({
                    "case_id": test_case.case_id,
                    "dimension": test_case.dimension,
                    "semantic_intent": test_case.semantic_intent,
                    "is_adversarial": test_case.is_adversarial,
                    "is_negative_test": test_case.is_negative_test
                })
        
        # Extract contract configurations
        if state.contracts:
            test_config.contract_configs = {
                "l3_application": bool(state.contracts.l3_application),
                "l2_semantic": bool(state.contracts.l2_semantic),
                "l1_api": bool(state.contracts.l1_api)
            }
        
        return test_config
    
    def _generate_reproduction_steps(
        self,
        exception: Exception,
        state: WorkflowState,
        error_context: ErrorContext,
        test_config: MRETestConfiguration
    ) -> ReproductionSteps:
        """
        Generate detailed reproduction steps.
        
        Args:
            exception: The exception that occurred
            state: Current workflow state
            error_context: Error context information
            test_config: Test configuration
            
        Returns:
            ReproductionSteps object
        """
        repro_steps = ReproductionSteps()
        
        # Generate preconditions
        repro_steps.preconditions.extend([
            f"Target database: {test_config.target_db_input}",
            f"Python version: {sys.version.split()[0]}",
            f"Business scenario: {test_config.business_scenario}",
            "Docker must be installed and running",
            "Required API keys must be configured in environment variables"
        ])
        
        # Generate reproduction steps
        repro_steps.steps.extend([
            "1. Configure environment variables (API keys, etc.)",
            "2. Start the AI-DB-QC pipeline with the following configuration:",
            f"   - target_db_input: {test_config.target_db_input}",
            f"   - max_iterations: {test_config.max_iterations}",
            f"   - max_token_budget: {test_config.max_token_budget}",
            "3. Allow the pipeline to run until the error occurs",
            f"4. Error occurs in component: {error_context.component}",
            f"5. Error type: {error_context.error_type}"
        ])
        
        # Add specific steps based on error type
        if error_context.error_category == "database_error":
            repro_steps.steps.extend([
                "6. Database connection will be attempted",
                "7. Error occurs during database operation"
            ])
        elif error_context.error_category == "api_error":
            repro_steps.steps.extend([
                "6. API calls will be made to LLM providers",
                "7. Error occurs during API request/response"
            ])
        
        # Expected behavior
        repro_steps.expected_behavior = (
            f"The pipeline should complete successfully without errors. "
            f"The {error_context.component} component should execute normally."
        )
        
        # Actual behavior
        repro_steps.actual_behavior = (
            f"An error occurred in {error_context.component}: "
            f"{error_context.error_type} - {error_context.error_message}"
        )
        
        # Additional notes
        if state.db_config:
            repro_steps.additional_notes = (
                f"Database configuration: {state.db_config.db_name} version {state.db_config.version}\n"
                f"Current iteration: {state.iteration_count}/{state.max_iterations}\n"
                f"Total tokens used: {state.total_tokens_used}/{state.max_token_budget}"
            )
        
        return repro_steps
    
    def _collect_test_cases(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """
        Collect test cases from workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        if not state.current_test_cases:
            return test_cases
        
        for test_case in state.current_test_cases[:self.config.max_test_cases]:
            test_case_dict = {
                "case_id": test_case.case_id,
                "dimension": test_case.dimension,
                "semantic_intent": test_case.semantic_intent,
                "is_adversarial": test_case.is_adversarial,
                "is_negative_test": test_case.is_negative_test,
                "expected_l1_legal": test_case.expected_l1_legal,
                "expected_l2_ready": test_case.expected_l2_ready
            }
            
            # Add query information
            if test_case.query_text:
                test_case_dict["query_text"] = test_case.query_text
            
            if test_case.query_vector:
                test_case_dict["query_vector_preview"] = test_case.query_vector[:5]
                test_case_dict["vector_dimension"] = len(test_case.query_vector)
            
            test_cases.append(test_case_dict)
        
        return test_cases
    
    def _collect_execution_results(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """
        Collect execution results from workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            List of execution result dictionaries
        """
        execution_results = []
        
        if not state.execution_results:
            return execution_results
        
        for result in state.execution_results[:self.config.max_test_cases]:
            result_dict = {
                "case_id": result.case_id,
                "success": result.success,
                "l1_passed": result.l1_passed,
                "l2_passed": result.l2_passed,
                "execution_time_ms": result.execution_time_ms
            }
            
            if result.error_message:
                result_dict["error_message"] = result.error_message
            
            if result.l1_warning:
                result_dict["l1_warning"] = result.l1_warning
            
            if result.l1_violation_details:
                result_dict["l1_violation_details"] = result.l1_violation_details
            
            execution_results.append(result_dict)
        
        return execution_results
    
    def _collect_log_snippets(self, run_id: str) -> List[str]:
        """
        Collect relevant log snippets.
        
        Args:
            run_id: Run identifier
            
        Returns:
            List of log snippet strings
        """
        log_snippets = []
        
        # Collect logs from various sources
        log_files = [
            self.log_dir / f"run_{run_id}.log",
            self.log_dir / "pipeline.log",
            self.log_dir / "agent_errors.log"
        ]
        
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Get last N lines
                    recent_lines = lines[-self.config.max_log_lines:]
                    log_snippets.append(f"=== {log_file.name} ===")
                    log_snippets.extend(recent_lines)
                    log_snippets.append("")  # Empty line between files
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read log file {log_file}: {e}")
        
        return log_snippets
    
    def save_mre(
        self,
        mre: MinimalReproducibleExample,
        run_id: str
    ) -> str:
        """
        Save MRE to disk.
        
        Args:
            mre: The MRE to save
            run_id: Run identifier
            
        Returns:
            Path to the saved MRE file
        """
        # Create run-specific directory
        run_mre_dir = self.mre_dir / run_id
        run_mre_dir.mkdir(parents=True, exist_ok=True)
        
        # Save MRE as JSON
        mre_file = run_mre_dir / f"{mre.mre_id}.json"
        
        try:
            with open(mre_file, 'w', encoding='utf-8') as f:
                f.write(mre.to_json())
            
            self.logger.info(f"MRE saved to {mre_file}")
            return str(mre_file)
        
        except Exception as e:
            self.logger.error(f"Failed to save MRE: {e}")
            return ""
    
    def generate_and_save_mre(
        self,
        exception: Exception,
        state: WorkflowState,
        run_id: str,
        node_name: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate and save MRE in one step.
        
        Args:
            exception: The exception that triggered MRE generation
            state: Current workflow state
            run_id: Run identifier
            node_name: Name of the node where error occurred
            additional_context: Additional context information
            
        Returns:
            Path to the saved MRE file
        """
        mre = self.generate_mre(
            exception=exception,
            state=state,
            run_id=run_id,
            node_name=node_name,
            additional_context=additional_context
        )
        
        return self.save_mre(mre, run_id)


# ============================================================================
# Utility Functions
# ============================================================================

def generate_mre_from_exception(
    exception: Exception,
    state: WorkflowState,
    run_id: str,
    node_name: str = "",
    additional_context: Optional[Dict[str, Any]] = None
) -> MinimalReproducibleExample:
    """
    Convenience function to generate MRE from exception.
    
    Args:
        exception: The exception that triggered MRE generation
        state: Current workflow state
        run_id: Run identifier
        node_name: Name of the node where error occurred
        additional_context: Additional context information
        
    Returns:
        MinimalReproducibleExample object
    """
    generator = MREGenerator()
    return generator.generate_mre(
        exception=exception,
        state=state,
        run_id=run_id,
        node_name=node_name,
        additional_context=additional_context
    )
