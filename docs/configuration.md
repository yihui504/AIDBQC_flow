# AI-DB-QC Configuration Guide

**Version**: 1.0.0
**Date**: 2026-03-30
**Author**: AI-DB-QC Team

---

## Overview

AI-DB-QC uses a centralized configuration system based on Pydantic Settings. Configuration can be provided through:

1. **Environment variables** (`.env` file)
2. **YAML configuration file** (`config.yaml`)
3. **Default values** (built into the code)

Priority: Environment variables > YAML file > Default values

---

## Quick Start

### Basic Usage

```python
from src.config import get_config

# Get configuration instance
config = get_config()

# Access configuration values
print(config.llm.model)          # LLM model name
print(config.database.host)       # Database host
print(config.harness.max_iterations)  # Max fuzzing iterations
```

### Using Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Configuration
LLM_PROVIDER=anthropic
LLM_API_KEY=your_api_key_here
LLM_MODEL=claude-opus-4-6

# Database Configuration
DB_TYPE=milvus
DB_HOST=localhost
DB_PORT=19530

# Harness Configuration
HARNESS_MAX_ITERATIONS=4
HARNESS_MAX_TOKEN_BUDGET=100000
```

### Using YAML Configuration

Create a `config.yaml` file:

```yaml
llm:
  provider: anthropic
  model: claude-opus-4-6
  temperature: 0.7

database:
  type: milvus
  host: localhost
  port: 19530

harness:
  max_iterations: 4
  max_token_budget: 100000
  target_db_input: "Weaviate 1.36.9"

run_guard:
  enabled: true
  enforce_weaviate_1369: true
  enforce_max_iterations_4: true
```

Then load it:

```python
from src.config import load_from_yaml

config = load_from_yaml("config.yaml")
```

---

## Configuration Sections

### LLM Configuration

Controls the LLM provider and model settings.

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `LLM_PROVIDER` | `llm.provider` | `anthropic` | LLM provider (anthropic, openai, zhipu) |
| `LLM_API_KEY` | `llm.api_key` | - | API key for the provider |
| `LLM_API_URL` | `llm.api_url` | - | Custom API URL (for proxies) |
| `LLM_MODEL` | `llm.model` | `claude-opus-4-6` | Model name |
| `LLM_MAX_TOKENS` | `llm.max_tokens` | `4096` | Max tokens per request |
| `LLM_TEMPERATURE` | `llm.temperature` | `0.7` | Generation temperature (0.0-2.0) |

**Example:**

```python
config = get_config()
config.llm.provider = "openai"
config.llm.model = "gpt-4"
config.llm.temperature = 0.5
```

### Database Configuration

Controls the target vector database connection.

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `DB_TYPE` | `database.type` | `milvus` | Database type |
| `DB_HOST` | `database.host` | `localhost` | Database host |
| `DB_PORT` | `database.port` | `19530` | Database port |
| `DB_USERNAME` | `database.username` | - | Username (if required) |
| `DB_PASSWORD` | `database.password` | - | Password (if required) |
| `DB_DATABASE` | `database.database` | - | Database name |
| `DB_SECURE` | `database.secure` | `false` | Use TLS/SSL |

**Example:**

```python
config = get_config()
config.database.type = "qdrant"
config.database.host = "localhost"
config.database.port = 6333
```

### Harness Configuration

Controls the workflow/fuzzing behavior.

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `HARNESS_MAX_ITERATIONS` | `harness.max_iterations` | `4` | Maximum fuzzing iterations |
| `HARNESS_MAX_TOKEN_BUDGET` | `harness.max_token_budget` | `100000` | Maximum token budget |
| `HARNESS_MAX_CONSECUTIVE_FAILURES` | `harness.max_consecutive_failures` | `3` | Max failures before recovery |
| `HARNESS_SIMILARITY_THRESHOLD` | `harness.similarity_threshold` | `0.9` | Mode collapse threshold |
| `HARNESS_HISTORY_LIMIT` | `harness.history_limit` | `100` | Max history vectors |

### Runtime Guard Configuration

用于禁止降级/替代/模拟路径的 fail-closed 运行守卫。

| YAML Path | Default | Description |
|-----------|---------|-------------|
| `run_guard.enabled` | `true` | Enable runtime guard |
| `run_guard.enforce_weaviate_1369` | `true` | Require target_db_input to contain Weaviate 1.36.9 |
| `run_guard.enforce_max_iterations_4` | `true` | Require harness.max_iterations == 4 |
| `run_guard.forbidden_terms` | see config | Forbidden degraded/simulated markers |

#### Collection Pool Settings

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `HARNESS_POOL_MIN_SIZE` | `harness.pool_min_size` | `3` | Min pool size |
| `HARNESS_POOL_MAX_SIZE` | `harness.pool_max_size` | `10` | Max pool size |
| `HARNESS_POOL_MAX_IDLE_SECONDS` | `harness.pool_max_idle_seconds` | `1800` | Max idle time (30 min) |

#### Telemetry Settings

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `HARNESS_TELEMETRY_ENABLED` | `harness.telemetry_enabled` | `true` | Enable telemetry |
| `HARNESS_TELEMETRY_DIR` | `harness.telemetry_dir` | `.trae/runs` | Log directory |
| `HARNESS_TELEMETRY_FILE` | `harness.telemetry_file` | `telemetry.jsonl` | Log filename |

### Agent Configuration

Controls individual agent timeouts.

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `AGENT_AGENT0_TIMEOUT` | `agents.agent0_timeout` | `30` | Agent 0 timeout (seconds) |
| `AGENT_AGENT1_TIMEOUT` | `agents.agent1_timeout` | `60` | Agent 1 timeout (seconds) |
| `AGENT_AGENT2_TIMEOUT` | `agents.agent2_timeout` | `90` | Agent 2 timeout (seconds) |
| `AGENT_AGENT3_TIMEOUT` | `agents.agent3_timeout` | `30` | Agent 3 timeout (seconds) |
| `AGENT_AGENT4_TIMEOUT` | `agents.agent4_timeout` | `60` | Agent 4 timeout (seconds) |
| `AGENT_AGENT5_TIMEOUT` | `agents.agent5_timeout` | `60` | Agent 5 timeout (seconds) |
| `AGENT_AGENT6_TIMEOUT` | `agents.agent6_timeout` | `30` | Agent 6 timeout (seconds) |

### Application Settings

General application configuration.

| Environment Variable | YAML Path | Default | Description |
|---------------------|-----------|---------|-------------|
| `APP_NAME` | `app_name` | `AI-DB-QC` | Application name |
| `APP_VERSION` | `app_version` | `1.0.0` | Application version |
| `ENVIRONMENT` | `environment` | `development` | Environment (development, testing, production) |
| `DEBUG` | `debug` | `false` | Debug mode |
| `LOG_LEVEL` | `log_level` | `INFO` | Logging level |

---

## Advanced Usage

### Programmatic Configuration

```python
from src.config import AppConfig, set_config

