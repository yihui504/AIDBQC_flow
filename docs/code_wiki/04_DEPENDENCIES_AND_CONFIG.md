# 依赖关系与配置

## Python 依赖

依赖以 pip requirements 形式提供：

- 主依赖清单：[requirements.txt](file:///workspace/requirements.txt)
- Dashboard 额外依赖：[requirements-dashboard.txt](file:///workspace/requirements-dashboard.txt)

其中关键依赖类别：

- 编排与链路：langgraph、langchain、langchain-core、langsmith
- 结构化数据：pydantic>=2、pydantic-settings
- DB 客户端：pymilvus、qdrant-client、weaviate-client
- 语义模型：sentence-transformers、torch、numpy
- 基础设施：docker、python-dotenv
- 测试：pytest、pytest-asyncio、pytest-cov

## Docker 依赖

仓库内置了三套 compose 文件用于拉起目标数据库：

- Milvus：[docker-compose.milvus.yml](file:///workspace/docker-compose.milvus.yml)
- Qdrant：[docker-compose.qdrant.yml](file:///workspace/docker-compose.qdrant.yml)
- Weaviate：[docker-compose.weaviate.yml](file:///workspace/docker-compose.weaviate.yml)

注意：部分 compose 文件会做端口映射（例如 Weaviate 可能映射到本机 8081），运行前应对齐 `configs/database_connections.yaml` 与 `.trae/config.yaml` 的端口配置。

## 配置系统

### 两套配置入口

仓库同时存在两类配置加载方式：

1) Pydantic Settings（面向库式调用，默认从 .env 读取）

- 入口：[get_config](file:///workspace/src/config.py#L225-L239)
- 聚合模型：[AppConfig](file:///workspace/src/config.py#L157-L216)

2) YAML + Env Override（面向 runner/流水线执行）

- 入口类：[ConfigLoader](file:///workspace/src/config.py#L376)
- 默认配置文件：[.trae/config.yaml](file:///workspace/.trae/config.yaml)
- env 覆盖前缀：AI_DB_QC_

实际执行入口 [main.py](file:///workspace/main.py) 使用的是 `ConfigLoader(config_path=".trae/config.yaml")`，见 [main.py:L164-L179](file:///workspace/main.py#L164-L179)。

### .env（密钥）

模板：[.env.example](file:///workspace/.env.example)

Runner 强制要求至少存在一个 API key（DeepSeek/Anthropic/ZhipuAI）：

- 检查逻辑见 [main.py:L214-L219](file:///workspace/main.py#L214-L219)

### RunGuard（强约束）

默认开启（.trae/config.yaml 的 `run_guard.enabled: true`），核心约束见 [_enforce_real_run_configuration](file:///workspace/main.py#L76-L119)：

- 目标 DB 版本白名单（Weaviate 1.36.9 或 Qdrant 1.17.1）
- `harness.max_iterations` 必须为 4（可配置关闭 enforce）
- `target_db_input` 不允许包含“degraded/fallback/simulate/mock”等标记

如果你希望开发/本地调试时支持 Milvus 或跑更长迭代：

- 将 `.trae/config.yaml` 中 `run_guard.enforce_weaviate_1369` 或 `run_guard.enforce_max_iterations_4` 设为 false
- 或通过环境变量覆盖（以 AI_DB_QC_ 开头）

### Harness 配置

关键字段（见 [.trae/config.yaml:harness](file:///workspace/.trae/config.yaml#L28-L33)）：

- `max_token_budget`：token 熔断阈值（影响 should_continue_fuzzing）
- `max_iterations`：最大 fuzz loop
- `target_db_input`：目标 DB（会进入 WorkflowState）
- `from_scratch`：是否禁用热 sandbox 复用（环境成本更高，但更“干净”）

### isolated_mre（MRE 隔离执行）

见 [.trae/config.yaml:isolated_mre](file:///workspace/.trae/config.yaml#L23-L27) 与 [IsolatedCodeRunner](file:///workspace/src/agents/agent6_verifier.py#L54)：

- 默认 enabled=true，image=python:3.11-slim，network_disabled=true
- 当 disabled 或 Docker 不可用时，执行器会 fail-closed（拒绝在 host 上执行 MRE）

## 其它配置文件

- 数据库连接信息：[configs/database_connections.yaml](file:///workspace/configs/database_connections.yaml)
- cross-db 测试任务：[configs/cross_db_test.yaml](file:///workspace/configs/cross_db_test.yaml)

