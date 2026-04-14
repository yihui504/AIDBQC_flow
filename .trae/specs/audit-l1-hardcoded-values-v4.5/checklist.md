# Checklist

- [x] agent3_executor.py:104 的 severity 阈值使用 dc_obj.max 而非硬编码 32768
- [x] agent3_executor.py:121 的 severity 阈值同上
- [x] agent3_executor.py:261-262 的 container_map 已删除，替换为动态解析
- [x] agent3_executor.py:358 的 32768 已替换为动态获取 dc.max
- [x] Milvus supported_metrics 与官方文档一致（BM25 已移除，TANIMOTO 已添加）
- [x] Qdrant supported_metrics 大小写与 API 一致
- [x] Weaviate supported_metrics 与官方文档一致
- [x] Milvus max_top_k 有文档依据（标注为 operational default）
- [x] Qdrant max_top_k 有文档依据（标注为 operational default）
- [x] Weaviate max_top_k 有文档依据（标注为 operational default）
- [x] py_compile.compile(agent3_executor.py) 通过
- [x] py_compile.compile(contract_fallbacks.py) 通过
- [x] severity 动态化断言测试通过（Qdrant dim=40000 → soft, dim=70000 → hard, dim=32768 → soft）
