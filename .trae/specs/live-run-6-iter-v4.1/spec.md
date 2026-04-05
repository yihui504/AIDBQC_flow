# 实战运行 6 轮完整流程 Spec

## 为什么

系统已完成多轮优化（MRE 真实向量注入率 83.3%，评分 4.07/5），但尚未进行过完整的 6 轮实战运行验证。需要：
1. 配置干净、隔离的虚拟环境确保依赖稳定
2. 执行完整的 6 轮实战运行
3. 边跑边观察，遇到问题立即定位修复
4. 验证全流程按预期工作、产出质量良好

## 变更内容

### 变更 1：创建虚拟环境并安装依赖

- 在项目根目录创建 `.venv` 虚拟环境
- 安装 `requirements.txt` 中的所有依赖
- 验证关键模块导入正常

### 变更 2：配置运行参数

- 使用本地文档 `c:\Users\11428\Desktop\ralph\.trae\cache\milvus_io_docs_depth3.jsonl`
- 设置 `max_iterations: 6`（在 `.trae/config.yaml` 中）
- 确保所有配置指向本地资源

### 变更 3：执行实战运行并实时修复

- 启动 `python main.py` 执行完整流程
- 实时观察日志输出
- 遇到错误立即定位根因并修复
- 不允许回退、模拟或跳过

## 影响范围

- **影响文件**: `.trae/config.yaml`（运行参数）、虚拟环境配置
- **不影响**: 核心业务逻辑（除非运行中发现 bug 需修复）

## ADDED 需求

### 需求：虚拟环境隔离

系统 SHALL 在独立的 Python 虚拟环境中运行，确保依赖隔离和可复现性。

#### 场景：虚拟环境创建
- **WHEN** 执行 `python -m venv .venv` 创建虚拟环境
- **THEN** `.venv` 目录存在且包含完整的 Python 环境
- **AND** `pip install -r requirements.txt` 成功安装所有依赖

#### 场景：关键模块导入验证
- **WHEN** 在虚拟环境中执行 `python -c "import langchain; import langgraph; import sentence_transformers; import pymilvus"`
- **THEN** 所有模块导入成功，无错误

### 需求：6 轮完整运行

系统 SHALL 完整执行 6 轮迭代，每轮包含 Agent0→Agent1→Agent2→Agent3→Agent4→Agent5→Agent6 的完整流程。

#### 场景：完整流程执行
- **WHEN** 执行 `python main.py`
- **THEN** 系统完成 6 轮迭代
- **AND** 每轮生成测试用例、执行、验证、生成 Issue
- **AND** 最终产出质量良好的 GitHub Issue

### 需求：实时问题修复

系统运行过程中遇到的问题 SHALL 立即定位根因并修复，不允许回退或模拟。

#### 场景：运行时错误处理
- **WHEN** 运行过程中出现异常
- **THEN** 立即分析堆栈跟踪定位根因
- **AND** 修复代码或配置后重新运行
- **AND** 不使用 mock、stub 或跳过逻辑

## 验收标准

1. 虚拟环境创建成功，所有依赖安装无错误
2. `python main.py` 完成 6 轮迭代，无崩溃
3. 最终产出至少 6 个 GitHub Issue 文件
4. Issue 文件包含真实语义向量（非占位符）
5. 全流程日志完整，无异常堆栈
