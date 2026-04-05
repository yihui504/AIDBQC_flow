# AI-DB-QC 实战评估 v3.7.0 - 任务列表

## [x] 任务 1：执行完整项目实战运行
- **优先级**：P0
- **依赖**：None
- **状态**：✅ 已完成（run_5af0cc02，2026-04-04 10:00~10:12 UTC+8）
- **子任务**：
  - [x] 1.1：确认环境就绪（venv 激活、依赖安装、API Key 配置、milvus_io_docs_depth3.jsonl 存在）
  - [x] 1.2：执行 `python main.py` 并全程捕获输出（实际运行 ~11.5 分钟）
  - [x] 1.3：记录运行过程中的关键事件（每个 agent 的进入/退出/耗时/状态）
  - [x] 1.4：识别运行中的任何异常、错误或非预期行为（400 Bad Request at agent6）

## [x] 任务 2：分析运行日志和行为
- **优先级**：P0
- **依赖**：任务 1
- **状态**：✅ 已完成
- **子任务**：
  - [x] 2.1：解析控制台输出，提取每个节点的执行记录（telemetry.jsonl 70 条事件）
  - [x] 2.2：统计各阶段耗时（agent0:8s, agent1:56s, Iter0:155s, Iter1:175s, Iter2:259s）
  - [x] 2.3：统计 Token 消耗总量和各节点分布（~69,092 tokens）
  - [x] 2.4：列出所有 WARNING / ERROR 级别的日志条目（400 Bad Request at agent6）
  - [x] 2.5：提取 LocalDocsLibrary 加载统计（docs_context = 6,939,985 字符）

## [x] 任务 3：审查产出文件完整性
- **优先级**：P0
- **依赖**：任务 1
- **状态**：✅ 已完成
- **子任务**：
  - [x] 3.1：列出新运行目录的所有文件（4 个文件：state.json.gz, metadata.json, raw_docs.json, docker-compose.yml）
  - [x] 3.2：验证 state.json.gz 存在且可解压（compression_ratio = 83.97%）
  - [x] 3.3：验证 metadata.json 存在且字段完整（version/timestamp/hash/is_incremental 等）
  - [x] 3.4：验证 telemetry.jsonl 有新的事件数据写入（70 条事件含 run_5af0cc02 数据）
  - [x] 3.5：验证 raw_docs.json 存在且包含完整文档内容（~10MB 完整文档库）
  - [x] 3.6：验证 docker-compose.yml 存在

## [x] 任务 4：严格审查缺陷报告质量（核心任务）
- **优先级**：P0
- **依赖**：任务 3
- **状态**：✅ 已完成
- **关键发现**：
  - 12 条缺陷报告（21 条原始去重后）
  - 全部 verdict=pending（agent6 未执行）
  - 全部 mre_code=null（无 MRE 代码）
  - 全部 doc_references=[]（无文档引用）
  - 字段完整性 100%（case_id/bug_type/root_cause_analysis/evidence_level 均有值）
  - Bug type 分布：Type-4(58.3%) + Type-1(33.3%) + Type-2(8.3%)
- **子任务**：
  - [x] 4.1：读取 state.json.gz 中的 defect_reports 和 verified_defects（12 defects, 0 verified）
  - [x] 4.2：统计缺陷总数、verified_defects 数量、各 verdict 分布（100% pending）
  - [x] 4.3：计算关键指标（验证率=0%, 无法计算误报率等）
  - [x] 4.4：逐条检查 defect_report 字段完整性（100% 覆盖）
  - [x] 4.5：抽样检查 verification_log 与 verdict 的一致性（N/A — 全部 pending）
  - [x] 4.6：检查 verified_defects 列表与 reproduced_bug=True 数量一致性（一致：均为 0）

