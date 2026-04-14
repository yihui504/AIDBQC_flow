# Checklist

- [x] _get_db_template_fragments() 的 qdrant 分支返回字典含 `db_env` 键
- [x] _get_db_template_fragments() 的 weaviate 分支返回字典含 `db_env` 键
- [x] _get_db_template_fragments() 的 milvus(else) 分支返回字典含 `db_env` 键
- [x] self.prompt.partial(**self._current_db_fragments) 调用不再因缺少 db_env 抛出异常
- [x] py_compile.compile(agent6_verifier.py) 通过，无语法错误
