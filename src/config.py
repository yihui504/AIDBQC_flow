"""
Configuration Management for AI-DB-QC

Centralized configuration using Pydantic Settings with support for:
- Environment variables
- Configuration files (YAML)
- Default values
- Validation

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import os
import logging
from typing import Optional, List, Any, Dict
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LLMConfig(BaseSettings):
    """LLM API Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    provider: str = Field(default="anthropic", description="LLM provider (anthropic, openai, zhipu)")
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    api_url: Optional[str] = Field(default=None, description="Custom API URL")
    model: str = Field(default="claude-opus-4-6", description="Model name")
    max_tokens: int = Field(default=4096, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate API URL format."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("api_url must start with http:// or https://")
        return v


class DatabaseConfig(BaseSettings):
    """Database Connection Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    type: str = Field(default="milvus", description="Database type (milvus, qdrant, weaviate)")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=19530, description="Database port")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[str] = Field(default=None, description="Database password")
    database: Optional[str] = Field(default=None, description="Database name")
    secure: bool = Field(default=False, description="Use TLS/SSL")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


class HarnessConfig(BaseSettings):
    """Harness (Workflow) Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="HARNESS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    max_iterations: int = Field(default=10, ge=1, description="Maximum fuzzing iterations")
    max_token_budget: int = Field(default=100000, ge=1, description="Maximum token budget")
    max_consecutive_failures: int = Field(default=3, ge=1, description="Max consecutive failures before recovery")
    similarity_threshold: float = Field(default=0.9, ge=0.0, le=1.0, description="Semantic similarity threshold for mode collapse")
    history_limit: int = Field(default=100, ge=1, description="Maximum history vectors to keep")

    # Collection pool settings
    pool_min_size: int = Field(default=3, ge=1, description="Minimum collection pool size")
    pool_max_size: int = Field(default=10, ge=1, description="Maximum collection pool size")
    pool_max_idle_seconds: int = Field(default=1800, ge=60, description="Collection max idle time before cleanup")

    # Telemetry settings
    telemetry_enabled: bool = Field(default=True, description="Enable telemetry logging")
    telemetry_dir: str = Field(default=".trae/runs", description="Telemetry log directory")
    telemetry_file: str = Field(default="telemetry.jsonl", description="Telemetry log filename")


class AgentConfig(BaseSettings):
    """Agent-specific Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Agent timeouts (in seconds)
    agent0_timeout: int = Field(default=30, ge=1, description="Agent 0 (Environment Recon) timeout")
    agent1_timeout: int = Field(default=60, ge=1, description="Agent 1 (Contract Analyst) timeout")
    agent2_timeout: int = Field(default=90, ge=1, description="Agent 2 (Test Generator) timeout")
    agent3_timeout: int = Field(default=30, ge=1, description="Agent 3 (Executor) timeout")
    agent4_timeout: int = Field(default=60, ge=1, description="Agent 4 (Oracle) timeout")
    agent5_timeout: int = Field(default=60, ge=1, description="Agent 5 (Diagnoser) timeout")
    agent6_timeout: int = Field(default=30, ge=1, description="Agent 6 (Verifier) timeout")


class DocsConfig(BaseSettings):
    """Documentation Source Configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DOCS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    source: str = Field(default="auto", description="Documentation source (auto, local_jsonl, crawl)")
    local_jsonl_path: str = Field(
        default=".trae/cache/{db_name}_io_docs_depth3.jsonl",
        description="Path template to local JSONL docs library (supports {db_name})",
    )
    
    # Cache settings
    cache_enabled: bool = Field(default=True, description="Enable document caching")
    cache_ttl_days: int = Field(default=7, ge=1, description="Cache TTL in days")
    
    # Filter settings
    allowed_versions: List[str] = Field(default=["2.6"], description="Allowed documentation versions")
    min_chars: int = Field(default=500, ge=100, description="Minimum characters per document")
    
    # Validation settings
    min_docs: int = Field(default=50, ge=10, description="Minimum number of documents required")
    required_docs: List[str] = Field(
        default=["index-explained", "single-vector-search", "multi-vector-search"],
        description="Required document keywords"
    )


class AppConfig(BaseSettings):
    """
    Main Application Configuration.

    This class aggregates all configuration sections and provides
    a single entry point for application settings.

    Usage:
        ```python
        from src.config import get_config

        config = get_config()
        print(config.llm.model)
        print(config.database.host)
        ```
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application metadata
    app_name: str = Field(default="AI-DB-QC", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, testing, production)")
    debug: bool = Field(default=False, description="Debug mode")

    # Sub-configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    harness: HarnessConfig = Field(default_factory=HarnessConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    docs: DocsConfig = Field(default_factory=DocsConfig)

    # Additional settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_environments = ["development", "testing", "production"]
        v_lower = v.lower()
        if v_lower not in valid_environments:
            raise ValueError(f"environment must be one of {valid_environments}")
        return v_lower

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper


# ============================================================================
# Global Configuration Instance
# ============================================================================

_config: Optional[AppConfig] = None


def get_config(reload: bool = False) -> AppConfig:
    """
    Get the global application configuration instance.

    Args:
        reload: If True, reload configuration from environment

    Returns:
        AppConfig instance
    """
    global _config
    if _config is None or reload:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """
    Reload configuration from environment.

    Returns:
        New AppConfig instance
    """
    return get_config(reload=True)


def set_config(config: AppConfig) -> None:
    """
    Set the global configuration instance.

    Args:
        config: AppConfig instance to set as global
    """
    global _config
    _config = config


# ============================================================================
# Configuration Export/Import
# ============================================================================

def export_to_dict() -> dict:
    """
    Export current configuration as dictionary.

    Returns:
        Dictionary representation of configuration
    """
    config = get_config()
    return config.model_dump()


def export_to_yaml(filepath: Optional[str] = None) -> str:
    """
    Export configuration to YAML format.

    Args:
        filepath: Optional filepath to write YAML to

    Returns:
        YAML string representation
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required for YAML export. Install with: pip install pyyaml")

    config_dict = export_to_dict()
    yaml_str = yaml.dump(config_dict, default_flow_style=False)

    if filepath:
        Path(filepath).write_text(yaml_str, encoding="utf-8")

    return yaml_str


def load_from_yaml(filepath: str) -> AppConfig:
    """
    Load configuration from YAML file.

    Args:
        filepath: Path to YAML configuration file

    Returns:
        AppConfig instance
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required for YAML import. Install with: pip install pyyaml")

    yaml_content = Path(filepath).read_text(encoding="utf-8")
    config_dict = yaml.safe_load(yaml_content)

    # Create AppConfig from dict
    config = AppConfig(**config_dict)
    set_config(config)
    return config


def print_config() -> None:
    """Print current configuration (excluding sensitive values)."""
    config = get_config()
    config_dict = config.model_dump()

    # Mask sensitive values
    sensitive_keys = ["api_key", "password", "token"]
    for key in sensitive_keys:
        if key in config_dict.get("llm", {}):
            config_dict["llm"][key] = "***MASKED***"
        if key in config_dict.get("database", {}):
            config_dict["database"][key] = "***MASKED***"

    import json
    print(json.dumps(config_dict, indent=2, ensure_ascii=False))


# ============================================================================
# Convenience Functions
# ============================================================================

def is_production() -> bool:
    """Check if running in production environment."""
    return get_config().environment == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return get_config().environment == "development"


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_config().environment == "testing"


def get_database_url() -> str:
    """
    Get database connection URL.

    Returns:
        Database connection string
    """
    db = get_config().database
    return f"{db.type}://{db.host}:{db.port}"


# ============================================================================
# ConfigLoader - Unified Configuration Loader
# ============================================================================

class ConfigLoader:
    """
    Unified configuration loader with support for YAML files and environment variable overrides.
    
    Features:
    - Load configuration from YAML files with default values
    - Environment variable overrides (format: AI_DB_QC_SECTION_KEY)
    - Type-safe getters (get, get_bool, get_int)
    - Friendly error messages with helpful suggestions
    
    Example:
        ```python
        loader = ConfigLoader(config_path=".trae/config.yaml")
        loader.load()
        
        # Get configuration values
        cache_enabled = loader.get_bool("cache.enabled", default=False)
        ttl_days = loader.get_int("cache.ttl_days", default=7)
        
        # Override from environment variables
        # Set AI_DB_QC_CACHE_ENABLED=true to override cache.enabled
        loader.override_from_env()
        ```
    """

    def __init__(self, config_path: str = ".trae/config.yaml"):
        """
        Initialize ConfigLoader.
        
        Args:
            config_path: Path to the configuration file (default: .trae/config.yaml)
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._env_prefix = "AI_DB_QC_"
        self._loaded = False

    def load(self) -> bool:
        """
        Load configuration from YAML file.
        
        Returns:
            True if loaded successfully, False otherwise
            
        Raises:
            FileNotFoundError: If config file doesn't exist and no defaults are available
            ValueError: If YAML parsing fails
        """
        try:
            if self.config_path.exists():
                try:
                    import yaml
                except ImportError:
                    raise ImportError(
                        "PyYAML is required for configuration loading. "
                        "Install with: pip install pyyaml"
                    )

                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}

                logger.info(f"Configuration loaded from {self.config_path}")
                self._loaded = True
                return True
            else:
                logger.warning(
                    f"Configuration file not found at {self.config_path}. "
                    "Using default values only."
                )
                self.config = {}
                self._loaded = True
                return False

        except yaml.YAMLError as e:
            error_msg = f"Failed to parse YAML configuration: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports nested keys with dot notation).
        
        Args:
            key: Configuration key (e.g., "cache.enabled" or "docker_pool.min_connections")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            logger.warning("Configuration not loaded. Loading now with defaults.")
            self.load()

        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Boolean value
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get integer configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Integer value
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Failed to convert '{key}' value '{value}' to int. Using default: {default}"
            )
            return default

    def override_from_env(self) -> Dict[str, str]:
        """
        Override configuration values from environment variables.
        
        Environment variable format: AI_DB_QC_SECTION_KEY=value
        Examples:
            AI_DB_QC_CACHE_ENABLED=true
            AI_DB_QC_DOCKER_POOL_MIN_CONNECTIONS=5
            AI_DB_QC_LOGGING_ASYNC=true
            AI_DB_QC_CACHE_TTL_DAYS=14
        
        Returns:
            Dictionary of overridden keys and their values
            
        Note:
            - Environment variable names are case-insensitive
            - First underscore after prefix maps to section, subsequent underscores within section names are kept
            - Boolean values: "true", "1", "yes", "on" are True; others are False
            - Integer values are automatically converted
        """
        overrides = {}
        
        for env_key, env_value in os.environ.items():
            if env_key.startswith(self._env_prefix):
                # Remove prefix and convert to lowercase
                key_part = env_key[len(self._env_prefix):].lower()
                
                # Parse the configuration key path
                # Format: SECTION_KEY or SECTION_SUBSECTION_KEY
                config_key = self._parse_env_key(key_part)
                
                # Parse the value
                parsed_value = self._parse_env_value(env_value)
                
                # Set the value in config
                self._set_nested_value(self.config, config_key, parsed_value)
                
                overrides[config_key] = env_value
                logger.info(f"Overriding config: {config_key} = {parsed_value} (from {env_key})")

        return overrides

    def _parse_env_key(self, key_part: str) -> str:
        """
        Parse environment variable key part to configuration key path.
        
        Handles both formats:
        - SIMPLE_KEY -> simple_key
        - SECTION_KEY -> section.key
        - SECTION_SUBSECTION_KEY -> section.subsection.key
        - CACHE_TTL_DAYS -> cache.ttl_days (preserves underscores in key names)
        - DOCKER_POOL_MIN_CONNECTIONS -> docker_pool.min_connections
        
        Args:
            key_part: Environment variable key part after prefix (lowercase)
            
        Returns:
            Dot-separated configuration key path
        """
        # Known section names that can be followed by additional parts
        # Single-word sections
        single_word_sections = ['cache', 'logging', 'harness', 'docs']
        # Multi-word sections (need to be combined)
        multi_word_sections = {
            'docker': 'docker_pool',
            'isolated': 'isolated_mre'
        }
        
        # Split by underscores
        parts = key_part.split('_')
        
        # If only one part, return as is
        if len(parts) == 1:
            return parts[0]
        
        # Check if first part is a single-word section
        if parts[0] in single_word_sections:
            # Join remaining parts with underscores for multi-word keys
            section = parts[0]
            key_name = '_'.join(parts[1:])
            return f"{section}.{key_name}" if key_name else section
        
        # Check if first part is a multi-word section start
        if parts[0] in multi_word_sections:
            full_section = multi_word_sections[parts[0]]
            # Check if second part matches the expected continuation
            if len(parts) >= 2:
                expected_second = full_section.split('_')[1]
                if parts[1] == expected_second:
                    # Join remaining parts with underscores for multi-word keys
                    key_name = '_'.join(parts[2:]) if len(parts) > 2 else ''
                    return f"{full_section}.{key_name}" if key_name else full_section
                else:
                    # Treat first part as section name
                    section = parts[0]
                    key_name = '_'.join(parts[1:])
                    return f"{section}.{key_name}"
        
        # Default: join with dots
        return key_part.replace('_', '.')

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Parsed value (bool, int, or string)
        """
        # Try boolean
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        if value.lower() in ('false', '0', 'no', 'off'):
            return False
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    def _set_nested_value(self, config_dict: Dict[str, Any], key_path: str, value: Any) -> None:
        """
        Set a nested value in configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary to modify
            key_path: Dot-separated key path (e.g., "cache.enabled")
            value: Value to set
        """
        keys = key_path.split('.')
        current = config_dict
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Path to save to (default: original config_path)
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for configuration saving. "
                "Install with: pip install pyyaml"
            )

        save_path = Path(path) if path else self.config_path
        
        # Ensure parent directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {save_path}")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate cache section
        if self.get("cache.enabled"):
            if not self.get("cache.path"):
                errors.append("cache.path is required when cache.enabled is true")
            ttl = self.get_int("cache.ttl_days", 7)
            if ttl <= 0:
                errors.append("cache.ttl_days must be positive")
        
        # Validate docker_pool section
        if self.get("docker_pool.enabled"):
            min_conn = self.get_int("docker_pool.min_connections", 1)
            max_conn = self.get_int("docker_pool.max_connections", 3)
            if min_conn < 1:
                errors.append("docker_pool.min_connections must be at least 1")
            if max_conn < min_conn:
                errors.append(
                    f"docker_pool.max_connections ({max_conn}) must be >= "
                    f"docker_pool.min_connections ({min_conn})"
                )
        
        # Validate logging section
        max_size = self.get_int("logging.max_file_size_mb", 50)
        if max_size <= 0:
            errors.append("logging.max_file_size_mb must be positive")
        
        backup_count = self.get_int("logging.backup_count", 10)
        if backup_count < 0:
            errors.append("logging.backup_count must be non-negative")
        
        # Validate isolated_mre section
        if self.get("isolated_mre.enabled"):
            timeout = self.get_int("isolated_mre.timeout_seconds", 30)
            if timeout <= 0:
                errors.append("isolated_mre.timeout_seconds must be positive")
            if not self.get("isolated_mre.image"):
                errors.append("isolated_mre.image is required when isolated_mre.enabled is true")
        
        return errors

    def print_config(self, mask_sensitive: bool = True) -> None:
        """
        Print current configuration.
        
        Args:
            mask_sensitive: Whether to mask sensitive values (passwords, api keys)
        """
        import json
        
        config_copy = self.to_dict()
        
        if mask_sensitive:
            sensitive_keys = ['password', 'api_key', 'token', 'secret']
            self._mask_sensitive_values(config_copy, sensitive_keys)
        
        print("Current Configuration:")
        print("=" * 50)
        print(json.dumps(config_copy, indent=2, ensure_ascii=False))

    def _mask_sensitive_values(self, config: Dict[str, Any], sensitive_keys: List[str]) -> None:
        """
        Recursively mask sensitive values in configuration.
        
        Args:
            config: Configuration dictionary to mask
            sensitive_keys: List of keys to mask
        """
        for key, value in config.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                config[key] = "***MASKED***"
            elif isinstance(value, dict):
                self._mask_sensitive_values(value, sensitive_keys)


# ============================================================================
# Module Entry Point
# ============================================================================

if __name__ == "__main__":
    # Print configuration when run directly
    print("AI-DB-QC Configuration:")
    print("=" * 50)
    print_config()