# Create custom configuration
custom_config = AppConfig(
    app_name="My AI-DB-QC",
    environment="production",
    llm={
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.3
    },
    database={
        "type": "qdrant",
        "host": "prod-db.example.com",
        "port": 6333
    }
)

# Set as global configuration
set_config(custom_config)
```

### Configuration Export

```python
from src.config import export_to_dict, export_to_yaml

# Export as dictionary
config_dict = export_to_dict()

# Export as YAML
yaml_string = export_to_yaml("output_config.yaml")
```

### Environment Detection

```python
from src.config import is_production, is_development, is_testing

if is_production():
    # Production-specific settings
    config.harness.telemetry_enabled = True

elif is_development():
    # Development-specific settings
    config.debug = True

elif is_testing():
    # Testing-specific settings
    config.harness.max_iterations = 3
```

### Database URL Generation

```python
from src.config import get_database_url

url = get_database_url()
# Returns: "milvus://localhost:19530"
```

### Reloading Configuration

```python
from src.config import reload_config

# Reload from environment (e.g., after .env changes)
config = reload_config()
```

---

## Configuration Validation

The configuration system automatically validates values:

### Type Validation

```python
# Invalid: port must be integer
DB_PORT="abc"  # Raises ValidationError

# Invalid: temperature must be between 0 and 2
LLM_TEMPERATURE=3.0  # Raises ValidationError
```

### Range Validation

```python
# Port must be 1-65535
DB_PORT=70000  # Raises ValueError

# Timeout must be positive
AGENT_AGENT0_TIMEOUT=-10  # Raises ValidationError
```

### Format Validation

```python
# API URL must start with http:// or https://
LLM_API_URL="invalid-url"  # Raises ValueError

