# 实战运行 6 轮完整流程 - 验证清单

## Task 1：虚拟环境
- [x] 项目已有 `venv/` 目录（Python 3.11.9）
- [x] 关键模块导入测试通过（langchain, langgraph, sentence_transformers, pymilvus, torch）

## Task 2：配置验证
- [x] `max_iterations: 6` 在 config.yaml 中设置正确
- [x] `docs.source: "local_jsonl"` 配置正确
- [x] 本地文档文件 `milvus_io_docs_depth3.jsonl` 存在且可读
- [x] API 环境变量配置正确（ANTHROPIC_BASE_URL 指向 codingplan 端点）

## Task 3-5：运行验证
- [x] Agent0 环境侦察成功执行
- [x] Agent1 场景分析成功执行
- [x] Agent2 测试生成成功执行
- [x] Agent3 执行门控成功执行
- [x] Agent4 执行器成功执行
- [x] Agent5 验证器成功执行
- [x] Agent6 Issue 生成成功执行
- [x] 6 轮迭代全部完成
- [x] 无未处理的异常（exit_code=0）

## Task 6：产出验证
- [x] 生成 **8 个 GitHub Issue 文件**（超过 6 个目标）
- [x] Issue 模板完整（Description/MRE/Expected/Actual/Evidence）
- [x] state.json.gz 状态文件存在且可解压（压缩率 84.56%）
- [x] 运行时间 1791.4 秒（约 30 分钟）
- [x] 内存峰值 1307.8MB，CPU 峰值 2676.2%
