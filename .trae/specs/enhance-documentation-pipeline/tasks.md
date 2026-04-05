# 任务列表

- [x] 任务 1：增强文档爬取与快照保全
  - [x] 子任务 1.1：修改 `agent0_env_recon.py`，增加搜索结果数至 5，并实现官方域名过滤。
  - [x] 子任务 1.2：重构 `scrape_url` 函数，移除 3000 字符截断，增加 HTML 清洗（去除 nav/footer/script）。
  - [x] 子任务 1.3：实现全量文档原子化落盘至 `raw_docs.json`。
- [x] 任务 2：实现结构化文档解析
  - [x] 子任务 2.1：创建 `src/parsers/doc_parser.py`，实现基于正则的 API 参数提取。
  - [x] 子任务 2.2：在 `agent1_contract_analyst.py` 中集成解析器，将结构化上下文注入 LLM Prompt。
- [x] 任务 3：升级 RAG 知识库
  - [x] 子任务 3.1：重写 `src/knowledge_base.py`，实现 document chunking (500 字符重叠分片)。
  - [x] 子任务 3.2：实现基于技术关键词的内存索引，支持语义+关键词的混合搜索。
- [x] 任务 4：实现引用相关性验证
  - [x] 子任务 4.1：创建 `src/validators/reference_validator.py`，使用 `sentence-transformers` 计算相似度。
  - [x] 子任务 4.2：在 `agent6_verifier.py` 中集成验证器，过滤评分低于 0.65 的引用。
- [x] 任务 5：全量回归测试与性能评估
  - [x] 子任务 5.1：编写 `tests/test_documentation_enhancement.py` 进行单元测试。
  - [x] 子任务 5.2：运行 10 轮压测，验证 Issue 中复现代码和文档引用的准确性。

# 任务依赖
- [任务 2] 依赖于 [任务 1] 产出的原始文档数据。
- [任务 4] 依赖于 [任务 3] 的向量化能力升级。
