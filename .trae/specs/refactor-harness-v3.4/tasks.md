# 任务列表

- [x] 任务 1：重构 MRE 验证网关逻辑
  - [x] 子任务 1.1：修改 `src/agents/agent6_verifier.py` 中的 `_verify_mre` 函数。
  - [x] 子任务 1.2：引入对 `SyntaxError`, `IndentationError`, `NameError` 等常见生成错误的专门拦截。
  - [x] 子任务 1.3：只有当报错信息包含具体的 Milvus 逻辑异常且 MRE 逻辑结构完整时，才标记为 `success`。
- [x] 任务 2：实现爬虫自适应回退机制
  - [x] 子任务 2.1：修改 `src/agents/agent0_env_recon.py` 中的 `_fetch_documentation`。
  - [x] 子任务 2.2：增加二级搜索策略：如果官方 URL 过滤后为空，触发 `search_tool.invoke` 使用更宽泛的关键词。
  - [x] 子任务 2.3：放宽 `_is_official_docs_url` 或增加 `allow_fallback` 标志。
- [x] 任务 3：清洗测试语料库
  - [x] 子任务 3.1：修改 `src/data_generator.py` 中的 `ControlledDataGenerator` 类。
  - [x] 子任务 3.2：移除所有硬编码的业务背景描述文本（如关于“building an e-commerce...”的内容）。
  - [x] 子任务 3.3：确保生成的文本仅包含商品名称、属性及相关的领域描述。
- [x] 任务 4：实战验证与回归
  - [x] 子任务 4.1：运行全流程测试，检查 `raw_docs.json` 是否包含回退后的文档。
  - [x] 子任务 4.2：审计 Issue 目录，验证是否还有“由于 MRE 代码写错而误判为成功”的现象。

# 任务依赖
- [任务 4] 依赖于 [任务 1, 2, 3] 的完成。
