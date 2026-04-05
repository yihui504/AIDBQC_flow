# Tasks

- [ ] Task 1：新增配置项以启用本地文档库模式
  - [ ] 1.1：在 `src/config.py` 支持读取 `docs.source`、`docs.local_jsonl_path`
  - [ ] 1.2：在 `.trae/config.yaml` 增加示例配置（默认关闭，不影响既有流程）

- [ ] Task 2：实现本地 JSONL 文档库加载与过滤
  - [ ] 2.1：实现 JSONL 流式读取（避免一次性读入超大文件）
  - [ ] 2.2：实现过滤规则（仅保留 docs/zh + 剔除显式非 v2.6.x 版本化页面）
  - [ ] 2.3：构造 `docs_context`（按 URL 分段拼接，包含来源 URL）
  - [ ] 2.4：输出可观测日志（加载条数、丢弃条数、最终字符数）

- [ ] Task 3：改造 Agent0 文档获取入口（禁用缓存与自动爬取）
  - [ ] 3.1：在 `agent0_env_recon.py` 中当 `docs.source=local_jsonl` 时走本地库分支
  - [ ] 3.2：确保该分支不调用 DocumentCache / DeepCrawler
  - [ ] 3.3：失败语义：文件缺失/解析失败直接抛错

- [ ] Task 4：集成回归验证（项目实战跑一轮）
  - [ ] 4.1：运行主流程（max_iterations=3），确认 Agent0 日志显示“使用本地文档库”
  - [ ] 4.2：确认未出现 Crawl4AI 爬取日志、未写入 DocumentCache
  - [ ] 4.3：输出统计：契约抽取 tokens、缺陷 verdict 分布、Issue 数

# Task Dependencies
- Task 3 depends on Task 1, Task 2
- Task 4 depends on Task 3

