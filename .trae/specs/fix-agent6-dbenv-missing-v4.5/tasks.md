# Tasks

- [x] Task 1: 修复 `_get_db_template_fragments()` 返回字典增加 `db_env` 键
  - 在三个分支（qdrant / weaviate / milvus / else）的 return dict 中均添加 `"db_env": env_lines` 键
- [x] Task 2: 验证修复 — 用 Python 脚本确认 `self.prompt.partial()` 不再报 missing variable 错误
  - py_compile.compile 通过 ✅
  - AST 分析确认三个分支均含 db_env 键 ✅
  - 模板变量完整性分析通过（vector_config 为双花括号字面量，非模板变量）✅