## [x] 任务 5：严格审查 GitHub Issue 质量（核心任务）
- **优先级**：P0
- **依赖**：任务 3
- **状态**：✅ 已完成（2026-04-04 补生成完成）
- **说明**：P0-1 修复后通过 `_regenerate_issues.py` 成功生成 12 个 Issue 文件
- **关键发现**：
  - 12/12 Issue 文件成功生成（100% 成功率）
  - 模板完整性 100%（全部包含 Environment/Describe bug/Steps To Reproduce/Expected-Actual/Evidence）
  - MRE 可运行性 4/5（语法正确、逻辑完整）
  - MRE 真实向量 0/5（全部使用占位符，未调用 EmbeddingGenerator）
  - 缺陷描述清晰度 4.5/5（场景具体、Expected/Actual 对比明确）
  - 文档引用真实性 1/5（0/12 有文档 URL 引用）
  - **Issue 加权均分：3.03/5**
  - 文件大小范围：1.9KB - 5.0KB（合理）
  - 总 Token 消耗：99,995
  - 总耗时：70.4 秒（平均每 Issue 5.9 秒）
- **子任务**：
  - [x] 5.1：读取所有 GitHub_Issue_*.md 或 issue_*.md 文件（12 个文件全部读取）
  - [x] 5.2：验证 Issue 格式包含所有必需字段（100% 符合模板）
  - [x] 5.3：提取并审查 MRE 代码（语法正确但使用占位符向量）
  - [x] 5.4：证据交叉验证（Reference URL 全部为 N/A）
  - [x] 5.5：对每个 Issue 给出质量评分（逐条评分表已完成）

## [x] 任务 6：审查遥测数据和性能指标
- **优先级**：P1
- **依赖**：任务 1
- **状态**：✅ 已完成
- **子任务**：
  - [x] 6.1：解析 telemetry.jsonl，提取完整事件序列（70 条事件，28 行 run_8b5fd707 + 42 行 run_5af0cc02）
  - [x] 6.2：验证事件序列覆盖了所有执行的节点（覆盖 agent0→agent5 + coverage_monitor + web_search；缺 agent6/reflection）
  - [x] 6.3：检查是否有 performance_monitor 数据（存在快照机制，本次未触发阈值告警）
  - [x] 6.4：评估内存/CPU 使用是否在合理范围（基于历史数据：峰值 845MB，均值 413MB）

## [x] 任务 7：生成客观评估报告
- **优先级**：P0
- **依赖**：任务 2-6 全部完成
- **状态**：✅ 已完成
- **产出**：`.trae/specs/live-evaluation-v3.7.0/EVALUATION_REPORT.md`（最终版，469 行）
- **评分结论**：**2.80 / 5.0**
- **核心发现**：docs_context=6.6MB 导致 agent6 400 Bad Request 是唯一阻塞性问题
- **子任务**：
  - [x] 7.1：汇总运行概况
  - [x] 7.2：汇总流程完整性评估
  - [x] 7.3：汇总产出质量评估
  - [x] 7.4：缺陷验证一致性专项分析（结果：无法检验，全部 pending）
  - [x] 7.5：列出核心问题清单（P0×2, P1×4, P2×3）
  - [x] 7.6：撰写与前次运行的对比分析（三次运行全面对比）
  - [x] 7.7：提供改进建议（紧急/短期/中期/长期 四档）
  - [x] 7.8：将最终报告写入 EVALUATION_REPORT.md

# 任务依赖关系
- 任务 2、3、6 并行依赖任务 1 ✅
- 任务 4、5 依赖任务 3 ✅
- 任务 7 依赖任务 2-6 全部完成 ✅

# 关键配置参数（当前值）
- `max_iterations`: 3（config.yaml） ✅ 全部完成
- `docs.source`: "local_jsonl"（不爬取，用本地文档库）
- `cache.enabled`: false
- `docker_pool.enabled`: false
- `logging.async`: false
- `isolated_mre.enabled`: false
- `rate_limiting.enabled`: true（max 5 req/min）

# 注意事项
- 用户已配置网络代理，LLM 调用（ZhipuAI/GLM-4）和 web_search 正常工作
- 运行时间 ~11.5 分钟（3 轮迭代全部完成）
- 本次评估的核心价值在于"严格审查"而非"跑通即可"
- **待解决 P0**：docs_context 过大（6.6MB）导致 agent6 400 Bad Request
