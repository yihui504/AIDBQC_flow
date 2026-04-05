# 优化运行时性能与日志管理规范

## 为什么

根据项目实战评估报告（v3.5.3），AI-DB-QC 系统存在以下关键问题：

1. **冷启动瓶颈**：首次运行时实时爬取文档耗时约 4-5 分钟，影响整体效率
2. **容器管理效率低**：每次测试创建新 Docker 容器，容器创建/销毁成本高，异常终止后容器残留
3. **日志文件管理问题**：遥测文件持续增长至 400MB+ 无轮转机制，影响日志分析性能
4. **MRE 验证安全风险**：在宿主机直接执行 LLM 生成的代码，存在安全风险

## 变更内容

* **新增本地 RAG 缓存层**：在 Agent0 实现文档缓存机制，支持增量更新和过期策略

* **实现 Docker 沙箱连接池**：在 StateManager 中实现容器连接池，复用容器实例

* **异步日志记录与文件轮转**：优化 TelemetryManager，引入异步日志和按大小/时间轮转

* **隔离式 MRE 验证环境**：在 Agent6 中实现隔离的代码执行环境（Docker 容器或虚拟环境）

## 影响

* 受影响代码：

  * `src/agents/agent0_env_recon.py` - 文档爬取逻辑

  * `src/state.py` - 状态管理和 Docker 容器生命周期

  * `src/telemetry.py` - 日志记录和管理

  * `src/agents/agent6_verifier.py` - MRE 代码验证逻辑

* 新增依赖（可选）：`watchdog`（文件监听）、`loguru`（异步日志）

## ADDED Requirements

### Requirement: 本地 RAG 缓存层

系统 SHALL 提供文档缓存机制，避免重复爬取相同文档。

#### 场景：缓存命中

* **WHEN** 启动系统且文档缓存存在且未过期

* **THEN** 系统从本地缓存加载文档，跳过网络爬取

* **验证**：日志显示 "Loading documents from cache"，冷启动时间减少至 10 秒内

#### 场景：缓存更新

* **WHEN** 文档缓存过期或不存在

* **THEN** 系统执行增量爬取，仅更新变更的文档

* **验证**：爬取时间比首次减少 50% 以上

### Requirement: Docker 沙箱连接池

系统 SHALL 实现 Docker 容器连接池，复用容器实例以减少创建/销毁开销。

#### 场景：容器复用

* **WHEN** 多个测试用例顺序执行

* **THEN** 连接池复用同一容器实例，避免重复创建

* **验证**：容器创建次数显著减少，测试总耗时减少 20-30%

#### 场景：异常清理

* **WHEN** 系统异常终止

* **THEN** 连接池在下次启动时自动清理残留容器

* **验证**：系统启动前自动清理孤立容器

### Requirement: 异步日志记录与文件轮转

系统 SHALL 实现异步日志记录和文件轮转机制。

#### 场景：异步日志

* **WHEN** 系统运行产生大量日志

* **THEN** 日志写入不阻塞主流程，使用后台线程处理

* **验证**：主流程性能不受日志写入影响

#### 场景：文件轮转

* **WHEN** 日志文件超过大小限制（如 50MB）或时间限制（如 1 天）

* **THEN** 系统自动创建新日志文件，保留历史文件（最多 N 个）

* **验证**：日志文件大小始终在限制内，历史日志可追溯

### Requirement: 隔离式 MRE 验证环境

系统 SHALL 在隔离环境中执行 LLM 生成的代码，确保宿主机安全。

#### 场景：容器化执行

* **WHEN** 验证 MRE 代码

* **THEN** 代码在独立的临时 Docker 容器中执行，限制网络访问和资源使用

* **验证**：恶意代码无法影响宿主机，容器自动销毁

#### 场景：超时控制

* **WHEN** MRE 代码执行超过时间限制（如 30 秒）

* **THEN** 系统终止执行并记录超时错误

* **验证**：无无限循环或资源耗尽风险

