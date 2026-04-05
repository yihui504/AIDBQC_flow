# 修复 P0-1 并补生成 Issue - 验证清单

## Task 1：docs_context 智能截断
- [ ] `_get_relevant_docs_for_defect()` 方法已实现，接受 defect、docs_map、max_chars 参数，返回截断后的相关文档片段
- [ ] 截断后的文档片段长度不超过 max_chars（默认 8000 字符）
- [ ] 关键词提取覆盖 case_id、operation、root_cause_analysis 三个字段
- [ ] `execute()` 方法不再将完整 docs_context 放入 env_context
- [ ] `_generate_issue_for_defect()` 使用截断后的文档片段构建 input_data
- [ ] 修改后代码无语法错误，可正常 import

## Task 2：Issue 补生成脚本
- [ ] `_regenerate_issues.py` 脚本存在且可执行
- [ ] 脚本能成功加载 run_5af0cc02 的 state.json.gz（12 条缺陷）
- [ ] 脚本执行过程中无 400 Bad Request 错误
- [ ] 脚本执行过程中无其他未捕获异常
- [ ] 至少生成了 1 个 GitHub_Issue_*.md 文件
- [ ] 控制台输出包含统计信息（成功/失败数、Token 消耗）

## Task 3：Issue 质量审查
- [ ] 每个 Issue 文件为 .md 格式，非空
- [ ] Issue 包含 Environment 段（含 Milvus version、Deployment mode 等）
- [ ] Issue 包含 Describe bug 段（清晰描述问题）
- [ ] Issue 包含 Steps To Reproduce 段（含 MRE Python 代码块）
- [ ] MRE 代码使用真实语义向量数值（检查是否有 `search_vector = [0.xxxxxx, ...]` 格式的多数字列表）
- [ ] Issue 包含 Expected Behavior 和 Actual Behavior 段
- [ ] Issue 包含 Evidence & Documentation 段（含 Violated Contract Type、Reference URL 等）
- [ ] 每个 Issue 已给出质量评分

## Task 4：报告更新
- [ ] EVALUATION_REPORT.md 已追加"补充评估"章节
- [ ] 最终评分已更新（Issue/MRE 维度 > 0）
- [ ] 总结结论反映补生成结果
