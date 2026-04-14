# 关键错误立即中断机制实施文档

## 概述

本文档描述了为AI-DB-QC系统实施的关键错误立即中断机制，包括关键错误分类系统、立即中断判断逻辑、清理和关闭流程，以及Docker端口管理功能。

## 实施的功能

### 1. 关键错误处理器模块 (`src/critical_error_handler.py`)

#### 主要功能

**1.1 关键错误分类系统**
- Docker端口冲突 (EMERGENCY级别)
- API限流 (CRITICAL级别)
- 资源耗尽 (CRITICAL级别)
- 数据库致命错误 (CRITICAL级别)
- 系统损坏 (EMERGENCY级别)
- 容器失败 (CRITICAL级别)
- 内存耗尽 (EMERGENCY级别)
- 磁盘已满 (CRITICAL级别)
- 网络失败 (SEVERE级别)

**1.2 立即中断判断逻辑**
- 基于错误消息模式匹配
- 基于异常类型匹配
- 支持混合匹配策略（类型或消息）
- 评估错误严重性级别
- 决定是否需要立即中断

**1.3 清理和关闭流程**
- 注册清理处理器
- 按优先级执行清理
- 信号处理（SIGINT, SIGTERM）
- 紧急状态保存
- 优雅的系统退出

**1.4 错误信息保存**
- 详细的错误分类信息
- 时间戳记录
- 上下文信息保存
- 堆栈跟踪记录
- 恢复建议生成

### 2. Docker端口管理器模块 (`src/docker_port_manager.py`)

#### 主要功能

**2.1 端口分配和释放管理**
- 服务特定的端口范围
- 线程安全的端口分配
- 优先端口支持
- 端口分配记录
- 自动端口释放

**2.2 端口冲突检测**
- Socket连接测试
- Docker容器检查
- 进程使用检测
- 冲突进程识别
- 自动冲突解决

**2.3 自动端口清理**
- 孤立端口检测
- 基于超时的清理
- 容器自动停止和删除
- 定期后台清理
- 强制清理选项

**2.4 端口使用跟踪**
- 分配历史记录
- 活跃分配查询
- 使用统计报告
- 心跳机制
- 状态持久化

### 3. 主程序集成 (`main.py`)

#### 集成功能

**3.1 初始化阶段**
- 配置驱动的初始化
- 全局处理器注册
- 清理处理器注册
- 日志系统集成

**3.2 异常处理**
- 关键错误检测
- 立即中断触发
- 详细错误保存
- 紧急状态转储
- 非关键错误处理

**3.3 清理阶段**
- 端口管理器清理
- 运行特定端口释放
- 使用统计报告
- 优雅关闭处理

### 4. 配置集成 (`.trae/config.yaml`)

#### 配置选项

**4.1 关键错误处理器配置**
```yaml
critical_error_handler:
  enabled: true
  log_dir: ".trae/logs"
  state_dir: ".trae/runs"
  enable_auto_cleanup: true
  max_shutdown_time_seconds: 30
  log_critical_errors: true
```

**4.2 Docker端口管理器配置**
```yaml
docker_port_manager:
  enabled: true
  state_dir: ".trae/port_manager"
  enable_auto_cleanup: true
  cleanup_interval_seconds: 300
  orphan_timeout_minutes: 60
  port_ranges:
    milvus: [19530, 19600]
    qdrant: [6333, 6400]
    weaviate: [8080, 8150]
    chroma: [8000, 8050]
    general: [9000, 9500]
    monitoring: [3000, 3050]
```

## 测试和验证

### 1. 单元测试

**关键错误处理器测试** (`tests/unit/test_critical_error_handler.py`)
- 错误分类测试
- 严重性评估测试
- 恢复建议生成测试
- 清理处理器注册测试
- 全局处理器测试
- 装饰器功能测试

**Docker端口管理器测试** (`tests/unit/test_docker_port_manager.py`)
- 端口分配测试
- 端口释放测试
- 冲突检测测试
- 孤立端口清理测试
- 线程安全测试
- 全局管理器测试

### 2. 集成测试

**快速功能测试** (`scripts/quick_test.py`)
- 基本错误检测验证
- 端口管理功能验证
- 全局处理器访问验证

**调试测试** (`scripts/debug_test.py`)
- 错误检测详细输出
- 分类逻辑验证

**演示脚本** (`scripts/demonstrate_critical_error_handling.py`)
- 完整功能演示
- 集成测试
- 使用示例

## 使用示例

### 1. 关键错误处理

```python
from src.critical_error_handler import get_global_critical_error_handler

# 获取全局处理器
handler = get_global_critical_error_handler()

# 检查错误是否为关键错误
try:
    # 执行可能失败的代码
    pass
except Exception as e:
    if handler.is_critical_error(e):
        # 处理关键错误
        critical_info = handler.handle_critical_error(
            exception=e,
            run_id="run_123",
            additional_context={"operation": "docker_compose"}
        )
        # 处理器将自动触发清理和关闭
```

### 2. Docker端口管理