## MODIFIED Requirements

### Requirement: Agent0 文档爬取

**修改前**：每次启动实时爬取所有文档
**修改后**：优先从缓存加载，仅在缓存过期时执行增量爬取

### Requirement: StateManager 容器管理

**修改前**：每次测试创建新容器，异常终止后容器残留
**修改后**：使用连接池复用容器，自动清理孤立容器

### Requirement: TelemetryManager 日志管理

**修改前**：同步写入单一日志文件，文件持续增长
**修改后**：异步写入多个轮转日志文件，大小和时间受控

### Requirement: Agent6 MRE 验证

**修改前**：在宿主机直接执行代码，无资源限制
**修改后**：在隔离容器中执行，有网络和资源限制

## REMOVED Requirements

无

## 技术方案

### 1. 本地 RAG 缓存层实现

* **缓存结构**：

  ```
  .trae/cache/
    docs/
      milvus/
        docs_index.json (文档元数据：URL、标题、哈希、爬取时间)
        content/ (分块存储文档内容)
    metadata.json (缓存元数据：版本、过期时间)
  ```

* **缓存策略**：

  * 基于文件哈希检测文档变更

  * 支持缓存过期配置（默认 7 天）

  * 支持强制刷新（--refresh-cache 参数）

* **实现位置**：`agent0_env_recon.py` 新增 `DocumentCache` 类

### 2. Docker 连接池实现

* **连接池配置**：

  * 最小连接数：1（保留一个预热容器）

  * 最大连接数：3（限制资源占用）

  * 容器生命周期：测试结束后保持，超过空闲时间（如 10 分钟）后销毁

* **清理机制**：

  * 系统启动时检查并清理孤立容器

  * 容器名称添加前缀 `ai_db_qc_` 以便识别

* **实现位置**：`state.py` 新增 `DockerContainerPool` 类

### 3. 异步日志与文件轮转实现

* **日志框架**：使用 `logging.handlers.RotatingFileHandler` 或 `loguru`

* **轮转配置**：

  * 最大文件大小：50MB

  * 保留文件数：10（最多 500MB）

  * 备份文件名：`telemetry_YYYYMMDD_HHMMSS.jsonl`

* **异步配置**：

  * 使用 `logging.handlers.QueueHandler` + `QueueListener`

  * 或使用 `loguru` 的内置异步功能

* **实现位置**：`telemetry.py` 重构 `TelemetryManager`

### 4. 隔离式 MRE 验证实现

* **容器配置**：

  * 镜像：`python:3.11-slim` 或自定义镜像（包含测试依赖）

  * 资源限制：CPU 1 核、内存 512MB、网络禁用

  * 超时时间：30 秒

* **执行流程**：

  1. 创建临时容器
  2. 挂载 MRE 代码文件
  3. 执行代码并捕获输出
  4. 销毁容器
  5. 返回执行结果

* **实现位置**：`agent6_verifier.py` 新增 `IsolatedCodeRunner` 类

## 兼容性说明

* 向后兼容：默认禁用新特性，通过配置文件启用

* 配置项：

  ```yaml
  cache:
    enabled: true
    path: ".trae/cache"
    ttl_days: 7

  docker_pool:
    enabled: true
    min_connections: 1
    max_connections: 3
    idle_timeout_minutes: 10

  logging:
    async: true
    max_file_size_mb: 50
    backup_count: 10

  isolated_mre:
    enabled: true
    timeout_seconds: 30
    image: "python:3.11-slim"
  ```

## 验收标准

1. 冷启动时间从 4-5 分钟减少至 10 秒内（缓存命中时）
2. 文档增量爬取时间比首次减少 50% 以上
3. 测试总耗时减少 20-30%（容器复用）
4. 日志文件大小始终在 50MB 以内
5. 历史日志可追溯，保留最多 10 个文件
6. MRE 验证在隔离环境中执行，不影响宿主机
7. 异常终止后残留容器自动清理