# Environment must be valid
ENVIRONMENT="staging"  # Raises ValueError (must be development/testing/production)
```

---

## Best Practices

### 1. Sensitive Values

Never commit sensitive values (API keys, passwords) to version control.

**✅ Good:**
```bash
# .env
LLM_API_KEY=sk-ant-...
DB_PASSWORD=my_secret_password
```

**❌ Bad:**
```python
# config.py
API_KEY = "sk-ant-..."  # Don't hardcode secrets!
```

### 2. Environment-Specific Configuration

Use different `.env` files for different environments:

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LLM_MODEL=claude-opus-4-6

# .env.production
ENVIRONMENT=production
DEBUG=false
LLM_MODEL=claude-sonnet-4-6
```

Load the appropriate file:

```bash
# Development
cp .env.development .env

# Production
cp .env.production .env
```

### 3. Validation at Startup

Validate configuration at application startup:

```python
from src.config import get_config

def validate_config():
    config = get_config()

    # Check required values
    if not config.llm.api_key:
        raise ValueError("LLM_API_KEY is required")

    # Check database connectivity
    try:
        import socket
        sock = socket.socket()
        sock.connect((config.database.host, config.database.port))
        sock.close()
    except:
        raise ValueError(f"Cannot connect to {config.database.type} at {config.database.host}:{config.database.port}")
```

### 4. Logging Configuration

Use the log level from configuration:

```python
import logging
from src.config import get_config

config = get_config()
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
```

---

## Troubleshooting

### Configuration Not Loading

**Problem**: Changes to `.env` not taking effect.

**Solution**:
```python
from src.config import reload_config
config = reload_config()  # Force reload
```

### Environment Variables Ignored

**Problem**: Environment variables not being read.

**Solution**: Ensure prefix is correct:
- LLM config: `LLM_*`
- Database config: `DB_*`
- Harness config: `HARNESS_*`
- Agent config: `AGENT_*`

### YAML Import Error

**Problem**: `load_from_yaml()` fails.

**Solution**: Install PyYAML:
```bash
pip install pyyaml
```

### Validation Errors

**Problem**: Configuration validation fails.

**Solution**: Check error message for specific validation failure:
```python
try:
    config = AppConfig()
except ValidationError as e:
    print(f"Configuration error: {e}")
```

---

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `get_config()` | Get global configuration instance |
| `reload_config()` | Reload configuration from environment |
| `set_config(config)` | Set global configuration instance |
| `export_to_dict()` | Export configuration as dictionary |
| `export_to_yaml(filepath)` | Export configuration to YAML file |
| `load_from_yaml(filepath)` | Load configuration from YAML file |
| `print_config()` | Print configuration (masks sensitive values) |
| `is_production()` | Check if production environment |
| `is_development()` | Check if development environment |
| `is_testing()` | Check if testing environment |
| `get_database_url()` | Get database connection URL |

### Classes

| Class | Description |
|-------|-------------|
| `AppConfig` | Main application configuration |
| `LLMConfig` | LLM provider configuration |
| `DatabaseConfig` | Database connection configuration |
| `HarnessConfig` | Workflow/harness configuration |
| `AgentConfig` | Agent-specific configuration |

---

## Examples

### Example 1: Custom LLM Provider

```python
from src.config import get_config

config = get_config()
config.llm.provider = "zhipu"
config.llm.api_url = "https://open.bigmodel.cn/api/paas/v4/"
config.llm.model = "glm-4"
```

### Example 2: Multiple Database Testing

```python
from src.config import set_config, AppConfig

# Test against Qdrant
qdrant_config = AppConfig(
    database={"type": "qdrant", "host": "localhost", "port": 6333}
)
set_config(qdrant_config)
# Run tests...

# Test against Weaviate
weaviate_config = AppConfig(
    database={"type": "weaviate", "host": "localhost", "port": 8080}
)
set_config(weaviate_config)
# Run tests...
```

### Example 3: Testing Environment

```python
import os
os.environ["ENVIRONMENT"] = "testing"
os.environ["HARNESS_MAX_ITERATIONS"] = "3"

from src.config import get_config
config = get_config()

assert config.environment == "testing"
assert config.harness.max_iterations == 3
```

---

## Changelog

### Version 1.0.0 (2026-03-30)
- Initial centralized configuration system
- Environment variable support
- YAML configuration support
- Pydantic validation
- Documentation