```python
from src.docker_port_manager import get_global_port_manager

# 获取全局端口管理器
port_manager = get_global_port_manager()

# 分配端口
port = port_manager.allocate_port(
    service_type="milvus",
    allocated_by="agent0_env_recon",
    run_id="run_123",
    purpose="vector_database"
)

# 使用端口进行操作
# ...

# 释放端口
port_manager.release_port(port)

# 或使用上下文管理器
with port_manager.allocated_port(
    service_type="general",
    allocated_by="temporary_task",
    purpose="testing"
) as port:
    # 在此使用端口
    pass
# 端口自动释放
```

### 3. 装饰器使用

```python
from src.critical_error_handler import handle_critical_errors, get_global_critical_error_handler

handler = get_global_critical_error_handler()

@handle_critical_errors(handler, run_id="run_123")
def critical_operation():
    # 可能产生关键错误的操作
    pass

# 自动错误处理和清理
critical_operation()
```

## 错误分类规则

### 1. Docker端口冲突
- **触发条件**: "port is already allocated", "address already in use", "bind: address already in use"
- **严重性**: EMERGENCY
- **立即中断**: 是
- **清理优先级**: 1

### 2. API限流
- **触发条件**: "rate limit exceeded", "too many requests", "quota exceeded", "429"
- **严重性**: CRITICAL
- **立即中断**: 是
- **清理优先级**: 2

### 3. 资源耗尽
- **触发条件**: "out of memory", "cannot allocate memory", "resource temporarily unavailable"
- **严重性**: CRITICAL
- **立即中断**: 是
- **清理优先级**: 3

### 4. 数据库致命错误
- **触发条件**: "connection refused", "connection timeout", "database is locked"
- **严重性**: CRITICAL
- **立即中断**: 是
- **清理优先级**: 4

### 5. 内存耗尽
- **触发条件**: MemoryError, "out of heap space", "memory limit reached"
- **严重性**: EMERGENCY
- **立即中断**: 是
- **清理优先级**: 1

## 恢复建议

系统为每种错误类型生成相应的恢复建议：

### Docker端口冲突
- 检查使用冲突端口的运行中Docker容器
- 停止或删除冲突容器
- 使用不同的端口配置
- 清理孤立的Docker容器

### API限流
- 等待限流重置
- 降低API请求频率
- 实现指数退避
- 检查API配额和限制

### 资源耗尽
- 释放系统内存
- 增加可用系统资源
- 减少并发操作
- 检查内存泄漏

## 日志和监控

### 1. 关键错误日志
- 位置: `.trae/logs/critical_error_*.json`
- 格式: JSON
- 内容: 完整错误信息、上下文、恢复建议

### 2. 端口管理日志
- 位置: `.trae/port_manager/port_allocations.json`
- 格式: JSON
- 内容: 端口分配记录、使用状态

### 3. 紧急状态转储
- 位置: `.trae/runs/{run_id}/emergency_shutdown.json`
- 格式: JSON
- 内容: 错误类型、时间戳、关闭原因

## 性能考虑

### 1. 线程安全
- 使用线程锁保护共享状态
- 支持并发端口分配
- 原子操作保证

### 2. 资源管理
- 限制历史记录大小
- 定期清理临时文件
- 内存优化设计

### 3. 性能监控
- 端口使用统计
- 错误分类性能
- 清理操作效率

## 扩展性

### 1. 添加新的错误类型
```python
# 在 CRITICAL_ERROR_PATTERNS 中添加新模式
ErrorPattern(
    error_type=CriticalErrorType.NEW_ERROR_TYPE,
    priority=CriticalityLevel.SEVERITY_LEVEL,
    message_patterns=["error pattern 1", "error pattern 2"],
    exception_types=[SpecificException],
    requires_immediate_shutdown=True,
    cleanup_priority=5
)
```

### 2. 自定义清理处理器
```python
def custom_cleanup(run_id=None):
    # 自定义清理逻辑
    pass

handler.register_cleanup_handler(custom_cleanup)
```

### 3. 自定义端口范围
```python
# 在配置文件中添加新的端口范围
docker_port_manager:
  port_ranges:
    custom_service: [10000, 10100]
```

## 故障排除

### 1. 关键错误未检测
- 检查错误消息模式
- 验证异常类型匹配
- 查看调试日志

### 2. 端口分配失败
- 检查端口范围配置
- 验证端口可用性
- 查看Docker容器状态

### 3. 清理未执行
- 验证处理器注册
- 检查清理权限
- 查看清理日志

## 最佳实践

### 1. 错误处理
- 始终检查关键错误
- 提供详细的上下文信息
- 实现适当的恢复策略

### 2. 端口管理
- 使用服务特定的端口范围
- 及时释放不再使用的端口
- 定期检查端口使用情况

### 3. 监控和日志
- 定期检查关键错误日志
- 监控端口使用统计
- 设置适当的告警

## 结论

关键错误立即中断机制为AI-DB-QC系统提供了强大的错误处理和恢复能力。通过集成关键错误分类、立即中断判断、自动清理和Docker端口管理，系统能够快速识别和处理严重错误，确保系统稳定性和数据完整性。

该实现遵循了现有项目的编码规范，使用了适当的异常处理和日志记录，并通过了全面的测试验证。系统现在具备了生产环境所需的错误处理能力。