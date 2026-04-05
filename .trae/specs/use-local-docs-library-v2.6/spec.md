# 使用本地绝对有效文档库（Milvus v2.6.x）Spec

## 为什么
当前 Agent0 的自动爬取/缓存文档存在内容不完整、版本混入与稳定性问题，导致后续契约抽取、测试生成与缺陷归因出现误报。需要支持直接使用用户提供的“绝对有效文档库”，并临时禁用原有缓存与自动爬取。

## 变更内容
- 引入“本地文档库模式”：从 `c:\Users\11428\Desktop\ralph\.trae\cache\milvus_io_docs_depth3.jsonl` 加载文档上下文
- 临时禁用 Agent0 现有文档缓存（DocumentCache）与自动深度爬取（Crawl4AI DeepCrawler）
- 对本地文档库内容做基础约束：仅允许 Milvus v2.6.x 相关内容进入上下文；出现明显非 v2.6.x 版本化页面时剔除
- 运行日志可观测：明确打印“正在使用本地文档库/已禁用自动爬取与缓存/加载条数与字节数”

## 影响
- 受影响能力：
  - 文档来源与版本控制
  - 契约抽取的证据基础
  - Issue 证据链（文档引用）命中率
- 受影响代码：
  - `src/agents/agent0_env_recon.py`（文档获取入口）
  - `src/config.py` 与 `.trae/config.yaml`（新增开关与路径）
  - 可能新增：`src/docs/local_docs_library.py`（本地库解析与过滤工具）

## ADDED Requirements

### Requirement: 本地文档库模式
系统 SHALL 支持在运行时从本地 JSONL 文档库加载文档上下文，并完全跳过自动爬取与缓存。

#### 场景：启用本地文档库
- **WHEN** 配置 `docs.source=local_jsonl`
- **THEN** Agent0 从 `docs.local_jsonl_path` 读取 JSONL
- **AND** Agent0 不调用 Crawl4AI 深度爬取
- **AND** Agent0 不读取/写入 DocumentCache
- **AND** 运行日志包含本地库路径、加载条数、拼接后的上下文长度

#### 场景：本地文档库缺失或不可读
- **WHEN** `docs.source=local_jsonl` 但文件缺失/不可读/解析失败
- **THEN** 系统立刻失败并抛出清晰错误（Fail Fast）

### Requirement: v2.6.x 版本过滤
系统 SHALL 从本地文档库中过滤掉明显不属于 v2.6.x 的内容，降低版本污染。

#### 场景：过滤显式非 v2.6.x 页面
- **WHEN** 文档条目的 URL 为版本化页面且版本不为 v2.6（例如 `/docs/v2.1.x/`、`/docs/v2.4.x/` 等）
- **THEN** 该条目不进入最终 docs_context

#### 场景：非文档站点内容剔除
- **WHEN** 文档条目的 URL 不在 `https://milvus.io/docs` 或 `https://milvus.io/docs/zh` 下
- **THEN** 该条目不进入最终 docs_context

## MODIFIED Requirements

### Requirement: Agent0 文档获取策略
当本地文档库模式启用时，Agent0 SHALL 优先使用本地库并禁用其他文档来源。

## REMOVED Requirements
无

