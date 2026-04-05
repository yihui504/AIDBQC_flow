# AI-DB-QC 实战评估 v3.7.0 - 验证清单

## 运行执行
- [x] 项目成功启动，无导入错误或配置错误
- [x] 所有智能体按预定顺序执行（agent0 → agent1 → agent2 → agent3 → reranker → agent4 → agent5 → coverage_monitor × 3轮）
- [ ] 运行正常结束（completion 或受控终止），无未捕获异常导致崩溃
  - **实际**：⚠️ agent6_verifier 因 400 Bad Request 崩溃，非受控终止
- [x] 控制台输出完整可读，包含各节点的关键信息（telemetry.jsonl 70 条事件）

## 本地文档库使用
- [x] LocalDocsLibrary 成功加载 milvus_io_docs_depth3.jsonl
- [x] 日志显示文档加载统计（docs_context = 6,939,985 字符）
- [x] docs_context 正确写入 state.db_config（非空、非截断）
- [x] raw_docs.json 在运行目录中保存了完整文档快照（~10MB）

## 过程行为监视
- [x] 每个 agent 节点有明确的进入/退出日志（telemetry END 事件）
- [x] telemetry.jsonl 在运行期间有新数据写入（42 条 run_5af0cc02 事件）
- [x] Token 消耗被正确追踪和记录（~69,092 tokens）
- [x] 异常情况有清晰记录（400 Bad Request at agent6）

## 产出文件完整性
- [x] 新运行目录 run_5af0cc02 在 .trae/runs/ 下创建
- [x] state.json.gz 存在且可成功解压（compression_ratio = 83.97%）
- [x] metadata.json 存在且包含 version/compression_ratio/timestamp/run_id/hash 等字段
- [x] telemetry.jsonl 包含本次运行的事件记录（42 条新事件）
- [x] raw_docs.json 存在且包含完整文档内容（~10MB）
- [x] docker-compose.yml 存在

## 缺陷报告质量（核心验证项）
- [x] defect_reports 列表非空（12 条缺陷）
- [x] 每条 defect_report 有完整关键字段（case_id, bug_type, root_cause_analysis, evidence_level, verification_status, verifier_verdict）— 100% 覆盖
- [ ] verified_defects 字段非 None，数量与 reproduced_bug=True 的缺陷数一致
  - **实际**：verified_defects = 0（因 agent6 未执行），与 reproduced_bug=False 一致
- [ ] verdict 分布合理（有 reproduced_bug 则必须有 expected_rejection/invalid_mre/inconclusive 等其他类别）
  - **实际**：100% pending — 不合理，但原因是 agent6 未执行而非逻辑错误
- [ ] false_positive 仅用于 expected_rejection 或"未复现"的情况，不滥用
  - **实际**：N/A — 无任何 verdict 判定
- [ ] verification_log 内容与 verifier_verdict 无矛盾
  - **实际**：N/A — 全部 pending
- [ ] 误报率数值已计算（false_positive / total）
  - **实际**：无法计算 — 全部 pending

## GitHub Issue 质量（如有生成）
- [x] Issue 文件存在且格式为 .md
  - **实际**：✅ 12 个 GitHub_Issue_TC_*.md 文件已生成（2026-04-04 补生成）
- [x] Issue 包含完整模板结构
  - **实际**：✅ 12/12 包含 Environment/Describe bug/Steps To Reproduce/Expected-Actual/Evidence
- [x] MRE 代码语法正确，逻辑合理
  - **实际**：✅ 语法正确、逻辑完整，可执行（评分 4/5）
- [ ] MRE 使用真实语义向量
  - **实际**：❌ 0/12 使用真实 embedding（全部为占位符：uniform fill / random / hand-crafted）
- [ ] Evidence 部分的引用可在 milvus_io_docs_depth3.jsonl 中找到对应原文
  - **实际**：❌ 0/12 有文档 URL 引用（Reference URL 全部为 N/A）
- [x] Issue 标题简洁准确
  - **实际**：✅ 标题清晰，包含 bug type 和核心问题描述
- [x] 每个 Issue 已给出质量评分
  - **实际**：✅ 逐条评分完成，加权均分 **3.03/5**

## 遥测与性能
- [x] telemetry.jsonl 包含 pipeline START 事件
- [x] 各 agent 节点的执行事件都被记录（agent0-agent5 + coverage_monitor + web_search）
- [x] Token 消耗数据合理（~69K tokens for 3 iterations）
- [ ] 性能摘要显示内存/CPU 在合理范围
  - **实际**：基于历史数据参考（峰值 845MB），本次无性能快照触发

## Reflection 输出
- [ ] reflection agent 正常执行（无异常退出）
  - **实际**：❌ 未执行（依赖 agent6）
- [ ] 总结内容基于实际发现的缺陷
- [ ] 如有策略写入 KB，KB 操作无报错

## 评估报告质量
- [x] 报告完全基于实际运行数据和产出文件
- [x] 报告不回避问题，明确指出不足（docs_context=6.6MB 致命问题、Issue 零产出等）
- [x] 每个问题都有具体的证据（文件名、数据值、现象描述）
- [x] 改进建议具体可操作（文件名+方法名+做法说明）
- [x] 报告按优先级排序问题（P0 > P1 > P2），每个优先级有明确定义
- [x] 报告包含短期/中期/长期改进路线图
- [x] 报告不含谄媚性语言（评分 2.80/5.0，客观冷静）
