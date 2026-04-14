# Tasks

## [x] Task 1：重构 Agent6 Verifier 为多数据库模板适配
- **优先级**：P0
- **子任务**：
  - [x] 1.1：在 agent6_verifier.py 中新增 `_get_db_template_fragments(db_name)` 方法，返回 milvus/qdrant/weaviate 三套模板片段（含 SDK名、MRE 连接代码、Environment 字段）✅ L290-L309
  - [x] 1.2：修改 `__init__` 中的 self.prompt 构建，将硬编码的 Milvus 内容替换为 `{db_label}`/`{db_env}`/`{mre_sdk_note}` 占位符 ✅ L313/L332/L341
  - [x] 1.3：修改 `execute()` 方法在 L1173-L1174 从 state.db_config 获取 db_name 并调用 `_get_db_template_fragments()` 存入 `self._current_db_fragments`
  - [x] 1.4：修改 `_generate_issue_for_defect()` 在 L1068 通过 `**self._current_db_fragments` 将模板片段 partial 注入 chain
  - [x] 1.5：确保 db_name 为空或未知时回退到 milvus 模板（向后兼容）✅ else 分支 L304-L309

## [x] Task 2：验证修复效果
- **优先级**：P0
- **依赖**：Task 1
- **子任务**：
  - [x] 2.1：检查修改后的 agent6_verifier.py 不再包含硬编码 "Milvus"/"pymilvus"/"localhost:19530"（仅 _get_db_template_fragments 的 milvus 分支内允许）✅ grep 确认仅 L307-308 在方法内部
  - [x] 2.2：确认三套模板（milvus/qdrant/weaviate）的 MRE 代码语法正确且符合各 SDK 实际 API ✅

# Task Dependencies
- [Task 2] depends on [Task 1]
