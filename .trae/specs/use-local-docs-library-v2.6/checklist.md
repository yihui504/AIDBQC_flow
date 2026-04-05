# Checklist

- [ ] 配置项可用：`docs.source=local_jsonl` 与 `docs.local_jsonl_path` 可被正确读取
- [ ] Agent0 使用本地库：日志明确显示本地库路径、加载条数与最终上下文长度
- [ ] 自动爬取被禁用：运行过程中不出现 Crawl4AI DeepCrawler 相关日志/调用
- [ ] 原有文档缓存被禁用：运行过程中不读取/写入 DocumentCache
- [ ] v2.6.x 过滤生效：显式 `/docs/v2.1.x/`、`/docs/v2.4.x/`、`/docs/v2.5.x/` 等不进入 docs_context
- [ ] 项目实战跑通：max_iterations=3 完整运行结束，且产出 defect verdict 分布与 Issue 数符合预期

